"""
路徑解析器 (PathResolver)
負責解析佔位符路徑、動態路徑生成

設計原則:
- 統一處理 {PLACEHOLDER} 替換
- 支援自訂佔位符
- 自動處理相對/絕對路徑
"""

from pathlib import Path
from typing import Dict, Optional, Union
import re

from .brand_manager import BrandManager, Brand


class PathResolver:
    """路徑解析器 - 處理 {PLACEHOLDER} 替換"""

    PLACEHOLDER_PATTERN = re.compile(r'\{([A-Z_]+)\}')

    def __init__(self, brand_manager: Optional[BrandManager] = None):
        self.brand_manager = brand_manager or BrandManager()

    def resolve(self, path_template: str, **kwargs) -> Path:
        """
        解析路徑模板

        Args:
            path_template: 路徑模板，例如 "outputs/FUNIT/briefs/{ARTICLE_SLUG}.json"
            **kwargs: 額外的佔位符值，例如 ARTICLE_SLUG="taipei-travel"

        Returns:
            解析後的完整路徑

        Example:
            >>> resolver = PathResolver()
            >>> resolver.resolve("outputs/FUNIT/briefs/{ARTICLE_SLUG}.json", ARTICLE_SLUG="taipei")
            PosixPath('/path/to/outputs/FUNIT/briefs/taipei.json')
        """
        brand = self.brand_manager.get_current_brand()

        # 建立佔位符字典
        placeholders = self._build_placeholders(brand, **kwargs)

        # 替換所有佔位符
        resolved_path = self._replace_placeholders(path_template, placeholders)

        # 如果不是絕對路徑，則相對於專案根目錄
        path = Path(resolved_path)
        if not path.is_absolute():
            path = self.brand_manager.base_dir / path

        return path

    def _build_placeholders(self, brand: Brand, **kwargs) -> Dict[str, str]:
        """建立佔位符字典"""
        return {
            'BRAND_NAME': brand.slug,
            'BRAND_DOMAIN': brand.domain,
            'BASE_DIR': str(self.brand_manager.base_dir),
            'OUTPUTS_DIR': str(brand.output_dir),
            'CONFIG_DIR': str(brand.config_dir),
            'LANCEDB_STYLE': str(brand.lancedb_style),
            'LANCEDB_CONTENT': str(brand.lancedb_content),
            **{k.upper(): str(v) for k, v in kwargs.items()}  # 用戶自訂的佔位符
        }

    def _replace_placeholders(self, template: str, placeholders: Dict[str, str]) -> str:
        """替換模板中的佔位符"""
        result = template

        for match in self.PLACEHOLDER_PATTERN.finditer(template):
            placeholder = match.group(1)
            if placeholder in placeholders:
                result = result.replace(
                    f'{{{placeholder}}}',
                    placeholders[placeholder]
                )
            else:
                raise ValueError(f"未知的佔位符: {{{placeholder}}}。可用: {list(placeholders.keys())}")

        return result

    def resolve_str(self, path_template: str, **kwargs) -> str:
        """解析路徑模板並返回字串"""
        return str(self.resolve(path_template, **kwargs))

    def ensure_dir(self, path_template: str, **kwargs) -> Path:
        """解析路徑並確保父目錄存在"""
        path = self.resolve(path_template, **kwargs)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def ensure_parent_dir(self, path_template: str, **kwargs) -> Path:
        """解析路徑並確保父目錄存在 (ensure_dir 的別名)"""
        return self.ensure_dir(path_template, **kwargs)

    def list_placeholders(self) -> Dict[str, str]:
        """列出所有可用的佔位符及其當前值"""
        try:
            brand = self.brand_manager.get_current_brand()
            return self._build_placeholders(brand)
        except RuntimeError:
            return {
                'BRAND_NAME': '<未設定>',
                'BRAND_DOMAIN': '<未設定>',
                'BASE_DIR': str(self.brand_manager.base_dir),
                'OUTPUTS_DIR': '<未設定>',
                'CONFIG_DIR': '<未設定>',
                'LANCEDB_STYLE': '<未設定>',
                'LANCEDB_CONTENT': '<未設定>',
            }

    def validate_template(self, path_template: str) -> bool:
        """驗證路徑模板是否有效 (所有佔位符都有定義)"""
        try:
            brand = self.brand_manager.get_current_brand()
            placeholders = self._build_placeholders(brand)

            for match in self.PLACEHOLDER_PATTERN.finditer(path_template):
                placeholder = match.group(1)
                if placeholder not in placeholders:
                    return False
            return True
        except Exception:
            return False


# 便捷函數
def resolve_path(path_template: str, **kwargs) -> Path:
    """解析路徑模板"""
    return PathResolver().resolve(path_template, **kwargs)


def resolve_path_str(path_template: str, **kwargs) -> str:
    """解析路徑模板並返回字串"""
    return PathResolver().resolve_str(path_template, **kwargs)
