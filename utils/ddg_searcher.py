"""
DuckDuckGo Search Utility - 免費網路搜尋工具

用於 Fact Checker 事實查核，取代 Gemini Search Grounding。
支援多品牌架構（品牌設定從 brand_profile.json 讀取區域偏好）。
"""

import time
import logging
from typing import Optional

from ddgs import DDGS
from ddgs.exceptions import RatelimitException, TimeoutException

logger = logging.getLogger(__name__)


class DDGSearcher:
    """DuckDuckGo 搜尋工具類別"""
    
    def __init__(
        self, 
        max_retries: int = 3, 
        delay_seconds: float = 1.5,
        default_region: str = "tw-tzh"
    ):
        """
        初始化 DDG 搜尋器
        
        Args:
            max_retries: 最大重試次數 (預設 3)
            delay_seconds: 重試延遲秒數 (預設 1.5)
            default_region: 預設搜尋區域 (預設台灣繁中)
        """
        self.max_retries = max_retries
        self.delay = delay_seconds
        self.default_region = default_region
    
    def search(
        self, 
        query: str, 
        max_results: int = 5, 
        region: Optional[str] = None,
        timelimit: str = "y"
    ) -> list[dict]:
        """
        執行 DuckDuckGo 搜尋
        
        Args:
            query: 搜尋關鍵字
            max_results: 最大結果數 (預設 5)
            region: 區域代碼，如 "tw-tzh", "us-en" (預設使用初始化時設定)
            timelimit: 時間範圍 - "d" (日), "w" (週), "m" (月), "y" (年)
        
        Returns:
            搜尋結果列表，每項包含:
            - title: 標題
            - href: URL
            - body: 摘要
            
        Example:
            >>> searcher = DDGSearcher()
            >>> results = searcher.search("大阪環球影城 快速通關 2025", max_results=3)
            >>> for r in results:
            ...     print(f"{r['title']}: {r['href']}")
        """
        search_region = region or self.default_region
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"DDG Search (attempt {attempt + 1}): {query[:50]}...")
                
                with DDGS() as ddgs:
                    results = list(ddgs.text(
                        query,
                        region=search_region,
                        max_results=max_results,
                        timelimit=timelimit
                    ))
                
                logger.info(f"  Found {len(results)} results")
                return results
                
            except RatelimitException:
                wait_time = self.delay * (attempt + 1)
                logger.warning(f"DDG Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
                
            except TimeoutException:
                logger.warning(f"DDG Timeout, attempt {attempt + 1}/{self.max_retries}")
                time.sleep(self.delay)
                
            except Exception as e:
                logger.error(f"DDG Search failed: {e}")
                return []
        
        logger.error(f"DDG Search exhausted all {self.max_retries} retries")
        return []
    
    def search_community(
        self, 
        query: str, 
        max_results: int = 5
    ) -> list[dict]:
        """
        專門搜尋社群/論壇內容 (Dcard, PTT, Facebook 等)
        
        Args:
            query: 搜尋關鍵字
            max_results: 最大結果數
            
        Returns:
            優先包含論壇連結的搜尋結果
        """
        # 加入論壇關鍵字提升相關性
        enhanced_query = f"{query} site:dcard.tw OR site:ptt.cc OR site:facebook.com"
        return self.search(enhanced_query, max_results=max_results, timelimit="y")


# 單例模式，方便直接 import 使用
ddg_searcher = DDGSearcher()
