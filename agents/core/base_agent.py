"""
Agent 基類 (BaseAgent)
提供統一的 Agent 介面、配置載入、日誌管理

設計原則:
- 抽象基類，子類必須實作 run()
- 內建品牌管理和路徑解析
- 統一的執行介面和錯誤處理
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import json

from .brand_manager import BrandManager, Brand
from .path_resolver import PathResolver


class BaseAgent(ABC):
    """Agent 基類 - 所有 Python 工具的父類"""

    def __init__(self, name: Optional[str] = None, brand_name: Optional[str] = None):
        """
        初始化 Agent

        Args:
            name: Agent 名稱 (預設使用類別名稱)
            brand_name: 單一品牌模式下忽略此參數
        """
        self.name = name or self.__class__.__name__
        self.brand_manager = BrandManager()

        # 單一品牌模式：不進行品牌切換
        if brand_name:
            self.logger = logging.getLogger(f"agent.{self.name}")
            self.logger.warning("Single brand mode: brand_name is ignored.")

        self.brand: Brand = self.brand_manager.get_current_brand()
        self.path_resolver = PathResolver(self.brand_manager)
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """設定日誌記錄器"""
        logger = logging.getLogger(f"agent.{self.name}")

        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # 控制台輸出
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # 檔案輸出 (可選)
            try:
                log_dir = self.brand.output_dir / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(
                    log_dir / f"{self.name}.log",
                    encoding='utf-8'
                )
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception:
                pass  # 忽略檔案日誌錯誤

        return logger

    def resolve_path(self, path_template: str, **kwargs) -> Path:
        """快捷方法：解析路徑"""
        return self.path_resolver.resolve(path_template, **kwargs)

    def read_json(self, path_template: str, **kwargs) -> Dict[str, Any]:
        """快捷方法：讀取 JSON 檔案"""
        path = self.resolve_path(path_template, **kwargs)
        self.logger.debug(f"讀取 JSON: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def write_json(self, path_template: str, data: Dict[str, Any], **kwargs):
        """快捷方法：寫入 JSON 檔案"""
        path = self.path_resolver.ensure_dir(path_template, **kwargs)
        self.logger.debug(f"寫入 JSON: {path}")

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def read_markdown(self, path_template: str, **kwargs) -> str:
        """快捷方法：讀取 Markdown 檔案"""
        path = self.resolve_path(path_template, **kwargs)
        self.logger.debug(f"讀取 Markdown: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_markdown(self, path_template: str, content: str, **kwargs):
        """快捷方法：寫入 Markdown 檔案"""
        path = self.path_resolver.ensure_dir(path_template, **kwargs)
        self.logger.debug(f"寫入 Markdown: {path}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_file(self, path_template: str, **kwargs) -> str:
        """快捷方法：讀取任意文字檔案"""
        path = self.resolve_path(path_template, **kwargs)
        self.logger.debug(f"讀取檔案: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, path_template: str, content: str, **kwargs):
        """快捷方法：寫入任意文字檔案"""
        path = self.path_resolver.ensure_dir(path_template, **kwargs)
        self.logger.debug(f"寫入檔案: {path}")

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def file_exists(self, path_template: str, **kwargs) -> bool:
        """檢查檔案是否存在"""
        path = self.resolve_path(path_template, **kwargs)
        return path.exists()

    def log_activity(self, message: str):
        """記錄活動 (向後兼容)"""
        self.logger.info(f"[{self.name}] {message}")

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行 Agent 任務 (子類必須實現)

        Args:
            input_data: 輸入參數字典

        Returns:
            執行結果字典
        """
        pass

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        統一的執行介面

        Args:
            **kwargs: 傳遞給 run() 的參數

        Returns:
            {
                "success": True/False,
                "data": {...}  # run() 的返回值
            }
            或
            {
                "success": False,
                "error": "錯誤訊息"
            }

        Example:
            >>> agent = ContentWriterAgent()
            >>> result = agent.execute(article_slug="taipei-travel")
        """
        try:
            self.logger.info(f"開始執行 {self.name}")
            result = self.run(kwargs)
            self.logger.info(f"執行完成 {self.name}")
            return {
                "success": True,
                "data": result
            }
        except FileNotFoundError as e:
            self.logger.error(f"檔案不存在: {e}")
            return {
                "success": False,
                "error": f"檔案不存在: {e}"
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON 解析錯誤: {e}")
            return {
                "success": False,
                "error": f"JSON 解析錯誤: {e}"
            }
        except Exception as e:
            self.logger.error(f"執行失敗: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# 向後兼容：保留舊的 BaseAgent 介面
class LegacyBaseAgent:
    """
    舊版 BaseAgent (向後兼容)

    新代碼請使用 agents.core.base_agent.BaseAgent
    """

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.logger = logging.getLogger(f"agent.{name}")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        Must be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the run method.")

    def log_activity(self, message: str):
        """Logs agent activity."""
        self.logger.info(f"[{self.name}] {message}")
