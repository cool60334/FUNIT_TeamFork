#!/usr/bin/env python3
"""
Refactor Article Agent - 重構工程師
Automates the process of refactoring existing WordPress articles.

Execution flow:
1. Fetch existing content from WordPress.
2. Clean HTML and extract text artifacts.
3. Run P02 Content Architect to generate a new optimized brief.
4. Save the new brief in the pipeline.
"""

import os
import sys
import argparse
import json
import logging
import html as html_lib
import re
from pathlib import Path
from typing import Dict, Any

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Try to use new architecture
try:
    from agents.core import BaseAgent
    from agents.planning.p02_content_architect import P02ContentArchitect
    from utils.wordpress_client import wp_client
    USE_NEW_ARCHITECTURE = True
except ImportError:
    USE_NEW_ARCHITECTURE = False
    print("Warning: New architecture modules not found. Using standalone mode.")

class RefactorArticleAgent(BaseAgent if USE_NEW_ARCHITECTURE else object):
    def __init__(self):
        if USE_NEW_ARCHITECTURE:
            super().__init__(name="Refactor_Article")
            self.brand_name = self.brand.slug
        else:
            self.brand_name = "FUNIT"
            
        self.output_dir = Path(f"outputs/{self.brand_name}/strategies")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_html(self, html_content: str) -> str:
        """Cleans WordPress HTML for better LLM processing."""
        if not html_content:
            return ""
        
        # 1. Remove Table of Contents containers
        html_content = re.sub(r'<div class="ez-toc-container".*?</div>', '', html_content, flags=re.DOTALL)
        
        # 2. Extract Alt Text from images and put it into the text
        html_content = re.sub(r'<img.*?alt="(.*?)".*?>', r'\n[Image: \1]\n', html_content)
        
        # 3. Strip all other tags
        text = re.sub(r'<[^>]+>', '\n', html_content)
        
        # 4. Decode HTML entities
        text = html_lib.unescape(text)
        
        # 5. Clean whitespace
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join([line for line in lines if line])
        
        return text

    def refactor(self, post_id: int):
        """Main refactoring logic."""
        print(f"\n{'='*60}")
        print(f"🔄 Refactor Article Agent - 文章重構中 (ID: {post_id})")
        print(f"{'='*60}\n")

        # 1. Fetch Post
        print(f"📥 正在從 WordPress 抓取文章 {post_id}...")
        try:
            post = wp_client.get_post(post_id)
            if not post:
                print(f"❌ 錯誤: 找不到文章 {post_id}")
                return
            
            title = post.get('title', {}).get('rendered', 'Untitled')
            raw_content = post.get('content', {}).get('rendered', '')
            slug = post.get('slug', '')
            
            print(f"✅ 成功抓取: {title}")
        except Exception as e:
            print(f"❌ 抓取失敗: {e}")
            return

        # 2. Clean Content
        print("🧹 正在清洗內容檔案...")
        cleaned_content = self.clean_html(raw_content)
        
        # 3. Preparatory strategy data for P02
        # Since we are refactoring, we use the existing content as the "Research Data"
        strategy_data = {
            "title": title,
            "original_slug": slug,
            "refactoring_source": cleaned_content[:5000],  # Limit length for LLM
            "is_refactoring": True,
            "primary_keyword": slug.replace('-', ' ') # Guessing PK from slug if not provided
        }
        
        strategy_file = self.output_dir / f"refactor_strategy_{post_id}.json"
        with open(strategy_file, "w", encoding="utf-8") as f:
            json.dump(strategy_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 暫存策略檔案已儲存: {strategy_file}")

        # 4. Trigger P02 Content Architect
        print("\n🚀 正在調度 P02 Content Architect 生成新 Brief...")
        try:
            architect = P02ContentArchitect()
            results = architect.run({
                "strategy_path": str(strategy_file),
                "topic": title,  # 使用原文標題作為新 Brief 的主題
                "is_refactoring": True
            })
            
            if results.get("status") == "success":
                print(f"\n✅ 重構成功！新 Brief 已生成於: {results.get('brief_path')}")
                return results
            else:
                print(f"\n❌ P02 執行失敗: {results.get('message')}")
        except Exception as e:
            print(f"\n❌ 調度失敗: {e}")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """BaseAgent run implementation."""
        post_id = input_data.get("post_id") or input_data.get("id")
        if not post_id:
            raise ValueError("缺少參數: post_id")
        
        return self.refactor(int(post_id))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Refactor Article Agent")
    parser.add_argument("--id", type=int, required=True, help="WordPress Post ID to refactor")
    args = parser.parse_args()
    
    agent = RefactorArticleAgent()
    agent.refactor(args.id)
