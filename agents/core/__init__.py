"""
核心模組 (Core Module)
提供品牌管理、路徑解析、Agent 基類

Usage:
    from agents.core import BrandManager, PathResolver, BaseAgent
    from agents.core import get_current_brand, switch_brand, resolve_path
"""

from .brand_manager import (
    BrandManager,
    Brand,
    get_brand_manager,
    get_current_brand,
    switch_brand,
)

from .path_resolver import (
    PathResolver,
    resolve_path,
    resolve_path_str,
)

from .base_agent import (
    BaseAgent,
    LegacyBaseAgent,
)

__all__ = [
    # BrandManager
    'BrandManager',
    'Brand',
    'get_brand_manager',
    'get_current_brand',
    'switch_brand',

    # PathResolver
    'PathResolver',
    'resolve_path',
    'resolve_path_str',

    # BaseAgent
    'BaseAgent',
    'LegacyBaseAgent',
]
