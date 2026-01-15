#!/usr/bin/env python3
"""
Agent Gardener - 資料準備與風格管理工具

Purpose: 
1. Harvest: 從 WordPress Revision 抓取差異，輸出結構化的 JSON 報告。
2. Plant: 將分析後的風格範例存入 Style Memory。

Usage:
    # 抓取差異
    python3 agents/monitoring/style_gardener.py harvest --post-id <ID> [--count <N>]

    # 存入風格
    python3 agents/monitoring/style_gardener.py plant --trigger "..." --change "..." --bad "..." --good "..." --tags "..."
"""

import requests
import os
import sys
import re
import argparse
from dotenv import load_dotenv
import base64
import json
import html as html_lib
from datetime import datetime

# Add project root to path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.insert(0, PROJECT_ROOT)

# Optional import for plant mode
try:
    from utils.style_memory_manager import StyleMemoryManager
    STYLE_MEMORY_AVAILABLE = True
except ImportError as e:
    # try path relative to project root if running as module
    try:
        from utils.style_memory_manager import StyleMemoryManager
        STYLE_MEMORY_AVAILABLE = True
    except ImportError:
        STYLE_MEMORY_AVAILABLE = False
        print(f"⚠️ StyleMemoryManager 不可用: {e}")

# 多品牌架構：使用專案根目錄的 .env symlink
env_path = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Fallback to config/.env for backward compatibility
    load_dotenv(os.path.join(PROJECT_ROOT, 'config/.env'))

