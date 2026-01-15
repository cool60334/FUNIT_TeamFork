"""
C02 SEO Optimizer - SEO 優化師

重構版本：繼承 BaseAgent，使用 PathResolver 處理路徑
向後兼容：如果核心模組不可用，則使用舊架構
"""

import os
import json
import argparse
import logging
import re
import sys
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
# 確保可以 import agents.core 模組
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from utils.prompt_assets import load_workflow_text, load_rules_text
from utils.output_validators import validate_seo_output
from utils.system_config import get_max_retries

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("C02_SEOOptimizer")

# 嘗試導入新的核心模組
try:
    from agents.core import BaseAgent, get_current_brand
    USE_NEW_ARCHITECTURE = True
except ImportError:
    USE_NEW_ARCHITECTURE = False
    logger.info("Core modules not available, using legacy architecture")

# 嘗試導入舊的 settings (向後兼容)
try:
    from config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False

# 嘗試導入 gemini_text_gen
try:
    from utils.gemini_text_gen import gemini_text_gen
    GEMINI_TEXT_GEN_AVAILABLE = True
except ImportError:
    GEMINI_TEXT_GEN_AVAILABLE = False
    logger.warning("gemini_text_gen not available")


class C02SEOOptimizerBase:
    """共用基類 - 包含所有業務邏輯"""

    def _get_prompt_context(self) -> str:
        if getattr(self, "_prompt_context", None) is not None:
            return self._prompt_context
        base_dir = Path(self.base_dir) if hasattr(self, "base_dir") else None
        workflow_content = load_workflow_text("c02_seo_optimizer", base_dir=base_dir)
        rules_content = load_rules_text("c02", base_dir=base_dir)
        combined = "\n\n".join([c for c in [workflow_content, rules_content] if c])
        self._prompt_context = combined
        return self._prompt_context

    def _get_brand_profile(self) -> Dict[str, Any]:
        if hasattr(self, "brand_config") and self.brand_config:
            return self.brand_config
        if hasattr(self, "brand_profile_path") and os.path.exists(self.brand_profile_path):
            try:
                with open(self.brand_profile_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading brand profile: {e}")
        return {}

    def _load_brand_profile_legacy(self) -> Dict[str, Any]:
        """Loads the brand profile JSON (legacy path)."""
        profile_path = "config/brand_profile.json"
        if not os.path.exists(profile_path):
            logger.warning(f"Brand profile not found at {profile_path}")
            return {}
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading brand profile: {e}")
            return {}

    def _load_seo_config(self) -> Dict[str, Any]:
        """Loads SEO configuration."""
        if hasattr(self, 'seo_config_path') and os.path.exists(self.seo_config_path):
            try:
                with open(self.seo_config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading SEO config: {e}")
        return {}

    def _generate_faq_with_llm(self, content: str, keyword: str) -> List[Dict[str, Any]]:
        """
        Generates 3-5 FAQs based on the article content using LLM.
        """
        if not GEMINI_TEXT_GEN_AVAILABLE:
            raise RuntimeError("gemini_text_gen not available")

        prompt_context = self._get_prompt_context()
        prompt = f"""
{prompt_context}

You are an SEO expert for "{self.brand_name}".
Generate 3 to 5 Frequently Asked Questions (FAQ) based on the following article content.
The FAQs should be highly relevant to the user's search intent and address common pain points related to "{keyword}".

## Article Content (Excerpt)
{content[:3000]}...

## Requirements
1. **Relevance**: Questions must be directly answered by the content or inferred from it.
2. **Format**: Return ONLY a JSON array of objects. Each object must have "title" (question) and "content" (answer).
3. **Language**: Traditional Chinese (Taiwan).
4. **Tone**: Professional, helpful, and empathetic.
5. **No Hallucinations**: Do not invent facts not present in the context or general knowledge.

## JSON Format Example
[
    {{
        "title": "Question 1?",
        "content": "Answer 1."
    }},
    {{
        "title": "Question 2?",
        "content": "Answer 2."
    }}
]

Generate JSON now:
"""
        response_text = gemini_text_gen.generate_text(prompt)

        # Clean up response to ensure valid JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]

        faqs = json.loads(response_text)

        return faqs

    def _generate_toc(self, content: str) -> str:
        """
        Generates a Markdown Table of Contents from H2 headers.
        """
        toc_lines = ["## 文章目錄", ""]
        # Find all H2 headers: ## Header Text
        headers = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)

        if not headers:
            return ""

        for header in headers:
            # Skip "文章目錄" itself if captured
            if "文章目錄" in header:
                continue
            # 1. Strip bolding/markdown from header text for the link text
            clean_header = re.sub(r'\*\*(.*?)\*\*', r'\1', header)

            # 2. Generate anchor
            anchor = header.lower()
            anchor = anchor.replace(" ", "-")
            anchor = re.sub(r'[：？！,.?!\(\)\[\]]', '', anchor)

            toc_lines.append(f"*   [{clean_header}](#{anchor})")

        return "\n".join(toc_lines) + "\n\n"

    def _generate_meta_description(self, content: str, keyword: str) -> str:
        """
        Generates a 3-part structured Meta Description using LLM.
        """
        if not GEMINI_TEXT_GEN_AVAILABLE:
            raise RuntimeError("gemini_text_gen not available")

        prompt_context = self._get_prompt_context()
        prompt = f"""
{prompt_context}

You are an SEO expert for "{self.brand_name}".
Create a compelling Meta Description for the following article.

## Requirement
1. **Length**: 75-80 Traditional Chinese characters (approx 150-160 chars total).
2. **Structure**: Must follow this 3-part structure:
   - Part 1: Start with a user pain point or question.
   - Part 2: Offer the article's solution (e.g., "This guide provides...").
   - Part 3: End with a soft Call-to-Action (CTA) and include the main keyword "{keyword}".
3. **No Conversational Filler**: Do NOT start with "Here is the description" or "Sure". Just output the description.
4. **Tone**: Professional, attractive, click-worthy.

## Article Content (Excerpt)
{content[:2000]}...

OUTPUT ONLY THE META DESCRIPTION TEXT:
"""
        response = gemini_text_gen.generate_text(prompt).strip()
        # Clean up quotes if present
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        return response

    def optimize_article(self, slug: str) -> Dict[str, Any]:
        """
        Optimizes a draft article for SEO.
        """
        logger.info(f"Starting SEO Optimization for: {slug}")

        # 1. Load Data
        # Priority: final > optimized > drafts
        draft_path = os.path.join(self.final_dir, f"{slug}.md")
        if not os.path.exists(draft_path):
            draft_path = os.path.join(self.optimized_dir, f"{slug}_with_recommendation.md")
            if not os.path.exists(draft_path):
                draft_path = os.path.join(self.drafts_dir, f"{slug}.md")

        brief_path = os.path.join(self.briefs_dir, f"{slug}_brief.json")
        site_structure_path = os.path.join(self.raw_data_dir, "site_structure.json")

        try:
            with open(draft_path, "r", encoding="utf-8") as f:
                draft_content = f.read()

            brand_profile = self._get_brand_profile()

            site_structure = {}
            if os.path.exists(site_structure_path):
                with open(site_structure_path, "r", encoding="utf-8") as f:
                    site_structure = json.load(f)

            brief_data = {}
            if os.path.exists(brief_path):
                with open(brief_path, "r", encoding="utf-8") as f:
                    brief_data = json.load(f)

            logger.info("Loaded all required data.")

        except FileNotFoundError as e:
            return {"status": "error", "message": f"File not found: {e}"}

        # 2. Extract Key Info
        title_match = re.search(r"^#\s+(.+)$", draft_content, re.MULTILINE)
        if title_match:
            current_title = title_match.group(1).strip()
        else:
            current_title = brief_data.get("title", "Untitled")

        primary_keyword = brief_data.get("primary_keyword", "")
        if not primary_keyword:
            primary_keyword = self.brand_name

        # 3. Optimize Elements

        # 3.1 Title Tag
        optimized_title = current_title
        if primary_keyword and primary_keyword not in optimized_title and len(primary_keyword) < 15:
            optimized_title = f"{primary_keyword}：{optimized_title}"

        # 3.2 Meta Description
        try:
            logger.info("Generating Meta Description with LLM...")
            max_retries = get_max_retries(default=2)
            attempt = 0
            meta_description = ""
            while attempt <= max_retries:
                meta_description = self._generate_meta_description(draft_content, primary_keyword)
                if len(meta_description) >= 50 and primary_keyword in meta_description:
                    break
                attempt += 1
            if len(meta_description) < 50:
                raise ValueError("Meta description too short after retries")
        except Exception as e:
            logger.warning(f"LLM Meta Description generation failed: {e}. Fallback to naive extraction.")
            first_para_match = re.search(r"^([^#\n].+)", draft_content, re.MULTILINE)
            first_para = first_para_match.group(1) if first_para_match else ""
            meta_description = f"{first_para[:140]}... 了解更多關於{primary_keyword}的資訊。"

        # 3.3 Categories & Tags
        categories = site_structure.get("categories", [])

        # Load SEO config for fallbacks
        seo_config = self._load_seo_config()
        seo_defaults = brand_profile.get("seo_defaults", seo_config)

        # Priority 1: Use category from Brief if available
        selected_category = brief_data.get("category", None)

        # Priority 2: Semantic matching based on content
        if not selected_category or selected_category == "Uncategorized":
            for cat in categories:
                cat_name = cat.get("name", "")
                if cat_name == "Uncategorized":
                    continue
                if cat_name in current_title or cat_name in draft_content[:500]:
                    selected_category = cat_name
                    break

        # Priority 3: Use fallback_category from seo_defaults
        fallback_category = seo_defaults.get("fallback_category", "Uncategorized")

        if not selected_category or selected_category == "Uncategorized":
            for cat in categories:
                if cat.get("name") == fallback_category:
                    selected_category = fallback_category
                    break

        if not selected_category:
            selected_category = "Uncategorized"

        # Tags
        default_tags = seo_defaults.get("default_tags", [])
        tags = [primary_keyword]
        tags.extend(default_tags)
        tags.append(self.brand_name)

        # 3.4 Schema
        brand_domain = brand_profile.get("identity", {}).get("domain", "") or \
                       brand_profile.get("brand_identity", {}).get("domain", "")

        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": optimized_title,
            "description": meta_description,
            "author": {
                "@type": "Organization",
                "name": self.brand_name
            },
            "publisher": {
                "@type": "Organization",
                "name": self.brand_name,
                "logo": {
                    "@type": "ImageObject",
                    "url": f"https://{brand_domain}/wp-content/uploads/logo.png"
                }
            }
        }

        # 3.5 FAQ Block
        seo_plugin = self.brand_config.get("wordpress_settings", {}).get("seo_plugin", "rankmath")
        try:
            logger.info(f"Generating dynamic FAQs for {seo_plugin} with LLM...")
            faq_questions = self._generate_faq_with_llm(draft_content, primary_keyword)
        except Exception as e:
            logger.warning(f"LLM FAQ generation failed: {e}. Falling back to brand-specific FAQs.")
            fallback_faq = seo_defaults.get("fallback_faq", [])
            faq_questions = fallback_faq if fallback_faq else [
                {
                    "title": f"為什麼選擇{self.brand_name}？",
                    "content": f"{self.brand_name}專注於提供專業服務，歡迎聯繫了解更多。"
                }
            ]

        if seo_plugin == "seopress":
            # SEOPress FAQ - HTML for Classic Editor
            seopress_faqs = [{"question": q["title"], "answer": q["content"]} for q in faq_questions]
            faq_block_html = '<div class="sp-faq-block">\n'
            for q in seopress_faqs:
                faq_block_html += f"  <div class=\"sp-faq-item\">\n    <h3 class=\"sp-faq-question\">{q['question']}</h3>\n    <div class=\"sp-faq-answer\">{q['answer']}</div>\n  </div>\n"
            faq_block_html += "</div>"
        else:
            # Rank Math FAQ - HTML for Classic Editor
            # No JSON block required
            faq_block_html = '<div class="rank-math-faq-list">\n'
            for q in faq_questions:
                faq_block_html += f"  <div class=\"rank-math-faq-item\">\n    <h3 class=\"rank-math-question\">{q['title']}</h3>\n    <div class=\"rank-math-answer\">{q['content']}</div>\n  </div>\n"
            faq_block_html += "</div>"

        # 4. Construct Output
        frontmatter = {
            "title": optimized_title,
            "slug": slug,
            "description": meta_description,
            "keywords": tags,
            "categories": [selected_category],
            "tags": tags,
            "schema": json.dumps(schema, ensure_ascii=False),
            "internal_link_suggestions": brief_data.get("internal_link_opportunities", [])
        }

        # Add SEO Plugin specific keys to frontmatter
        if seo_plugin == "seopress":
            frontmatter["_seopress_titles_title"] = optimized_title
            frontmatter["_seopress_titles_desc"] = meta_description
            frontmatter["_seopress_analysis_target_kw"] = primary_keyword

        frontmatter_yaml = "---\n"
        for key, value in frontmatter.items():
            if key == "schema":
                frontmatter_yaml += f"{key}: '{value}'\n"
            else:
                frontmatter_yaml += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
        frontmatter_yaml += "---\n\n"

        content_body = draft_content

        # 1. Strip existing Frontmatter if any
        fm_match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', content_body, re.DOTALL)
        if fm_match:
            content_body = fm_match.group(1).strip()

        # 2. Strip "Chat Filler" before the first H1
        h1_match = re.search(r'^#\s+', content_body, re.MULTILINE)
        if h1_match:
            content_body = content_body[h1_match.start():]

        # 3. Remove the H1 Title
        content_body = re.sub(r"^#\s+.+\n", "", content_body, count=1).strip()

        # Strip existing text FAQ section
        faq_pattern = re.compile(r'^(?:##|###)\s+[^\n]*(?:常見問題|QA|FAQ|常見迷思).*?(?=\n##\s|$)', re.MULTILINE | re.DOTALL | re.IGNORECASE)
        content_body = faq_pattern.sub('', content_body).strip()

        # Strip existing TOC section
        toc_pattern = re.compile(r'^##\s+文章目錄.*?(?=\n##\s|$)', re.MULTILINE | re.DOTALL)
        content_body = toc_pattern.sub('', content_body).strip()

        # 4.1 Auto-Generate Table of Contents (TOC)
        toc_content = self._generate_toc(content_body)
        if toc_content:
            content_body = toc_content + content_body

        final_content = frontmatter_yaml + content_body + "\n\n" + f"## {primary_keyword}常見問題 QA\n" + faq_block_html

        # 5. Save Output
        os.makedirs(self.final_dir, exist_ok=True)
        output_path = os.path.join(self.final_dir, f"{slug}.md")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        validation_errors = validate_seo_output(final_content)
        if validation_errors:
            logger.warning(f"SEO output validation warnings: {validation_errors}")

        logger.info(f"Optimized article saved to {output_path}")

        return {
            "status": "success",
            "output_path": output_path,
            "validation_errors": validation_errors
        }


