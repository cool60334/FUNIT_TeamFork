
import sys
import os
import json
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def inspect_seopress_meta():
    connector = WordPressConnector()
    post_id = 34436
    
    print(f"--- Inspecting Post {post_id} Meta for SEOPress ---")
    
    try:
        post = connector.get(f'/wp-json/wp/v2/posts/{post_id}', params={'context': 'edit'})
        
        if 'meta' in post:
            print("Found 'meta' field. keys:")
            found_seopress = False
            for k, v in post['meta'].items():
                if '_seopress' in k:
                    print(f"  {k}: {v}")
                    found_seopress = True
            
            if not found_seopress:
                print("No SEOPress keys found in meta.")
        else:
            print("No 'meta' field in response.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_seopress_meta()
