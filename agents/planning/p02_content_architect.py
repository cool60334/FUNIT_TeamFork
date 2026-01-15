from agents.core import BaseAgent, PathResolver, resolve_path
from utils.vector_db_manager import vector_db
from typing import Dict, Any, List
import json
import os
import argparse
import sys
from utils.content_fetcher import ContentFetcher
from utils.prompt_assets import load_workflow_text, load_rules_text
from utils.output_validators import validate_brief
from utils.system_config import get_max_retries

class P02ContentArchitect(BaseAgent):
    """
    P02 Content Architect - 內容架構師
    
    架構設計：
    - ⚙️ Python: 接收 P01 結果（含重複性檢查）
    - 🧠 Antigravity: 生成詳細內容 Brief (執行 .agent/workflows/p02_content_architect.md)
    - ⚙️ Python: 儲存 Brief JSON (使用 LanceDB 作為輔助資料源)
    """
    
    def __init__(self):
        super().__init__(name="P02_ContentArchitect")
        self.brand_profile = self.brand.brand_config or {}
        self.brand_name = self.brand.slug
        self.content_fetcher = ContentFetcher()
        self.vector_db = vector_db
        self.resolver = PathResolver()
        # Initialize LLM
        try:
            from utils.gemini_text_gen import GeminiTextGenerator
            self.llm = GeminiTextGenerator()
        except ImportError:
            self.log_activity("Warning: utils.gemini_text_gen not found. LLM features disabled.")
            self.llm = None

    def _load_workflow_prompt(self) -> str:
        """Loads workflow content for prompt injection."""
        return load_workflow_text("p02_content_architect")

    def _load_rules_prompt(self) -> str:
        """Loads rules content for prompt injection."""
        return load_rules_text("p02")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates comprehensive content briefs based on keyword strategy.
        """
        topic = input_data.get("topic", "")
        strategy_path = input_data.get("strategy_path")
        
        if not topic:
            return {"status": "error", "message": "Topic is required"}

        self.log_activity(f"Starting Content Architect for topic: {topic}")

        # 1. Load Strategy
        if not strategy_path:
            strategy_path = self.resolver.resolve("outputs/{BRAND_NAME}/strategies/topic_cluster_{TOPIC_SLUG}.json", TOPIC_SLUG=topic.replace(" ", "-"))
        
        try:
            with open(strategy_path, "r", encoding="utf-8") as f:
                strategy = json.load(f)
            self.log_activity(f"Loaded strategy from {strategy_path}")
        except FileNotFoundError:
            return {"status": "error", "message": f"Strategy file not found: {strategy_path}"}

        # 2. Load Context (Optional but recommended)
        context_path = self.resolver.resolve("outputs/{BRAND_NAME}/raw_data/p01_context.json")
        context_data = {}
        try:
            if os.path.exists(context_path):
                with open(context_path, "r", encoding="utf-8") as f:
                    context_data = json.load(f)
                self.log_activity(f"Loaded context from {context_path}")
        except Exception as e:
            self.log_activity(f"Warning: Could not load context: {e}")

        # 3. Generate Briefs
        generated_briefs = []
        strategy_audience = strategy.get("target_audience", "")
        
        # 3.1 Generate Pillar Page Brief
        if "pillar_page" in strategy:
            pillar_brief = self._generate_single_brief(strategy["pillar_page"], "Pillar Page", context_data, strategy_audience)
            self._save_brief(pillar_brief)
            generated_briefs.append(pillar_brief["slug"])

        # 3.2 Generate Cluster Page Briefs
        if "cluster_pages" in strategy:
            for page in strategy["cluster_pages"]:
                # Check duplication status from strategy
                page_status = page.get("status", "planned")
                # Ensure we pass this status down
                page["status"] = page_status 
                
                cluster_brief = self._generate_single_brief(page, "Cluster Page", context_data, strategy_audience)
                self._save_brief(cluster_brief)
                generated_briefs.append(cluster_brief["slug"])

        self.log_activity(f"Generated {len(generated_briefs)} briefs.")
        
        return {
            "status": "success",
            "generated_briefs": generated_briefs
        }



    def _generate_single_brief(self, page_data: Dict[str, Any], page_type: str, context: Dict[str, Any], strategy_audience: str = "") -> Dict[str, Any]:
        """
        Generates a brief object for a single page using LLM.
        """
        title = page_data.get("title", "")
        slug = page_data.get("slug", "")
        keyword = page_data.get("primary_keyword", page_data.get("keyword", ""))
        intent = page_data.get("search_intent", page_data.get("intent", "Informational"))
        
        # 2. Add Context (Existing Content for Refactoring)
        existing_content = page_data.get("existing_content", "")
        existing_url = page_data.get("existing_url")
        status = page_data.get("status", "planned") # check if EXISTING or planned

        if not existing_content and existing_url:
            self.log_activity(f"Refactoring Mode: Fetching existing content from {existing_url}")
            fetched_text = self.content_fetcher.fetch(existing_url)
            if fetched_text:
                existing_content = fetched_text[:8000] # Increased limit for LLM context
                self.log_activity(f"Fetched {len(existing_content)} chars from existing URL.")
            else:
                self.log_activity(f"Warning: Failed to fetch content from {existing_url}")
        
        # Determine Target Audience
        brand_style_list = context.get("brand_style", [])
        brand_style_meta = {}
        if isinstance(brand_style_list, list) and len(brand_style_list) > 0:
            # Look for a dict result
            first_res = brand_style_list[0]
            if isinstance(first_res, dict):
                brand_style_meta = first_res.get("metadata", {})
        
        raw_target_audience = strategy_audience or brand_style_meta.get("target_audience", "一般大眾")
        target_audience = self._resolve_target_audience(raw_target_audience)
        
        # Generate with LLM if available
        if self.llm:
            return self._generate_brief_with_llm(
                title=title,
                slug=slug,
                keyword=keyword,
                intent=intent,
                page_type=page_type,
                target_audience=target_audience,
                existing_content=existing_content,
                context_data=context
            )
        
        # Fallback to Template if LLM unavailable
        brief = {
            "title": title,
            "slug": slug,
            "primary_keyword": keyword,
            "page_type": page_type,
            "search_intent": intent,
            "target_audience": target_audience,
            "tone": "專業、同理、值得信賴 (請參考 Brand Guideline)",
            "category": self._determine_category(keyword, title, context),
            "outline": self._generate_outline_template(intent, title),
            "word_count_target": 2500 if "Pillar" in page_type else 1500,
            "cta": "歡迎聯繫我們了解更多",
            "internal_link_opportunities": self._find_internal_links(keyword, slug),
            "status": status,
            "existing_content_raw": existing_content
        }
        
        if page_type == "Cluster Page":
            brief["pillar_page_slug"] = context.get("topic", "unknown-topic").replace(" ", "-")
            brief["angle"] = page_data.get("angle", "")

        return brief

    def _generate_brief_with_llm(self, title, slug, keyword, intent, page_type, target_audience, existing_content, context_data) -> Dict[str, Any]:
        """
        Uses LLM to generate a detailed brief.
        """
        self.log_activity(f"Generating intelligent brief for '{title}' via LLM...")
        
        brand_style_list = context_data.get("brand_style", [])
        brand_tone = "Professional, Empathetic"
        if isinstance(brand_style_list, list) and len(brand_style_list) > 0:
            # Fallback to metadata of first result if it exists
            first_res = brand_style_list[0]
            if isinstance(first_res, dict):
                brand_tone = first_res.get("metadata", {}).get("tone", brand_tone)
        
        workflow_content = self._load_workflow_prompt()
        rules_content = self._load_rules_prompt()

        # Load available categories from site_structure.json
        available_categories = self._get_available_category_names()
        categories_str = ", ".join(available_categories) if available_categories else "General"
        
        prompt = f"""
        {workflow_content}

        {rules_content}

        You are a Senior Content Architect for {self.brand_name}.
        Task: Create a detailed Content Brief JSON for a new or optimized article.
        
        # Context
        - **Title**: {title}
        - **Primary Keyword**: {keyword}
        - **Page Type**: {page_type}
        - **Search Intent**: {intent}
        - **Target Audience**: {target_audience}
        - **Brand Tone**: {brand_tone}
        - **Language**: {self.brand_profile.get('content_strategy', {}).get('language', 'Traditional Chinese')} (Must output in this language)
        
        # Available Categories (MUST use one of these exactly)
        {categories_str}
        
        # Requirement
        1. **Hook Strategy**: Design a specific, engaging hook (e.g., data-backed, story-driven) based on the keyword intent.
        2. **Outline**: Create a detailed H2 structure. 
           - If `existing_content` is provided, this is a **REFACTORING** task. You MUST keep valuable parts of the old content but reorganize/rewrite to match the new intent and keyword. Highlight what to [KEEP], [UPDATE], or [NEW].
           - If new content, design from scratch.
        3. **Gap Analysis**: If refactoring, what's missing in the old content vs specific competitors or user needs?
        4. **Category**: MUST select from the "Available Categories" list above. Do NOT invent new category names.
        
        # Existing Content (for Refactoring)
        {existing_content if existing_content else "N/A (New Article)"}
        
        # Output Format (Strict JSON)
        {{
          "title": "{title}",
          "slug": "{slug}",
          "primary_keyword": "{keyword}",
          "page_type": "{page_type}",
          "search_intent": "{intent}",
          "target_audience": "{target_audience}",
          "tone": "...",
          "category": "...",
          "word_count_target": 2000,
          "search_intent_research": {{
            "query": "{keyword}",
            "recommended_hook_strategy": "...",
            "content_gaps": ["gap 1", "gap 2"]
          }},
          "outline": [
            {{
              "section": "Introduction",
              "h2_title": "...",
              "key_points": ["point 1", "point 2"]
            }},
            ...
          ],
          "cta": "...",
          "internal_link_opportunities": [] 
        }}
        """
        
        try:
            max_retries = get_max_retries(default=2)
            attempt = 0
            last_errors = []

            while attempt <= max_retries:
                response = self.llm.generate_text(prompt)
                clean_json = response.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json.split("\n", 1)[1]
                if clean_json.endswith("```"):
                    clean_json = clean_json.rsplit("\n", 1)[0]

                try:
                    brief = json.loads(clean_json)
                except Exception as e:
                    last_errors = [f"Brief JSON 解析失敗: {e}"]
                    attempt += 1
                    prompt = f"""
{workflow_content}

