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
import re
import logging
from PIL import Image
from utils.gemini_image_gen import gemini_image_gen
from utils.wordpress_client import wp_client
from utils.output_validators import validate_final_article

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class C04VisualDirector(BaseAgent):
    """
    C04 Visual Director - AI 視覺總監
    
    負責為文章生成高品質配圖，並處理圖片上傳與連結替換。
    """
    
    def __init__(self):
        super().__init__(name="C04_VisualDirector")
        self.brand_profile = self._load_brand_profile()
        self.brand_name = self.brand.slug
        self.visual_identity = self.brand_profile.get("visual_identity", {})
        
        # Ensure output directories exist
        self.output_dir = "outputs/FUNIT/final"
        self.images_dir = "outputs/FUNIT/images"
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)

    def _load_brand_profile(self) -> Dict:
        """Loads the brand profile configuration."""
        if hasattr(self, "brand") and getattr(self, "brand", None):
            return self.brand.brand_config or {}
        return {}

    def _construct_standard_prompt(self, description: str) -> str:
        """Construct a standard prompt based on visual identity"""
        style = self.visual_identity.get("style", "Modern and clean")
        mood = self.visual_identity.get("mood", "Professional and trustworthy")
        palette = self.visual_identity.get("color_palette", {})
        primary_color = palette.get("primary", "Navy Blue")
        
        # Detect if it's a chart or table
        is_chart = self._is_chart_or_table(description)
        
        prompt = (
            f"Generate an image of: {description}. "
            f"Style: {style}. "
            f"Mood: {mood}. "
            f"Primary color: {primary_color}. "
        )
        
        if is_chart:
            # Force Traditional Chinese for charts
            prompt += (
                " CRITICAL: All text, labels, legends, and annotations "
                "MUST be in Traditional Chinese (繁體中文). "
                "No Simplified Chinese, no English. "
                "Font style: Clean, professional Traditional Chinese typography."
            )
        else:
            # Standard cultural context from brand profile
            context_keywords = self.visual_identity.get("reference_keywords", [])
            context_str = ", ".join(context_keywords) if context_keywords else "Clean and professional"
            prompt += f" {context_str}."
            
        prompt += " No distorted text. High quality, detailed."
            
        return prompt

    def _is_chart_or_table(self, description: str) -> bool:
        """判斷是否為表格/圖表類"""
        chart_keywords = [
            "表格", "圖表", "流程圖", "對照表", "比較圖", "示意圖", "解剖", "架構圖",
            "chart", "table", "diagram", "infographic", 
            "flowchart", "comparison", "數據", "統計", "analysis", "data"
        ]
        return any(kw in description.lower() for kw in chart_keywords)

    def _process_image(self, image_path: str, slug: str, index: int) -> str:
        """Compresses and converts image to WebP."""
        try:
            img = Image.open(image_path)
            
            # Resize if too large (e.g., max width 1920)
            max_width = 1920
            if img.width > max_width:
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # Save as WebP
            filename = f"{slug}-{index}.webp"
            output_path = os.path.join(self.images_dir, filename)
            
            img.save(output_path, "WEBP", quality=85)
            self.log_activity(f"Processed image saved to {output_path}")
            return output_path
        except Exception as e:
            self.log_activity(f"Error processing image {image_path}: {e}")
            raise

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates images for an article.
        """
        slug = input_data.get("slug", "")
        if not slug:
            return {"status": "error", "message": "Slug is required"}

        self.log_activity(f"Starting Visual Director for: {slug}")

        # 1. Determine Input File
        # Priority: _with_recommendation.md > .md
        # Locations: optimized > final > drafts
        
        search_paths = [
            f"outputs/FUNIT/optimized/{slug}_with_recommendation.md",
            f"outputs/FUNIT/optimized/{slug}.md",
            f"outputs/FUNIT/final/{slug}_with_recommendation.md",
            f"outputs/FUNIT/final/{slug}.md",
            f"outputs/FUNIT/drafts/{slug}.md",
        ]
        
        input_path = ""
        for path in search_paths:
            if os.path.exists(path):
                input_path = path
                break
        
        if not input_path:
             return {"status": "error", "message": f"Input file not found for slug: {slug}. Searched in: {search_paths}"}
        
        self.log_activity(f"Reading input from: {input_path}")

        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1.5 Placeholder-only mode
        image_strategy = self.visual_identity.get("image_strategy", {})
        if image_strategy.get("mode") == "placeholder_only":
            standard_placeholders = re.findall(r'!\[(.*?)\]\(PLACEHOLDER\)', content)
            premium_placeholders = re.findall(r'!\[(.*?)\]\(PREMIUM_PLACEHOLDER\)', content)
            shot_list = [
                {"type": "standard", "alt_text": alt} for alt in standard_placeholders
            ] + [
                {"type": "premium", "alt_text": alt} for alt in premium_placeholders
            ]

            output_path = os.path.join(self.output_dir, f"{slug}.md")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.log_activity("Image strategy set to placeholder_only. Skipping generation.")
            return {
                "status": "skipped",
                "output_path": output_path,
                "image_shot_list": shot_list
            }

        # 2. Process Images
        new_content = content
        image_count = 0
        
        # 2.1 Extract Premium Prompts
        premium_prompt_pattern = re.compile(r'\[PREMIUM_IMAGE_PROMPT\](.*?)\[/PREMIUM_IMAGE_PROMPT\]', re.DOTALL)
        premium_prompts = premium_prompt_pattern.findall(content)
        
        # Remove prompt blocks from content
        new_content = premium_prompt_pattern.sub('', new_content)
        
        # 2.2 Handle Premium Placeholders
        premium_placeholder_pattern = re.compile(r'!\[(.*?)\]\(PREMIUM_PLACEHOLDER\)')
        
        def replace_premium(match):
            nonlocal image_count
            alt_text = match.group(1)
            image_count += 1
            
            if premium_prompts:
                prompt = premium_prompts.pop(0).strip()
            else:
                prompt = self._construct_standard_prompt(alt_text)
                self.log_activity("No premium prompt block found for premium placeholder, using standard prompt.")
            
            self.log_activity(f"Generating PREMIUM image {image_count}: {alt_text}")
            
            # Generate
            temp_path = os.path.join(self.images_dir, f"temp_{slug}_{image_count}.png")
            try:
                gemini_image_gen.generate_image(prompt, temp_path, model_type="premium")
            except Exception as e:
                self.log_activity(f"Premium generation failed ({e}), falling back to standard model...")
                gemini_image_gen.generate_image(prompt, temp_path, model_type="standard")
            
            # Process & Upload
            try:
                final_path = self._process_image(temp_path, slug, image_count)
                self.log_activity("Uploading to WordPress...")
                media_info = wp_client.upload_media(final_path, caption=alt_text)
                image_url = media_info.get("source_url")
                
                if not image_url:
                    self.log_activity("Failed to get image URL from WordPress")
                    return match.group(0)
                
                return f"![{alt_text}]({image_url})"
            except Exception as e:
                self.log_activity(f"Error handling image {image_count}: {e}")
                return match.group(0)

        new_content = premium_placeholder_pattern.sub(replace_premium, new_content)
        
        # 2.3 Handle Standard Placeholders
        standard_placeholder_pattern = re.compile(r'!\[(.*?)\]\(PLACEHOLDER\)')
        
        def replace_standard(match):
            nonlocal image_count
            alt_text = match.group(1)
            image_count += 1
            
            prompt = self._construct_standard_prompt(alt_text)
            self.log_activity(f"Generating STANDARD image {image_count}: {alt_text}")
            
            # Generate
            temp_path = os.path.join(self.images_dir, f"temp_{slug}_{image_count}.png")
            try:
                gemini_image_gen.generate_image(prompt, temp_path, model_type="standard")
                
                # Process & Upload
                final_path = self._process_image(temp_path, slug, image_count)
                self.log_activity("Uploading to WordPress...")
                media_info = wp_client.upload_media(final_path, caption=alt_text)
                image_url = media_info.get("source_url")
                
                if not image_url:
                    self.log_activity("Failed to get image URL from WordPress")
                    return match.group(0)
                    
                return f"![{alt_text}]({image_url})"
            except Exception as e:
                 self.log_activity(f"Error handling image {image_count}: {e}")
                 return match.group(0)

        new_content = standard_placeholder_pattern.sub(replace_standard, new_content)
        
        # 3. Save Final Article
        output_path = os.path.join(self.output_dir, f"{slug}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        validation_errors = validate_final_article(new_content)
        if validation_errors:
            self.log_activity(f"Final article validation warnings: {validation_errors}")
            return {"status": "warning", "output_path": output_path, "issues": validation_errors}

        self.log_activity(f"Article processing complete! Saved to: {output_path}")
        
        return {
            "status": "success",
            "output_path": output_path
        }

# Global instance
c04_visual_director = C04VisualDirector()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='C04 Visual Director')
    parser.add_argument('--slug', type=str, required=True, help='Slug of the article to process')
    
    args = parser.parse_args()
    
    try:
        result = c04_visual_director.run({
            "slug": args.slug
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)
