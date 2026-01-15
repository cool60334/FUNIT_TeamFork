from typing import List, Dict, Any
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.vector_db_manager import vector_db
import logging
from agents.core import PathResolver

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InternalLinkFinder:
    def __init__(self):
        self.resolver = PathResolver()

    def find_links_for_pillar(self, topic: str, category_name: str) -> List[Dict[str, Any]]:
        """
        Find relevant Cluster Pages for a Pillar Page.
        Strategy: Search within the same category for high similarity articles.
        """
        return self._find_links(topic, category_name, min_sim=0.4, max_sim=0.9, limit=15)

    def find_links_for_cluster(self, topic: str, category_name: str, pillar_slug: str = None) -> List[Dict[str, Any]]:
        """
        Find links for a Cluster Page.
        Strategy: 
        1. Link back to Pillar Page (if known).
        2. Link to other related Cluster Pages (Similarity Band 0.3-0.7).
        """
        links = []
        
        # 1. TODO: If we had a way to identify the Pillar Page technically (e.g., specific tag or flag), we'd fetch it here.
        # For now, we rely on P02 providing the pillar anchor/slug explicitly if known.
        
        # 2. Find related peers
        peers = self._find_links(topic, category_name, min_sim=0.3, max_sim=0.7, limit=5)
        links.extend(peers)
        
        return links

    def _find_links(self, topic: str, category_name: str, min_sim: float, max_sim: float, limit: int) -> List[Dict[str, Any]]:
        """
        Core logic for finding links within a similarity band.
        """
        # Use LanceDB-compatible operator ($like) for JSON-string categories
        where_filter = {"categories": {"$like": category_name}} if category_name else None
        
        # Query more than needed to filter by band
        results = vector_db.query_content_with_filter(
            query_text=topic,
            where=where_filter,
            n_results=limit * 3
        )
        
        valid_links = []
        seen_slugs = set()
        
        for res in results:
            sim = 1 - res.get('distance', 1.0)
            slug = res['metadata'].get('slug')
            
            if slug in seen_slugs:
                continue
                
            if min_sim <= sim <= max_sim:
                valid_links.append({
                    "title": res['metadata'].get('title'),
                    "slug": slug,
                    "url": res['metadata'].get('url', f"/{slug}/"),
                    "similarity": round(sim, 2),
                    "anchor_text_suggestion": res['metadata'].get('title') # Default anchor
                })
                seen_slugs.add(slug)
                
            if len(valid_links) >= limit:
                break
                
        return valid_links

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Internal Link Finder - 尋找相關內部連結")
    parser.add_argument("--topic", required=True, help="主題關鍵字")
    parser.add_argument("--category", required=False, default=None, help="分類名稱（選填）")
    parser.add_argument("--type", choices=["pillar", "cluster"], default="cluster", 
                        help="頁面類型 (pillar 或 cluster，預設為 cluster)")
    parser.add_argument("--pillar-slug", required=False, help="Pillar Page Slug（若為 cluster 頁面且已知）")
    args = parser.parse_args()
    
    finder = InternalLinkFinder()
    
    try:
        if args.type == "pillar":
            results = finder.find_links_for_pillar(args.topic, args.category)
            print(f"\n找到 {len(results)} 個適合 Pillar Page 的內部連結候選：\n")
        else:
            results = finder.find_links_for_cluster(args.topic, args.category, args.pillar_slug)
            print(f"\n找到 {len(results)} 個適合 Cluster Page 的內部連結候選：\n")
        
        if results:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            print("未找到相關文章。可能原因：")
            print("1. 向量資料庫中無相關內容")
            print("2. 分類篩選過於嚴格")
            print("建議：移除 --category 參數重試，或執行 site_auditor.py 同步最新資料")
    except Exception as e:
        logger.error(f"執行錯誤: {e}")
        print(f"\n❌ 錯誤: {e}")
        sys.exit(1)
