"""
WordPress Publisher - Core Publishing Logic
Adapted from legacy wp_publisher.py.
"""

import logging
import re
import json
import os
import markdown
from typing import Dict, List, Optional, Any, Tuple
from .connector import WordPressConnector
from .seo import SEOOperations
from .media import MediaOperations
from .taxonomy import TaxonomyOperations
from agents.core.brand_manager import BrandManager

logger = logging.getLogger(__name__)

class WordPressPublisher:
    """Core publisher class that orchestrates the publishing process."""
    
    def __init__(self, connector: WordPressConnector, seo_plugin: str = None):
        self.connector = connector
        self.seo = SEOOperations(connector)
        self.media = MediaOperations(connector)
        self.taxonomy = TaxonomyOperations(connector)
        self.brand_config = self._load_brand_config()
        
        # Determine SEO Plugin:
        # 1. Explicit arg
        # 2. Config file 'wordpress_settings.seo_plugin'
        # 3. Default to 'rankmath'
        if seo_plugin:
            self.seo_plugin = seo_plugin
        else:
            self.seo_plugin = self.brand_config.get('wordpress_settings', {}).get('seo_plugin', 'rankmath')
            
        logger.info(f"WordPressPublisher initialized with SEO Plugin: {self.seo_plugin}")

        
    def _load_brand_config(self) -> Dict[str, Any]:
        """Load brand configuration from JSON file."""
        try:
            brand = BrandManager().get_current_brand()
            if brand and brand.brand_config:
                return brand.brand_config
        except Exception as e:
            logger.warning(f"BrandManager load failed: {e}")

        try:
            config_path = 'config/brand_profile.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load brand config: {e}")
        return {}
        
    def _convert_markdown_to_html(self, content: str) -> str:
        """Convert Markdown to HTML with table support."""
        # Pre-process: Manually convert fenced code blocks to HTML
        # This bypasses the fenced_code extension which has parsing issues
        def convert_fenced_code(match):
            lang = match.group(1) or ''
            code = match.group(2)
            # HTML-escape special characters in code
            code = code.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            lang_class = f' class="language-{lang}"' if lang else ''
            return f'<pre class="wp-block-code"><code{lang_class}>{code}</code></pre>'
        
        # Match fenced code blocks: ```lang\n...\n```
        content = re.sub(r'```(\w*)\n(.*?)\n```', convert_fenced_code, content, flags=re.DOTALL)
        
        # Now convert the rest with markdown (without fenced_code since we handled it)
        md = markdown.Markdown(extensions=['tables', 'nl2br'])
        return md.convert(content)

    def _convert_to_gutenberg_blocks(self, html_content: str) -> str:
        """
        Convert raw HTML to Gutenberg Blocks format.
        
        MODIFIED FOR CLASSIC EDITOR:
        Simply returns the HTML content without block wrapping.
        """
        # In Classic Editor mode, we do NOT want Gutenberg blocks.
        # We just want raw HTML.
        return html_content

    def _convert_faq_to_rankmath_block(self, faq_block: str) -> str:
        """Convert FAQ markdown to Rank Math FAQ Block."""
        # This method now handles the logic previously in _convert_faq_to_block
        lines = faq_block.strip().split('\n')
        questions = []
        current_q = None
        current_a = []
        
        for line in lines:
            if line.startswith('#### '):
                if current_q:
                    questions.append({'title': current_q, 'content': '\n'.join(current_a).strip()})
                current_q = line.replace('#### ', '').strip()
                current_a = []
            elif line.strip() and current_q:
                current_a.append(line.strip())
                
        if current_q:
             questions.append({'title': current_q, 'content': '\n'.join(current_a).strip()})
             
        # Generate JSON for Rank Math
        import json
        rm_json = {
            "titleWrapper": "h3",
            "questions": [
                {"id": f"faq-item-{i}", "title": q['title'], "content": q['content'], "visible": True}
                for i, q in enumerate(questions)
            ]
        }
        
        inner_html = '<div class="rank-math-block">'
        for q in questions:
            inner_html += f'<div class="rank-math-list-item"><h3 class="rank-math-question">{q["title"]}</h3><div class="rank-math-answer">{q["content"]}</div></div>'
        inner_html += '</div>'

        return f'<!-- wp:rank-math/faq-block {json.dumps(rm_json)} -->{inner_html}<!-- /wp:rank-math/faq-block -->'

    def _convert_faq_to_seopress_block(self, faq_block: str) -> str:
        """
        Convert FAQ markdown to SEOPress FAQ Block.
        Correct Namespace: `wpseopress/faq-block`
        Attribute: `faqs` (List of objects with question/answer)
        Structure: <!-- wp:wpseopress/faq-block {"faqs":[{"question":"Q1","answer":"A1"}, ...]} -->
        """
        lines = faq_block.strip().split('\n')
        
        # Extract Q&A
        qa_pairs = []
        current_q = None
        current_a = []
        
        for line in lines:
            if line.startswith('#### '):
                if current_q:
                    qa_pairs.append({'question': current_q, 'answer': '\n'.join(current_a).strip()})
                current_q = line.replace('#### ', '').strip()
                current_a = []
            elif line.strip() and current_q:
                current_a.append(line.strip())
        
        if current_q:
            qa_pairs.append({'question': current_q, 'answer': '\n'.join(current_a).strip()})
            
        if not qa_pairs:
            return ""

        # Build Block HTML
        import json
        block_attrs = {
            "faqs": qa_pairs,
            "block_unique_id": "", # Optional but often used
            "style": {} # Optional
        }
        json_str = json.dumps(block_attrs)
        
        # Note: HTML inside the comment is usually just a render fallback or matching structure.
        # For V1 block, it iterates over `faqs`.
        block_html = f'<!-- wp:wpseopress/faq-block {json_str} -->'
        block_html += '<div class="wp-block-wpseopress-faq-block">'
        
        for i, item in enumerate(qa_pairs):
            q = item['question']
            a = item['answer']
            # V1 typically uses a specific structure, but simple details/summary might be V2.
            # Let's try to mimic a generic structure that V1 might output or just empty div if it's dynamic.
            # Safest is to provide the rendered HTML matching the data so it doesn't break visuals if JS fails.
            block_html += f'''
            <div class="wpseopress-faq-item seopress-faq-item">
                <h3 class="wpseopress-faq-question seopress-faq-question">{q}</h3>
                <div class="wpseopress-faq-answer seopress-faq-answer">{a}</div>
            </div>
            '''
        
        block_html += '</div>'
        block_html += '<!-- /wp:wpseopress/faq-block -->'
        
        return block_html

    def _prepare_content(self, content: str) -> str:
        """
        Unified method to prepare content for WordPress.
        Smartly handles conversion from Markdown to HTML/Gutenberg blocks.
        """
        # CRITICAL: Check if content already contains Gutenberg block markers
        # If so, skip MD→HTML→Gutenberg conversion to avoid double-wrapping
        # if '<!-- wp:' in content:
        #    logger.info("Content already contains Gutenberg blocks, skipping conversion")
        #    return content
        
        # 0. Pre-process FAQ Section
        # DISABLED FOR CLASSIC EDITOR: We do not want specific FAQ blocks.
        # Just let them be regular headers and paragraphs.
        
        # def process_faq_section(match):
        #    header = match.group(1)
        #    faq_body = match.group(2)
        #    
        #    # Use the preferred convert method
        #    if self.seo_plugin == 'seopress':
        #       block_html = self._convert_faq_to_seopress_block(faq_body)
        #    else:
        #       block_html = self._convert_faq_to_rankmath_block(faq_body)
        #    
        #    if not block_html:
        #        return match.group(0) # fallback
        #        
        #    return f'\n## {header}\n\n{block_html}\n'

        # content = re.sub(
        #     r'^##\s+(.*(?:QA|FAQ|常見問題).*)$([\s\S]*?)(?=^## |\Z)', 
        #     process_faq_section, 
        #     content, 
        #     flags=re.MULTILINE
        # )
            
        # 1. Convert Markdown to HTML
        html_content = self._convert_markdown_to_html(content)
        
        # 2. Convert HTML to Gutenberg Blocks
        return self._convert_to_gutenberg_blocks(html_content)

    def _prepare_post_data(self, title: str, content: str, status: str, 
                          categories: List[int], tags: List[int], 
                          excerpt: str, slug: str = "", featured_media_id: int = 0) -> Dict[str, Any]:
        """Prepare the data dictionary for API requests."""
        post_data = {
            'title': title,
            'content': self._prepare_content(content),
            'status': status,
            'categories': categories,
            'tags': tags,
            'excerpt': excerpt,
        }
        
        if featured_media_id > 0:
            post_data['featured_media'] = featured_media_id
            
        if slug:
            post_data['slug'] = slug
            
        return post_data

    def _update_seo_meta(self, post_id: int, meta: Dict[str, Any]):
        """Helper to update SEO data (Rank Math or SEOPress)."""
        if not meta:
            return

        seo_kwargs = {}
        
        if self.seo_plugin == 'seopress':
             # Map metadata to SEOPress keys and update via standard post meta
             # Note: This usually needs to be passed during post update, not separate API call if using standard meta.
             # However, we can do a separate update if needed.
             seopress_map = {
                 'title': '_seopress_titles_title',
                 'description': '_seopress_titles_desc',
                 'focus_keyword': '_seopress_analysis_target_kw'
             }
             
             meta_payload = {}
             for key, value in meta.items():
                 # Handle rank_math_ prefix removal if legacy data
                 clean_key = key.replace('rank_math_', '')
                 if clean_key in seopress_map:
                     meta_payload[seopress_map[clean_key]] = value
             
             if meta_payload:
                 # Update via connector
                 self.connector.post(f'/wp-json/wp/v2/posts/{post_id}', data={'meta': meta_payload})
                 
        else: # Default to Rank Math
            supported_fields = {'title', 'description', 'focus_keyword', 'permalink'}
            for key, value in meta.items():
                if key.startswith('rank_math_'):
                    param_name = key.replace('rank_math_', '')
                    if param_name in supported_fields:
                        seo_kwargs[param_name] = value
            
            if seo_kwargs:
                self.seo.update_seo_meta(post_id, **seo_kwargs)


    def create_post(self, title: str, content: str, status: str = 'draft', 
                   categories: List[int] = [], tags: List[int] = [], 
                   featured_media_id: int = 0, slug: str = "",
                   excerpt: str = "", meta: Dict[str, Any] = {}) -> Optional[Dict]:
        """
        Create a new post in WordPress.
        """
        post_data = self._prepare_post_data(
            title, content, status, categories, tags, 
            excerpt, slug, featured_media_id
        )
            
        try:
            logger.info(f"Creating post: {title}")
            post = self.connector.post('/wp-json/wp/v2/posts', data=post_data)
            
            if not post or 'id' not in post:
                logger.error("Failed to create post: No ID returned")
                return None
                
            post_id = post['id']
            logger.info(f"✅ Post created: ID {post_id}")
            
            self._update_seo_meta(post_id, meta)
            
            return post
            
        except Exception as e:
            logger.error(f"❌ Failed to create post: {e}")
            return None
            
    def update_post(self, post_id: int, title: str, content: str, status: str = 'draft', 
                   categories: List[int] = [], tags: List[int] = [], 
                   featured_media_id: int = 0, slug: str = "",
                   excerpt: str = "", meta: Dict[str, Any] = {}) -> Optional[Dict]:
        """
        Update an existing post in WordPress.
        """
        post_data = self._prepare_post_data(
            title, content, status, categories, tags, 
            excerpt, slug, featured_media_id
        )
        
        try:
            logger.info(f"Updating post {post_id}: {title}")
            post = self.connector.post(f'/wp-json/wp/v2/posts/{post_id}', data=post_data)
            
            if not post or 'id' not in post:
                logger.error(f"Failed to update post {post_id}")
                return None
                
            logger.info(f"✅ Post updated: ID {post_id}")
            
            self._update_seo_meta(post_id, meta)
            
            return post
            
        except Exception as e:
            logger.error(f"❌ Failed to update post {post_id}: {e}")
            return None
