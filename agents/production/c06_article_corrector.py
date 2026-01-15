"""
C06 Article Corrector - 文章修正員
負責更新已發布的 WordPress 文章，並將修正記錄存入 Fact Memory。
"""

import os
import sys
import argparse
import logging
import json
from pathlib import Path
from typing import Optional

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from agents.wordpress.connector import WordPressConnector
from agents.wordpress.publisher import WordPressPublisher
try:
    from utils.fact_memory_manager import FactMemoryManager
    FACT_MEMORY_AVAILABLE = True
except ImportError:
    FACT_MEMORY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("C06_ArticleCorrector")

class C06ArticleCorrector:
    def __init__(self):
        self._init_wordpress()
        if FACT_MEMORY_AVAILABLE:
            self.fact_memory = FactMemoryManager()
        else:
            self.fact_memory = None
            logger.warning("FactMemoryManager not available. Corrections will not be memorized.")

    def _init_wordpress(self):
        """Initialize WordPress connection."""
        self.client = WordPressConnector()
        if not self.client.base_url or not self.client.username:
            logger.error("WordPress credentials missing in environment variables.")
            sys.exit(1)
            
        # Test connection
        if not self.client.test_connection():
            logger.error("Failed to connect to WordPress.")
            sys.exit(1)
            
        self.publisher = WordPressPublisher(self.client)

    def correct_article(self, post_id: int, target_text: str, replacement_text: str, source: str = "Manual Correction") -> bool:
        """
        Corrects an article by replacing target_text with replacement_text.
        Then saves the correction to Fact Memory.
        """
        logger.info(f"Fetching post {post_id}...")
        
        # 1. Get existing post
        try:
            post = self.client.get(f"/wp-json/wp/v2/posts/{post_id}", params={'context': 'edit'})
        except Exception as e:
            logger.error(f"Failed to fetch post: {e}")
            return False

        if not post or 'content' not in post:
            logger.error("Post not found or invalid response.")
            return False

        current_content_raw = post['content']['raw']
        
        # 2. Perform Replacement
        if target_text not in current_content_raw:
            logger.warning(f"Target text '{target_text}' not found in post content. Aborting.")
            # Optional: Implement fuzzy search or LLM search here
            return False
            
        new_content_raw = current_content_raw.replace(target_text, replacement_text)
        
        if new_content_raw == current_content_raw:
            logger.info("No changes made.")
            return True

        # 3. Update WordPress
        logger.info("Content modified. Updating WordPress...")
        try:
            # Note: We update the 'content' field. 
            # In 'edit' context, the API expects 'content' to be the new content string.
            update_data = {
                'content': new_content_raw
            }
            response = self.client.post(f"/wp-json/wp/v2/posts/{post_id}", data=update_data)
            
            if 'id' in response:
                logger.info(f"✅ Successfully updated post {post_id}.")
                link = response.get('link', '')
                logger.info(f"Post Link: {link}")
            else:
                logger.error(f"Failed to update post. Response: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating post: {e}")
            return False

        # 4. Save to Fact Memory
        if self.fact_memory:
            logger.info("Saving correction to Fact Memory...")
            try:
                self.fact_memory.add_fact(
                    context=f"Correction for Post {post_id}",
                    claim=target_text,
                    correction=replacement_text,
                    source=source
                )
                logger.info("✅ Fact Memory updated.")
            except Exception as e:
                logger.error(f"Failed to update Fact Memory: {e}")
                
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C06 Article Corrector Agent")
    parser.add_argument("--post-id", type=int, required=True, help="WordPress Post ID")
    parser.add_argument("--target-text", required=True, help="Text to replace")
    parser.add_argument("--replacement-text", required=True, help="New text")
    parser.add_argument("--source", default="Manual Correction", help="Source of the correction")
    
    args = parser.parse_args()
    
    corrector = C06ArticleCorrector()
    success = corrector.correct_article(
        post_id=args.post_id,
        target_text=args.target_text,
        replacement_text=args.replacement_text,
        source=args.source
    )
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)
