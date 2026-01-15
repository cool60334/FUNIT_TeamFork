"""
Cluster Scanner - 雙軌內容重複性檢查工具
用於 P01 流程，解決純向量搜尋無法識別標題關鍵字重複的問題。

功能：
1. Track A: 標題關鍵字掃描 (Grep-like)
2. Track B: 語意向量搜尋 (Vector DB)
3. Track C: H2 結構比對 (從 LanceDB 取回全文解析)
"""

import os
import sys
import json
import logging
import argparse
import re
from typing import List, Dict, Any, Set

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.vector_db_manager import vector_db
from config.settings import settings
from agents.core import PathResolver

# Configure logging - route to stderr to avoid polluting JSON output
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define constants
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../outputs"))


class ClusterScanner:
    def __init__(self):
        self.resolver = PathResolver()
        self.brand_name = self.resolver.brand_manager.get_current_brand().slug
        self.site_structure_path = self.resolver.resolve("outputs/{BRAND_NAME}/raw_data/site_structure.json")
        self.posts = self._load_site_structure()
        
    def _load_site_structure(self) -> List[Dict]:
        """載入 site_structure.json"""
        if not os.path.exists(self.site_structure_path):
            logger.error(f"Site structure file not found: {self.site_structure_path}")
            return []
            
        try:
            with open(self.site_structure_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("posts", [])
        except Exception as e:
            logger.error(f"Failed to load site structure: {str(e)}")
            return []

    def _extract_h2s(self, content: str) -> List[str]:
        """從 Markdown 內容解析 H2 標題"""
        if not content:
            return []
        # 改進 regex 以支援各類換行符與簡單格式
        h2_pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
        return h2_pattern.findall(content)

    def _track_a_keyword_scan(self, topic: str, match_mode: str = "any") -> List[Dict]:
        """
        Track A: 標題關鍵字掃描 (支援 AND/OR 匹配)
        
        Args:
            topic: 搜尋詞 (空格分隔多個關鍵字)
            match_mode: 
                - "all": 所有關鍵字都必須存在 (AND)
                - "any": 任一關鍵字存在即可 (OR)
        """
        matches = []
        keywords = topic.split()
        
        # 如果是單一長詞且無空格，視為單一關鍵字
        if len(keywords) == 1 and len(topic) > 10:
            keywords = [topic]
            
        # Synonym Expansion (Can be extended via config in the future)
        extended_keywords = list(keywords)
        synonyms = {
            # Add brand-specific synonyms here if needed
            # e.g., "景點": "觀光地"
        }
        
        for k in keywords:
            k_lower = k.lower()
            if k_lower in synonyms:
                extended_keywords.append(synonyms[k_lower])
        
        # Use extended keywords for matching
        check_keywords = set([k.lower() for k in extended_keywords])
             
        for post in self.posts:
            title = post.get('title', '')
            title_lower = title.lower()
            
            # 計算匹配的關鍵字數量 (Check against extended keywords)
            # 這裡的邏輯是: 只要 matched 中包含了原本意圖的任一變體即可
            # 但為了簡單起見，我們先算有多少個 unique keyword 命中
            matched_keywords = [kw for kw in check_keywords if kw in title_lower]
            match_count = len(matched_keywords)
            
            # 根據匹配模式判定
            if match_mode == "all":
                is_match = (match_count == len(keywords))
            else:  # "any"
                is_match = (match_count > 0)
            
            if is_match:
                # 計算 relevance score (匹配關鍵字數 / 總關鍵字數)
                relevance = match_count / len(keywords) if keywords else 0
                
                matches.append({
                    "id": str(post.get('id')),
                    "title": title,
                    "slug": post.get('slug'),
                    "link": post.get('link'),
                    "match_type": "title_keyword",
                    "matched_keywords": matched_keywords,
                    "match_count": match_count,
                    "similarity": round(relevance, 2)  # 用 relevance 作為 similarity
                })
        
        # 按匹配數量排序 (匹配越多越前面)
        matches.sort(key=lambda x: x['match_count'], reverse=True)
        return matches

    def _track_b_vector_search(self, topic: str, exclude_ids: Set[str], threshold: float = 0.5) -> List[Dict]:
        """Track B: 語意向量搜尋"""
        results = vector_db.query_content(topic, n_results=10)
        candidates = []
        
        for res in results:
            doc_id = str(res['id'])
            if doc_id in exclude_ids:
                continue
                
            distance = res.get('distance', 1.0)
            similarity = 1 - distance
            
            if similarity >= threshold:
                candidates.append({
                    "id": doc_id,
                    "title": res['metadata'].get('title', 'Unknown'),
                    "slug": res['metadata'].get('slug', ''),
                    "match_type": "vector_semantic",
                    "similarity": round(similarity, 3)
                })
        return candidates

    def scan(self, topic: str, match_mode: str = "any") -> Dict[str, Any]:
        """
        執行雙軌掃描與 H2 分析
        
        Args:
            topic: 搜尋詞
            match_mode: "all" (AND) 或 "any" (OR)
        """
        logger.info(f"Scanning topic: {topic} (mode: {match_mode}) for brand: {self.brand_name}")
        
        # Track A
        track_a_results = self._track_a_keyword_scan(topic, match_mode=match_mode)
        found_ids = {r['id'] for r in track_a_results}
        
        # Track B
        track_b_results = self._track_b_vector_search(topic, exclude_ids=found_ids)
        
        # Merge Results
        all_candidates = track_a_results + track_b_results
        
        # Track C: Fetch Content & Extract H2s
        detailed_results = []
        for cand in all_candidates:
            # Fetch full content from DB
            db_res_list = vector_db.get_content_by_ids(ids=[cand['id']])
            content = ""
            h2s = []
            
            if db_res_list:
                db_res = db_res_list[0]
                content = db_res.get('document', '')
                h2s = self._extract_h2s(content)
            
            cand['h2_tags'] = h2s
            cand['h2_count'] = len(h2s)
            detailed_results.append(cand)
            
        # Decision Logic (Rule-based)
        recommendation = "create_new"
        reason = "No high similarity content found."
        
        if detailed_results:
            top_match = detailed_results[0]
            if top_match['match_type'] == 'title_keyword':
                recommendation = "optimize_existing"
                reason = f"Found existing article with keyword match: {top_match['title']}"
            elif top_match['similarity'] > 0.75:
                recommendation = "optimize_existing"
                reason = f"Found high semantic similarity article: {top_match['title']} ({top_match['similarity']})"
            else:
                recommendation = "check_manual"
                reason = "Found related content but similarity is moderate. Check H2s."

        return {
            "topic": topic,
            "candidates": detailed_results,
            "recommendation": recommendation,
            "reason": reason
        }

def main():
    parser = argparse.ArgumentParser(description="Cluster Content Scanner")
    parser.add_argument("--topic", required=True, help="Topic/Keyword to scan (空格分隔多個關鍵字)")
    parser.add_argument("--mode", choices=["all", "any"], default="any",
                        help="Match mode: 'all' = AND (全部符合), 'any' = OR (任一符合，預設)")
    args = parser.parse_args()
    
    scanner = ClusterScanner()
    result = scanner.scan(args.topic, match_mode=args.mode)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
