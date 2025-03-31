"""
Rollout API Authentication Utilities

This module provides functions for generating JWT tokens required
for authentication with the Rollout API.
"""

import os
import time
import jwt
import json
import logging
import hashlib
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from config/rollout.env
config_path = Path(__file__).parents[2] / "config" / "rollout.env"
load_dotenv(config_path)

# Configure logging
logger = logging.getLogger(__name__)

# Get credentials from environment
ROLLOUT_PROJECT_KEY = os.getenv("ROLLOUT_PROJECT_KEY")
ROLLOUT_CLIENT_ID = os.getenv("ROLLOUT_CLIENT_ID")
ROLLOUT_CLIENT_SECRET = os.getenv("ROLLOUT_CLIENT_SECRET")
ROLLOUT_BASE_URL = os.getenv("ROLLOUT_BASE_URL")

def generate_rollout_jwt():
    """
    Generate a JWT token for Rollout API authentication
    
    Returns:
        str: JWT token for authorization header
    """
    # Check if all required credentials are present
    missing_creds = []
    if not ROLLOUT_PROJECT_KEY:
        missing_creds.append("ROLLOUT_PROJECT_KEY")
    if not ROLLOUT_CLIENT_ID:
        missing_creds.append("ROLLOUT_CLIENT_ID")
    if not ROLLOUT_CLIENT_SECRET:
        missing_creds.append("ROLLOUT_CLIENT_SECRET")
        
    if missing_creds:
        error_msg = f"Rollout credentials missing: {', '.join(missing_creds)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Create JWT payload
    now = int(time.time())
    # Add token jitter to avoid many tokens expiring simultaneously
    jitter = int(hashlib.md5(str(now).encode()).hexdigest(), 16) % 300  # Up to 5 minutes jitter
    
    payload = {
        "iss": ROLLOUT_CLIENT_ID,
        "aud": ROLLOUT_PROJECT_KEY,
        "iat": now,
        "exp": now + 3600 - jitter,  # Token valid for ~1 hour with jitter
        "jti": hashlib.md5(f"{ROLLOUT_CLIENT_ID}:{now}".encode()).hexdigest()  # Unique token ID
    }
    
    # Log token creation at debug level
    logger.debug(
        f"Generating JWT token for Rollout API. Expires in {3600-jitter} seconds."
    )
    
    try:
        # Sign the JWT with the client secret
        token = jwt.encode(
            payload, 
            ROLLOUT_CLIENT_SECRET, 
            algorithm="HS256"
        )
        
        # Return the token
        return token
    except Exception as e:
        # Log the error and raise a more informative exception
        error_msg = f"Error generating JWT token: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # OLD CODE - REPLACED WITH TRY/EXCEPT ABOVE
    # Sign the JWT with the client secret
    token = jwt.encode(
        payload, 
        ROLLOUT_CLIENT_SECRET, 
        algorithm="HS256"
    )
    
    return token
    
def get_rollout_api_url(endpoint=None):
    """
    Get the full URL for a Rollout API endpoint
    
    Args:
        endpoint (str, optional): API endpoint path
        
    Returns:
        str: Full URL for the API endpoint
    """
    base_url = ROLLOUT_BASE_URL
    
    if not base_url:
        base_url = f"https://{ROLLOUT_PROJECT_KEY}.rolloutapp.com/api"
        logger.debug(f"Using generated Rollout API base URL: {base_url}")
    
    if endpoint:
        # Remove leading slash if present
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
            
        full_url = f"{base_url}/{endpoint}"
        logger.debug(f"Generated Rollout API URL: {full_url}")
        return full_url
    
    logger.debug(f"Returning Rollout API base URL: {base_url}")
    return base_url
    
# Store a token fingerprint for detecting token refreshes
def get_token_fingerprint(token):
    """Generate a short fingerprint of the token for logging"""
    return hashlib.md5(token.encode()).hexdigest()[:8]