#!/usr/bin/env python
"""
Test Script for Rollout Integration

This script demonstrates the error handling and retry logic in the
Rollout integration, along with credential management.
"""

import asyncio
import logging
import sys
import os
import json
from datetime import datetime
import argparse

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import project modules
from app.services.rollout_client import rollout_client, RolloutError, RolloutRateLimitError
from app.utils.credential_store import credential_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("rollout-test")

async def test_connection():
    """Test connection to Rollout API"""
    logger.info("Testing connection to Rollout API...")
    
    try:
        # Get available connectors to test API connection
        connectors = await rollout_client.get_available_connectors()
        connector_count = len(connectors) if isinstance(connectors, dict) else 0
        
        logger.info(f"Connection successful! Found {connector_count} connectors")
        return True
    except RolloutError as e:
        logger.error(f"Connection test failed: {str(e)}")
        return False

async def test_crm_listing():
    """Test listing available CRMs"""
    logger.info("Testing CRM listing...")
    
    try:
        # List available CRMs
        crms = await rollout_client.get_available_crms()
        
        logger.info(f"Found {len(crms)} available CRMs:")
        for crm in crms:
            logger.info(f"  - {crm.get('name')} (key: {crm.get('key')})")
            
        return crms
    except RolloutError as e:
        logger.error(f"CRM listing failed: {str(e)}")
        return []

async def test_retry_mechanism(force_error=False):
    """Test the retry mechanism with simulated errors"""
    logger.info("Testing retry mechanism...")
    
    # If force_error is True, we'll use an invalid endpoint to trigger retries
    endpoint = "/invalid-endpoint" if force_error else "/connectors/"
    
    try:
        # Attempt to call API with retry logic
        logger.info(f"Making API call to {endpoint} with built-in retry logic")
        result = await rollout_client.call_api(endpoint)
        
        logger.info("API call successful!")
        return True
    except RolloutRateLimitError as e:
        logger.error(f"Rate limit error after retries: {str(e)}")
        return False
    except RolloutError as e:
        logger.error(f"API error after retries: {str(e)}")
        return False

async def run_tests(args):
    """Run all tests"""
    if args.store_credentials:
        # Store credentials from environment in the secure store
        # Only do this if explicitly requested
        from dotenv import load_dotenv
        from pathlib import Path
        
        # Load environment variables from config/rollout.env
        config_path = Path(__file__).parents[1] / "config" / "rollout.env"
        load_dotenv(config_path)
        
        project_key = os.getenv("ROLLOUT_PROJECT_KEY")
        client_id = os.getenv("ROLLOUT_CLIENT_ID")
        client_secret = os.getenv("ROLLOUT_CLIENT_SECRET")
        base_url = os.getenv("ROLLOUT_BASE_URL")
        
        if all([project_key, client_id, client_secret]):
            logger.info("Storing Rollout credentials in secure store...")
            result = credential_store.store_rollout_credentials(
                project_key=project_key,
                client_id=client_id,
                client_secret=client_secret,
                base_url=base_url
            )
            
            if result:
                logger.info("Credentials stored successfully!")
            else:
                logger.error("Failed to store credentials")
        else:
            logger.error("Missing required credentials in environment")
    
    # Test connection
    await test_connection()
    
    # Test CRM listing
    await test_crm_listing()
    
    if args.test_retry:
        # Test retry mechanism with forced error
        await test_retry_mechanism(force_error=True)
    
    # Test credential storage
    if args.check_credentials:
        creds = credential_store.get_rollout_credentials()
        if creds:
            logger.info("Successfully retrieved credentials from secure store")
            # Print partial credential info for verification
            masked_secret = "****" + creds.get("client_secret", "")[-4:] if creds.get("client_secret") else None
            logger.info(f"Project Key: {creds.get('project_key')}")
            logger.info(f"Client ID: {creds.get('client_id')}")
            logger.info(f"Client Secret: {masked_secret}")
        else:
            logger.warning("No credentials found in secure store")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test Rollout Integration")
    parser.add_argument("--store-credentials", action="store_true", help="Store credentials from environment in secure store")
    parser.add_argument("--check-credentials", action="store_true", help="Check if credentials are stored in secure store")
    parser.add_argument("--test-retry", action="store_true", help="Test retry mechanism with forced error")
    
    args = parser.parse_args()
    
    # Run the tests
    asyncio.run(run_tests(args))

if __name__ == "__main__":
    main()