import sys
from pathlib import Path
import json

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.wordpress_client import wp_client

def inspect_raw_content():
    post_id = 1921
    print(f"Fetching Raw Post {post_id}...")
    try:
        # We need to manually use _request to pass context=edit because the helper might not support it
        response = wp_client._request("GET", f"posts/{post_id}", params={"context": "edit"})
        post = response.json()
        raw_content = post['content']['raw']
        
        print("\n--- Raw Content Structure (First 2000 chars) ---")
        print(raw_content[:2000])
        
        print("\n--- Identifying Table Blocks ---")
        if "<!-- wp:table" in raw_content:
            print("Found wp:table blocks!")
            # Extract and print table blocks to see which one to replace
            parts = raw_content.split("<!-- wp:table")
            for i, p in enumerate(parts[1:], 1):
                block = "<!-- wp:table" + p.split("<!-- /wp:table -->")[0] + "<!-- /wp:table -->"
                print(f"\n[Table Block {i}]:")
                print(block[:500] + "...") # Print start of block
        else:
            print("No wp:table blocks found (Might be Classic Block now?)")

    except Exception as e:
        print(f"Error fetching post: {e}")

if __name__ == "__main__":
    inspect_raw_content()
