from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import os


WORKFLOW_ALIASES: Dict[str, List[str]] = {
    "c01_content_writer": ["c01_content_writer.md", "c01_內容撰寫.md"],
    "c02_seo_optimizer": ["c02_seo_optimizer.md", "c02_SEO優化.md"],
    "c02a_fact_checker": ["c02a_fact_checker.md", "c02a_事實查核.md"],
    "c03_service_recommender": ["c03_service_recommender.md", "c03_服務推薦.md"],
    "c04_visual_director": ["c04_visual_director.md", "c04_視覺設計.md"],
    "c05_publisher": ["c05_publisher.md", "c05_文章發布.md"],
    "p01_keyword_strategist": ["p01_keyword_strategist.md", "p01_關鍵字策略.md"],
    "p02_content_architect": ["p02_content_architect.md", "p02_內容企劃.md"],
    "s01_brand_builder": ["s01_brand_builder.md", "s01_品牌建構師.md"],
}

# Map keys to skill folder names (Traditional Chinese)
SKILL_FOLDER_MAPPING = {
    "c01_content_writer": "內容撰稿人",
    "c02_seo_optimizer": "SEO優化",
    "c02a_fact_checker": "資訊確認(fact check)",
    "c03_service_recommender": "服務推廣員",
    "c04_visual_director": "視覺總監",
    "c05_publisher": "文章發布工作流程",
    "p01_keyword_strategist": "1. 關鍵字策略",
    "p02_content_architect": "2. 內容企劃",
    "s01_brand_builder": "0C. 品牌建構師",
}


def _get_base_dir() -> Path:
    try:
        from agents.core.brand_manager import BrandManager
        # Fix: use .base_dir instead of .get_base_dir()
        return BrandManager().base_dir
    except Exception:
        return Path(__file__).resolve().parent.parent


def load_workflow_text(key: str, base_dir: Optional[Path] = None) -> str:
    base = base_dir or _get_base_dir()
    
    # 1. Try legacy .agent/workflows paths
    candidates = WORKFLOW_ALIASES.get(key, [f"{key}.md"])
    for filename in candidates:
        path = base / ".agent" / "workflows" / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
            
    # 2. Try .gemini/skills paths (Traditional Chinese)
    skill_folder = SKILL_FOLDER_MAPPING.get(key)
    if skill_folder:
        # Tried 技能.md first (legacy), then SKILL.md (standard)
        path = base / ".gemini" / "skills" / skill_folder / "SKILL.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
        path = base / ".gemini" / "skills" / skill_folder / "技能.md"
        if path.exists():
            return path.read_text(encoding="utf-8")
            
    return ""


def load_rules_text(rule_key: str, base_dir: Optional[Path] = None) -> str:
    base = base_dir or _get_base_dir()
    path = base / ".agent" / "rules" / f"{rule_key}_rules.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""
