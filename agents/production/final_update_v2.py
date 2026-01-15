
import sys
import os
import re
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector
from agents.wordpress.publisher import WordPressPublisher

def update_post_content():
    connector = WordPressConnector()
    publisher = WordPressPublisher(connector)
    
    post_id = 34436
    md_path = "outputs/FUNIT/final/2026-student-visa-risk-guide.md"
    
    print(f"--- Updating Post {post_id} Content ---")

    with open(md_path, 'r', encoding='utf-8') as f:
        content_md = f.read()

    try:
        parts = content_md.split('---', 2)
        if len(parts) >= 3:
            raw_body = parts[2].strip()
            title_match = re.search(r'^title:\s*(.*)$', parts[1], re.MULTILINE)
            title = title_match.group(1).strip() if title_match else "Updated Title"
            
            desc_match = re.search(r'^rank_math_description:\s*(.*)$', parts[1], re.MULTILINE)
            if not desc_match:
                 desc_match = re.search(r'^description:\s*(.*)$', parts[1], re.MULTILINE)
            description = desc_match.group(1).strip() if desc_match else ""
            
            kw_match = re.search(r'^rank_math_focus_keyword:\s*(.*)$', parts[1], re.MULTILINE)
            focus_kw = kw_match.group(1).strip() if kw_match else ""

            print(f"Title: {title}")
            print(f"Desc: {description[:50]}...")
            print(f"KW: {focus_kw}")
            
            meta = {
                'rank_math_title': title,
                'rank_math_description': description,
                'rank_math_focus_keyword': focus_kw
            }
            
            res = publisher.update_post(
                post_id=post_id,
                content=raw_body,
                title=title,
                status='publish',
                slug='2026-student-visa-risk-guide',
                categories=[477],
                meta=meta
            )
            
            if res:
                print("✅ Update Successful!")
                print(f"Link: {res.get('link')}")
                print(f"Slug: {res.get('slug')}")
            else:
                print("❌ Update Failed.")
        else:
            print("❌ Invalid MD format (no frontmatter)")
            
    except Exception as e:
        print(f"❌ Error during update: {e}")

if __name__ == "__main__":
    update_post_content()
