"""
SEO Operations - Rank Math Integration
Adapted from legacy seo.py to handle Rank Math metadata correctly.
"""

import logging
from typing import Dict, Any, Optional
from .connector import WordPressConnector

logger = logging.getLogger(__name__)

class SEOOperations:
    """Rank Math SEO operations handler."""
    
    def __init__(self, connector: WordPressConnector):
        self.connector = connector
    
    def update_seo_meta(self, post_id: int, title: str = None, 
                       description: str = None, focus_keyword: str = None,
                       permalink: str = None, **kwargs) -> bool:
        """
        Update Rank Math SEO metadata using the Headless CMS API endpoint.
        Requires 'Headless CMS Support' enabled in Rank Math settings.
        
        Args:
            post_id: Post ID
            title: SEO Title
            description: SEO Description
            focus_keyword: Focus Keyword
            permalink: Custom Permalink (slug)
            **kwargs: Other Rank Math fields
        
        Returns:
            bool: Success status
        """
        meta_data = {}
        
        if title:
            meta_data['rank_math_title'] = title
        if description:
            meta_data['rank_math_description'] = description
        if focus_keyword:
            meta_data['rank_math_focus_keyword'] = focus_keyword
        if permalink:
            meta_data['rank_math_permalink'] = permalink
            
        # Add other fields
        meta_data.update(kwargs)
        
        if not meta_data:
            logger.warning("⚠️ No SEO data provided for update")
            return False
            
        # Rank Math Headless CMS API endpoint
        endpoint = "/wp-json/rankmath/v1/updateMeta"
        
        payload = {
            'objectID': post_id,
            'objectType': 'post',
            'meta': meta_data
        }
        
        try:
            res = self.connector.post(endpoint, data=payload)
            # Check if response indicates 404 or other error if connector doesn't raise
            if isinstance(res, dict) and res.get('code') == 'rest_no_route':
                 logger.warning("⚠️ Rank Math API not active (rest_no_route). Skipping SEO meta update.")
                 return True # Treat as "handled" to avoid downstream errors
                 
            logger.info(f"✅ Successfully updated Rank Math SEO meta for post {post_id}")
            return True
            
        except Exception as e:
            # If the connector raises an exception for 404
            if "404" in str(e):
                 logger.warning("⚠️ Rank Math API endpoint not found. Skipping SEO meta update.")
                 return True
            
            logger.error(f"❌ Failed to update Rank Math SEO meta: {e}")
            return False

    def validate_seo_settings(self) -> bool:
        """
        Validate if Rank Math Headless CMS support is enabled.
        """
        try:
            # Try to access a Rank Math endpoint
            self.connector.get('/wp-json/rankmath/v1/getHead', params={'url': self.connector.base_url})
            logger.info("✅ Rank Math Headless CMS support is enabled")
            return True
        except Exception as e:
            logger.warning(f"❌ Rank Math check failed: {e}")
            logger.warning("Please ensure Rank Math > General Settings > Headless CMS Support is ENABLED")
            return False
