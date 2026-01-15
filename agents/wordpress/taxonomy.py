"""
Taxonomy Operations - Categories and Tags
Adapted from legacy taxonomy.py.
"""

import logging
from typing import Dict, List, Optional
from .connector import WordPressConnector

logger = logging.getLogger(__name__)

class TaxonomyOperations:
    """WordPress Taxonomy (Categories/Tags) operations."""
    
    def __init__(self, connector: WordPressConnector):
        self.connector = connector
        
    def get_categories(self) -> List[Dict]:
        """Get all categories."""
        categories = []
        page = 1
        
        while True:
            params = {'per_page': 100, 'page': page}
            batch = self.connector.get('/wp-json/wp/v2/categories', params=params)
            
            if not batch:
                break
                
            categories.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            
        return categories
    
    def get_tags(self) -> List[Dict]:
        """Get all tags."""
        tags = []
        page = 1
        
        while True:
            params = {'per_page': 100, 'page': page}
            batch = self.connector.get('/wp-json/wp/v2/tags', params=params)
            
            if not batch:
                break
                
            tags.extend(batch)
            if len(batch) < 100:
                break
            page += 1
            
        return tags
        
    def create_category(self, name: str, slug: str = None) -> Optional[Dict]:
        """Create a new category."""
        data = {'name': name}
        if slug:
            data['slug'] = slug
            
        try:
            return self.connector.post('/wp-json/wp/v2/categories', data=data)
        except Exception as e:
            logger.error(f"Failed to create category {name}: {e}")
            return None
            
    def create_tag(self, name: str, slug: str = None) -> Optional[Dict]:
        """Create a new tag."""
        data = {'name': name}
        if slug:
            data['slug'] = slug
            
        try:
            return self.connector.post('/wp-json/wp/v2/tags', data=data)
        except Exception as e:
            logger.error(f"Failed to create tag {name}: {e}")
            return None
