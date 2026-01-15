from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import yaml


def _normalize_heading(text: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", "", text or "", flags=re.UNICODE)
    return cleaned.lower()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize_heading(a), _normalize_heading(b)).ratio()


def validate_brief(brief: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    required = ["title", "slug", "primary_keyword", "target_audience", "outline"]
    for key in required:
        if not brief.get(key):
            errors.append(f"Brief 缺少必要欄位: {key}")

    target_audience = brief.get("target_audience", "")
    if isinstance(target_audience, str) and (target_audience.endswith(".md") or "/" in target_audience):
        errors.append("target_audience 仍是檔案路徑，必須是具體描述")

    outline = brief.get("outline", [])
    if not isinstance(outline, list) or not outline:
        errors.append("outline 為空或格式錯誤")
    else:
        for idx, section in enumerate(outline):
            if not section.get("h2_title"):
                errors.append(f"outline[{idx}] 缺少 h2_title")
            key_points = section.get("key_points") or []
            if not key_points:
                errors.append(f"outline[{idx}] 缺少 key_points")

    search_intent = brief.get("search_intent_research", {})
    if not search_intent or not search_intent.get("recommended_hook_strategy"):
        errors.append("search_intent_research.recommended_hook_strategy 缺失")

    # Hook 泛化檢查
    if outline:
        hook_points = outline[0].get("key_points", [])
        hook_text = " ".join(hook_points)
        vague_patterns = ["用痛點開場", "痛點開場", "引人入勝", "吸引讀者", "簡短介紹"]
        if any(pat in hook_text for pat in vague_patterns):
            errors.append("Hook 策略過於空泛，需具體化")

    return errors


    return errors


def validate_hook(content: str) -> List[str]:
    """
    Validates the hook (opening paragraph) for generic AI patterns.
    """
    errors: List[str] = []
    # Extract the first paragraph (naive split by double newline)
    paragraphs = content.strip().split("\n\n")
    if not paragraphs:
        return []
    
    first_para = paragraphs[0].strip()
    
    # Generic AI Openers check
    ai_openers = [
        "In this digital age", "In today's fast-paced world", "Have you ever wondered",
        "這是一個", "在當今", "在這個", "隨著", "你是否曾經", "有沒有想過",
        "不可否認", "眾所周知", "隨著科技的進步", "深入探討"
    ]
    
    # Check strict prefix or containment for some patterns
    for pattern in ai_openers:
        if pattern in first_para:
             # Heuristic: If it's very short and contains the pattern, it's likely a bad hook.
             # Or if it starts with it.
             if first_para.startswith(pattern) or f"，{pattern}" in first_para:
                 errors.append(f"Hook 過於泛泛或充滿 AI 味: '{pattern}'")
                 break

    return errors


def _check_ai_phrases(content: str) -> List[str]:
    """
    Scans content for banned AI-like phrases.
    """
    errors: List[str] = []
    banned_phrases = [
        "總而言之", "綜上所述", "不可否認", "值得注意的是", "各個面向",
        "讓我們一起", "深入探討", "這篇文章將", "本文將", 
        "不僅...而且...", "若是...則...", # Symmetrical structures (harder to catch strictly, maybe stick to exact phrases first)
        "為您揭曉", "一探究竟"
    ]
    
    for phrase in banned_phrases:
        if phrase in content:
            errors.append(f"出現 AI 常用語 (請換成更自然的表達): {phrase}")
            
    return errors


def validate_draft(content: str, brief: Dict[str, Any], brand_config: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not content or not content.strip():
        return ["草稿內容為空"]

    # 1. H2 對齊
    h2_titles = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
    outline = brief.get("outline", [])
    for section in outline:
        expected = section.get("h2_title", "")
        if not expected:
            continue
        if not any(_similarity(expected, actual) >= 0.75 for actual in h2_titles):
            errors.append(f"缺少或偏離 H2 標題: {expected}")

    # 2. Forbidden terms from brief
    forbidden_terms = brief.get("forbidden_terms", [])
    for term in forbidden_terms:
        if term and term in content:
            errors.append(f"出現禁用詞彙: {term}")

    # 3. Internal links
    internal_links = brief.get("internal_link_opportunities", [])
    for link in internal_links:
        url = link.get("url") or ""
        if url and url not in content:
            errors.append(f"缺少內部連結: {url}")

    # 4. CTA contact link
    contact_channels = (
        brand_config.get("data_sources", {}).get("contact_channels", {})
        if isinstance(brand_config, dict)
        else {}
    )
    official_line = contact_channels.get("official_line", "")
    if official_line:
        expected_link = f"{official_line}?utm_source=blog&utm_medium=article&utm_campaign=seo_content"
        if expected_link not in content:
            errors.append("缺少主要聯絡管道 CTA 或 UTM 參數")
            
    # 5. Hook Validation (New)
    hook_errors = validate_hook(content)
    errors.extend(hook_errors)
    
    # 6. De-AI Phrase Check (New)
    ai_errors = _check_ai_phrases(content)
    errors.extend(ai_errors)

    return errors


def _parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not match:
        return {}, content
    fm = yaml.safe_load(match.group(1)) or {}
    body = match.group(2)
    return fm if isinstance(fm, dict) else {}, body


def validate_seo_output(content: str) -> List[str]:
    errors: List[str] = []
    frontmatter, body = _parse_frontmatter(content)

    required_fields = ["title", "slug", "description", "categories", "tags", "schema"]
    for key in required_fields:
        if key not in frontmatter:
            errors.append(f"Frontmatter 缺少欄位: {key}")

    description = frontmatter.get("description", "")
    if isinstance(description, str) and len(description) < 50:
        errors.append("Meta Description 長度過短")

    if "<!-- wp:rank-math/faq-block" not in body:
        errors.append("缺少 Rank Math FAQ Block")

    return errors


def validate_recommendation_block(block_md: str, allowed_urls: List[str]) -> List[str]:
    errors: List[str] = []
    if "?utm_source=blog&utm_medium=article&utm_campaign=service_recommendation" not in block_md:
        errors.append("缺少 UTM 參數")

    links = re.findall(r"\]\((https?://[^)]+)\)", block_md)
    if not links:
        errors.append("推薦區塊缺少連結")
    else:
        for link in links:
            if link not in allowed_urls:
                errors.append(f"推薦連結不在允許清單: {link}")

    return errors


def validate_final_article(content: str) -> List[str]:
    errors: List[str] = []
    placeholders = ["(PLACEHOLDER)", "(PREMIUM_PLACEHOLDER)"]
    if any(ph in content for ph in placeholders):
        errors.append("仍存在圖片佔位符")
    if "[PREMIUM_IMAGE_PROMPT]" in content or "[/PREMIUM_IMAGE_PROMPT]" in content:
        errors.append("仍存在 Premium 圖片指令區塊")
    return errors
