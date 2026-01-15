"""
Media Operations - Image Upload and Management
Adapted from legacy media.py for robust handling.
"""

import os
import logging
from typing import Dict, Optional, Tuple
from .connector import WordPressConnector

logger = logging.getLogger(__name__)

class MediaOperations:
    """WordPress Media Library operations."""
    
    def __init__(self, connector: WordPressConnector):
        self.connector = connector
        
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type based on file extension."""
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        return mime_types.get(ext, 'application/octet-stream')

    def check_existing_media(self, filename: str) -> Optional[Tuple[int, str]]:
        """
        Check if media with same filename already exists.
        
        Args:
            filename: Name of the file (e.g., image.jpg)
            
        Returns:
            tuple: (media_id, source_url) if found, else None
        """
        try:
            # Search by filename (without extension)
            search_term = os.path.splitext(filename)[0]
            params = {
                'search': search_term,
                'per_page': 5,
                'media_type': 'image'
            }
            
            media_list = self.connector.get('/wp-json/wp/v2/media', params=params)
            
            if not media_list:
                return None
                
            for media in media_list:
                # Check if filename matches in source_url or title
                # This is a loose check, might need refinement
                if search_term.lower() in media.get('source_url', '').lower():
                    logger.info(f"🔄 Found existing media: {filename} (ID: {media['id']})")
                    return media['id'], media['source_url']
                    
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to check existing media: {e}")
            return None

    def upload_image(self, file_path: str, title: str = None, 
                    alt_text: str = None, caption: str = None) -> Optional[Dict]:
        """
        Upload image to WordPress Media Library.
        
        Args:
            file_path: Path to local file
            title: Image title
            alt_text: Alt text for SEO
            caption: Image caption
            
        Returns:
            dict: Media data if successful, None otherwise
        """
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None
            
        filename = os.path.basename(file_path)
        
        # Check existing first
        existing = self.check_existing_media(filename)
        if existing:
            # Fetch full media data
            return self.connector.get(f'/wp-json/wp/v2/media/{existing[0]}')
            
        # Prepare upload
        try:
            with open(file_path, 'rb') as f:
                files = {
                    'file': (filename, f, self._get_mime_type(file_path))
                }
                
                headers = {
                    'Content-Disposition': f'attachment; filename="{filename}"'
                }
                
                # Upload
                logger.info(f"📤 Uploading image: {filename}")
                media_data = self.connector.post('/wp-json/wp/v2/media', files=files)
                
                if not media_data or 'id' not in media_data:
                    logger.error("❌ Upload failed: No ID returned")
                    return None
                
                media_id = media_data['id']
                
                # Update metadata (alt text, caption)
                update_data = {}
                if alt_text:
                    update_data['alt_text'] = alt_text
                if caption:
                    update_data['caption'] = caption
                if title:
                    update_data['title'] = title
                    
                if update_data:
                    self.connector.post(f'/wp-json/wp/v2/media/{media_id}', data=update_data)
                    
                logger.info(f"✅ Image uploaded successfully: ID {media_id}")
                return media_data
                
        except Exception as e:
            logger.error(f"❌ Upload failed: {e}")
            return None
