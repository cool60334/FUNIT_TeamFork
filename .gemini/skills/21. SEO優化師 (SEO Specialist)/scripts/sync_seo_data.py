import os
import re
import json
import sys
from pathlib import Path

def sync_seo_data():
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    setup_file = project_root / "config" / "seo_data_setup.md"
    resource_dir = project_root / ".gemini" / "skills" / "21. SEO優化師 (SEO Specialist)" / "resources" / "structured_data"
    output_file = resource_dir / "site_profile.json"

    if not setup_file.exists():
        print(f"❌ 找不到設定檔: {setup_file}")
        return

    print(f"🔍 正在從 {setup_file} 提取資料...")
    
    with open(setup_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 簡單的正則提取
    data = {
        "organization": {
            "name": extract_value(content, "名稱 (Name)"),
            "url": extract_value(content, "官方網址 (URL)"),
            "logo": extract_value(content, "Logo 網址 (Logo URL)"),
            "phone": extract_value(content, "聯絡電話 (Phone)"),
            "social": extract_list(content, "社群連結 (Social Links)")
        },
        "local_business": {
            "name": extract_value(content, "商家名稱 (Business Name)"),
            "type": extract_value(content, "商家類型 (Type)"),
            "address": extract_value(content, "地址 (Address)"),
            "city": extract_value(content, "城市 (City)"),
            "postalCode": extract_value(content, "郵遞區號 (Postal Code)")
        },
        "article_defaults": {
            "author": extract_value(content, "作者名稱 (Author Name)"),
            "author_url": extract_value(content, "作者網址 (Author URL)"),
            "copyright": extract_value(content, "版權持有者 (Copyright Holder)")
        }
    }

    resource_dir.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ 同步完成！資料已存至: {output_file}")

def extract_value(text, label):
    pattern = rf"- \*\*{re.escape(label)}\*\*: (.*)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""

def extract_list(text, label):
    # 找標題下的列表項
    pattern = rf"- \*\*{re.escape(label)}\*\*:\s*\n((?:\s*- .*\n?)*)"
    match = re.search(pattern, text)
    if match:
        list_text = match.group(1)
        return [item.strip("- ").strip() for item in list_text.strip().split("\n") if item.strip()]
    return []

if __name__ == "__main__":
    sync_seo_data()
