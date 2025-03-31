"""
Secure Credential Storage Utilities

This module provides functions for securely storing and retrieving 
credentials for external services like Rollout API.
"""

import os
import json
import base64
import logging
import hashlib
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger(__name__)

class CredentialStore:
    """
    Secure storage for API credentials and tokens
    
    Uses encryption to secure sensitive credentials in the filesystem.
    """
    
    def __init__(self, storage_dir=None, encryption_key=None):
        """
        Initialize the credential store
        
        Args:
            storage_dir: Directory to store encrypted credentials
            encryption_key: Key for encryption, or None to generate/load
        """
        # Set storage directory
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = Path(__file__).parents[2] / "config" / "credentials"
            
        # Create directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Set up encryption
        self.encryption_key = encryption_key
        
        if not self.encryption_key:
            # Try to load existing key or generate a new one
            key_path = self.storage_dir / ".key"
            if key_path.exists():
                with open(key_path, "rb") as f:
                    self.encryption_key = f.read()
            else:
                # Generate a new key
                self.encryption_key = Fernet.generate_key()
                # Save the key
                with open(key_path, "wb") as f:
                    f.write(self.encryption_key)
                
                # Set file permissions to be secure (owner read-only)
                try:
                    key_path.chmod(0o600)  # Only owner can read/write
                except Exception as e:
                    logger.warning(f"Could not set key file permissions: {str(e)}")
                    
        # Create the cipher suite
        self.cipher = Fernet(self.encryption_key)
                
    def store_credentials(self, service_name, credentials):
        """
        Store credentials for a service
        
        Args:
            service_name: Name of the service (e.g., 'rollout', 'hubspot')
            credentials: Dictionary of credentials to store
            
        Returns:
            bool: True if stored successfully
        """
        try:
            # Prepare file path for service credentials
            file_path = self.storage_dir / f"{service_name}.enc"
            
            # Serialize credentials to JSON and encrypt
            credential_json = json.dumps(credentials).encode()
            encrypted_data = self.cipher.encrypt(credential_json)
            
            # Write encrypted credentials to file
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
                
            # Set file permissions to be secure (owner read-only)
            try:
                file_path.chmod(0o600)  # Only owner can read/write
            except Exception as e:
                logger.warning(f"Could not set credential file permissions: {str(e)}")
                
            logger.info(f"Stored credentials for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error storing credentials for {service_name}: {str(e)}")
            return False
            
    def get_credentials(self, service_name):
        """
        Retrieve credentials for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            dict: Decrypted credentials, or None if not found
        """
        try:
            # Prepare file path for service credentials
            file_path = self.storage_dir / f"{service_name}.enc"
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"No stored credentials found for {service_name}")
                return None
                
            # Read and decrypt credentials
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
                
            decrypted_data = self.cipher.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            logger.debug(f"Retrieved credentials for service: {service_name}")
            return credentials
            
        except Exception as e:
            logger.error(f"Error retrieving credentials for {service_name}: {str(e)}")
            return None
            
    def remove_credentials(self, service_name):
        """
        Delete stored credentials for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            bool: True if removed successfully
        """
        try:
            # Prepare file path for service credentials
            file_path = self.storage_dir / f"{service_name}.enc"
            
            # Check if file exists
            if not file_path.exists():
                logger.warning(f"No stored credentials found for {service_name}")
                return False
                
            # Remove the file
            os.unlink(file_path)
            logger.info(f"Removed credentials for service: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing credentials for {service_name}: {str(e)}")
            return False

    def store_rollout_credentials(self, project_key, client_id, client_secret, base_url=None):
        """
        Store Rollout API credentials
        
        Args:
            project_key: Rollout project key
            client_id: Rollout client ID
            client_secret: Rollout client secret
            base_url: Optional base URL for Rollout API
            
        Returns:
            bool: True if stored successfully
        """
        credentials = {
            "project_key": project_key,
            "client_id": client_id,
            "client_secret": client_secret
        }
        
        if base_url:
            credentials["base_url"] = base_url
            
        return self.store_credentials("rollout", credentials)
        
    def get_rollout_credentials(self):
        """
        Get Rollout API credentials
        
        Returns:
            dict: Rollout credentials, or None if not found
        """
        return self.get_credentials("rollout")
        
    def store_jwt_token(self, service_name, token, expiry):
        """
        Store a JWT token with expiry time
        
        Args:
            service_name: Name of the service
            token: JWT token string
            expiry: Expiry timestamp
            
        Returns:
            bool: True if stored successfully
        """
        token_data = {
            "token": token,
            "expiry": expiry
        }
        
        return self.store_credentials(f"{service_name}_token", token_data)
        
    def get_jwt_token(self, service_name):
        """
        Get a stored JWT token with expiry time
        
        Args:
            service_name: Name of the service
            
        Returns:
            tuple: (token, expiry) or (None, None) if not found
        """
        token_data = self.get_credentials(f"{service_name}_token")
        
        if not token_data:
            return None, None
            
        return token_data.get("token"), token_data.get("expiry")

# Singleton instance for easy import throughout the app
credential_store = CredentialStore()