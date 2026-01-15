
import sys
import os
import re
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def update_post_content():
    connector = WordPressConnector()
    post_id = 34436
    md_path = "outputs/FUNIT/final/2026-student-visa-risk-guide.md"
    
    print(f"--- Updating Post {post_id} Content ---")
    
    # Read patched MD
    with open(md_path, 'r', encoding='utf-8') as f:
        content_md = f.read()

    # We need to convert MD to HTML/Blocks again? 
    # Or simpler: The publisher usually does this.
    # But since I want to be 100% sure I don't break blocks, I should strictly USE the Publisher class if possible
    # However, for speed and safety, I can just use the publisher.py's logic or call it via a script that invokes Publisher.
    
    # Let's try to simulate what Publisher.update_post does but just for content.
    # Actually, importing the publisher is safer.
    
    from agents.wordpress.publisher import WordPressPublisher
    publisher = WordPressPublisher(connector)
    
    # Extract Title and Content from MD (simplified)
    # The file has frontmatter.
    # I should use the correct method to parse it if I can, OR just pass the raw string if the publisher handles it.
    # Based on previous `view_file` of publisher.py, it takes `content` (markdown string).
    
    # We need to parse frontmatter to get the clean content.
    try:
        # Simple frontmatter split
        parts = content_md.split('---', 2)
        if len(parts) >= 3:
            raw_body = parts[2].strip()
            # We also need to extract title from frontmatter 'title: ...'
            title_match = re.search(r'^title:\s*(.*)$', parts[1], re.MULTILINE)
            title = title_match.group(1).strip() if title_match else "Updated Title"
            
            # Categories?
            # It's already set to 477. We can pass it again or leave it.
            # Publisher.update_post arguments: (post_id, content, title, ...)
            
            print(f"Updating Title: {title}")
            
            # NOTE: Publisher converts to blocks.
            res = publisher.update_post(
                post_id=post_id,
                content=raw_body,
                title=title,
                status='publish', # Ensure it remains published
                slug='2026-student-visa-risk-guide', # Ensure slug is kept
                categories=[477] # Ensure category is kept
            )
            
            if res:
                print("✅ Update Successful!")
                print(f"Link: {res.get('link')}")
            else:
                print("❌ Update Failed.")
        else:
            print("❌ Invalid MD format (no frontmatter)")
            
    except Exception as e:
        print(f"❌ Error during update: {e}")

if __name__ == "__main__":
    update_post_content()
