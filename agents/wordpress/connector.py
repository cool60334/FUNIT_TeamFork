"""
WordPress Connector - Core Connection Module
Adapted from legacy connector.py for robust API handling.
"""

import os
import base64
import requests
import time
import logging
from typing import Optional, Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WordPressConnector:
    """Core connector for WordPress REST API with authentication and retries."""
    
    def __init__(self, base_url: str = None, username: str = None, app_password: str = None):
        """
        Initialize WordPress Connector.
        
        Args:
            base_url: WordPress site URL
            username: WordPress username
            app_password: WordPress application password
        """
        # Load from env if not provided
        self.base_url = base_url or os.getenv("WP_SITE_URL", "")
        self.username = username or os.getenv("WP_USERNAME", "")
        self.app_password = app_password or os.getenv("WP_APP_PASSWORD", "")
        
        # Ensure URL has protocol
        if self.base_url and not self.base_url.startswith('http'):
            self.base_url = f"https://{self.base_url}"
        
        # Remove trailing slash
        self.base_url = self.base_url.rstrip('/')
        
        if not self.base_url or not self.username or not self.app_password:
            logger.warning("WordPress credentials incomplete. Please check environment variables.")
        
        # Construct auth header
        credentials = f"{self.username}:{self.app_password}"
        self.token = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            'Authorization': f'Basic {self.token}',
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None, files: Dict = None, max_retries: int = 3) -> Dict:
        """
        Unified HTTP request handler with retry logic.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /wp-json/wp/v2/pages)
            data: JSON data (for POST/PUT)
            params: URL query parameters
            files: File uploads (for media)
            max_retries: Number of retries for failed requests
        
        Returns:
            dict: API response data
        """
        # Ensure endpoint starts with /
        if not endpoint.startswith('/'):
            endpoint = f"/{endpoint}"
            
        url = f"{self.base_url}{endpoint}"
        
        # If uploading files, don't set Content-Type to json
        headers = self.headers.copy()
        if files:
            headers.pop('Content-Type', None)
        
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if not files else None,
                    params=params,
                    files=files,
                    timeout=30
                )
                
                response.raise_for_status()
                
                # Handle empty content (e.g. 204 No Content)
                if response.status_code == 204:
                    return {}
                    
                return response.json()
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (Attempt {attempt + 1}/{max_retries}): {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.warning(f"Response content: {e.response.text}")
                
                if attempt == max_retries - 1:
                    raise
                
                time.sleep(2 ** attempt)  # Exponential backoff
        
        return {}
    
    def get(self, endpoint: str, params: Dict = None) -> Dict:
        """GET request"""
        return self._make_request('GET', endpoint, params=params)
    
    def post(self, endpoint: str, data: Dict = None, files: Dict = None) -> Dict:
        """POST request"""
        return self._make_request('POST', endpoint, data=data, files=files)
    
    def put(self, endpoint: str, data: Dict) -> Dict:
        """PUT request"""
        return self._make_request('PUT', endpoint, data=data)
    
    def delete(self, endpoint: str, params: Dict = None) -> Dict:
        """DELETE request"""
        return self._make_request('DELETE', endpoint, params=params)
    
    def test_connection(self) -> bool:
        """Test connection to WordPress"""
        try:
            response = self.get('/wp-json/wp/v2/users/me')
            logger.info(f"✅ Connection successful! User: {response.get('name', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            return False
