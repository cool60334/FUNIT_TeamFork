
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def test_meta_update():
    connector = WordPressConnector()
    post_id = 34436
    
    print(f"--- Testing Meta Update for Post {post_id} ---")
    
    # Attempt 1: Standard 'rank_math_title' in meta
    # This often requires the key to be registered for REST, but let's try.
    payload = {
        'meta': {
            'rank_math_title': 'Test Title Update via Meta',
            'rank_math_focus_keyword': 'TestKeyword'
        }
    }
    
    try:
        res = connector.post(f'/wp-json/wp/v2/posts/{post_id}', data=payload)
        if 'id' in res:
            print("Update call successful (HTTP 200). Checking if meta saved...")
            # Fetch back
            check = connector.get(f'/wp-json/wp/v2/posts/{post_id}', params={'context': 'edit'})
            meta = check.get('meta', {})
            if meta.get('rank_math_title') == 'Test Title Update via Meta':
                print("✅ Success! 'rank_math_title' updated via standard meta.")
            else:
                print(f"❌ Failed. Meta value is: {meta.get('rank_math_title')}")
                print("Note: If the key is not registered in REST, it is ignored.")
        else:
            print(f"Update failed: {res}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_meta_update()
