import json
import csv
import os
from datetime import datetime

class SeoAuditExporter:
    def __init__(self):
        self.brand = "FUNIT"
        self.input_file = "outputs/FUNIT/收集到的資料/posts_index.json"
        self.output_file = "outputs/FUNIT/reports/seo_audit_results.csv"
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)

    def run(self):
        if not os.path.exists(self.input_file):
            print(f"❌ Input file not found: {self.input_file}")
            return

        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        posts = data.get('posts', [])
        rows = []
        
        now = datetime.now()

        for p in posts:
            post_id = p.get('id')
            title = p.get('title')
            slug = p.get('slug')
            wc = p.get('word_count', 0)
            h2_count = len(p.get('h2_headings', []))
            
            date_str = p.get('last_modified') or p.get('date')
            days_since_update = 0
            if date_str:
                try:
                    post_date = datetime.fromisoformat(date_str)
                    days_since_update = (now - post_date).days
                except:
                    pass

            # Classification Logic
            phase = ""
            action = ""
            priority = ""
            
            # Phase 1: Structure (Missing H2)
            if h2_count == 0:
                phase = "Phase 1: Structure Fix"
                action = "自動重構 (補 H2)"
                priority = "🔴 Critical"
            
            # Phase 3: Pruning (Thin Content)
            # Check this BEFORE Phase 2, because thin content might also be old, but pruning is a distinct action
            elif wc < 800:
                phase = "Phase 3: Pruning"
                action = "合併或刪除"
                priority = "🟡 Low"
                
            # Phase 2: Refresh (Outdated)
            elif days_since_update > 365:
                phase = "Phase 2: Core Refresh"
                action = "內容翻新 (P01+C06)"
                priority = "🟠 High"
                
            else:
                phase = "Maintenance"
                action = "定期監控"
                priority = "🟢 High"

            rows.append({
                "Phase": phase,
                "Priority": priority,
                "Post ID": post_id,
                "Title": title,
                "Word Count": wc,
                "H2 Count": h2_count,
                "Days Since Update": days_since_update,
                "Action": action,
                "Slug": slug,
                "Link": p.get('link')
            })

        # Sort: Phase 1 -> Phase 2 -> Phase 3 -> Maintenance
        phase_order = {
            "Phase 1: Structure Fix": 1,
            "Phase 2: Core Refresh": 2,
            "Phase 3: Pruning": 3,
            "Maintenance": 4
        }
        rows.sort(key=lambda x: phase_order.get(x["Phase"], 99))

        # Write CSV
        headers = ["Phase", "Priority", "Post ID", "Title", "Word Count", "H2 Count", "Days Since Update", "Action", "Slug", "Link"]
        
        with open(self.output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
            
        print(f"✅ Audit Report generated: {self.output_file}")
        print(f"Total rows: {len(rows)}")

if __name__ == "__main__":
    exporter = SeoAuditExporter()
    exporter.run()