{rules_content}

Please output ONLY valid JSON. Fix these issues:
{json.dumps(last_errors, ensure_ascii=False, indent=2)}

Previous Output:
{clean_json}
"""
                    continue

                # Post-processing imports & links
                brief["internal_link_opportunities"] = self._find_internal_links(keyword, slug)
                brief["existing_content_raw"] = existing_content

                errors = validate_brief(brief)
                if not errors:
                    return brief

                last_errors = errors
                attempt += 1
                prompt = f"""
{workflow_content}

{rules_content}

Fix the brief JSON based on these validation errors. Output ONLY valid JSON.
Errors:
{json.dumps(errors, ensure_ascii=False, indent=2)}

Current Brief JSON:
{json.dumps(brief, ensure_ascii=False, indent=2)}
"""

            self.log_activity(f"Brief validation failed after retries: {last_errors}")
            return brief
        except Exception as e:
            self.log_activity(f"LLM generation failed: {e}. Falling back to template.")
            # Return basic info so caller can decide or partially save
            return {
                "title": title,
                "slug": slug,
                "primary_keyword": keyword,
                "page_type": page_type,
                "search_intent": intent,
                "target_audience": target_audience,
                "tone": "專業 (Fallback)",
                "category": self._determine_category(keyword, title, context_data),
                "outline": self._generate_outline_template(intent, title),
                "word_count_target": 1500,
                "cta": "聯繫我們",
                "internal_link_opportunities": self._find_internal_links(keyword, slug),
                "error": str(e)
            }

    def _get_available_category_names(self) -> List[str]:
        """
        Loads available category names from site_structure.json.
        Returns a list of category names (excluding 'Uncategorized').
        """
        try:
            structure_path = self.resolver.resolve("outputs/{BRAND_NAME}/raw_data/site_structure.json")
            if not structure_path.exists():
                return []
            
            with open(structure_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                categories = data.get("categories", [])
            
            # Extract names, excluding 'Uncategorized'
            names = [cat.get("name") for cat in categories if cat.get("name") and cat.get("name") != "Uncategorized"]
            return names
        except Exception as e:
            self.log_activity(f"Error loading category names: {e}")
            return []

    def _get_default_category(self) -> str:
        """
        Returns the default category from brand config or a generic fallback.
        """
        default = self.brand_profile.get("content_strategy", {}).get("default_category", "General")
        return default


    def _determine_category(self, keyword: str, title: str, context: Dict[str, Any]) -> str:
        """
        Dynamically determines the best category based on keyword and title.
        Loads categories from site_structure.json.
        """
        try:
            # 1. Load Categories
            structure_path = self.resolver.resolve("outputs/{BRAND_NAME}/raw_data/site_structure.json")
            
            if not structure_path.exists():
                self.log_activity(f"Warning: site_structure.json not found at {structure_path}, using default.")
                return self._get_default_category() # Read from brand config

            with open(structure_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                categories = data.get("categories", [])

            if not categories:
                return self._get_default_category()

            # 2. Simple Keyword Matching
            # Score each category based on how many characters of the keyword/title appear in the category name
            best_category = None
            max_score = 0
            
            search_text = (keyword + " " + title).lower()
            
            for cat in categories:
                cat_name = cat.get("name", "")
                if cat_name == "Uncategorized":
                    continue
                    
                score = 0
                cat_name_lower = cat_name.lower()
                
                # Bonus for exact substring match
                if cat_name_lower in search_text:
                    score += 10
                
                # Bonus for overlap words
                cat_words = set(cat_name_lower)
                search_words = set(search_text)
                overlap = len(cat_words.intersection(search_words))
                score += overlap
                
                if score > max_score:
                    max_score = score
                    best_category = cat_name

            # Heuristic: Penalize "Testimonial" categories if title doesn't imply it
            if best_category and any(x in best_category for x in ["心得", "故事", "分享"]):
                if not any(x in search_text for x in ["心得", "故事", "分享", "經驗", "採訪"]):
                     # Look for the next best category that isn't a testimonial
                     self.log_activity(f"Downgrading '{best_category}' because title lacks testimonial keywords.")
                     
                     # Re-evaluate without testimonial categories
                     best_category = None
                     max_score = 0
                     for cat in categories:
                        cat_name = cat.get("name", "")
                        if any(x in cat_name for x in ["心得", "故事", "分享"]): # Skip testimonials
                            continue
                        if cat_name == "Uncategorized":
                            continue

                        score = 0
                        cat_name_lower = cat_name.lower()
                        if cat_name_lower in search_text:
                            score += 10
                        cat_words = set(cat_name_lower)
                        search_words = set(search_text)
                        score += len(cat_words.intersection(search_words))
                        
                        if score > max_score:
                            max_score = score
                            best_category = cat_name

            if best_category:
                self.log_activity(f"Determined category '{best_category}' for '{title}' (Score: {max_score})")
                return best_category
            
            # 3. Default if no match found
            # Attempt to return the most generic category usually found in education sites
            # Or just the one with the most posts (highest count)
            sorted_cats = sorted(categories, key=lambda x: x.get("count", 0), reverse=True)
            if sorted_cats:
                fallback = sorted_cats[0].get("name")
                if fallback == "Uncategorized" and len(sorted_cats) > 1:
                    fallback = sorted_cats[1].get("name")
                self.log_activity(f"No specific category match, using most popular: {fallback}")
                return fallback

            return self._get_default_category()

        except Exception as e:
            self.log_activity(f"Error determining category: {e}")
            return self._get_default_category()

    def _find_internal_links(self, keyword: str, current_slug: str, limit: int = 3) -> List[Dict[str, str]]:
        """
        Search for relevant internal link opportunities using Vector DB.
        """
        if not keyword:
            return []
            
        try:
            # Query vector DB for semantically similar content
            # Query more candidates to allow for filtering
            results = self.vector_db.query_content(query_text=keyword, n_results=limit + 5)
            
            links = []
            domain = self.brand_profile.get("brand_identity", {}).get("domain", "")
            
            for res in results:
                metadata = res.get("metadata", {})
                res_slug = metadata.get("slug")
                res_title = metadata.get("title")
                res_type = metadata.get("type", "post")
                
                # Filter criteria:
                # 1. Must have slug and title
                # 2. Exclude self
                # 3. Only include posts and pages
                if not res_slug or not res_title:
                    continue
                if res_slug == current_slug:
                    continue
                if res_type not in ["post", "page"]:
                    continue
                if any(l["url"].endswith(res_slug) for l in links): # Avoid duplicates
                    continue

                # Construct URL
                # Handle both naked domain or full url in config (normalize)
                base_url = f"https://{domain}" if domain and not domain.startswith("http") else domain
                if not base_url: 
                    base_url = "" # Fallback
                
                # Try to look up in site_structure.json for precise URL (path segments)
                precise_url = ""
                try:
                    structure_path = self.resolver.resolve("outputs/{BRAND_NAME}/raw_data/site_structure.json")
                    if structure_path.exists():
                        with open(structure_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            for item in data.get("posts", []) + data.get("pages", []):
                                if item.get("slug") == res_slug or str(item.get("id")) == str(metadata.get("id")):
                                    precise_url = item.get("link")
                                    break
                except Exception:
                    pass

                url = precise_url if precise_url else f"{base_url.rstrip('/')}/{res_slug.lstrip('/')}"
                if not url.endswith("/") and not "?" in url:
                    url += "/"
                
                links.append({
                    "title": res_title,
                    "url": url,
                    "distance": res.get("distance")
                })
                
                if len(links) >= limit:
                    break
            
            self.log_activity(f"Found {len(links)} internal link opportunities for '{keyword}'")
            return links
            
        except Exception as e:
            self.log_activity(f"Error searching for internal links: {e}")
            return []

    def _generate_outline_template(self, intent: str, title: str) -> List[Dict[str, Any]]:
        """
        Generates a basic outline template based on intent.
        """
        outline = []
        
        # Introduction
        outline.append({
            "section": "Introduction",
            "h2_title": "引言",
            "key_points": [
                "用讀者感同身受的痛點開場。",
                f"簡短介紹 {title}。",
                "說明讀者將從本文學到什麼。"
            ]
        })
        
        # Body Paragraphs (Generic Structure)
        if "Commercial" in intent:
            outline.append({
                "section": "Main Body",
                "h2_title": "關鍵考量因素",
                "key_points": ["因素 1", "因素 2", "因素 3"]
            })
            outline.append({
                "section": "Main Body",
                "h2_title": "精選推薦",
                "key_points": ["選項 A", "選項 B", "比較分析"]
            })
        else: # Informational
            outline.append({
                "section": "Main Body",
                "h2_title": "基礎知識",
                "key_points": ["定義", "背景/歷史"]
            })
            outline.append({
                "section": "Main Body",
                "h2_title": "步驟教學",
                "key_points": ["步驟 1", "步驟 2", "步驟 3"]
            })

        # Conclusion
        outline.append({
            "section": "Conclusion",
            "h2_title": "結論",
            "key_points": [
                "總結重點。",
                "行動呼籲 (CTA)。"
            ]
        })
        
        return outline

    def _save_brief(self, brief: Dict[str, Any]):
        """
        Saves the brief as JSON and Markdown.
        """
        slug = brief.get("slug", "untitled")
        output_dir = f"outputs/{self.brand_name}/briefs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Save JSON
        json_path = self.resolver.resolve("outputs/{BRAND_NAME}/briefs/{SLUG}_brief.json", SLUG=slug)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(brief, f, ensure_ascii=False, indent=2)
            
        # Save Markdown
        md_path = self.resolver.resolve("outputs/{BRAND_NAME}/briefs/{SLUG}_brief.md", SLUG=slug)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Content Brief: {brief.get('title', 'Untitled')}\n\n")
            f.write(f"- **網址代稱 (Slug)**: `{slug}`\n")
            f.write(f"- **關鍵字 (Keyword)**: {brief.get('primary_keyword', 'N/A')}\n")
            f.write(f"- **搜尋意圖 (Intent)**: {brief.get('search_intent', 'N/A')}\n")
            f.write(f"- **文章類型 (Type)**: {brief.get('page_type', 'N/A')}\n\n")
            
            f.write("## 大綱 (Outline)\n")
            for section in brief.get("outline", []):
                f.write(f"### {section.get('h2_title', 'Section')}\n")
                for point in section.get('key_points', []):
                    f.write(f"- {point}\n")
                f.write("\n")
            
            f.write("## 切入角度與筆記 (Angle & Notes)\n")
            if "angle" in brief:
                f.write(f"- **切入角度 (Angle)**: {brief.get('angle')}\n")
            f.write(f"- **目標受眾 (Target Audience)**: {brief.get('target_audience', 'N/A')}\n")

    def _resolve_target_audience(self, target_audience: str) -> str:
        """
        Resolves the target audience. If it's a file path, reads the file content.
        """
        if not target_audience:
            return "一般大眾"
            
        # Check if it looks like a file path (starts with docs/ or outputs/ or ends with .md)
        if target_audience.endswith(".md") or "/" in target_audience:
            # Try to resolve relative to project root (cwd)
            # Or formatted path
            if os.path.exists(target_audience):
                try:
                    with open(target_audience, "r", encoding="utf-8") as f:
                        content = f.read()
                        self.log_activity(f"Resolved target audience from file: {target_audience}")
                        # If file is huge, maybe summarize? For now, we assume it's the specific section or file.
                        return content
                except Exception as e:
                    self.log_activity(f"Error reading target audience file {target_audience}: {e}")
                    return target_audience # Fallback to string
            elif hasattr(self, "brand") and getattr(self, "brand", None):
                rel_path = os.path.join(str(self.brand.config_dir), target_audience)
                if os.path.exists(rel_path):
                    try:
                        with open(rel_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            self.log_activity(f"Resolved target audience from file: {rel_path}")
                            return content
                    except Exception as e:
                        self.log_activity(f"Error reading target audience file {rel_path}: {e}")
                        return target_audience
            else:
                 self.log_activity(f"Target audience file not found: {target_audience}, utilizing raw string.")
        
        return target_audience

# Global instance
p02_content_architect = P02ContentArchitect()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='P02 Content Architect')
    parser.add_argument('--topic', type=str, required=True, help='Topic to generate briefs for')
    parser.add_argument('--strategy_path', type=str, help='Path to strategy JSON file')
    
    args = parser.parse_args()
    
    try:
        result = p02_content_architect.run({
            "topic": args.topic,
            "strategy_path": args.strategy_path
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)
