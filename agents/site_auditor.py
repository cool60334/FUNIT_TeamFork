"""
Agent Site Auditor
負責抓取 WordPress 網站結構（文章、頁面、分類、商品），並生成 site_structure.json。
同時將內容同步至向量資料庫 (Content DB)。
"""

import json
import os
import sys
from typing import Dict, Any, List
from datetime import datetime
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.wordpress_client import wp_client
from utils.vector_db_manager import vector_db
from utils.metadata_standards import MetadataStandards
from config.settings import settings
from agents.core import get_current_brand

class SiteAuditor:
    def __init__(self):
        # 取得當前品牌
        self.brand = get_current_brand()
        
        # 優先選擇「收集到的資料」目錄，若不存在則使用 raw_data
        brand_dir = str(self.brand.output_dir)
        zh_dir = os.path.join(brand_dir, "收集到的資料")
        en_dir = os.path.join(brand_dir, "raw_data")
        
        if os.path.exists(zh_dir):
            self.output_dir = zh_dir
        else:
            # 預設建立收集到的資料
            self.output_dir = zh_dir
            
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _extract_text_and_h2(self, html_content: str) -> tuple[str, List[str], int]:
        """
        從 HTML 中提取純文字、H2 標題，並計算字數
        Returns: (clean_text, h2_list, word_count)
        """
        if not html_content:
            return "", [], 0
            
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 0. 移除垃圾與干擾元素 (Noise Reduction)
        for element in soup(["script", "style", "noscript", "iframe"]):
            element.decompose()
            
        for toc in soup.select("#ez-toc-container, .ez-toc-v2_0_33, .mw-admin-bar"):
            toc.decompose()
            
        # 1. 提取並增強圖片內容 (Image Enrichment)
        for img in soup.find_all("img"):
            alt_text = img.get("alt", "").strip()
            if alt_text:
                img_repr = f"\n[IMAGE: {alt_text}]\n"
                img.replace_with(img_repr)
            else:
                img.decompose()
        
        # 2. 提取並清清洗 H2 Heading (Header Cleaning)
        h2_list = []
        for h2 in soup.find_all("h2"):
            clean_h2 = h2.get_text(strip=True)
            if clean_h2:
                h2_list.append(clean_h2)
        
        # 3. 提取純文字 (Text Extraction)
        text = soup.get_text(separator="\n").strip()
        
        # 4. 文本正規化 (Text Normalization)
        lines = []
        for line in text.splitlines():
            clean_line = line.strip()
            if clean_line:
                lines.append(clean_line)
        
        final_text = "\n".join(lines)
        word_count = len(final_text)
        
        return final_text, h2_list, word_count

    def _get_category_names(self, category_ids: List[int], all_categories: List[Dict]) -> List[str]:
        """將 Category IDs 轉換為名稱"""
        cat_map = {c["id"]: c["name"] for c in all_categories}
        return [cat_map.get(cid, str(cid)) for cid in category_ids]

    def _generate_category_summary(self, categories: List[Dict]):
        """
        產生分類摘要報告 (categories_summary.md)
        讓客戶清楚知道網站有哪些分類可用
        """
        if not categories:
            return
        
        # 按文章數量排序
        sorted_cats = sorted(categories, key=lambda x: x.get("count", 0), reverse=True)
        
        # 分離主分類（有前綴▸）和子分類
        main_cats = [c for c in sorted_cats if c["name"].startswith("▸")]
        sub_cats = [c for c in sorted_cats if not c["name"].startswith("▸")]
        
        lines = [
            "# 📂 網站分類摘要",
            "",
            f"> 生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"> 總分類數：{len(categories)} 個",
            "",
            "---",
            "",
            "## 🏷️ 主分類 (Main Categories)",
            "",
            "| 分類名稱 | Slug | 文章數 |",
            "|----------|------|--------|"
        ]
        
        for cat in main_cats:
            lines.append(f"| {cat['name']} | `{cat['slug']}` | {cat['count']} |")
        
        if sub_cats:
            lines.extend([
                "",
                "---",
                "",
                "## 📍 子分類 / 地區分類 (Sub Categories)",
                "",
                "| 分類名稱 | Slug | 文章數 |",
                "|----------|------|--------|"
            ])
            
            for cat in sub_cats[:50]:  # 限制顯示前 50 個
                lines.append(f"| {cat['name']} | `{cat['slug']}` | {cat['count']} |")
            
            if len(sub_cats) > 50:
                lines.append(f"| ... 還有 {len(sub_cats) - 50} 個分類 | | |")
        
        lines.extend([
            "",
            "---",
            "",
            "## 💡 使用說明",
            "",
            "1. **發布文章時**：系統會自動根據關鍵字匹配最適合的分類",
            "2. **預設分類**：在 `config/brand_profile.json` 的 `content_strategy.default_category` 設定",
            "3. **新增分類**：請直接在 WordPress 後台新增，下次執行 `/全站掃描同步` 時會自動更新",
            ""
        ])
        
        summary_path = os.path.join(self.output_dir, "categories_summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        print(f"   📄 Generated: {summary_path}")


    def run_audit(self, sync_db: bool = True) -> Dict[str, Any]:
        """執行網站稽核，抓取所有資料並同步至 DB"""
        print(f"🚀 Starting Site Audit for: {self.brand.name}")
        if sync_db:
            print("💾 Database Sync: ENABLED (Content DB)")
        
        structure = {
            "meta": {
                "generated_at": datetime.now().isoformat(),
                "brand_name": self.brand.name,
                "wordpress_url": self.brand.domain or settings.wordpress_url
            },
            "categories": [],
            "posts": [],
            "pages": [],
            "products": []
        }
        
        # 1. Fetch Categories
        print("📂 Fetching Categories...")
        all_categories = []
        try:
            all_categories = wp_client.get_categories()
            structure["categories"] = [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "slug": c["slug"],
                    "count": c["count"]
                } for c in all_categories
            ]
            print(f"   ✅ Found {len(all_categories)} categories")
            # 產生分類摘要報告
            self._generate_category_summary(structure["categories"])
        except Exception as e:
            print(f"   ❌ Error fetching categories: {e}")

        # 2. Fetch Posts & Sync to DB
        print("📝 Fetching Posts (Incremental Batch Processing)...")
        try:
            page = 1
            per_page = 20
            total_processed = 0
            
            posts_batch, total_pages = wp_client.get_posts_batch(page=page, per_page=per_page)
            structure["meta"]["total_pages"] = total_pages
            
            print(f"   📊 Estimated {total_pages} pages to process.")

            while True:
                if not posts_batch:
                    break
                
                print(f"   🔄 Processing Page {page}/{total_pages} ({len(posts_batch)} posts)...")
                
                batch_items = []

                for p in posts_batch:
                    post_id = str(p["id"])
                    title = p["title"]["rendered"]
                    content_html = p["content"]["rendered"]
                    excerpt_html = p.get("excerpt", {}).get("rendered", "")
                    
                    # 提取 Excerpt 純文字
                    soup_excerpt = BeautifulSoup(excerpt_html, "html.parser")
                    excerpt_text = soup_excerpt.get_text(strip=True)

                    # 解析內容
                    clean_text, h2_list, word_count = self._extract_text_and_h2(content_html)
                    category_names = self._get_category_names(p.get("categories", []), all_categories)
                    
                    # 儲存 posts 的基本資訊到 JSON
                    structure["posts"].append({
                        "id": p["id"],
                        "title": title,
                        "slug": p["slug"],
                        "excerpt": excerpt_text,
                        "h2_headings": h2_list,
                        "word_count": word_count,
                        "status": p["status"],
                        "categories": p["categories"],
                        "tags": p.get("tags", []),
                        "date": p["date"],
                        "last_modified": p["modified"],
                        "link": p["link"]
                    })

                    # 同步到向量資料庫
                    if sync_db and clean_text:
                        metadata = MetadataStandards.create_post_metadata(
                            post_id=post_id,
                            slug=p["slug"],
                            categories=category_names,
                            status=p["status"],
                            date=p["date"],
                            modified=p["modified"],
                            h2_headings=h2_list,
                            title=title
                        )
                        
                        metadata["category_ids"] = p["categories"]
                        document_content = f"# {title}\n\n{clean_text}"
                        
                        batch_items.append({
                            "id": f"post_{post_id}",
                            "document": document_content,
                            "metadata": metadata
                        })
                
                # Upsert batch to Vector DB
                if sync_db and batch_items:
                    try:
                        vector_db.upsert_content_batch(batch_items)
                    except Exception as ve:
                        print(f"   ⚠️ Vector DB Upsert Error on page {page}: {ve}")

                total_processed += len(posts_batch)
                
                if page >= total_pages:
                    break
                page += 1
                posts_batch, _ = wp_client.get_posts_batch(page=page, per_page=per_page)

            structure["meta"]["total_posts"] = total_processed
            print(f"   ✅ Processed {total_processed} posts and synced to Vector DB.")

        except Exception as e:
            print(f"   ❌ Error fetching posts: {e}")

        # 3. Fetch Pages
        print("📄 Fetching Pages...")
        try:
            pages = wp_client.get_all_pages()
            for p in pages:
                page_id = str(p["id"])
                title = p["title"]["rendered"]
                content_html = p["content"]["rendered"]
                clean_text, h2_list, word_count = self._extract_text_and_h2(content_html)
                
                structure["pages"].append({
                    "id": p["id"],
                    "title": title,
                    "slug": p["slug"],
                    "status": p["status"],
                    "date": p["date"],
                    "last_modified": p["modified"],
                    "link": p["link"]
                })
                
                if sync_db and clean_text:
                    metadata = MetadataStandards.create_page_metadata(
                        page_id=page_id,
                        slug=p["slug"],
                        status=p["status"],
                        date=p["date"],
                        modified=p["modified"],
                        title=title
                    )
                    document_content = f"# {title}\n\n{clean_text}"
                    
                    vector_db.upsert_content_batch([{
                        "id": f"page_{page_id}",
                        "document": document_content,
                        "metadata": metadata
                    }])

            print(f"   ✅ Processed {len(pages)} pages")
        except Exception as e:
            print(f"   ❌ Error fetching pages: {e}")

        # 4. Fetch Products
        print("🛍️ Fetching Products...")
        try:
            products = wp_client.get_all_products()
            for p in products:
                prod_id = str(p["id"])
                name = p.get("title", {}).get("rendered", p.get("name", "Unknown"))
                description = p.get("content", {}).get("rendered", p.get("description", ""))
                stock_status = p.get("stock_status", "instock")
                
                if stock_status == "outofstock":
                    continue

                clean_text, _, word_count = self._extract_text_and_h2(description)
                
                structure["products"].append({
                    "id": p["id"],
                    "name": name,
                    "slug": p["slug"],
                    "status": p["status"],
                    "stock_status": stock_status,
                    "link": p["link"],
                    "categories": p.get("product_cat", []),
                    "tags": p.get("product_tag", [])
                })
                
                if sync_db and clean_text:
                    metadata = MetadataStandards.create_product_metadata(
                        product_id=prod_id,
                        slug=p["slug"],
                        categories=[], 
                        status=p["status"],
                        price=float(p.get("price", 0) or 0),
                        name=name
                    )
                    document_content = f"# {name}\n\n{clean_text}"
                    
                    vector_db.upsert_content_batch([{
                        "id": f"product_{prod_id}",
                        "document": document_content,
                        "metadata": metadata
                    }])

            print(f"   ✅ Processed {len(products)} products")
        except Exception as e:
            print(f"   ⚠️ Error fetching products: {e}")

        # Save to site_structure.json
        output_file = os.path.join(self.output_dir, "site_structure.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(structure, f, ensure_ascii=False, indent=2)
            
        # Save to posts_index.json (User's preferred format)
        posts_index = {
            "crawl_date": structure["meta"]["generated_at"],
            "brand_name": structure["meta"]["brand_name"],
            "total_posts": structure["meta"]["total_posts"],
            "posts": structure["posts"]
        }
        index_file = os.path.join(self.output_dir, "posts_index.json")
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(posts_index, f, ensure_ascii=False, indent=2)
            
        print(f"\n✨ Audit Complete! Data saved to: {self.output_dir}")
        print(f"   - {output_file}")
        print(f"   - {index_file}")
        
        return structure

if __name__ == "__main__":
    auditor = SiteAuditor()
    auditor.run_audit(sync_db=True)
