"""
C05 WordPress Publisher - 發布工程師

重構版本：繼承 BaseAgent，使用 PathResolver 處理路徑
向後兼容：如果核心模組不可用，則使用舊架構
"""

import os
import time
import datetime
import json
import argparse
import logging
import re
import sys
import yaml
import requests
import markdown
from typing import Dict, Any, Optional, List
from pathlib import Path

# 確保可以 import agents.core 模組
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("C05_Publisher")

# 嘗試導入新的核心模組
try:
    from agents.core import BaseAgent, get_current_brand
    USE_NEW_ARCHITECTURE = True
except ImportError:
    USE_NEW_ARCHITECTURE = False
    logger.info("Core modules not available, using legacy architecture")

# 嘗試導入舊的 settings (向後兼容)
try:
    from config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False

# 嘗試導入 WordPress 模組
try:
    from agents.wordpress.connector import WordPressConnector
    from agents.wordpress.publisher import WordPressPublisher
    from agents.wordpress.media import MediaOperations
    WORDPRESS_AVAILABLE = True
except ImportError:
    WORDPRESS_AVAILABLE = False
    logger.warning("WordPress modules not available")


class C05PublisherBase:
    """共用基類 - 包含所有業務邏輯"""

    def _parse_frontmatter(self, content: str) -> tuple:
        """Parses frontmatter and content from markdown file using PyYAML."""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)

        if match:
            frontmatter_str = match.group(1)
            body = match.group(2)
            try:
                frontmatter = yaml.safe_load(frontmatter_str)
                if not isinstance(frontmatter, dict):
                    frontmatter = {}
                return frontmatter, body
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML frontmatter: {e}")
                return {}, content
        else:
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    try:
                        return yaml.safe_load(parts[1]), parts[2].strip()
                    except:
                        pass
            return {}, content

    def _load_site_structure(self) -> Dict:
        """Loads site structure from brand's collected data."""
        possible_paths = [
            os.path.join(self.raw_data_dir, "site_structure.json"),
            os.path.join(self.collected_data_dir, "site_structure.json")
        ]

        for structure_path in possible_paths:
            if os.path.exists(structure_path):
                with open(structure_path, "r", encoding="utf-8") as f:
                    return json.load(f)

        logger.warning(f"Site structure not found in any of: {possible_paths}")
        return {}

    def _get_category_id(self, category_name: str) -> Optional[int]:
        """Gets category ID by name from site_structure.json."""
        try:
            site_structure = self._load_site_structure()
            categories = site_structure.get('categories', [])

            for cat in categories:
                if cat.get('name') == category_name:
                    return cat.get('id')

            logger.warning(f"Category '{category_name}' not found in site_structure.json")
            return None
        except Exception as e:
            logger.error(f"Failed to get category: {e}")
            return None

    def _extract_first_image_url(self, content: str) -> Optional[str]:
        """Extracts the first image URL from content."""
        pattern = r'!\[.*?\]\((https?://[^\)]+)\)'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None

    def _get_media_id_from_url(self, image_url: str) -> Optional[int]:
        """Gets media ID from WordPress URL using MediaOperations."""
        if not hasattr(self, 'media') or self.media is None:
            return None
        try:
            filename = os.path.basename(image_url)
            existing = self.media.check_existing_media(filename)
            if existing:
                return existing[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get media ID for {image_url}: {e}")
            return None

    def publish_article(self, slug: str) -> Dict[str, Any]:
        """
        Publishes a finalized markdown article to WordPress.
        """
        article_path = os.path.join(self.final_dir, f"{slug}.md")
        if not os.path.exists(article_path):
            return {"status": "error", "message": f"Article not found at {article_path}"}

        logger.info(f"Publishing article: {slug}")

        with open(article_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse frontmatter
        frontmatter, body = self._parse_frontmatter(content)

        # Validate required fields
        required_fields = ['title', 'slug', 'description']
        for field in required_fields:
            if field not in frontmatter:
                logger.error(f"Missing required frontmatter field: {field}")
                return {"status": "error", "message": f"Missing required frontmatter field: {field}"}

        # Get category IDs
        categories_raw = frontmatter.get('categories', [])
        if isinstance(categories_raw, str):
            category_names = [c.strip() for c in categories_raw.split(',')]
        elif isinstance(categories_raw, list):
            category_names = categories_raw
        else:
            category_names = []

        category_ids = []
        for cat_name in category_names:
            cat_name = str(cat_name).strip()
            if cat_name:
                cat_id = self._get_category_id(cat_name)
                if cat_id:
                    category_ids.append(cat_id)
                else:
                    logger.warning(f"Category '{cat_name}' not found. Skipping.")

        if not category_ids:
            logger.warning("No valid categories found. Post will be Uncategorized.")

        # Get featured image
        featured_image_id = None
        first_image_url = self._extract_first_image_url(body)
        if first_image_url:
            featured_image_id = self._get_media_id_from_url(first_image_url)
            if featured_image_id:
                logger.info(f"Featured image set: {first_image_url} (ID: {featured_image_id})")

        # Prepare meta for RankMath
        meta = {}
        if 'title' in frontmatter:
            meta['rank_math_title'] = frontmatter['title']
        if 'description' in frontmatter:
            meta['rank_math_description'] = frontmatter['description']
        if 'keywords' in frontmatter:
            keywords_raw = frontmatter['keywords']
            if isinstance(keywords_raw, list):
                keywords = keywords_raw
            elif isinstance(keywords_raw, str):
                keywords = [k.strip() for k in keywords_raw.split(',')]
            else:
                keywords = []

            if keywords:
                meta['rank_math_focus_keyword'] = keywords[0]
        if 'schema' in frontmatter:
            meta['rank_math_schema'] = frontmatter['schema']
        if 'slug' in frontmatter:
            meta['rank_math_permalink'] = frontmatter['slug']
        if 'canonical_url' in frontmatter:
            meta['rank_math_canonical_url'] = frontmatter['canonical_url']

        if category_ids:
            primary_cat_id = str(category_ids[0])
            meta['rank_math_primary_category'] = primary_cat_id
            meta['_rank_math_primary_category'] = primary_cat_id

        # Check if publisher is available
        if not hasattr(self, 'publisher') or self.publisher is None:
            return {"status": "error", "message": "WordPress publisher not initialized"}

        # Check if post already exists
        existing_post = None
        
        # Priority 1: Check by wordpress_id from frontmatter
        wp_id_from_fm = frontmatter.get('wordpress_id')
        if wp_id_from_fm:
            try:
                response = self.connector.get(f'/wp-json/wp/v2/posts/{wp_id_from_fm}', params={'status': 'any'})
                if response:
                    existing_post = response
                    logger.info(f"Found existing post with ID {wp_id_from_fm} from frontmatter")
            except Exception as e:
                logger.warning(f"Post ID {wp_id_from_fm} not found or error: {e}")

        # Priority 2: Check by slug if not found by ID
        if not existing_post:
            try:
                response = self.connector.get('/wp-json/wp/v2/posts', params={'slug': frontmatter['slug'], 'status': 'any'})
                if response and len(response) > 0:
                    existing_post = response[0]
                    logger.info(f"Found existing post with slug '{frontmatter['slug']}': ID {existing_post['id']}")
            except Exception as e:
                logger.error(f"Error checking for existing post by slug: {e}")

        # Create or Update post
        if existing_post:
            post_id = existing_post['id']
            logger.info(f"Updating existing post ID: {post_id}")
            # Convert Markdown to HTML for Classic Editor
            html_content = markdown.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])
            
            post = self.publisher.update_post(
                post_id=post_id,
                title=frontmatter['title'],
                content=html_content,
                status='draft',
                categories=category_ids,
                featured_media_id=featured_image_id or 0,
                slug=frontmatter['slug'],
                excerpt=frontmatter.get('description', ''),
                meta=meta
            )
        else:
            logger.info("No existing post found, creating new post...")
            # Convert Markdown to HTML for Classic Editor
            if 'html_content' not in locals():
                 html_content = markdown.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])

            post = self.publisher.create_post(
                title=frontmatter['title'],
                content=html_content,
                status='draft',
                categories=category_ids,
                featured_media_id=featured_image_id or 0,
                slug=frontmatter['slug'],
                excerpt=frontmatter.get('description', ''),
                meta=meta
            )

        if not post:
            logger.error("Failed to publish article")
            return {"status": "error", "message": "Failed to publish article"}

        post_id = post.get('id')
        post_link = post.get('link')

        # Write Post ID back to Frontmatter
        frontmatter['wordpress_id'] = post_id

        # Reconstruct the file with updated frontmatter
        updated_frontmatter_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False)
        updated_content = f"---\n{updated_frontmatter_str}---\n{body}"

        with open(article_path, "w", encoding="utf-8") as f:
            f.write(updated_content)

        logger.info(f"Successfully published draft. ID: {post_id}, Link: {post_link}")
        logger.info(f"Updated Frontmatter with wordpress_id: {post_id}")

        return {
            "status": "success",
            "post_id": post_id,
            "link": post_link,
            "title": frontmatter['title']
        }


