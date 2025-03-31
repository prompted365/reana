"""
Rollout API Client

This module provides a client for interacting with the Rollout API and the Rollout MCP server
for CRM integrations.
"""

import aiohttp
import json
import logging
import asyncio
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from ..utils.rollout_auth import generate_rollout_jwt, get_rollout_api_url
from ..utils.monitoring import ApiMetricsContext, api_monitor
from ..utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError

# Configure logging
logger = logging.getLogger(__name__)

# MCP server ID for Rollout integration
ROLLOUT_MCP_SERVER_ID = "e552bffb-b799-4965-9e60-a2bfa664af91"

# Error retry configuration
MAX_RETRIES = 5
BASE_BACKOFF = 1  # seconds
MAX_BACKOFF = 32  # seconds
RATE_LIMIT_RESET_DELAY = 60  # seconds

# Error types
class RolloutError(Exception):
    """Base exception for Rollout API errors"""
    pass

class RolloutAuthError(RolloutError):
    """Authentication error with Rollout API"""
    pass

class RolloutRateLimitError(RolloutError):
    """Rate limit exceeded error"""
    pass

class RolloutServerError(RolloutError):
    """Rollout server-side error"""
    pass

class RolloutCircuitOpenError(RolloutError):
    """Error raised when circuit breaker is open"""
    pass


