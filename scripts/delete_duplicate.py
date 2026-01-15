import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.wordpress_client import wp_client

def delete_duplicate():
    try:
        post_id = 2150
        print(f"Deleting duplicate post {post_id}...")
        wp_client.delete_post(post_id)
        print("Successfully deleted.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    delete_duplicate()
