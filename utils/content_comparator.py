
"""
Content Comparator - 向量化內容比對工具
使用 Gemini Embedding 和 ChromaDB 進行語意比對，避免內容重複和關鍵字蠶食
"""

import os
import json
import logging
import argparse
from typing import List, Dict, Any
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.vector_db_manager import vector_db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentComparator:
    def __init__(self):
        # Access Vector DB directly
        pass

    def find_similar(self, topic: str, threshold: float = 0.5) -> List[Dict]:
        """
        全站搜尋相似文章 (Basic Vector Search)
        """
        results = vector_db.query_content(topic, n_results=20)
        
        candidates = []
        for res in results:
            # VectorDBManager returns 'distance'. Convert to similarity.
            # ChromaDB cosine distance: 0 (identical) -> 2 (opposite)
            # We assume distance is cosine distance here.
            distance = res.get('distance', 1.0)
            similarity = 1 - distance
            
            if similarity >= threshold:
                candidates.append({
                    "id": res['id'],
                    "title": res['metadata'].get('title', 'Unknown'),
                    "slug": res['metadata'].get('slug', ''),
                    "similarity": round(similarity, 3),
                    "categories": res['metadata'].get('categories', [])
                })
        
        return candidates

    def find_similar_with_category(self, topic: str, category_id: int = None, category_name: str = None) -> List[Dict]:
        """
        分類限定搜尋 (Category Filtered Search)
        使用 Two-Stage 策略：同分類優先 + 全站補充
        """
        candidates = []
        seen_ids = set()

        # Stage 1: Category Filter
        if category_id or category_name:
            where_filter = {}
            if category_id:
                where_filter = {"category_ids": {"$contains": str(category_id)}} # Assuming metadata stores as string/json list
            elif category_name:
                where_filter = {"categories": {"$contains": category_name}}
            
            cat_results = vector_db.query_content_with_filter(
                query_text=topic,
                where=where_filter,
                n_results=20
            )
            
            for res in cat_results:
                sim = 1 - res.get('distance', 1)
                if sim > 0.3: # Lower threshold for same category
                    candidates.append({**res, "similarity": round(sim, 3), "source": "category"})
                    seen_ids.add(res['id'])

        # Stage 2: Global Search (Supplement)
        global_results = vector_db.query_content(topic, n_results=20)
        for res in global_results:
            if res['id'] not in seen_ids:
                sim = 1 - res.get('distance', 1)
                if sim > 0.5: # Higher threshold for cross-category
                    candidates.append({**res, "similarity": round(sim, 3), "source": "global"})

        # Sort by similarity
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates

    def find_internal_link_candidates(self, topic: str, current_category: str = None) -> List[Dict]:
        """
        尋找內部連結建議 (Similarity Band Search)
        Target: Similarity 0.3 - 0.7 (避免重複，但要相關)
        """
        # 優先搜尋同分類
        where = {"categories": {"$contains": current_category}} if current_category else None
        
        raw_results = vector_db.query_content_with_filter(
            query_text=topic,
            where=where,
            n_results=30
        )
        
        candidates = []
        for res in raw_results:
            sim = 1 - res.get('distance', 1)
            # Similarity Band check
            if 0.3 <= sim <= 0.8: 
                candidates.append({
                    "title": res['metadata'].get('title'),
                    "slug": res['metadata'].get('slug'),
                    "similarity": round(sim, 3),
                    "reason": "Related Context"
                })
                
        return candidates[:10]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--action', choices=['search', 'link_suggest'], required=True)
    parser.add_argument('--topic', help='Search topic', required=True)
    parser.add_argument('--category', help='Category filter (name)')
    args = parser.parse_args()
    
    comparator = ContentComparator()
    
    if args.action == 'search':
        results = comparator.find_similar_with_category(args.topic, category_name=args.category)
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.action == 'link_suggest':
        results = comparator.find_internal_link_candidates(args.topic, current_category=args.category)
        print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