class RolloutClient:
    """Client for interacting with Rollout API and MCP server"""
    
    def __init__(self):
        """Initialize the Rollout API client"""
        self.session = None
        self.jwt_token = generate_rollout_jwt()
        self.token_expiry = datetime.utcnow() + timedelta(minutes=55)  # Set expiry 5 minutes before actual expiration
        self.requests_since_last_reset = 0
        self.rate_limit_remaining = 100  # Default assumption, will be updated based on API responses
        
        # Create circuit breakers for API and MCP calls
        self.api_circuit = CircuitBreaker(
            name="rollout-api",
            failure_threshold=3,
            recovery_timeout=60,  # 1 minute recovery time
            excluded_exceptions=[RolloutRateLimitError]  # Don't count rate limits as circuit failures
        )
        self.mcp_circuit = CircuitBreaker(name="rollout-mcp", failure_threshold=5, recovery_timeout=120)
        
    def refresh_jwt(self):
        """Generate a fresh JWT token for API authentication"""
        self.jwt_token = generate_rollout_jwt()
        self.token_expiry = datetime.utcnow() + timedelta(minutes=55)  # Set expiry 5 minutes before actual expiration
        logger.info("JWT token refreshed, new expiry: %s", self.token_expiry)
        
    async def ensure_session(self):
        """Ensure an aiohttp session exists"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            
    async def close(self):
        """Close the aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _check_token_expiry(self):
        """Check if token is expired or close to expiry and refresh if needed"""
        if datetime.utcnow() >= self.token_expiry:
            logger.info("JWT token expired or close to expiry, refreshing")
            self.refresh_jwt()

    async def _handle_rate_limiting(self, response=None):
        """
        Handle rate limiting by tracking request counts and respecting limits

        Args:
            response: API response to extract rate limit headers from
        """
        endpoint = "rollout-api"  # Default endpoint name when not specified
        # Update rate limit tracking if headers are available
        if response and 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
            
            # Record rate limit information in monitoring system
            if 'X-RateLimit-Limit' in response.headers and 'X-RateLimit-Reset' in response.headers:
                reset_seconds = int(response.headers.get('X-RateLimit-Reset', RATE_LIMIT_RESET_DELAY))
                reset_time = datetime.utcnow() + timedelta(seconds=reset_seconds)
                api_monitor.record_rate_limit(
                    endpoint=endpoint,
                    limit=int(response.headers.get('X-RateLimit-Limit')),
                    remaining=self.rate_limit_remaining,
                    reset_time=reset_time
                )
            
        # If we're at or close to the rate limit, pause execution
        if self.rate_limit_remaining <= 5:
            reset_time = int(response.headers.get('X-RateLimit-Reset', RATE_LIMIT_RESET_DELAY))
            logger.warning(f"Rate limit close to exceeded, pausing for {reset_time} seconds")
            await asyncio.sleep(reset_time)
            
    def _get_retry_delay(self, retry_count):
        """
        Calculate exponential backoff delay with jitter
        
        Args:
            retry_count: Current retry attempt number
            
        Returns:
            float: Delay in seconds before next retry
        """
        # Exponential backoff with full jitter
        delay = min(MAX_BACKOFF, BASE_BACKOFF * (2 ** retry_count))
        jitter = random.uniform(0, delay)
        return jitter
            
    async def call_api(self,
                      endpoint: str,
                      method: str = "GET",
                      data: Optional[Dict] = None,
                      retry_count: int = 0) -> Dict:
        """
        Make an authenticated request to the Rollout API
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, etc.)
            data: Request data for POST/PUT methods
            retry_count: Current retry attempt (used internally for recursion)
            
        Returns:
            Dict: API response data
            
        Raises:
            RolloutAuthError: When authentication fails
            RolloutRateLimitError: When rate limits are exceeded
            RolloutServerError: When server errors occur
            RolloutError: For other API errors
        """
        # Use context manager to track API metrics
        with ApiMetricsContext(endpoint) as metrics:
            try:
                await self.ensure_session()
                await self._check_token_expiry()

                # Check if circuit is open
                try:
                    if not await self.api_circuit.allow_request():
                        logger.warning(f"Circuit breaker for Rollout API is open, blocking request to {endpoint}")
                        raise RolloutCircuitOpenError(
                            f"Rollout API circuit breaker is open. Too many failures recently. "
                            f"Please try again later or contact support if this persists."
                        )
                except CircuitBreakerOpenError as e:
                    logger.warning(f"Circuit breaker blocked API call to {endpoint}: {str(e)}")
                    raise RolloutCircuitOpenError(str(e))
                
                url = get_rollout_api_url(endpoint)
                headers = {
                    "Authorization": f"Bearer {self.jwt_token}",
                    "Content-Type": "application/json"
                }

                # Log request information at debug level
                logger.debug(f"Making {method} request to {url}")
                
                try:
                    async with self.session.request(
                        method, url, headers=headers, json=data, timeout=30
                    ) as response:
                        # Check rate limits
                        await self._handle_rate_limiting(response)
                        
                        # Handle different response statuses
                        if response.status == 200 or response.status == 201:
                            # Record success in circuit breaker
                            await self.api_circuit.record_success()
                            metrics.set_success(True)
                            return await response.json()
                        
                        elif response.status == 401 or response.status == 403:
                            # Don't record auth failures in circuit breaker yet - we'll retry once
                            # Only if retry fails do we consider it a failure
                            # Authentication issue - refresh token and retry once
                            error_text = await response.text()
                            logger.warning(f"Authentication error: {error_text}. Refreshing token and retrying.")
                            self.refresh_jwt()
                            
                            if retry_count == 0:  # Only retry auth errors once
                                return await self.call_api(endpoint, method, data, 1)
                            else:
                                error = RolloutAuthError(f"Authentication failed after token refresh: {error_text}")
                                await self.api_circuit.record_failure(error)
                                metrics.set_success(False)
                                raise error
                        
                        elif response.status == 429:
                            # Rate limit exceeded
                            error_text = await response.text()
                            reset_time = int(response.headers.get('X-RateLimit-Reset', RATE_LIMIT_RESET_DELAY))
                            logger.warning(f"Rate limit exceeded: {error_text}. Resetting in {reset_time} seconds.")
                            
                            if retry_count < MAX_RETRIES:
                                # Wait for the reset time plus some jitter
                                await asyncio.sleep(reset_time + random.uniform(0, 5))
                                metrics.set_retries(retry_count + 1)
                                return await self.call_api(endpoint, method, data, retry_count + 1)
                            else:
                                error = RolloutRateLimitError(f"Rate limit exceeded after {MAX_RETRIES} retries: {error_text}")
                                # We don't record rate limit errors in circuit breaker as they're expected and handled separately
                                metrics.set_success(False)
                                raise error
                        
                        elif 500 <= response.status < 600:
                            # Server error - retryable
                            error_text = await response.text()
                            logger.warning(f"Rollout server error ({response.status}): {error_text}")
                            
                            if retry_count < MAX_RETRIES:
                                # Exponential backoff with jitter
                                delay = self._get_retry_delay(retry_count)
                                logger.info(f"Retrying in {delay:.2f} seconds (attempt {retry_count+1}/{MAX_RETRIES})")
                                await asyncio.sleep(delay)
                                metrics.set_retries(retry_count + 1)
                                return await self.call_api(endpoint, method, data, retry_count + 1)
                            else:
                                error = RolloutServerError(f"Server error after {MAX_RETRIES} retries: {error_text}")
                                await self.api_circuit.record_failure(error)
                                metrics.set_success(False)
                                raise error
                        
                        else:
                            # Other client errors - generally not retryable
                            try:
                                error_text = await response.text()
                                error_data = json.loads(error_text) if error_text else {}
                                error_message = error_data.get('message', error_text)
                                logger.error(f"Rollout API error ({response.status}): {error_message}")
                                error = RolloutError(f"API error: {error_message}")
                                await self.api_circuit.record_failure(error)
                                metrics.set_success(False)
                                raise error
                            except json.JSONDecodeError:
                                logger.error(f"Rollout API error ({response.status}): {error_text}")
                                metrics.set_success(False)
                                raise RolloutError(f"API error ({response.status}): {error_text}")
                                
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"Network error calling Rollout API: {str(e)}")
                    
                    if retry_count < MAX_RETRIES:
                        # Retry network errors with backoff
                        delay = self._get_retry_delay(retry_count)
                        logger.info(f"Retrying in {delay:.2f} seconds (attempt {retry_count+1}/{MAX_RETRIES})")
                        await asyncio.sleep(delay)
                        metrics.set_retries(retry_count + 1)
                        return await self.call_api(endpoint, method, data, retry_count + 1)
                    else:
                        logger.error(f"Failed to call Rollout API after {MAX_RETRIES} retries: {str(e)}")
                        error = RolloutError(f"Network error after {MAX_RETRIES} retries: {str(e)}")
                        await self.api_circuit.record_failure(error)
                        metrics.set_success(False)
                        raise error
            except Exception:
                metrics.set_success(False)
                raise
                
    async def call_mcp_tool(self, tool_name: str, arguments: Dict) -> Dict:
        """
        Call a tool on the Rollout MCP server
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Dict: Tool response data
        """
        # In a real implementation, you would have an MCP client library
        # For now, we'll simulate it with a direct API call to an MCP endpoint
        # Use context manager to track MCP tool metrics
        with ApiMetricsContext(f"mcp:{tool_name}") as metrics:
            try:
                # Check if circuit is open
                try:
                    if not await self.mcp_circuit.allow_request():
                        logger.warning(f"Circuit breaker for Rollout MCP is open, blocking call to {tool_name}")
                        raise RolloutCircuitOpenError(
                            f"Rollout MCP circuit breaker is open. Too many failures recently. "
                            f"Please try again later or contact support if this persists."
                        )
                except CircuitBreakerOpenError as e:
                    logger.warning(f"Circuit breaker blocked MCP call to {tool_name}: {str(e)}")
                    metrics.set_success(False)
                    raise RolloutCircuitOpenError(str(e))
                    
                logger.info(f"Calling MCP tool {tool_name} with arguments: {json.dumps(arguments)[:100]}...")
                
                # Retry logic for MCP tool calls
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        # This is a placeholder implementation - in practice you would use your MCP client
                        # to connect to the MCP server and call the tool
                        if tool_name == "configure_rollout":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {"status": "success", "message": "Rollout configured successfully"}
                        elif tool_name == "list_available_crms":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {
                                "status": "success",
                                "crms": [
                                    {"key": "hubspot", "name": "HubSpot"},
                                    {"key": "salesforce", "name": "Salesforce"},
                                    {"key": "zoho-crm", "name": "Zoho CRM"},
                                    {"key": "pipedrive", "name": "Pipedrive"},
                                    {"key": "gohighlevel", "name": "GoHighLevel"}
                                ]
                            }
                        elif tool_name == "configure_crm_connection":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {"status": "success", "message": f"Connected to {arguments.get('crmType')} CRM"}
                        elif tool_name == "sync_tour_data":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {"status": "success", "message": "Tour data synced successfully"}
                        elif tool_name == "sync_feedback_data":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {"status": "success", "message": "Feedback data synced successfully"}
                        elif tool_name == "create_automation":
                            await self.mcp_circuit.record_success()
                            metrics.set_success(True)
                            return {"status": "success", "message": "Automation created successfully", "id": "auto-123"}
                        else:
                            raise ValueError(f"Unknown MCP tool: {tool_name}")

                    except Exception as e:
                        if attempt < MAX_RETRIES:
                            # Calculate backoff with jitter
                            delay = self._get_retry_delay(attempt)
                            logger.warning(
                                f"Error calling MCP tool {tool_name}: {str(e)}. "
                                f"Retrying in {delay:.2f} seconds (attempt {attempt+1}/{MAX_RETRIES})"
                            )
                            await asyncio.sleep(delay)
                            metrics.set_retries(attempt + 1)
                        else:
                            logger.error(f"Failed to call MCP tool {tool_name} after {MAX_RETRIES} retries: {str(e)}")
                            await self.mcp_circuit.record_failure(e)
                            metrics.set_success(False)
                            raise

            except Exception as e:
                logger.error(f"Error in call_mcp_tool for {tool_name}: {str(e)}")
                await self.mcp_circuit.record_failure(e)
                metrics.set_success(False)
                raise
    
    # Higher-level methods for specific use cases
    
    async def get_available_connectors(self) -> Dict:
        """
        Get available connectors from Rollout
        
        Returns:
            Dict: Available connectors data
        """
        try:
            return await self.call_api("/connectors/")
        except Exception as e:
            logger.error(f"Error getting available connectors: {str(e)}")
            # Return empty dict instead of failing completely
            return {}
    
    async def get_connector_details(self, connector_key: str) -> Dict:
        """
        Get details for a specific connector
        
        Args:
            connector_key: Key of the connector to get details for
            
        Returns:
            Dict: Connector details
        """
        try:
            endpoint = f"/connectors/{connector_key}"
            return await self.call_api(endpoint)
        except Exception as e:
            logger.error(f"Error getting connector details for {connector_key}: {str(e)}")
            # Return empty dict instead of failing completely
            return {}
    
    async def get_automation_runs(self, limit: int = 10) -> List[Dict]:
        """
        Get available connectors from Rollout
        
        Returns:
            Dict: Available connectors data
        """
        return await self.call_api("/connectors/")

    async def get_automation_status(self, automation_id: str) -> Dict:
        """Get the status of a specific automation"""
        endpoint = f"/automations/{automation_id}"
        return await self.call_api(endpoint)
        

    async def get_available_crms(self) -> List[Dict]:
        """
        Get available CRM connectors 
        
        Returns:
            List[Dict]: List of available CRM connectors
        """
        try:
            response = await self.call_mcp_tool("list_available_crms", {})
            return response.get("crms", [])
        except RolloutError as e:
            logger.error(f"Error getting available CRMs: {str(e)}", exc_info=True)
            return [{"key": "error", "name": "Error loading CRMs"}]
    
    async def configure_crm(self, crm_type: str, credential_key: str) -> Dict:
        """
        Configure a connection to a specific CRM
        
        Args:
            crm_type: Type of CRM (e.g., 'hubspot', 'salesforce')
            credential_key: Credential key from Rollout
            
        Returns:
            Dict: Configuration result
        """
        arguments = {
            "crmType": crm_type,
            "credentialKey": credential_key
        }
        return await self.call_mcp_tool("configure_crm_connection", arguments)
        
    async def test_crm_connection(self, crm_type: str, credential_key: str) -> Dict:
        """
        Test a connection to a specific CRM
        
        Args:
            crm_type: Type of CRM (e.g., 'hubspot', 'salesforce')
            credential_key: Credential key from Rollout
        """
        arguments = {
            "crmType": crm_type,
            "credentialKey": credential_key
        }
        return await self.call_mcp_tool("test_crm_connection", arguments)
    
    async def sync_tour(self, tour_id: str, agent_id: str, 
                        properties: List[Dict], crm_type: str = "all") -> Dict:
        """
        Sync a tour schedule to CRM systems
        
        Args:
            tour_id: Tour identifier
            agent_id: Agent identifier
            properties: List of property details (address, time, property_id)
            crm_type: CRM to sync with (or 'all' for all CRMs)
            
        Returns:
            Dict: Sync result
        """
        arguments = {
            "tourData": {
                "tourId": tour_id,
                "agentId": agent_id,
                "properties": properties
            },
            "crmType": crm_type
        }
        return await self.call_mcp_tool("sync_tour_data", arguments)
    
    async def sync_feedback(self, property_id: str, tour_id: str, 
                           feedback: str, buyer_id: Optional[str] = None, 
                           timestamp: Optional[str] = None, 
                           crm_type: str = "all") -> Dict:
        """
        Sync property feedback to CRM systems
        
        Args:
            property_id: Property identifier
            tour_id: Tour identifier
            feedback: Feedback text
            buyer_id: Buyer identifier (optional)
            timestamp: Feedback timestamp (optional)
            crm_type: CRM to sync with (or 'all' for all CRMs)
            
        Returns:
            Dict: Sync result
        """
        feedback_data = {
            "propertyId": property_id,
            "tourId": tour_id,
            "feedback": feedback
        }
        
        if buyer_id:
            feedback_data["buyerId"] = buyer_id
            
        if timestamp:
            feedback_data["timestamp"] = timestamp
            
        arguments = {
            "feedbackData": feedback_data,
            "crmType": crm_type
        }
        
        return await self.call_mcp_tool("sync_feedback_data", arguments)
    
    async def create_custom_automation(self, name: str, 
                                      trigger: Dict, 
                                      action: Dict) -> Dict:
        """
        Create a custom automation in Rollout
        
        Args:
            name: Automation name
            trigger: Trigger configuration
            action: Action configuration
            
        Returns:
            Dict: Automation creation result
        """
        arguments = {
            "name": name,
            "trigger": trigger,
            "action": action
        }
        return await self.call_mcp_tool("create_automation", arguments)


# Singleton instance for easy import throughout the app
rollout_client = RolloutClient()