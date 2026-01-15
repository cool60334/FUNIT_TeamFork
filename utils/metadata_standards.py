"""
Metadata Standards for Vector Database

定義向量資料庫的 metadata 標準，確保所有 Agent 使用一致的資料結構。
"""

from typing import Dict, Any, Literal
from datetime import datetime

# Type definitions
ContentType = Literal["post", "page", "guideline", "product"]
ContentStatus = Literal["publish", "draft", "pending", "private"]

class MetadataStandards:
    """Metadata 標準定義"""
    
    @staticmethod
    def create_post_metadata(
        post_id: str,
        slug: str,
        categories: list,
        status: ContentStatus = "publish",
        date: str = None,
        modified: str = None,
        h2_headings: list = None,  # 新增: H2 標題列表
        **extra
    ) -> Dict[str, Any]:
        """
        WordPress 文章的 metadata 標準
        
        Args:
            post_id: 文章 ID
            slug: 文章網址代稱
            categories: 分類列表
            status: 發布狀態
            date: 發布日期
            modified: 最後修改日期
            h2_headings: H2 標題列表
        """
        now = datetime.now().isoformat()
        return {
            "type": "post",
            "id": post_id,
            "slug": slug,
            "categories": categories,
            "status": status,
            "date": date or now,
            "modified": modified or now,
            "h2_headings": h2_headings or [],  # 儲存 H2 列表
            **extra
        }
    
    @staticmethod
    def create_page_metadata(
        page_id: str,
        slug: str,
        status: ContentStatus = "publish",
        date: str = None,
        modified: str = None,
        **extra
    ) -> Dict[str, Any]:
        """
        WordPress 頁面的 metadata 標準
        
        Args:
            page_id: 頁面 ID (e.g., "456")
            slug: 頁面網址代稱 (e.g., "about-us")
            status: 發布狀態
            date: 發布日期
            modified: 最後修改日期
        """
        now = datetime.now().isoformat()
        return {
            "type": "page",
            "id": page_id,
            "slug": slug,
            "status": status,
            "date": date or now,
            "modified": modified or now,
            **extra
        }
    
    @staticmethod
    def create_guideline_metadata(
        guideline_id: str,
        source: str,
        section: str,
        status: ContentStatus = "publish",
        **extra
    ) -> Dict[str, Any]:
        """
        品牌指南 Markdown 文件的 metadata 標準
        
        Args:
            guideline_id: 指南段落 ID (e.g., "brand_guideline_section_0")
            source: 檔案名稱 (e.g., "brand_guideline.md")
            section: 章節標題 (e.g., "品牌核心 (The Core)")
            status: 發布狀態
        """
        now = datetime.now().isoformat()
        return {
            "type": "guideline",
            "id": guideline_id,
            "source": source,
            "section": section,
            "status": status,
            "date": now,
            "modified": now,
            **extra
        }
    
    @staticmethod
    def create_product_metadata(
        product_id: str,
        slug: str,
        categories: list,
        status: ContentStatus = "publish",
        price: float = None,
        **extra
    ) -> Dict[str, Any]:
        """
        WooCommerce 商品的 metadata 標準
        
        Args:
            product_id: 商品 ID
            slug: 商品網址代稱
            categories: 商品分類
            status: 發布狀態
            price: 商品價格
        """
        now = datetime.now().isoformat()
        return {
            "type": "product",
            "id": product_id,
            "slug": slug,
            "categories": categories,
            "status": status,
            "price": price,
            "date": now,
            "modified": now,
            **extra
        }

# Similarity Thresholds (統一標準)
SIMILARITY_THRESHOLDS = {
    "high_overlap": 0.7,      # Similarity > 0.7: 高度重疊 (SKIP)
    "moderate_overlap": 0.4,  # Similarity 0.4-0.7: 中度重疊 (REFERENCE)
    "no_overlap": 0.4         # Similarity < 0.4: 無重疊 (WRITE)
}

def calculate_similarity(distance: float) -> float:
    """
    將 ChromaDB 的 distance 轉換為 similarity
    
    Args:
        distance: ChromaDB 返回的距離值 (0.0 = identical, higher = more different)
    
    Returns:
        similarity: 相似度 (0.0-1.0, higher = more similar)
    """
    return 1.0 - distance

def get_content_action(similarity: float) -> str:
    """
    根據 similarity 決定內容策略
    
    Args:
        similarity: 相似度 (0.0-1.0)
    
    Returns:
        action: "skip", "reference", or "write"
    """
    if similarity > SIMILARITY_THRESHOLDS["high_overlap"]:
        return "skip"
    elif similarity >= SIMILARITY_THRESHOLDS["moderate_overlap"]:
        return "reference"
    else:
        return "write"