# =============================================================================
# 根據環境選擇架構
# =============================================================================

if USE_NEW_ARCHITECTURE:
    class C02SEOOptimizer(BaseAgent, C02SEOOptimizerBase):
        """C02 SEO Optimizer - 使用新架構"""

        def __init__(self):
            BaseAgent.__init__(self, name="C02_SEOOptimizer")
            self.brand_name = self.brand.slug
            self.base_dir = str(self.brand_manager.base_dir)
            self.brand_config = self.brand.brand_config or {}

            # 設定所有路徑
            self.final_dir = str(self.resolve_path("outputs/FUNIT/final"))
            self.optimized_dir = str(self.resolve_path("outputs/FUNIT/optimized"))
            self.drafts_dir = str(self.resolve_path("outputs/FUNIT/drafts"))
            self.briefs_dir = str(self.resolve_path("outputs/FUNIT/briefs"))
            self.raw_data_dir = str(self.resolve_path("outputs/FUNIT/收集到的資料"))

            # 品牌設定路徑
            self.brand_profile_path = str(self.brand.config_dir / "brand_profile.json")
            self.seo_config_path = str(self.brand.config_dir / "seo.json")

        def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """執行 SEO 優化任務"""
            slug = input_data.get("slug") or input_data.get("article_slug")
            if not slug:
                raise ValueError("缺少必需參數: slug")

            return self.optimize_article(slug)

