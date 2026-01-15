"""
C01 內容創作者 - 品牌化長篇文章撰寫

重構版本：繼承 BaseAgent，使用 PathResolver 處理路徑
向後兼容：如果核心模組不可用，則使用舊架構
"""

import os
import json
import argparse
import logging
import re
import sys
from typing import Dict, Any
from pathlib import Path

# 確保可以 import agents.core 模組
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

import google.generativeai as genai
from utils.prompt_assets import load_workflow_text, load_rules_text
from utils.output_validators import validate_draft
from utils.system_config import get_max_retries

# 設定 logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("C01_ContentWriter")

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

# Try to import StyleMemoryManager
try:
    from utils.style_memory_manager import StyleMemoryManager
    STYLE_MEMORY_AVAILABLE = True
except ImportError:
    STYLE_MEMORY_AVAILABLE = False

# Try to import FactMemoryManager
try:
    from utils.fact_memory_manager import FactMemoryManager
    FACT_MEMORY_AVAILABLE = True
except ImportError:
    FACT_MEMORY_AVAILABLE = False


class C01ContentWriterBase:
    """共用基類 - 包含所有業務邏輯"""

    def _configure_llm(self):
        """配置 LLM"""
        api_key = None
        if SETTINGS_AVAILABLE:
            api_key = settings.gemini_api_key
        if not api_key:
            api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.error("Error: GEMINI_API_KEY not found.")
            return
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3-pro-preview')

    def load_brief(self, slug: str) -> Dict[str, Any]:
        """Loads the brief JSON file for the given slug."""
        brief_path = os.path.join(self.briefs_dir, f"{slug}_brief.json")
        if not os.path.exists(brief_path):
            raise FileNotFoundError(f"Brief not found for slug: {slug} at {brief_path}")
        with open(brief_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_brand_profile(self) -> Dict[str, Any]:
        """Loads the brand profile JSON."""
        if hasattr(self, "brand") and getattr(self, "brand", None):
            return self.brand.brand_config or {}
        if not os.path.exists(self.brand_profile_path):
            logger.warning(f"Brand profile not found at {self.brand_profile_path}")
            return {}
        with open(self.brand_profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_workflow_prompt(self) -> str:
        """載入 workflow 文件"""
        return load_workflow_text("c01_content_writer", base_dir=Path(self.base_dir))

    def _load_rules_prompt(self) -> str:
        """載入規則文件"""
        return load_rules_text("c01", base_dir=Path(self.base_dir))

    def _clean_llm_output(self, text: str) -> str:
        """Strip code fences and extra wrappers from LLM output."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\s*", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    def _retrieve_style_rules(self, brief: Dict) -> str:
        """Retrieves relevant style rules from Style Memory."""
        if not self.style_memory:
            return ""
        contexts = ["Introduction / Article Start", "Reference to 旅遊資訊", "Social Proof"]
        style_guide_text = "\n### 🧬 Style Memory (Learned from Feedback)\n"
        style_guide_text += "> CRITICAL: You must strictly adhere to these rules derived from past user corrections.\n\n"
        has_rules = False
        for ctx in contexts:
            examples = self.style_memory.retrieve_examples(query=ctx, k=1)
            if examples:
                has_rules = True
                for ex in examples:
                    doc = ex.get('document', '')
                    style_guide_text += f"**Scenario: {ctx}**\n"
                    style_guide_text += "\n".join([f"> {line}" for line in doc.split('\n')]) + "\n\n"
        return style_guide_text if has_rules else ""

    def _retrieve_fact_reminders(self, brief: Dict) -> str:
        """Retrieves relevant verified facts from Fact Memory."""
        if not self.fact_memory:
            return ""
        queries = []
        pk = brief.get("primary_keyword")
        if pk:
            queries.append(pk)
        sks = brief.get("secondary_keywords", [])
        if sks:
            queries.extend(sks[:3])
        if not queries:
            return ""
        fact_block = "\n### 🧠 Fact Memory (Verified Corrections)\n"
        fact_block += "> CRITICAL: The following are verified facts from previous corrections.\n\n"
        seen_facts = set()
        has_facts = False
        for q in queries:
            results = self.fact_memory.retrieve_facts(query=q, k=2)
            for res in results:
                fact_text = res.get('verified_fact', '') or res.get('document', '')
                if fact_text and fact_text not in seen_facts:
                    fact_block += f"- {fact_text}\n"
                    seen_facts.add(fact_text)
                    has_facts = True
        return fact_block + "\n" if has_facts else ""

    def save_draft(self, slug: str, content: str):
        """Saves the generated markdown draft."""
        draft_path = os.path.join(str(self.output_dir), f"{slug}.md")
        with open(draft_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Draft saved to: {draft_path}")

    def generate_draft(self, slug: str):
        """Generates a draft using Gemini based on the workflow and brief."""
        logger.info(f"Starting Content Writer for slug: {slug}")
        try:
            brief = self.load_brief(slug)
            brand_profile = self.load_brand_profile()
            workflow_content = self._load_workflow_prompt()
            rules_content = self._load_rules_prompt()
            if not workflow_content:
                return

            brand_name = self.brand_name
            article_slug = slug

            contact_channels = brand_profile.get("data_sources", {}).get("contact_channels", {})
            official_line = contact_channels.get("official_line", "")
            brand_community = contact_channels.get("品牌社群", "")
            contact_link_with_utm = f"{official_line}?utm_source=blog&utm_medium=article&utm_campaign=seo_content" if official_line else "#"

            content_strategy = brand_profile.get("content_strategy", {})
            visual_identity = brand_profile.get("visual_identity", {})
            target_language = content_strategy.get("language", "zh-TW")
            target_language_desc = "Traditional Chinese (繁體中文)" if target_language == "zh-TW" else target_language
            premium_model = visual_identity.get("image_generation_preferences", {}).get("premium_model", "gemini-3-pro-image-preview")
            target_forums = "Dcard, PTT"

            style_memory_block = self._retrieve_style_rules(brief)
            fact_memory_block = self._retrieve_fact_reminders(brief)

            prompt = f"""
{workflow_content}

{rules_content}

{style_memory_block}

{fact_memory_block}

---

## Current Task Execution

Please execute the role of C01 Content Writer for the following article:

**Brand Name**: {brand_name}
**Article Slug**: {article_slug}

**Content Brief**:
```json
{json.dumps(brief, ensure_ascii=False, indent=2)}
```

**Dynamic Links**:
- BRAND_OFFICIAL_LINE: {official_line}
- BRAND_COMMUNITY_URL: {brand_community}

**Dynamic Configuration**:
- Target Language: {target_language_desc}
- Premium Image Model: {premium_model}
- Target Forums: {target_forums}
- Contact Link: {contact_link_with_utm}

**Instructions**:
1. Strictly follow the "C01 Content Writer" workflow defined above.
2. **PRIORITY**: Check the "Style Memory" section. Follow the "Good" example and avoid the "Bad" example.
3. Use the provided Content Brief as your source of truth.
4. **IMAGE FORMAT (CRITICAL)**: When inserting images, use ONLY the format `![SEO關鍵字: 畫面描述](PLACEHOLDER)`. Do NOT use external URLs like via.placeholder.com or unsplash.com. The word PLACEHOLDER must appear literally.
5. Output ONLY the final Markdown article content.
"""
            logger.info(f"Sending request to Gemini for {slug}...")
            response = self.model.generate_content(prompt)
            if not response.text:
                logger.error("Gemini returned empty response.")
                return

            draft_text = self._clean_llm_output(response.text)
            max_retries = get_max_retries(default=2)
            attempt = 0
            errors = validate_draft(draft_text, brief, brand_profile)

            while errors and attempt < max_retries:
                attempt += 1
                logger.warning(f"Draft validation failed (attempt {attempt}): {errors}")
                fix_prompt = f"""
{workflow_content}

{rules_content}

{style_memory_block}

{fact_memory_block}

You are a strict editor. Fix the draft to satisfy the following issues:
{json.dumps(errors, ensure_ascii=False, indent=2)}

Rules:
1. Keep the structure aligned with the brief H2 outline.
2. Preserve the brand tone and content requirements.
3. Output ONLY the corrected Markdown article.

Content Brief:
```json
{json.dumps(brief, ensure_ascii=False, indent=2)}
```

Draft:
```markdown
{draft_text}
```
"""
                fix_response = self.model.generate_content(fix_prompt)
                if not fix_response.text:
                    break
                draft_text = self._clean_llm_output(fix_response.text)
                errors = validate_draft(draft_text, brief, brand_profile)

            if errors:
                logger.warning(f"Draft validation still failed after retries: {errors}")

            self.save_draft(slug, draft_text)
            logger.info(f"Successfully generated draft for {slug}")
        except Exception as e:
            logger.error(f"Error generating draft: {e}")
            raise


# =============================================================================
# 根據環境選擇架構
# =============================================================================

if USE_NEW_ARCHITECTURE:
    class C01ContentWriter(BaseAgent, C01ContentWriterBase):
        """C01 內容創作者 - 使用新架構"""

        def __init__(self):
            BaseAgent.__init__(self, name="C01_ContentWriter")
            self.brand_name = self.brand.slug
            self.base_dir = str(self.brand_manager.base_dir)
            self.output_dir = self.resolve_path("outputs/FUNIT/drafts")
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.briefs_dir = str(self.resolve_path("outputs/FUNIT/briefs"))
            self.brand_profile_path = str(self.brand.config_dir / "brand_profile.json")

            # Initialize Style Memory if available
            self.style_memory = StyleMemoryManager() if STYLE_MEMORY_AVAILABLE else None
            self.fact_memory = FactMemoryManager() if FACT_MEMORY_AVAILABLE else None

            self._configure_llm()

        def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
            """執行內容撰寫任務"""
            slug = input_data.get("slug") or input_data.get("article_slug")
            if not slug:
                raise ValueError("缺少必需參數: slug")

            self.generate_draft(slug)

            draft_path = self.resolve_path(
                "outputs/FUNIT/drafts/{ARTICLE_SLUG}.md",
                ARTICLE_SLUG=slug
            )
            return {
                "draft_path": str(draft_path),
                "slug": slug,
                "brand": self.brand.slug
            }

else:
    class C01ContentWriter(C01ContentWriterBase):
        """C01 內容創作者 - 舊架構 (向後兼容)"""

        def __init__(self):
            if SETTINGS_AVAILABLE:
                self.brand_name = settings.brand_name
            else:
                self.brand_name = "FUNIT"
            self.base_dir = os.getcwd()
            self.output_dir = os.path.join(self.base_dir, "outputs", "FUNIT", "drafts")
            self.briefs_dir = os.path.join(self.base_dir, "outputs", "FUNIT", "briefs")
            self.brand_profile_path = os.path.join(self.base_dir, "config", "brand_profile.json")

            os.makedirs(self.output_dir, exist_ok=True)

            self.style_memory = StyleMemoryManager() if STYLE_MEMORY_AVAILABLE else None
            self.fact_memory = FactMemoryManager() if FACT_MEMORY_AVAILABLE else None
            self.logger = logger

            self._configure_llm()


# =============================================================================
# CLI 介面
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="C01 Content Writer Agent")
    parser.add_argument("--slug", required=True, help="The slug of the article to write")
    args = parser.parse_args()

    writer = C01ContentWriter()
    writer.generate_draft(args.slug)
