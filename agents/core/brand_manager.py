"""
核心模組 (Core Module) - Single Brand Edition
提供品牌管理、路徑解析、Agent 基類

Usage:
    from agents.core import BrandManager, PathResolver, BaseAgent
    from agents.core import get_current_brand, resolve_path
"""

from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
import json
import os

@dataclass
class Brand:
    """品牌數據類 (Single Brand)"""
    slug: str
    name: str
    domain: str
    config_dir: Path
    output_dir: Path
    base_dir: Path
    lancedb_style: Path
    lancedb_content: Path
    brand_config: Dict[str, Any] = field(default_factory=dict)

    def get_wordpress_url(self) -> str:
        return self.brand_config.get('brand_identity', {}).get('domain', '')

    def get_primary_keywords(self) -> List[str]:
        return self.brand_config.get('content_strategy', {}).get('primary_keywords', [])

    def get_visual_config(self) -> Dict[str, Any]:
        return self.brand_config.get('visual_identity', {})

    def get_seo_defaults(self) -> Optional[Dict[str, Any]]:
        return self.brand_config.get('seo_defaults')


class BrandManager:
    """品牌管理器 - Single Brand Implementation"""
    
    _instance = None
    _brand: Optional[Brand] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # 專案根目錄（以目前工作目錄為準）
        self.base_dir = Path(os.getcwd())

        self._load_brand()
        self._initialized = True

    def _load_brand(self):
        """Load the single brand configuration"""
        config_path = self.base_dir / "config" / "brand_profile.json"
        
        if not config_path.exists():
            # Fallback if running from parent directory context
            config_path = self.base_dir / "FunIT" / "config" / "brand_profile.json"
            if config_path.exists():
                self.base_dir = self.base_dir / "FunIT"
            else:
                raise FileNotFoundError(f"Config not found at {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            profile = json.load(f)

        identity = profile.get("brand_identity", {})
        
        self._brand = Brand(
            slug="FUNIT",
            name=identity.get("name", "好好玩FUNIT"),
            domain=identity.get("domain", ""),
            config_dir=self.base_dir / "config",
            output_dir=self.base_dir / "outputs" / "FUNIT",
            base_dir=self.base_dir,
            lancedb_style=self.base_dir / "data" / "lancedb_style",
            lancedb_content=self.base_dir / "data" / "lancedb_content",
            brand_config=profile,
        )

    def get_current_brand(self) -> Brand:
        return self._brand

    def list_brands(self) -> List[str]:
        return [self._brand.slug]

    def switch_brand(self, slug: str):
        print(f"Single brand project. Already on {self._brand.name}")
        return self._brand

# Global accessors
def get_brand_manager() -> BrandManager:
    return BrandManager()

def get_current_brand() -> Brand:
    return BrandManager().get_current_brand()

def switch_brand(slug: str) -> Brand:
    return BrandManager().switch_brand(slug)