else:
    class C02SEOOptimizer(C02SEOOptimizerBase):
        """C02 SEO Optimizer - 舊架構 (向後兼容)"""

        def __init__(self):
            if SETTINGS_AVAILABLE:
                self.brand_name = settings.brand_name
            else:
                self.brand_name = "FUNIT"
            self.base_dir = os.getcwd()

            # 設定所有路徑
            base_output = os.path.join(self.base_dir, "outputs", "FUNIT")
            self.final_dir = os.path.join(base_output, "final")
            self.optimized_dir = os.path.join(base_output, "optimized")
            self.drafts_dir = os.path.join(base_output, "drafts")
            self.briefs_dir = os.path.join(base_output, "briefs")
            self.raw_data_dir = os.path.join(base_output, "收集到的資料")

            # 品牌設定路徑 (舊版)
            self.brand_profile_path = os.path.join(self.base_dir, "config", "brand_profile.json")
            self.seo_config_path = ""  # 舊架構沒有獨立的 SEO config

            self.logger = logger

        def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """執行 SEO 優化任務"""
            slug = input_data.get("slug") or input_data.get("article_slug")
            if not slug:
                return {"status": "error", "message": "Slug is required"}

            return self.optimize_article(slug)

        def log_activity(self, message: str):
            """Legacy logging method"""
            logger.info(message)


# =============================================================================
# CLI 介面
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C02 SEO Optimizer Agent")
    parser.add_argument("--slug", required=True, help="The slug of the article to optimize")
    args = parser.parse_args()

    optimizer = C02SEOOptimizer()
    result = optimizer.run({"slug": args.slug})
    print(json.dumps(result, ensure_ascii=False, indent=2))