class AgentGardener:
    def __init__(self):
        self.site_url = os.getenv("WP_SITE_URL")
        self.username = os.getenv("WP_USERNAME")
        self.app_password = os.getenv("WP_APP_PASSWORD")
        
        # 使用 requests auth tuple 取代手動 Base64 編碼
        if self.username and self.app_password:
            self.auth = (self.username, self.app_password)
        else:
            self.auth = None
        
        # 加入 User-Agent 避免被 WAF/OpenResty 阻擋
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        self.brand_profile = self._load_brand_profile()

    def _load_brand_profile(self):
        """Loads the brand profile JSON."""
        profile_path = os.path.join(PROJECT_ROOT, "config/brand_profile.json")
        if not os.path.exists(profile_path):
            return {}
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Error loading brand profile: {e}")
            return {}


    def fetch_revisions(self, post_id, count=1):
        """
        抓取文章的修訂紀錄
        
        Args:
            post_id: 文章 ID
            count: 要分析的版本數量 (無上限，會自動分頁抓取)
            
        Returns:
            list: [(latest_content, previous_content, revision_info), ...]
        """
        if not self.auth:
            print("❌ 錯誤: 未設定 WP_USERNAME 或 WP_APP_PASSWORD")
            return []

        endpoint = f"{self.site_url}/wp-json/wp/v2/posts/{post_id}/revisions"
        
        # 分頁抓取所有需要的修訂
        all_revisions = []
        page = 1
        per_page = 100  # WordPress API 最大值
        needed = count + 1  # 需要 count+1 筆才能比對 count 組
        
        try:
            while len(all_revisions) < needed:
                response = requests.get(
                    endpoint, 
                    auth=self.auth,
                    headers=self.headers, 
                    params={'per_page': per_page, 'page': page}
                )
                response.raise_for_status()
                batch = response.json()
                
                if not batch:
                    break  # 沒有更多資料
                    
                all_revisions.extend(batch)
                
                # 檢查是否還有下一頁
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                page += 1
            
            revisions = all_revisions[:needed]  # 只取需要的數量
            
            if len(revisions) < 2:
                print(f"⚠️ 文章 {post_id} 只有 {len(revisions)} 個版本，無法比對")
                return []
            
            # 返回連續版本對
            pairs = []
            for i in range(min(count, len(revisions) - 1)):
                latest = revisions[i]
                previous = revisions[i + 1]
                
                pairs.append({
                    'latest': {
                        'id': latest['id'],
                        'date': latest['date'],
                        'content': latest['content']['rendered']
                    },
                    'previous': {
                        'id': previous['id'],
                        'date': previous['date'],
                        'content': previous['content']['rendered']
                    }
                })
            
            print(f"✅ 成功抓取 {len(pairs)} 組修訂紀錄")
            return pairs
            
        except Exception as e:
            print(f"❌ 抓取失敗: {e}")
            return []

    def clean_html(self, raw_html):
        """清洗 HTML，返回純文字"""
        if not raw_html:
            return ""
        
        # 移除 Gutenberg 註解
        text = re.sub(r'<!--.*?-->', '', raw_html, flags=re.DOTALL)
        # 移除 HTML 標籤
        text = re.sub(r'<[^>]+>', '', text)
        # 解碼 HTML 實體
        text = html_lib.unescape(text)
        # 清理空白
        lines = [line.strip() for line in text.split('\n')]
        lines = [line for line in lines if line]
        text = '\n'.join(lines)
        
        return text

    def extract_diff(self, text_before, text_after):
        """
        提取差異片段
        
        Returns:
            list: [{'before': '...', 'after': '...', 'context': '...'}, ...]
        """
        import difflib
        
        lines_before = text_before.split('\n')
        lines_after = text_after.split('\n')
        
        diff = difflib.unified_diff(lines_before, lines_after, lineterm='', n=2)
        
        changes = []
        current_before = []
        current_after = []
        context_before = []
        context_after = []
        
        in_change = False
        
        for line in diff:
            if line.startswith('@@'):
                # 新的差異區塊
                if current_before or current_after:
                    changes.append({
                        'before': '\n'.join(current_before),
                        'after': '\n'.join(current_after),
                        'context_before': '\n'.join(context_before),
                        'context_after': '\n'.join(context_after)
                    })
                    current_before = []
                    current_after = []
                    context_before = []
                    context_after = []
                in_change = True
            elif line.startswith('---') or line.startswith('+++'):
                continue
            elif line.startswith('-'):
                current_before.append(line[1:])
            elif line.startswith('+'):
                current_after.append(line[1:])
            elif line.startswith(' '):
                # 上下文
                if not current_before and not current_after:
                    context_before.append(line[1:])
                else:
                    context_after.append(line[1:])
        
        # 處理最後一個change
        if current_before or current_after:
            changes.append({
                'before': '\n'.join(current_before),
                'after': '\n'.join(current_after),
                'context_before': '\n'.join(context_before),
                'context_after': '\n'.join(context_after)
            })
        
        return changes

    def harvest(self, post_id, count=1, output_json=False):
        """
        完整的資料準備流程
        
        Returns:
            dict: 結構化的差異報告
        """
        print(f"\n{'='*60}")
        print(f"🌱 Agent Gardener - 資料準備中 (Harvest Mode)")
        print(f"{'='*60}\n")
        
        # Step 1: 抓取修訂紀錄
        print(f"📥 Step 1: 抓取最近 {count} 次修改...")
        revision_pairs = self.fetch_revisions(post_id, count)
        
        if not revision_pairs:
            return None
        
        # Step 2 & 3: 清洗與提取差異
        all_diffs = []
        
        for idx, pair in enumerate(revision_pairs, 1):
            print(f"\n🧹 處理第 {idx} 組修改...")
            print(f"   版本: {pair['latest']['id']} ({pair['latest']['date']})")
            print(f"   ← {pair['previous']['id']} ({pair['previous']['date']})")
            
            # 清洗
            latest_clean = self.clean_html(pair['latest']['content'])
            previous_clean = self.clean_html(pair['previous']['content'])
            
            # 提取差異
            changes = self.extract_diff(previous_clean, latest_clean)
            
            if changes:
                print(f"   ✅ 發現 {len(changes)} 個差異片段")
                all_diffs.append({
                    'revision_info': {
                        'latest_id': pair['latest']['id'],
                        'latest_date': pair['latest']['date'],
                        'previous_id': pair['previous']['id'],
                        'previous_date': pair['previous']['date']
                    },
                    'changes': changes
                })
            else:
                print(f"   ⚠️ 未發現語意差異")
        
        # Step 4: 輸出報告
        report = {
            'post_id': post_id,
            'total_revisions_analyzed': len(revision_pairs),
            'total_changes_found': sum(len(d['changes']) for d in all_diffs),
            'timestamp': datetime.now().isoformat(),
            'diffs': all_diffs
        }
        
        if output_json:
            # 輸出為 JSON 檔案
            filename = f"diff_report_{post_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"\n💾 報告已儲存: {filename}")
        else:
            # 輸出到終端機
            print(f"\n{'='*60}")
            print(f"📋 差異報告")
            print(f"{'='*60}\n")
            print(json.dumps(report, ensure_ascii=False, indent=2))
        
        return report

    def plant(self, trigger, change, bad, good, tags):
        """
        將風格範例存入 Style Memory
        """
        print(f"\n{'='*60}")
        print(f"🌱 Agent Gardener - 種植風格 (Plant Mode)")
        print(f"{'='*60}\n")
        
        try:
            mgr = StyleMemoryManager()
            
            # Parse tags if string
            if isinstance(tags, str):
                tags_list = [t.strip() for t in tags.split(',')]
            else:
                tags_list = tags

            print(f"📝 正在存入範例...")
            print(f"   情境: {trigger}")
            print(f"   變化: {change}")
            
            ex_id = mgr.add_example(
                trigger_scenario=trigger,
                style_change=change,
                bad_example=bad,
                good_example=good,
                tags=tags_list
            )
            
            if ex_id:
                print(f"\n✅ 種植成功！ ID: {ex_id}")
                return True
            else:
                print(f"\n❌ 種植失敗")
                return False
                
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")
            return False

    def analyze_report(self, report_path: str, interactive: bool = True):
        """
        分析 revision_scanner 產出的報告，並決定是否存入 Style Memory
        
        Args:
            report_path: revision_scanner 報告的路徑
            interactive: 是否進入互動模式讓使用者決定
        """
        print(f"\n{'='*60}")
        print(f"🌱 Agent Gardener - 報告分析 (Analyze Mode)")
        print(f"{'='*60}\n")
        
        # 讀取報告
        if not os.path.exists(report_path):
            print(f"❌ 找不到報告: {report_path}")
            return None
        
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        
        meta = report.get('meta', {})
        details = report.get('details', [])
        
        print(f"📊 報告資訊:")
        print(f"   品牌: {meta.get('brand_name', 'N/A')}")
        print(f"   掃描時間: {meta.get('generated_at', 'N/A')}")
        print(f"   文章數: {meta.get('total_posts_scanned', 0)}")
        print(f"   有差異文章: {meta.get('posts_with_changes', 0)}")
        print(f"   差異總數: {meta.get('total_meaningful_diffs', 0)}")
        
        # 篩選有差異的文章
        posts_with_changes = [d for d in details if d.get('has_changes', False)]
        
        if not posts_with_changes:
            print("\n⚠️ 報告中沒有需要分析的差異")
            return []
        
        print(f"\n{'='*60}")
        print(f"🔍 開始分析 {len(posts_with_changes)} 篇有修改的文章")
        print(f"{'='*60}")
        
        all_diffs = []
        
        for post in posts_with_changes:
            post_id = post['post_id']
            title = post['title']
            
            print(f"\n📌 ID {post_id}: {title[:50]}...")
            print(f"   版本數: {post['revision_count']}, 差異數: {post['total_meaningful_diffs']}")
            
            for comp in post.get('comparisons', []):
                for i, diff in enumerate(comp.get('diffs', []), 1):
                    diff_info = {
                        'post_id': post_id,
                        'title': title,
                        'version': f"{comp['latest_id']} ← {comp['previous_id']}",
                        'date': comp['latest_date'],
                        'before': diff['before'],
                        'after': diff['after'],
                        'before_preview': diff.get('before_preview', diff['before'][:100]),
                        'after_preview': diff.get('after_preview', diff['after'][:100])
                    }
                    all_diffs.append(diff_info)
                    
                    print(f"\n   【差異 #{len(all_diffs)}】")
                    print(f"   ❌ 刪除: {diff_info['before_preview']}")
                    print(f"   ✅ 新增: {diff_info['after_preview']}")
        
        print(f"\n{'='*60}")
        print(f"📊 分析完成: 共 {len(all_diffs)} 個差異待審核")
        print(f"{'='*60}")
        
        # 輸出結構化結果供進一步處理
        return {
            'meta': meta,
            'total_diffs': len(all_diffs),
            'diffs': all_diffs
        }


