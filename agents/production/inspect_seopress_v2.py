
import sys
import os
import argparse
import json
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())

from agents.wordpress.connector import WordPressConnector

def inspect_seopress_meta(post_id):
    load_dotenv()
    connector = WordPressConnector()
    
    print(f"--- Inspecting Post {post_id} Meta for SEOPress ---")
    
    try:
        # Avoid context=edit if it causes 401, but we need it for meta
        # Actually, let's try without if it works, or check why 401
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=34428)
    args = parser.parse_args()
    inspect_seopress_meta(args.id)