# =============================================================================
# 根據環境選擇架構
# =============================================================================

if USE_NEW_ARCHITECTURE:
    class C05Publisher(BaseAgent, C05PublisherBase):
        """C05 WordPress Publisher - 使用新架構"""

        def __init__(self):
            BaseAgent.__init__(self, name="C05_Publisher")
            self.brand_name = self.brand.slug
            self.base_dir = str(self.brand_manager.base_dir)

            # 設定所有路徑
            self.final_dir = str(self.resolve_path("outputs/FUNIT/final"))
            self.raw_data_dir = str(self.resolve_path("outputs/FUNIT/raw_data"))
            self.collected_data_dir = str(self.resolve_path("outputs/FUNIT/收集到的資料"))

            # 載入 WordPress 設定
            self._init_wordpress()

        def _init_wordpress(self):
            """Initialize WordPress connection from brand config."""
            self.connector = None
            self.publisher = None
            self.media = None

            if not WORDPRESS_AVAILABLE:
                logger.warning("WordPress modules not available")
                return

            # 嘗試從 wordpress.env 載入設定
            wp_env_path = self.brand.config_dir / "wordpress.env"
            # Fallback to root .env
            if not wp_env_path.exists():
                 wp_env_path = Path(self.base_dir) / ".env"
                
            wp_config = {}

            if wp_env_path.exists():
                with open(wp_env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            wp_config[key.strip()] = value.strip()

            wp_url = wp_config.get("WP_SITE_URL", "")
            wp_username = wp_config.get("WP_USERNAME", "")
            wp_password = wp_config.get("WP_APP_PASSWORD", "")

            if wp_url and wp_username and wp_password:
                try:
                    self.connector = WordPressConnector(
                        base_url=wp_url,
                        username=wp_username,
                        app_password=wp_password
                    )
                    self.publisher = WordPressPublisher(self.connector)
                    self.media = MediaOperations(self.connector)
                    logger.info(f"WordPress connection initialized for {wp_url}")
                except Exception as e:
                    logger.error(f"Failed to initialize WordPress: {e}")

        def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """執行發布任務"""
            slug = input_data.get("slug") or input_data.get("article_slug")
            if not slug:
                raise ValueError("缺少必需參數: slug")

            return self.publish_article(slug)

else:
    class C05Publisher(C05PublisherBase):
        """C05 WordPress Publisher - 舊架構 (向後兼容)"""

        def __init__(self):
            if SETTINGS_AVAILABLE:
                self.brand_name = settings.brand_name
            else:
                self.brand_name = "FUNIT"
            self.base_dir = os.getcwd()

            # 設定所有路徑
            base_output = os.path.join(self.base_dir, "outputs", "FUNIT")
            self.final_dir = os.path.join(base_output, "final")
            self.raw_data_dir = os.path.join(base_output, "raw_data")
            self.collected_data_dir = os.path.join(base_output, "收集到的資料")

            # 初始化 WordPress
            self.connector = None
            self.publisher = None
            self.media = None

            if WORDPRESS_AVAILABLE and SETTINGS_AVAILABLE:
                try:
                    self.connector = WordPressConnector(
                        base_url=settings.wordpress_url,
                        username=settings.wordpress_username,
                        app_password=settings.wordpress_app_password
                    )
                    self.publisher = WordPressPublisher(self.connector)
                    self.media = MediaOperations(self.connector)
                except Exception as e:
                    logger.error(f"Failed to initialize WordPress: {e}")

            self.logger = logger

        def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """執行發布任務"""
            slug = input_data.get("slug") or input_data.get("article_slug")
            if not slug:
                return {"status": "error", "message": "Slug is required"}

            return self.publish_article(slug)

        def log_activity(self, message: str):
            """Legacy logging method"""
            logger.info(message)


# =============================================================================
# CLI 介面
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C05 WordPress Publisher Agent")
    parser.add_argument("--slug", required=True, help="The slug of the article to publish")
    args = parser.parse_args()

    publisher = C05Publisher()
    result = publisher.run({"slug": args.slug})
    print(json.dumps(result, ensure_ascii=False, indent=2))
