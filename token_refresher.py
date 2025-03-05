import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("token_refresher.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("token_refresher")

# File to store tokens
CONFIG_FILE = "config.json"

def load_tokens():
    """Load tokens from the config file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                tokens = {
                    # Only load the bearer tokens and credentials needed for refreshing
                    "bearer_token": config["Aalexhealth_token"].get("access_bearer_token"),
                    "refresh_token": config["Aalexhealth_token"].get("access_refersh_bearer_token"),
                    "expires_at": config["Aalexhealth_token"].get("token_expires_at"),
                    "client_id": config["Aalexhealth_token"].get("client_id"),
                    "client_id_secret": config["Aalexhealth_token"].get("client_id_secret")
                }
                logger.debug("Tokens loaded successfully from config.json")
                return tokens
        else:
            logger.warning(f"Config file {CONFIG_FILE} not found")
            return None
    except Exception as e:
        logger.error(f"Error loading tokens from config: {e}")
        return None

def save_tokens(tokens):
    """Save tokens to the config file, only updating the bearer tokens."""
    try:
        # Load existing config
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        else:
            config = {"Aalexhealth_token": {}}
        
        # Only update the bearer tokens and expiry time
        if "bearer_token" in tokens:
            config["Aalexhealth_token"]["access_bearer_token"] = tokens.get("bearer_token")
        if "refresh_token" in tokens:
            config["Aalexhealth_token"]["access_refersh_bearer_token"] = tokens.get("refresh_token")
        if "expires_at" in tokens:
            config["Aalexhealth_token"]["token_expires_at"] = tokens.get("expires_at")
        
        # Save updated config
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        logger.debug("Bearer tokens saved successfully to config.json")
    except Exception as e:
        logger.error(f"Error saving tokens to config: {e}")

def refresh_access_token(client_id, client_secret, refresh_token):
    """Refresh the Twitter API bearer tokens using the refresh token."""
    logger.info("Refreshing Twitter API bearer tokens")
    
    if not refresh_token:
        logger.error("No refresh token available")
        return None
    
    try:
        # Prepare the request
        url = "https://api.twitter.com/2/oauth2/token"
        auth = (client_id, client_secret)
        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        # Make the request
        response = requests.post(url, auth=auth, data=data)
        
        # Check if the request was successful
        if response.status_code == 200:
            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 7200)  # Default to 2 hours
            expires_at = int(time.time()) + expires_in
            
            # Create tokens dictionary with only the bearer tokens
            tokens = {
                "bearer_token": token_data.get("access_token"),
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expires_at": expires_at
            }
            
            # Save the new tokens
            save_tokens(tokens)
            
            logger.info(f"Bearer tokens refreshed successfully, expires in {expires_in} seconds")
            return tokens
        else:
            logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return None

def check_token_expiry():
    """Check if the access token is expired or about to expire."""
    tokens = load_tokens()
    
    if not tokens:
        logger.warning("No tokens found")
        return True  # Tokens need refreshing
    
    if "expires_at" not in tokens or not tokens["expires_at"]:
        logger.warning("No expiration time found in tokens")
        return True  # Tokens need refreshing
    
    # Check if token is expired or about to expire (within 5 minutes)
    current_time = int(time.time())
    expires_at = int(tokens["expires_at"])
    time_left = expires_at - current_time
    
    if time_left <= 300:  # 5 minutes in seconds
        logger.info(f"Token expires in {time_left} seconds, needs refreshing")
        return True
    else:
        logger.debug(f"Token is valid for {time_left} more seconds")
        return False

def main():
    """Main function to check and refresh tokens if needed."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Twitter API Token Refresher")
    parser.add_argument("--force", action="store_true", help="Force token refresh even if not expired")
    args = parser.parse_args()
    
    if args.force:
        logger.info("Forcing token refresh")
        needs_refresh = True
    else:
        needs_refresh = check_token_expiry()
    
    if needs_refresh:
        # Load tokens to get credentials
        tokens = load_tokens()
        
        if not tokens:
            logger.error("No tokens found, cannot refresh")
            return
        
        # Refresh the token
        refresh_access_token(
            tokens.get("client_id"),
            tokens.get("client_id_secret"),
            tokens.get("refresh_token")
        )
    else:
        logger.info("Token is still valid, no refresh needed")

if __name__ == "__main__":
    main()
