#!/usr/bin/env python3
"""
Revision Scanner - 全站修訂紀錄掃描與分析工具

Purpose: 
1. 從 site_structure.json 讀取所有文章
2. 批次抓取每篇文章的 WordPress 修訂紀錄
3. 分析有意義的差異（過濾純格式調整）
4. 輸出結構化 JSON 報告供 Style Gardener 使用

Usage:
    # 掃描全站並輸出報告
    python3 agents/monitoring/revision_scanner.py scan
    
    # 掃描並只顯示有差異的文章
    python3 agents/monitoring/revision_scanner.py scan --only-changes
    
    # 掃描特定數量的文章（用於測試）
    python3 agents/monitoring/revision_scanner.py scan --limit 10
    
    # 指定輸出檔案
    python3 agents/monitoring/revision_scanner.py scan --output reports/revision_report.json

Output:
    outputs/FUNIT/reports/revision_scan_{timestamp}.json
"""

import subprocess
import json
import re
import html as html_lib
import difflib
import time
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
# 載入專案根目錄的 .env
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

class RevisionScanner:
    def __init__(self):
        self.site_url = os.getenv("WP_SITE_URL")
        self.username = os.getenv("WP_USERNAME")
        self.app_password = os.getenv("WP_APP_PASSWORD")
        self.brand_name = "FUNIT"
        
        # 建立輸出目錄
        self.output_dir = Path("outputs/FUNIT/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # site_structure.json 路徑 (raw_data 是 Site Auditor 的輸出目錄)
        self.site_structure_path = Path("outputs/FUNIT/raw_data/site_structure.json")
        
    def _curl_request(self, endpoint: str) -> dict:
        """使用 curl 發送請求（繞過 WAF）"""
        result = subprocess.run([
            'curl', '-s',
            '-u', f'{self.username}:{self.app_password}',
            endpoint
        ], capture_output=True, text=True)
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return None
    
    def _clean_html(self, raw_html: str) -> str:
        """清洗 HTML，返回純文字"""
        if not raw_html:
            return ""
        text = re.sub(r'<!--.*?-->', '', raw_html, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        text = html_lib.unescape(text)
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)
    
    def _is_meaningful_diff(self, before: str, after: str) -> bool:
        """判斷是否為有意義的差異（非純格式調整）"""
        if not before.strip() and not after.strip():
            return False
        
        # 純括號格式變化
        if before.replace('(', '（').replace(')', '）') == after:
            return False
        if before.replace('（', '(').replace('）', ')') == after:
            return False
        
        # 純空白變化
        if before.replace(' ', '').replace('\n', '') == after.replace(' ', '').replace('\n', ''):
            return False
        
        # 純冒號格式變化
        if before.replace(':', '：') == after or before.replace('：', ':') == after:
            return False
            
        return True
    
    def _extract_diffs(self, content_before: str, content_after: str) -> list:
        """提取兩版本間的差異"""
        lines_before = content_before.split('\n')
        lines_after = content_after.split('\n')
        
        d = difflib.unified_diff(lines_before, lines_after, lineterm='', n=0)
        
        current_block = {'before': [], 'after': []}
        blocks = []
        
        for line in d:
            if line.startswith('@@'):
                if current_block['before'] or current_block['after']:
                    blocks.append(current_block)
                    current_block = {'before': [], 'after': []}
            elif line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('-'):
                current_block['before'].append(line[1:])
            elif line.startswith('+'):
                current_block['after'].append(line[1:])
        
        if current_block['before'] or current_block['after']:
            blocks.append(current_block)
        
        # 過濾有意義的差異
        meaningful_diffs = []
        for block in blocks:
            before_text = '\n'.join(block['before'])
            after_text = '\n'.join(block['after'])
            
            if self._is_meaningful_diff(before_text, after_text):
                meaningful_diffs.append({
                    'before': before_text,
                    'after': after_text,
                    'before_preview': before_text[:200] + ('...' if len(before_text) > 200 else ''),
                    'after_preview': after_text[:200] + ('...' if len(after_text) > 200 else '')
                })
        
        return meaningful_diffs
    
    def fetch_revisions(self, post_id: int) -> list:
        """抓取單篇文章的修訂紀錄"""
        endpoint = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}/revisions?per_page=10"
        return self._curl_request(endpoint) or []
    
    def analyze_post(self, post_id: int, title: str) -> dict:
        """分析單篇文章的修訂紀錄"""
        revisions = self.fetch_revisions(post_id)
        
        if not isinstance(revisions, list) or len(revisions) < 2:
            return {
                'post_id': post_id,
                'title': title,
                'revision_count': len(revisions) if isinstance(revisions, list) else 0,
                'has_changes': False,
                'comparisons': []
            }
        
        comparisons = []
        
        for i in range(min(5, len(revisions) - 1)):
            latest = revisions[i]
            previous = revisions[i + 1]
            
            latest_clean = self._clean_html(latest['content']['rendered'])
            previous_clean = self._clean_html(previous['content']['rendered'])
            
            diffs = self._extract_diffs(previous_clean, latest_clean)
            
            if diffs:
                comparisons.append({
                    'latest_id': latest['id'],
                    'latest_date': latest['date'],
                    'previous_id': previous['id'],
                    'previous_date': previous['date'],
                    'diff_count': len(diffs),
                    'diffs': diffs
                })
        
        return {
            'post_id': post_id,
            'title': title,
            'revision_count': len(revisions),
            'has_changes': len(comparisons) > 0,
            'total_meaningful_diffs': sum(c['diff_count'] for c in comparisons),
            'comparisons': comparisons
        }
    
    def scan_all(self, limit: int = None, only_changes: bool = False, delay: float = 0.3) -> dict:
        """掃描全站文章"""
        # 載入 site_structure.json
        if not self.site_structure_path.exists():
            print(f"❌ 找不到 {self.site_structure_path}")
            return None
        
        with open(self.site_structure_path, 'r', encoding='utf-8') as f:
            site_data = json.load(f)
        
        posts = site_data.get('posts', [])
        
        if limit:
            posts = posts[:limit]
        
        print(f"📊 全站修訂紀錄掃描")
        print(f"📋 共 {len(posts)} 篇文章待分析")
        print(f"🌐 網站: {self.site_url}")
        print("=" * 70)
        
        results = []
        posts_with_changes = 0
        total_diffs = 0
        
        for i, post in enumerate(posts, 1):
            post_id = post['id']
            title = post['title'][:50]
            
            result = self.analyze_post(post_id, post['title'])
            
            if result['has_changes']:
                posts_with_changes += 1
                total_diffs += result['total_meaningful_diffs']
                print(f"✅ [{i}/{len(posts)}] ID {post_id}: {result['revision_count']} 版本, {result['total_meaningful_diffs']} 差異 - {title}")
                results.append(result)
            else:
                if not only_changes:
                    print(f"⬜ [{i}/{len(posts)}] ID {post_id}: {result['revision_count']} 版本 - {title}")
                    results.append(result)
            
            time.sleep(delay)  # 避免 API 限流
        
        # 生成報告
        report = {
            'meta': {
                'generated_at': datetime.now().isoformat(),
                'brand_name': self.brand_name,
                'site_url': self.site_url,
                'total_posts_scanned': len(posts),
                'posts_with_changes': posts_with_changes,
                'total_meaningful_diffs': total_diffs
            },
            'summary': {
                'posts_needing_review': [
                    {
                        'post_id': r['post_id'],
                        'title': r['title'],
                        'diff_count': r['total_meaningful_diffs']
                    }
                    for r in results if r['has_changes']
                ]
            },
            'details': results if not only_changes else [r for r in results if r['has_changes']]
        }
        
        return report
    
    def save_report(self, report: dict, output_path: str = None) -> str:
        """儲存報告至 JSON 檔案"""
        if output_path:
            filepath = Path(output_path)
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = self.output_dir / f"revision_scan_{timestamp}.json"
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    def print_summary(self, report: dict):
        """印出掃描摘要"""
        meta = report['meta']
        summary = report['summary']
        
        print("\n" + "=" * 70)
        print("📊 掃描結果摘要")
        print("=" * 70)
        print(f"🌐 網站: {meta['site_url']}")
        print(f"📋 掃描文章數: {meta['total_posts_scanned']}")
        print(f"✅ 有修改的文章: {meta['posts_with_changes']}")
        print(f"🔍 有意義差異總數: {meta['total_meaningful_diffs']}")
        
        if summary['posts_needing_review']:
            print(f"\n🎯 需要審核的文章 ({len(summary['posts_needing_review'])} 篇):")
            for post in summary['posts_needing_review']:
                print(f"   📌 ID {post['post_id']}: {post['diff_count']} 差異 - {post['title'][:40]}...")


def main():
    parser = argparse.ArgumentParser(description='全站修訂紀錄掃描與分析工具')
    subparsers = parser.add_subparsers(dest='command', help='可用指令')
    
    # Scan subcommand
    scan_parser = subparsers.add_parser('scan', help='掃描全站修訂紀錄')
    scan_parser.add_argument('--limit', type=int, help='限制掃描文章數量（用於測試）')
    scan_parser.add_argument('--only-changes', action='store_true', help='只顯示有差異的文章')
    scan_parser.add_argument('--output', type=str, help='指定輸出檔案路徑')
    scan_parser.add_argument('--delay', type=float, default=0.3, help='API 請求間隔（秒）')
    scan_parser.add_argument('--no-save', action='store_true', help='不儲存報告檔案')
    
    args = parser.parse_args()
    
    if args.command == 'scan':
        scanner = RevisionScanner()
        
        report = scanner.scan_all(
            limit=args.limit,
            only_changes=args.only_changes,
            delay=args.delay
        )
        
        if report:
            scanner.print_summary(report)
            
            if not args.no_save:
                filepath = scanner.save_report(report, args.output)
                print(f"\n💾 報告已儲存: {filepath}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
