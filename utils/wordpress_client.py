import requests
import os
import time
from requests.auth import HTTPBasicAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config.settings import settings
from agents.core.brand_manager import BrandManager
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WordPressClient:
    def __init__(self):
        wp_config = {}
        try:
            brand = BrandManager().get_current_brand()
            candidate_paths = [
                brand.config_dir / "wordpress.env",
                brand.config_dir / ".env",
                brand.config_dir.parent / ".env",
            ]
            for wp_env_path in candidate_paths:
                if wp_env_path.exists():
                    with open(wp_env_path, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith("#") and "=" in line:
                                key, value = line.split("=", 1)
                                wp_config[key.strip()] = value.strip()
                    break
        except Exception:
            wp_config = {}

        base_url = wp_config.get("WP_SITE_URL") or settings.wordpress_url
        username = wp_config.get("WP_USERNAME") or settings.wordpress_username
        app_password = wp_config.get("WP_APP_PASSWORD") or settings.wordpress_app_password

        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, app_password)
        self.headers = {
            "Content-Type": "application/json"
        }
        
        # Configure Retry Strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.auth = self.auth
        # Add browser User-Agent to bypass server-side blocking of Python requests
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """Executes an HTTP request using the configured session."""
        url = f"{self.base_url}/wp-json/wp/v2/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            raise

    def create_post(self, title: str, content: str, excerpt: str, categories: List[int], status: str = "draft", meta: Dict[str, Any] = None) -> Dict[str, Any]:
        """Creates a new WordPress post."""
        data = {
            "title": title,
            "content": content,
            "excerpt": excerpt,
            "categories": categories,
            "status": status
        }
        if meta:
            data["meta"] = meta

        response = self._request("POST", "posts", json=data)
        return response.json()

    def update_post(self, post_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing WordPress post."""
        response = self._request("POST", f"posts/{post_id}", json=data)
        return response.json()

    def delete_post(self, post_id: int) -> Dict[str, Any]:
        """Deletes a WordPress post."""
        response = self._request("DELETE", f"posts/{post_id}", params={"force": True})
        return response.json()

    def upload_media(self, file_path: str, caption: str = "") -> Dict[str, Any]:
        """Uploads an image to the WordPress Media Library."""
        url = f"{self.base_url}/wp-json/wp/v2/media"
        file_name = os.path.basename(file_path)
        
        # Determine MIME type (basic implementation)
        mime_type = "image/jpeg"
        if file_name.lower().endswith(".png"):
            mime_type = "image/png"
        elif file_name.lower().endswith(".gif"):
            mime_type = "image/gif"

        headers = {
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": mime_type
        }

        with open(file_path, "rb") as file:
            # Note: For media upload, we don't use the _request_with_retry wrapper directly 
            # because the headers and data structure are different (binary data).
            # Implementing simple retry logic here for consistency.
            max_retries = 3
            backoff_factor = 2
            for attempt in range(max_retries):
                try:
                    # Use self.session to ensure User-Agent is sent
                    response = self.session.post(url, data=file, headers=headers)
                    response.raise_for_status()
                    return response.json()
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Media upload failed (Attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(backoff_factor ** attempt)
        return {}

    def get_categories(self) -> List[Dict[str, Any]]:
        """Retrieves all categories."""
        return self._get_all_items("categories")

    def get_post(self, post_id: int, **kwargs) -> Dict[str, Any]:
        """Retrieves a single post by ID."""
        response = self._request("GET", f"posts/{post_id}", **kwargs)
        return response.json()

    def get_all_posts(self) -> List[Dict[str, Any]]:
        """Retrieves all posts with pagination."""
        return self._get_all_items("posts")

    def get_revisions(self, post_id: int) -> List[Dict[str, Any]]:
        """Retrieves revision history for a post."""
        try:
            response = self._request("GET", f"posts/{post_id}/revisions")
            return response.json()
        except Exception as e:
            logger.warning(f"Failed to get revisions for post {post_id}: {e}")
            return []

    def get_posts_batch(self, page: int = 1, per_page: int = 50) -> tuple[List[Dict[str, Any]], int]:
        """Retrieves a batch of posts and total pages count."""
        try:
            response = self._request("GET", "posts", params={"per_page": per_page, "page": page})
            total_pages = int(response.headers.get("X-WP-TotalPages", 0))
            return response.json(), total_pages
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                return [], 0
            raise

    def get_all_pages(self) -> List[Dict[str, Any]]:
        """Retrieves all pages with pagination."""
        return self._get_all_items("pages")
        
    def get_all_products(self) -> List[Dict[str, Any]]:
        """Retrieves all products with pagination (requires WooCommerce)."""
        # WooCommerce products endpoint is usually wp-json/wc/v3/products
        # But for simplicity and if using standard WP API extensions, we'll try 'product' post type first
        # or check if we need to implement WC specific client.
        # For now, let's assume standard WP REST API custom post type 'product' if exposed,
        # or use the WC endpoint if configured.
        
        # Note: Standard WP REST API doesn't expose WC products by default without auth/setup.
        # We'll try the 'product' endpoint assuming WC REST API is active and we use the same auth.
        # However, WC usually uses /wc/v3/. Let's stick to WP REST API pattern first.
        # If this fails, we might need a specific WC client.
        try:
            return self._get_all_items("product") # Custom post type often used
        except Exception:
            # Fallback or specific handling for WooCommerce could be added here
            logger.warning("Could not fetch products via standard 'product' endpoint.")
            return []

    def _get_all_items(self, endpoint: str) -> List[Dict[str, Any]]:
        """Helper to fetch all items with pagination."""
        items = []
        page = 1
        # Reduced from 100 to 50 to avoid server load issues
        per_page = 50
        
        while True:
            try:
                response = self._request("GET", endpoint, params={"per_page": per_page, "page": page})
                batch = response.json()
                
                if not batch:
                    break
                    
                items.extend(batch)
                
                # Check if we've reached the last page
                total_pages = int(response.headers.get("X-WP-TotalPages", 0))
                if page >= total_pages:
                    break
                    
                page += 1
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 400: # Often means page out of range
                    break
                raise
                
        return items

# Global instance
wp_client = WordPressClient()
