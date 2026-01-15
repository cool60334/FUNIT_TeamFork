
import sys
import os
import json
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def inspect_post_meta():
    connector = WordPressConnector()
    post_id = 34436
    
    print(f"--- Inspecting Post {post_id} Meta ---")
    
    try:
        # Get context=edit to see all meta
        post = connector.get(f'/wp-json/wp/v2/posts/{post_id}', params={'context': 'edit'})
        
        if 'meta' in post:
            print("Found 'meta' field. Keys:")
            for k, v in post['meta'].items():
                if 'rank_math' in k:
                    print(f"  {k}: {v}")
        else:
            print("No 'meta' field in response.")
            
        print("\n--- Checking for dedicated Rank Math fields in root ---")
        for k in post.keys():
            if 'rank_math' in k or 'seo' in k:
                print(f"  Root Key: {k}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_post_meta()
