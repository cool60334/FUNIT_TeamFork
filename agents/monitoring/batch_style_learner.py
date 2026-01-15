#!/usr/bin/env python3
"""
Batch Style Learner - 批次風格學習工具
Iterates through WordPress posts and revisions to extract style rules into Style Memory.

Workflow:
1. Scan latest N posts or specific categories.
2. For each post, harvest revisions using AgentGardener.
3. Consolidate results into a batch report.
4. (Future) Use LLM to analyze the batch report and 'plant' rules.
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Fix paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional import for Style Gardener
try:
    from agents.monitoring.style_gardener import AgentGardener
    from utils.wordpress_client import wp_client
except ImportError as e:
    print(f"❌ Error importing dependencies: {e}")
    sys.exit(1)

class BatchStyleLearner:
    def __init__(self, brand_name="FUNIT"):
        self.brand_name = brand_name
        self.gardener = AgentGardener()
        self.output_dir = Path(f"outputs/{self.brand_name}/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def learn_styles(self, count=10, revisions_per_post=1):
        """Scans posts and extracts revision diffs."""
        print(f"\n{'='*60}")
        print(f"🎨 Batch Style Learner - 開始批次學習 ({self.brand_name})")
        print(f"{'='*60}\n")

        print(f"🔍 正在抓取最近 {count} 篇文章...")
        posts, _ = wp_client.get_posts_batch(page=1, per_page=count)
        
        if not posts:
            print("⚠️ 找不到任何文章")
            return

        report = {
            "meta": {
                "brand_name": self.brand_name,
                "total_posts_scanned": len(posts),
                "generated_at": datetime.now().isoformat(),
                "posts_with_changes": 0,
                "total_meaningful_diffs": 0
            },
            "details": []
        }

        for post in posts:
            post_id = post['id']
            title = post['title']['rendered']
            print(f"\n------------------------------------------------------------")
            print(f"📄 處理文章: [{post_id}] {title[:30]}...")

            # Harvest diffs
            diff_report = self.gardener.harvest(post_id, count=revisions_per_post)
            
            if diff_report and diff_report.get('diffs'):
                meaningful_diffs = diff_report['diffs']
                report["meta"]["posts_with_changes"] += 1
                report["meta"]["total_meaningful_diffs"] += len(meaningful_diffs)
                
                report["details"].append({
                    "post_id": post_id,
                    "title": title,
                    "has_changes": True,
                    "revision_count": len(meaningful_diffs),
                    "total_meaningful_diffs": sum(len(d['changes']) for d in meaningful_diffs),
                    "comparisons": meaningful_diffs
                })
                print(f"✅ 發現修訂差異")
            else:
                report["details"].append({
                    "post_id": post_id,
                    "title": title,
                    "has_changes": False
                })
                print(f"⏭️ 無修訂差異")

        # Save report
        report_path = self.output_dir / f"batch_style_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n{'='*60}")
        print(f"📊 學習任務完成！")
        print(f"   總文章數: {report['meta']['total_posts_scanned']}")
        print(f"   有差異篇數: {report['meta']['posts_with_changes']}")
        print(f"   報告路徑: {report_path}")
        print(f"{'='*60}\n")
        
        return report_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Style Learner")
    parser.add_argument("--count", type=int, default=10, help="Number of latest posts to scan")
    parser.add_argument("--revs", type=int, default=1, help="Number of revisions per post to analyze")
    args = parser.parse_args()
    
    learner = BatchStyleLearner()
    learner.learn_styles(count=args.count, revisions_per_post=args.revs)
