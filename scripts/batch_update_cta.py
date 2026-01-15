import os
import re
import json
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BatchCTAUpdate")

# Configuration
CONFIG_PATH = Path("config/brand_profile.json")
TARGET_DIR = Path("outputs/FUNIT/final")

def load_brand_config():
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None

def batch_update():
    config = load_brand_config()
    if not config:
        return

    # Extract Official LINE URL from SSOT
    contact_channels = config.get("data_sources", {}).get("contact_channels", {})
    official_line = contact_channels.get("official_line", "")
    
    if not official_line:
        logger.error("❌ 'official_line' not found in brand_profile.json under data_sources.contact_channels")
        return

    # Construct URLs
    # Clean base URL (remove any existing params for the pattern)
    base_url = official_line.split("?")[0]
    escaped_base_url = re.escape(base_url)
    
    # OLD_URL pattern: specific base URL with ANY or NO query params
    # We want to catch instances with missing tracking or WRONG tracking
    old_url_pattern = rf"{escaped_base_url}(?:\?[^ \)\n\r\"<>]*)?"
    
    # NEW_URL: Standardized tracking
    new_url = f"{base_url}?utm_source=blog&utm_medium=article&utm_campaign=seo_content"
    
    logger.info(f"Targeting Base URL: {base_url}")
    logger.info(f"Replacing with: {new_url}")

    if not TARGET_DIR.exists():
        logger.error(f"Directory {TARGET_DIR} does not exist.")
        return

    updated_files = 0
    total_matches = 0

    for file_path in TARGET_DIR.glob("*.md"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Find matches
            # We use a substitution function to avoid replacing already correct URLs if we want to be picky,
            # but blindly enforcing the standard is usually safer for consistency unless we have complex needs.
            # However, if the URL is ALREADY correct, we shouldn't count it as an update.
            
            matches = re.findall(old_url_pattern, content)
            if not matches:
                continue

            # Standardize: Replace all occurrences of the base pattern with the full new URL
            new_content = re.sub(old_url_pattern, new_url, content)
            
            if new_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                logger.info(f"✅ Updated: {file_path.name}")
                updated_files += 1
                total_matches += len(matches)
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_path.name}: {e}")

    logger.info(f"Summary: Updated {updated_files} files.")

if __name__ == "__main__":
    batch_update()
