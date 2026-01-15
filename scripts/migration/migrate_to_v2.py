#!/usr/bin/env python3
"""
配置遷移腳本 (Legacy)

此腳本為過去多品牌架構的遷移工具，單一品牌版本不再使用。
"""

import argparse
import json
import shutil
import sys
import os
from pathlib import Path
from datetime import datetime

# 確保可以 import agents 模組
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def load_brand_profile(brand_dir: Path) -> dict:
    """載入現有 brand_profile.json"""
    profile_path = brand_dir / "brand_profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"找不到 {profile_path}")

    with open(profile_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_brand_json(profile: dict) -> dict:
    """提取 brand.json 內容"""
    identity = profile.get('brand_identity', {})
    strategy = profile.get('content_strategy', {})

    return {
        "version": "2.0",
        "brand_identity": {
            "name": identity.get('name', ''),
            "english_name": identity.get('english_name', ''),
            "domain": identity.get('domain', ''),
            "category": identity.get('category', ''),
            "tagline": identity.get('tagline', ''),
            "description": identity.get('description', ''),
            "founding_story": identity.get('founding_story', '')
        },
        "content_strategy": {
            "language": strategy.get('language', 'zh-TW'),
            "primary_keywords": strategy.get('primary_keywords', []),
            "target_audience_file": "brand_guideline.md",
            "tone_voice_file": "brand_guideline.md",
            "competitors": strategy.get('competitors', [])
        },
        "data_sources": profile.get('data_sources', {}),
        "file_paths": profile.get('file_paths', {})
    }


def extract_visual_json(profile: dict) -> dict:
    """提取 visual.json 內容"""
    visual = profile.get('visual_identity', {})

    return {
        "version": "2.0",
        "illustration_style": visual.get('illustration_style', ''),
        "illustration_style_details": visual.get('illustration_style_details', ''),
        "color_palette": visual.get('color_palette', {}),
        "mood": visual.get('mood', ''),
        "reference_keywords": visual.get('reference_keywords', []),
        "image_generation": visual.get('image_generation_preferences', {
            "standard_model": "gemini-flash-2.5-image",
            "premium_model": "gemini-3-pro-image-preview",
            "max_premium_per_article": 1,
            "preferred_aspect_ratio": "16:9"
        }),
        "image_strategy": visual.get('image_strategy', {
            "mode": "placeholder_only",
            "density": "standard",
            "placeholder_format": "![{keyword}: {scene_description}](PLACEHOLDER)"
        })
    }


def extract_seo_json(profile: dict) -> dict | None:
    """提取 seo.json 內容 (如果存在)"""
    seo_defaults = profile.get('seo_defaults')
    if not seo_defaults:
        return None

    return {
        "version": "2.0",
        "fallback_category": seo_defaults.get('fallback_category', ''),
        "default_tags": seo_defaults.get('default_tags', []),
        "fallback_faq": seo_defaults.get('fallback_faq', []),
        "structured_data": {
            "enable_faq_schema": True,
            "enable_article_schema": True,
            "enable_breadcrumb_schema": True
        }
    }


def extract_wordpress_env(brand_dir: Path) -> str:
    """提取 wordpress.env 內容"""
    env_path = brand_dir / ".env"
    if not env_path.exists():
        return ""

    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 篩選 WordPress 相關變數
    wp_lines = []
    for line in content.split('\n'):
        line = line.strip()
        if line and not line.startswith('#'):
            if any(key in line for key in ['WP_', 'WORDPRESS_']):
                wp_lines.append(line)
            elif '=' in line:
                # 保留所有環境變數
                wp_lines.append(line)

    return '\n'.join(wp_lines)


def migrate_brand(brand_slug: str, base_dir: Path, dry_run: bool = True) -> dict:
    """遷移單一品牌"""
    brand_dir = base_dir / "brands" / brand_slug
    config_dir = brand_dir / "config"

    result = {
        "brand": brand_slug,
        "success": False,
        "actions": [],
        "errors": []
    }

    try:
        # 載入現有配置
        profile = load_brand_profile(brand_dir)
        result["actions"].append(f"✅ 讀取 {brand_slug}/brand_profile.json")

        # 提取新配置
        brand_json = extract_brand_json(profile)
        visual_json = extract_visual_json(profile)
        seo_json = extract_seo_json(profile)
        wordpress_env = extract_wordpress_env(brand_dir)

        if dry_run:
            # 預覽模式
            result["actions"].append(f"📝 將建立 config/brand.json")
            result["actions"].append(f"📝 將建立 config/visual.json")
            if seo_json:
                result["actions"].append(f"📝 將建立 config/seo.json")
            if wordpress_env:
                result["actions"].append(f"📝 將建立 config/wordpress.env")

            result["preview"] = {
                "brand.json": brand_json,
                "visual.json": visual_json,
                "seo.json": seo_json,
                "wordpress.env": wordpress_env[:100] + "..." if len(wordpress_env) > 100 else wordpress_env
            }
        else:
            # 執行模式
            config_dir.mkdir(parents=True, exist_ok=True)

            # 備份原始檔案
            backup_dir = brand_dir / "backup" / datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir.mkdir(parents=True, exist_ok=True)

            profile_path = brand_dir / "brand_profile.json"
            if profile_path.exists():
                shutil.copy(profile_path, backup_dir / "brand_profile.json")
                result["actions"].append(f"📦 備份 brand_profile.json 到 backup/")

            # 寫入新配置
            with open(config_dir / "brand.json", 'w', encoding='utf-8') as f:
                json.dump(brand_json, f, ensure_ascii=False, indent=2)
            result["actions"].append(f"✅ 建立 config/brand.json")

            with open(config_dir / "visual.json", 'w', encoding='utf-8') as f:
                json.dump(visual_json, f, ensure_ascii=False, indent=2)
            result["actions"].append(f"✅ 建立 config/visual.json")

            if seo_json:
                with open(config_dir / "seo.json", 'w', encoding='utf-8') as f:
                    json.dump(seo_json, f, ensure_ascii=False, indent=2)
                result["actions"].append(f"✅ 建立 config/seo.json")

            if wordpress_env:
                with open(config_dir / "wordpress.env", 'w', encoding='utf-8') as f:
                    f.write(wordpress_env)
                result["actions"].append(f"✅ 建立 config/wordpress.env")

        result["success"] = True

    except Exception as e:
        result["errors"].append(str(e))

    return result


def main():
    parser = argparse.ArgumentParser(description="配置遷移腳本")
    parser.add_argument("--brand", type=str, help="指定品牌 (好好玩FUNIT)")
    parser.add_argument("--all", action="store_true", help="遷移所有品牌")
    parser.add_argument("--dry-run", action="store_true", help="預覽模式，不實際執行")
    parser.add_argument("--execute", action="store_true", help="執行遷移")

    args = parser.parse_args()

    if not args.brand and not args.all:
        parser.print_help()
        print("\n❌ 請指定 --brand 或 --all")
        sys.exit(1)

    if not args.dry_run and not args.execute:
        print("⚠️  未指定 --dry-run 或 --execute，預設使用 --dry-run")
        args.dry_run = True

    base_dir = Path(project_root)

    if args.all:
        brands = ["好好玩FUNIT"]
    else:
        brands = [args.brand]

    print(f"\n{'=' * 50}")
    print(f"配置遷移 {'(預覽模式)' if args.dry_run else '(執行模式)'}")
    print(f"{'=' * 50}\n")

    for brand in brands:
        print(f"\n--- {brand} ---")
        result = migrate_brand(brand, base_dir, dry_run=args.dry_run)

        for action in result["actions"]:
            print(f"  {action}")

        if result["errors"]:
            for error in result["errors"]:
                print(f"  ❌ {error}")

        if result.get("preview") and args.dry_run:
            print(f"\n  預覽 brand.json:")
            print(f"    name: {result['preview']['brand.json']['brand_identity']['name']}")
            print(f"    domain: {result['preview']['brand.json']['brand_identity']['domain']}")

    print(f"\n{'=' * 50}")
    if args.dry_run:
        print("預覽完成。使用 --execute 執行實際遷移。")
    else:
        print("遷移完成！")
    print(f"{'=' * 50}\n")


if __name__ == "__main__":
    main()
