"""
Full Site Crawler - 完整網站文章爬取器
用於爬取 600+ 篇文章的標題、摘要、H2 結構等關鍵資訊
"""

import json
import os
import re
import argparse
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FullSiteCrawler:
    """完整網站爬取器，提取所有文章的詳細資訊"""
    
    def __init__(self, brand_name: str):
        self.brand_name = brand_name
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.output_dir = os.path.join(self.base_dir, "outputs", brand_name, "raw_data")
        
        # Load WordPress credentials
        self._load_config()
        
    def _load_config(self):
        """載入 WordPress 設定"""
        from dotenv import load_dotenv
        load_dotenv(os.path.join(self.base_dir, '.env'))
        
        self.wp_url = os.environ.get("WP_SITE_URL", "")
        self.wp_username = os.environ.get("WP_USERNAME", "")
        self.wp_password = os.environ.get("WP_APP_PASSWORD", "")
        
        if not all([self.wp_url, self.wp_username, self.wp_password]):
            raise ValueError("Missing WordPress credentials in .env")
    
    def _fetch_api(self, endpoint: str, params: Dict = None) -> Optional[Any]:
        """使用 curl 呼叫 WordPress API（避免 WAF 阻擋）"""
        url = f"{self.wp_url}/wp-json/wp/v2/{endpoint}"
        
        # Build query string
        if params:
            query_parts = [f"{k}={v}" for k, v in params.items()]
            url += "?" + "&".join(query_parts)
        
        try:
            result = subprocess.run(
                ['curl', '-s', '-u', f'{self.wp_username}:{self.wp_password}', url],
                capture_output=True, text=True, timeout=30
            )
            return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return None
    
    def _extract_h2_headings(self, html_content: str) -> List[str]:
        """從 HTML 內容中提取所有 H2 標題"""
        soup = BeautifulSoup(html_content, 'html.parser')
        h2_tags = soup.find_all('h2')
        return [h2.get_text(strip=True) for h2 in h2_tags]
    
    def _count_words(self, html_content: str) -> int:
        """計算文章字數（中文字元 + 英文單詞）"""
        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()
        
        # Count Chinese characters
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        
        # Count English words
        english_words = len(re.findall(r'[a-zA-Z]+', text))
        
        return chinese_chars + english_words
    
    def _extract_meta_description(self, post_id: int) -> str:
        """提取 Rank Math SEO 的 Meta Description"""
        # Try to get from post meta
        meta = self._fetch_api(f"posts/{post_id}", {"_fields": "meta"})
        if meta and 'meta' in meta:
            return meta.get('meta', {}).get('rank_math_description', '')
        return ''
    
    def crawl_all_posts(self, include_drafts: bool = False) -> List[Dict[str, Any]]:
        """爬取所有文章"""
        all_posts = []
        page = 1
        per_page = 100  # Maximum allowed by WordPress API
        
        status = "publish,draft" if include_drafts else "publish"
        
        logger.info(f"Starting full site crawl for {self.brand_name}...")
        
        while True:
            logger.info(f"Fetching page {page}...")
            
            posts = self._fetch_api("posts", {
                "page": page,
                "per_page": per_page,
                "status": status,
                "_fields": "id,title,slug,excerpt,content,categories,tags,date,modified"
            })
            
            # Check if posts is a list (valid response) or dict (error response)
            if isinstance(posts, dict):
                if 'code' in posts:
                    if posts['code'] == 'rest_post_invalid_page_number':
                        logger.info("Reached end of pages.")
                    else:
                        logger.warning(f"API returned error: {posts.get('message')}")
                break
            
            if not isinstance(posts, list):
                logger.error(f"Unexpected API response format: {type(posts)}")
                break
            
            if len(posts) == 0:
                break
            
            for post in posts:
                post_data = self._process_post(post)
                all_posts.append(post_data)
                logger.info(f"  Processed: {post_data['title'][:50]}...")
            
            page += 1
            
            # Safety limit
            if page > 100:
                logger.warning("Reached page limit (100 pages)")
                break
        
        logger.info(f"Crawl complete. Total posts: {len(all_posts)}")
        return all_posts
    
    def _process_post(self, post: Dict) -> Dict[str, Any]:
        """處理單篇文章，提取所需資訊"""
        content_html = post.get('content', {}).get('rendered', '')
        
        return {
            "id": post.get('id'),
            "title": post.get('title', {}).get('rendered', ''),
            "slug": post.get('slug', ''),
            "excerpt": BeautifulSoup(
                post.get('excerpt', {}).get('rendered', ''), 'html.parser'
            ).get_text(strip=True)[:200],
            "h2_headings": self._extract_h2_headings(content_html),
            "word_count": self._count_words(content_html),
            "categories": post.get('categories', []),
            "tags": post.get('tags', []),
            "date": post.get('date', ''),
            "last_modified": post.get('modified', '')
        }
    
    def save_to_index(self, posts: List[Dict[str, Any]], filename: str = "posts_index.json"):
        """存儲爬取結果"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        output_path = os.path.join(self.output_dir, filename)
        
        index_data = {
            "crawl_date": datetime.now().isoformat(),
            "brand_name": self.brand_name,
            "total_posts": len(posts),
            "posts": posts
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Index saved to: {output_path}")
        return output_path
    
    def generate_summary(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成爬取摘要統計"""
        total_words = sum(p['word_count'] for p in posts)
        avg_h2_count = sum(len(p['h2_headings']) for p in posts) / len(posts) if posts else 0
        
        return {
            "total_posts": len(posts),
            "total_words": total_words,
            "avg_word_count": total_words // len(posts) if posts else 0,
            "avg_h2_count": round(avg_h2_count, 1)
        }


def main():
    parser = argparse.ArgumentParser(description='Full Site Crawler')
    parser.add_argument('--brand', required=True, help='Brand name')
    parser.add_argument('--include-drafts', action='store_true', help='Include draft posts')
    parser.add_argument('--output', default='posts_index.json', help='Output filename')
    
    args = parser.parse_args()
    
    try:
        crawler = FullSiteCrawler(args.brand)
        posts = crawler.crawl_all_posts(include_drafts=args.include_drafts)
        output_path = crawler.save_to_index(posts, args.output)
        
        summary = crawler.generate_summary(posts)
        print("\n" + "=" * 60)
        print("📊 爬取完成摘要")
        print("=" * 60)
        print(f"📝 總文章數: {summary['total_posts']}")
        print(f"📖 總字數: {summary['total_words']:,}")
        print(f"📏 平均字數: {summary['avg_word_count']:,}")
        print(f"📑 平均 H2 數: {summary['avg_h2_count']}")
        print(f"💾 存儲位置: {output_path}")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Crawl failed: {e}")
        raise


if __name__ == "__main__":
    main()