def main():
    parser = argparse.ArgumentParser(description='Agent Gardener - 資料準備與風格管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用指令')

    # Harvest Subcommand
    harvest_parser = subparsers.add_parser('harvest', help='抓取 WordPress 修訂紀錄')
    harvest_parser.add_argument('--post-id', type=int, required=True, help='WordPress 文章 ID')
    harvest_parser.add_argument('--count', type=int, default=1, help='分析最近 N 次修改')
    harvest_parser.add_argument('--json', action='store_true', help='輸出為 JSON 檔案')

    # Plant Subcommand
    plant_parser = subparsers.add_parser('plant', help='存入風格範例')
    plant_parser.add_argument('--trigger', required=True, help='觸發情境')
    plant_parser.add_argument('--change', required=True, help='風格變化描述')
    plant_parser.add_argument('--bad', required=True, help='修改前 (Bad Example)')
    plant_parser.add_argument('--good', required=True, help='修改後 (Good Example)')
    plant_parser.add_argument('--tags', required=True, help='標籤 (逗號分隔)')

    # Analyze Subcommand (NEW)
    analyze_parser = subparsers.add_parser('analyze', help='分析 revision_scanner 報告')
    analyze_parser.add_argument('--report', required=True, help='revision_scanner 報告路徑')

    args = parser.parse_args()
    
    gardener = AgentGardener()

    if args.command == 'harvest':
        count = max(1, args.count)  # 移除上限限制，由 API 分頁處理
        try:
            gardener.harvest(args.post_id, count, args.json)
        except Exception as e:
            print(f"\n❌ 錯誤: {e}")

    elif args.command == 'plant':
        gardener.plant(args.trigger, args.change, args.bad, args.good, args.tags)

    elif args.command == 'analyze':
        gardener.analyze_report(args.report)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()

