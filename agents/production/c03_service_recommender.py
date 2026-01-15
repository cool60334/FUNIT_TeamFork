import os
import argparse
import sys
from pathlib import Path

# Fix sys.path to allow imports from project root
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agents.core import BaseAgent
from typing import Dict, Any, List
import json
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
import re
from utils.prompt_assets import load_workflow_text, load_rules_text
from utils.output_validators import validate_recommendation_block
from utils.system_config import get_max_retries

class C03ServiceRecommender(BaseAgent):
    """
    C03 Service Recommender - 服務推薦師 (Workflow-Driven)
    """
    
    def __init__(self):
        super().__init__(name="C03_ServiceRecommender")
        self.brand_profile = self.brand.brand_config or {}
        self.brand_name = self.brand.slug
        self.rules_content = load_rules_text("c03")
        self._configure_llm()


    def _configure_llm(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.log_activity("Error: GEMINI_API_KEY not found in environment.")
            print(json.dumps({"status": "error", "message": "GEMINI_API_KEY not found"}, ensure_ascii=False))
            sys.exit(1)
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3-pro-preview')

    def _load_prompt_template(self) -> str:
        """Reads the prompt template from the workflow markdown file."""
        try:
            content = load_workflow_text("c03_service_recommender")
            
            # Extract content between ```markdown and ``` in the "AI Prompt Template" section
            # This is a simple extraction, assuming the structure matches the file we just edited.
            # We look for the block after "## AI Prompt Template"
            
            pattern = r"## AI Prompt Template.*?```markdown\n(.*?)\n```"
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1)
            else:
                self.log_activity("Warning: Could not extract prompt template from workflow file. Using fallback.")
                return "" # Should define a fallback or fail
        except FileNotFoundError:
            self.log_activity("Error: Workflow file not found for C03")
            return ""

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        slug = input_data.get("slug", "")
        if not slug:
            return {"status": "error", "message": "Slug is required"}

        self.log_activity(f"Starting Workflow-Driven Recommendation for: {slug}")

        # 1. Load Data
        optimized_path = f"outputs/FUNIT/optimized/{slug}.md"
        if not os.path.exists(optimized_path):
             optimized_path = f"outputs/FUNIT/final/{slug}.md"
        
        # Try multiple paths for site_structure.json
        possible_paths = [
            "outputs/FUNIT/raw_data/site_structure.json",
            "outputs/FUNIT/收集到的資料/site_structure.json",
            "outputs/收集到的資料/site_structure.json",
            "outputs/FUNIT/data/site_structure.json",
        ]
        
        site_structure_path = ""
        for path in possible_paths:
            if os.path.exists(path):
                site_structure_path = path
                self.log_activity(f"Found site_structure.json at: {path}")
                break
        
        if not site_structure_path:
             self.log_activity(f"Warning: site_structure.json not found in any expected location: {possible_paths}")
             site_structure_path = possible_paths[0] # Fallback to avoid crash, though it will fail later if not handled

        try:
            with open(optimized_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Load Brand Profile
            # Already loaded in init, but can reload if needed or just use self.brand_profile
            brand_profile = self.brand_profile


            site_structure = {}
            if os.path.exists(site_structure_path):
                with open(site_structure_path, "r", encoding="utf-8") as f:
                    site_structure = json.load(f)
            else:
                self.log_activity(f"Warning: site_structure.json not found.")
                
        except FileNotFoundError as e:
            return {"status": "error", "message": f"File not found: {e}"}

        # 2. Prepare Context
        article_context = content[:3000] # Increased context
        
        candidates = []
        # Add Products (now with description/categories)
        for p in site_structure.get("products", []):
            candidates.append({
                "id": p.get("id"),
                "type": "product",
                "name": p.get("name"),
                "link": p.get("link"),
                "description": p.get("description", "")[:200]
            })
        # Add Services
        for p in site_structure.get("pages", []):
             title = p.get("title", "")
             if any(x in title for x in ["服務", "行程", "關於", "課程", "聯絡"]):
                  candidates.append({
                     "id": p.get("id"),
                     "type": "service",
                     "name": title,
                     "link": p.get("link"),
                     "description": "Service Page"
                 })

        # 3. Prepare Prompt
        prompt_template = self._load_prompt_template()
        if not prompt_template:
            return {"status": "error", "message": "Prompt template not found"}
            
        prompt = prompt_template.replace("{BRAND_NAME}", self.brand_name)
        prompt = prompt.replace("{ARTICLE_CONTEXT}", article_context)
        prompt = prompt.replace("{CANDIDATES_JSON}", json.dumps(candidates, ensure_ascii=False, indent=2))
        
        # Pass Brand Community URL
        # Handle hierarchical or flat structure in brand_profile.json
        channels = brand_profile.get("contact_channels", {}) or brand_profile.get("data_sources", {}).get("contact_channels", {})
        brand_community_url = channels.get("品牌社群", "") or channels.get("official_line", "")
        prompt = prompt.replace("{BRAND_COMMUNITY_URL}", brand_community_url)
        if self.rules_content:
            prompt = f"{self.rules_content}\n\n{prompt}"

        # 4. Call LLM
        try:
            max_retries = get_max_retries(default=2)
            attempt = 0
            rec_block = ""
            allowed_urls = [c.get("link") for c in candidates if c.get("link")]
            if brand_community_url:
                allowed_urls.append(brand_community_url)
            allowed_urls = [
                f"{u}{'&' if '?' in u else '?'}utm_source=blog&utm_medium=article&utm_campaign=service_recommendation"
                for u in allowed_urls
            ]

            while attempt <= max_retries:
                response = self.model.generate_content(prompt)
                rec_block = response.text.strip() if response.text else ""
                if not rec_block:
                    attempt += 1
                    continue

                match = re.search(r"```markdown\s*(.*?)(?:```|$)", rec_block, re.DOTALL)
                if match:
                    rec_block = match.group(1).strip()
                else:
                    header_match = re.search(r"(##\s+[🚀💡🎁🤝].*)", rec_block, re.DOTALL)
                    if header_match:
                        rec_block = header_match.group(1).strip()
                    else:
                        if rec_block.startswith("```"):
                            rec_block = re.sub(r"^```\w*\s*", "", rec_block)
                        if rec_block.endswith("```"):
                            rec_block = re.sub(r"\s*```$", "", rec_block)

                rec_block = rec_block.strip()
                errors = validate_recommendation_block(rec_block, allowed_urls)
                if not errors:
                    break

                attempt += 1
                if attempt > max_retries:
                    break
                fix_prompt = f"""
Fix the recommendation block based on these issues. Output ONLY Markdown.
Errors:
{json.dumps(errors, ensure_ascii=False, indent=2)}

Current Block:
```markdown
{rec_block}
```
"""
                prompt = f"{self.rules_content}\n\n{fix_prompt}"
                
        except Exception as e:
            self.log_activity(f"LLM Generation Failed: {e}")
            return {"status": "error", "message": str(e)}

        # 5. Insert Block
        # Rule: Insert AFTER FAQ Block if present
        # Modified for Classic Editor: Also check for HTML FAQ blocks
        faq_markers = [
            "<!-- /wp:rank-math/faq-block -->",
            "<!-- /wp:wpseopress/faq-block -->",
            '</div><!-- /wp:wpseopress/faq-block -->',
            '</div><!-- /wp:rank-math/faq-block -->',
            '</div>\n<!-- /wp:rank-math/faq-block -->',
            '</div>\n<!-- /wp:wpseopress/faq-block -->',
            '</div>\n</div>' # Potential nested end
        ]
        
        # New markers for Classic Editor (HTML)
        classic_faq_markers = [
            '<div class="sp-faq-block">',
            '<div class="wp-block-rank-math-faq-block">'
        ]
        
        insert_pos = -1
        
        # 1. Try Gutenberg markers first
        for marker in faq_markers:
            pos = content.find(marker)
            if pos != -1:
                insert_pos = pos + len(marker)
                break
        
        # 2. Try Classic markers (find the end of the div)
        if insert_pos == -1:
            for marker in classic_faq_markers:
                pos = content.find(marker)
                if pos != -1:
                    # Find the closing </div> of this block
                    # This is a bit simplified, but since our C02 generates a single outer <div>,
                    # we look for the last </div>
                    last_div = content.rfind('</div>')
                    if last_div != -1 and last_div > pos:
                        insert_pos = last_div + 6 # After </div>
                    break

        if insert_pos != -1:
            final_content = content[:insert_pos] + "\n\n" + rec_block + content[insert_pos:]
        else:
            # Fallback: Before Conclusion
            conclusion_markers = ["## Conclusion", "## 結語"]
            conclusion_pos = -1
            for marker in conclusion_markers:
                pos = content.find(marker)
                if pos != -1:
                    conclusion_pos = pos
                    break
            
            if conclusion_pos != -1:
                 final_content = content[:conclusion_pos] + rec_block + "\n\n" + content[conclusion_pos:]
            else:
                 final_content = content + "\n\n" + rec_block

        # 6. Save Output
        output_dir = "outputs/FUNIT/optimized"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{slug}_with_recommendation.md")
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)
            
        self.log_activity(f"Recommendation inserted for {slug}")

        return {
            "status": "success",
            "output_path": output_path
        }

# Handle singleton initialization carefully when brand is dynamic
c03_service_recommender = None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='C03 Service Recommender')
    parser.add_argument('--slug', type=str, required=True, help='Slug of the optimized article')
    args = parser.parse_args()
    
    c03_service_recommender = C03ServiceRecommender()
    
    try:
        result = c03_service_recommender.run({
            "slug": args.slug
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)
