
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def verify_faq_block():
    connector = WordPressConnector()
    post_id = 34436
    
    print(f"--- Verifying FAQ Block for Post {post_id} ---")
    try:
        post = connector.get(f'/wp-json/wp/v2/posts/{post_id}', params={'context': 'edit'})
        content = post.get('content', {}).get('raw', '')
        
        if '<!-- wp:wpseopress/faq-block' in content:
            print("✅ Found SEOPress FAQ Block marker (wpseopress/faq-block).")
        else:
            print("❌ SEOPress FAQ Block marker NOT found.")
            
        if '<!-- wp:rank-math/faq-block' in content:
            print("❌ Found Rank Math FAQ Block marker (Should be gone).")
        else:
            print("✅ Rank Math FAQ Block marker is GONE.")
            
        if '<details class="seopress-faq-item">' in content:
            print("✅ Found HTML structure (<details class='seopress-faq-item'>).")
        else:
            print("❌ HTML structure check failed.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_faq_block()
