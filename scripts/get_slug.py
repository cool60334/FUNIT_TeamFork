import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from utils.wordpress_client import wp_client

try:
    post = wp_client.get_post(1921)
    print(f"Slug: {post['slug']}")
    print(f"Title: {post['title']['rendered']}")
except Exception as e:
    print(f"Error: {e}")
