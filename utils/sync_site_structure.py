import json
import logging
import os
import sys
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.append(os.getcwd())

try:
    from utils.wordpress_client import wp_client
except ImportError:
    from .utils.wordpress_client import wp_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_brand_profile() -> Dict[str, Any]:
    """Loads the brand profile JSON."""
    profile_path = "config/brand_profile.json"
    if not os.path.exists(profile_path):
        logger.error(f"Brand profile not found at {profile_path}")
        return {}
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading brand profile: {e}")
        return {}

def sync_structure(brand_profile: Dict[str, Any]):
    """Syncs WordPress site structure to local JSON."""
    brand_name = "FUNIT"
    logger.info(f"Syncing site structure for {brand_name}...")
    
    # 1. Fetch Categories
    categories = wp_client.get_categories()
    logger.info(f"Fetched {len(categories)} categories.")
    
    # 2. Fetch Posts
    posts = wp_client.get_all_posts()
    logger.info(f"Fetched {len(posts)} posts.")
    
    # 3. Fetch Pages (Optional but good for completeness)
    pages = wp_client.get_all_pages()
    logger.info(f"Fetched {len(pages)} pages.")

    # 4. Filter/Clean Data for internal storage
    clean_categories = [
        {
            "id": c["id"],
            "name": c["name"],
            "slug": c["slug"],
            "count": c["count"]
        } for c in categories
    ]
    
    clean_posts = [
        {
            "id": p["id"],
            "title": p["title"]["rendered"],
            "slug": p["slug"],
            "status": p["status"],
            "categories": p["categories"],
            "category_names": [
                next((c["name"] for c in categories if c["id"] == cat_id), "Unknown")
                for cat_id in p.get("categories", [])
            ],
            "date": p["date"],
            "link": p["link"]
        } for p in posts
    ]
    
    clean_pages = [
         {
            "id": p["id"],
            "title": p["title"]["rendered"],
            "slug": p["slug"],
            "status": p["status"],
            "date": p["date"],
            "link": p["link"]
        } for p in pages
    ]
    
    structure_data = {
        "meta": {
            "generated_at": datetime.datetime.now().isoformat(),
            "brand_name": brand_name,
            "wordpress_url": brand_profile.get("identity", {}).get("wordpress_url")
        },
        "categories": clean_categories,
        "posts": clean_posts,
        "pages": clean_pages
    }
    
    # 5. Save to file
    # Determine output path based on brand (mimicking s01 logic or hardcoded for now)
    output_dir = "outputs/FUNIT/收集到的資料"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "site_structure.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(structure_data, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Site structure saved to {output_path}")

if __name__ == "__main__":
    import datetime
    
    # Load profile
    profile = load_brand_profile()
    if profile:
        sync_structure(profile)
