
import sys
import os
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from agents.wordpress.connector import WordPressConnector
from agents.core.brand_manager import BrandManager

def inspect_post(post_id):
    try:
        # Load Brand Config
        brand = BrandManager().get_current_brand()
        wp_config = {}
        wp_env_path = brand.config_dir / "wordpress.env"
        if not wp_env_path.exists():
            wp_env_path = brand.config_dir.parent / ".env"
        
        if wp_env_path.exists():
            with open(wp_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        wp_config[key.strip()] = value.strip()
        
        connector = WordPressConnector(
            base_url=wp_config.get("WP_SITE_URL"),
            username=wp_config.get("WP_USERNAME"),
            app_password=wp_config.get("WP_APP_PASSWORD")
        )
        
        print(f"Fetching Post {post_id}...")
        post = connector.get(f"/wp-json/wp/v2/posts/{post_id}")
        
        if not post:
            print("Post not found.")
            return

        content = post.get('content', {}).get('rendered', '')
        
        output_file = f"outputs/FUNIT/raw_data/post_{post_id}_raw.html"
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"Saved raw HTML to {output_file}")
        print(f"Content length: {len(content)}")
        
        if "<table" in content:
            print("✅ HTML Tables detected!")
            count = content.count("<table")
            print(f"Found {count} tables.")
        else:
            print("❌ No HTML tables found.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_post(12770)
