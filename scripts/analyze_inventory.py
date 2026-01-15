import json
from datetime import datetime, timedelta
import collections
import os

# Path to the SC posts index
# Note: Using the dynamic path finding would be better, but we know the path from previous context
file_path = "outputs/FUNIT/收集到的資料/posts_index.json"

def analyze_inventory():
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = data.get('posts', [])
    total_posts = len(posts)
    
    print(f"📊 Content Inventory Analysis for {data.get('brand_name', 'Unknown')}")
    print(f"Total Posts: {total_posts}")
    print("-" * 30)

    # Metrics
    thin_content = 0      # < 800 words
    good_content = 0      # 800 - 2000 words
    long_form = 0         # > 2000 words
    
    outdated = 0          # > 1 year
    recent = 0            # < 1 year
    
    missing_h2 = 0
    
    categories = collections.defaultdict(int)
    
    now = datetime.now()

    for p in posts:
        # Word Count
        wc = p.get('word_count', 0)
        if wc < 800:
            thin_content += 1
        elif wc > 2000:
            long_form += 1
        else:
            good_content += 1
            
        # Date
        date_str = p.get('last_modified') or p.get('date')
        if date_str:
            try:
                post_date = datetime.fromisoformat(date_str)
                if (now - post_date).days > 365:
                    outdated += 1
                else:
                    recent += 1
            except:
                pass
                
        # Structure
        if not p.get('h2_headings'):
            missing_h2 += 1
            
        # Categories
        for cat_id in p.get('categories', []):
            categories[cat_id] += 1

    print("\n📝 Word Count Distribution (Content Depth):")
    print(f"  • Thin Content (< 800 words): {thin_content} ({thin_content/total_posts*100:.1f}%) -> 建議合併或重寫")
    print(f"  • Standard Content (800-2000): {good_content} ({good_content/total_posts*100:.1f}%)")
    print(f"  • Long-form Content (> 2000): {long_form} ({long_form/total_posts*100:.1f}%) -> 可能是 Pillar Page 潛力股")
    
    print("\n📅 Freshness (Content Age):")
    print(f"  • Recent (< 1 year): {recent}")
    print(f"  • Outdated (> 1 year): {outdated} ({outdated/total_posts*100:.1f}%) -> 優先依據新法規/新數據更新")
    
    print("\n🏗 Structure Health:")
    print(f"  • Missing H2 Headings: {missing_h2} ({missing_h2/total_posts*100:.1f}%) -> SEO 扣分項目，需立即修復")

if __name__ == "__main__":
    analyze_inventory()
