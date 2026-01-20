from agents.base_agent import BaseAgent
from utils.vector_db_manager import vector_db
from utils.gemini_text_gen import gemini_text_gen
from utils.web_researcher import WebResearcher
from typing import Dict, Any
import json
import os
import argparse
import sys
from config.settings import settings

class C01ContentWriter(BaseAgent):
    """
    C01 Content Writer - 內容寫手
    """
    
    
    def __init__(self):
        super().__init__(name="C01_ContentWriter", role="Content Writer")

    def run(self, brief_path: str = None, manual_reviews: str = None):
        """
        Main execution flow.
        """
        try:
            # 1. Load Brand Guidelines & Profile
            # This part was added by the user's instruction, assuming brand_profile.json exists
            brand_guidelines = self._get_brand_guidelines()
            brand_profile = self._load_brand_profile()

            # 2. Load Brief
            if not brief_path:
                self.log_activity("No brief_path provided. Please specify a valid brief file.")
                return {"status": "error", "message": "brief_path is required"}
            
            if not os.path.exists(brief_path):
                 self.log_activity(f"Brief file not found: {brief_path}")
                 return {"status": "error", "message": f"Brief file not found: {brief_path}"}

            with open(brief_path, "r", encoding="utf-8") as f:
                brief = json.load(f)
            
            self.log_activity(f"Loaded brief for: {brief.get('title')}")

            # 3. Generate Content
            draft_content = self._generate_draft_content(brief, brand_guidelines, brand_profile, manual_reviews)

            
            # ⚙️ Step 3: Save Draft
            slug = brief.get("slug", "untitled")
            output_dir = f"outputs/{settings.brand_name}/drafts"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{slug}.md")
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(draft_content)

            self.log_activity(f"Content draft saved to: {output_path}")
            
            return {
                "status": "success",
                "draft_path": output_path
            }

        except Exception as e:
            self.log_activity(f"An error occurred during content generation: {e}")
            return {"status": "error", "message": str(e)}

    def _get_brand_guidelines(self) -> str:
        """Retrieves brand guidelines from Style DB."""
        try:
            # Retrieve style rules
            results = vector_db.style_collection.query(
                query_texts=["brand tone voice vocabulary"],
                n_results=5
            )
            
            guidelines = "## Brand Guidelines & Style Preferences\n"
            if results['ids'] and len(results['ids'][0]) > 0:
                for i in range(len(results['ids'][0])):
                    meta = results['metadatas'][0][i]
                    guidelines += f"- **{meta.get('trigger_scenario', 'Rule')}**: {meta.get('style_change', '')} (Good: {meta.get('good_example', '')})\n"
            
            return guidelines
        except Exception as e:
            self.log_activity(f"Error retrieving brand guidelines: {e}")
            return "Professional, informative tone."

    def _load_brand_profile(self) -> Dict[str, Any]:
        """Loads the brand profile JSON."""
        profile_path = "config/brand_profile.json"
        if not os.path.exists(profile_path):
            self.log_activity(f"Brand profile not found at {profile_path}")
            return {}
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _generate_draft_content(self, brief: Dict[str, Any], brand_guidelines: str, brand_profile: Dict[str, Any], manual_reviews: str = None) -> str:

        """
        Generates the article draft based on the brief and guidelines using LLM.
        """
        # Prepare data for the prompt
        brief_data = {
            "title": brief.get("title", "Untitled"),
            "target_audience": brief.get("target_audience", "General Audience"),
            "tone": brief.get("tone", "Professional"),
            "word_count_target": brief.get("word_count_target", 1500),
            "outline": brief.get("outline", []),
            "internal_link_opportunities": brief.get("internal_link_opportunities", []),
            "forbidden_terms": brief.get("forbidden_terms", []),
            "brand_terms": brief.get("brand_terms", [])

        }

        # Extract Brand Profile Variables
        content_strategy = brand_profile.get("content_strategy", {})
        visual_identity = brand_profile.get("visual_identity", {})
        data_sources = brand_profile.get("data_sources", {})
        
        target_language = content_strategy.get("language", "zh-TW")
        if target_language == "zh-TW":
            target_language_desc = "Traditional Chinese (繁體中文)"
        else:
            target_language_desc = target_language

        premium_model = visual_identity.get("image_generation_preferences", {}).get("premium_model", "gemini-3-pro-image-preview")
        
        # Forums
        # Since forum_research_urls is a list of URLs, we might need a generic string if empty, or extract domains.
        # For now, let's look for a hardcoded target or just default.
        # We can also add a new field 'target_forums' to brand_profile in the future.
        # For now, we will construct a string.
        target_forums_list = content_strategy.get("target_audience_profile", "Dcard, PTT") # This might be a path in current JSON, let's check
        # Actually in the current JSON 'target_audience_profile' is a path. 
        # Let's use a default if not found or try to infer.
        # Let's just use "Dcard, PTT" as default for Taiwanese context, or allow config override.
        target_forums = "Dcard, PTT" 
        target_forum_example = "Dcard"

        # Contact Link
        contact_channels = data_sources.get("contact_channels", {})
        official_line = contact_channels.get("official_line", "")
        # Construct UTM
        contact_link_with_utm = f"{official_line}?utm_source=blog&utm_medium=article&utm_campaign=seo_content" if official_line else "#"


        # Construct the prompt
        # 1. Perform Web Research (Browser Enablement)
        review_data = []
        researcher = WebResearcher()
        
        # Enhanced Research: Search for both brand reviews and TOPIC reviews (e.g., Dcard/PTT insights)
        topic = brief.get("primary_keyword", "")
        queries = [f"{settings.brand_name} 評價", f"{topic} ptt dcard 比較", f"{topic} 心得 轉考"]
        
        if manual_reviews:
            try:
                review_data = json.loads(manual_reviews)
                self.log_activity(f"Using manual reviews: {len(review_data)} items")
            except json.JSONDecodeError:
                self.log_activity("Failed to parse manual_reviews JSON. Falling back to WebResearcher.")
                for q in queries:
                    self.log_activity(f"Searching: {q}")
                    review_data.extend(researcher.search_reviews(q))
        else:
            for q in queries:
                self.log_activity(f"Searching: {q}")
                # Use a more generic search if needed, but search_reviews is usually fine
                results = researcher.search_reviews(q)
                review_data.extend(results)
        
        # Deduplicate results by URL
        seen_urls = set()
        unique_reviews = []
        for r in review_data:
            if r['url'] not in seen_urls:
                unique_reviews.append(r)
                seen_urls.add(r['url'])
        review_data = unique_reviews[:5] # Limit to top 5 for context
        
        review_context = ""
        if review_data:
            review_context = "### Real-time Research & Review Data (USE THESE for human-like anecdotes):\n"
            for item in review_data:
                review_context += f"- [{item['title']}]({item['url']})\n"
        else:
            review_context = "### Real-time Review Data\nNo specific reviews found. Use general industry insights but keep the tone human."
        
        target_language = brand_profile.get("content_strategy", {}).get("target_language", "Traditional Chinese (Taiwan)")
        
        # Extract existing content for refactoring if available
        existing_content = brief.get("existing_content_raw", "")
        existing_content_section = ""
        if existing_content:
            existing_content_section = f"\n### Existing Content (For Refactoring Reference - DO NOT copy outdated years)\n{existing_content}\n"
        
        import datetime
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.datetime.now().year
        next_year = current_year + 1

        # Extract Internal Links for explicit instruction
        internal_links = brief.get("internal_link_opportunities", [])
        internal_links_str = ""
        if internal_links:
            internal_links_str = "### 🔗 MANDATORY INTERNAL LINKS (Must be perfectly integrated into the text body):\n"
            for link in internal_links:
                title = link.get('title', 'Link')
                url = link.get('url', '#')
                anchor = link.get('anchor_text', title)
                internal_links_str += f"- Use anchor text similar to: '{anchor}' -> Target: {url}\n"

        prompt = f"""
You are a Senior Content Writer for {brand_profile.get('identity', {}).get('brand_name', 'Brand')}.
Your mission is to write an article that is NOT only informative but also **FEELS HUMAN** and **FREE OF AI TASTE**.

### 🚫 ANTI-AI-TASTE RULES (CRITICAL)
1. **NO MONOTONY**: Mix short, punchy sentences with longer ones. Use dashes (——) or breaks for rhythm.
2. **NO CLICHÉS**: Avoid "delve into", "comprehensive guide", "seamlessly", "not to be missed". 
3. **NO FORMULAIC TRANSITIONS**: Avoid "Additionally", "Moreover", "In conclusion", "Furthermore". Use situational transitions like "Speaking of which..." or "But what does this mean for you?".
4. **NO ROBOTIC CONCLUSIONS**: Do not start conclusions with "In summary" or "All in all". Use an emotional or action-driven close.
5. **HUMAN ELEMENTS**: Inject personal perspective ("I", "We"), situational anecdotes, or emotional cues.
6. **BLACKLISTED TERMS**: Avoid 「不容錯過」、「深入探討」、「全方位」、「無縫接軌」、「總而言之」、「綜上所述」、「值得一提的是」、「然而」(don't use too much).

### 💡 HUMANIZATION TECHNIQUES
- **Sentence Rhythm**: "Travel is about freedom. (Break) No plans. Just go." -> Better: "Travel isn't just about checking off lists—it's about the freedom to get lost and find yourself. Just go."
- **Emotional Anchoring**: Describe the *feeling* of arriving at a new destination or the *joy* of discovering hidden gems.

### 📅 CRITICAL TIME CONTEXT
- **TODAY**: {current_date_str} (Target years: {current_year}-{next_year})
- **RULE**: Update ALL outdated info from "Existing Content".

### Content Brief & Context
{json.dumps(brief, ensure_ascii=False, indent=2)}
{existing_content_section}
{review_context}
{internal_links_str}

### Configuration
- **Target Language**: {target_language_desc}
- **Contact Link**: {contact_link_with_utm}

### Instruction
1. **Hook**: Use the specific strategy in the brief. **STRICTLY PROHIBITED**: starting with "Are you...?" or "Do you...?". **ALSO PROHIBITED**: Starting with "This is a cruel statistic..." or overly redundant AI empathy patterns like "You may have experienced that despair...".
2. **Terminology**: Use local terms where appropriate for authenticity (e.g., 「老街」instead of 「古街」).
3. **Refactoring**: If existing content is provided, high-quality portions should be KEPT but rewritten to match the Human Tone and updated for {current_year}.
4. **Reviews**: Use the provided URLs to reference real sentiments from {target_forums}.
5. **CTA**: Ensure the mandatory LINE CTA is at the very end.

Write the full article in Markdown. Start directly with the H1 title.
"""
        try:
            self.log_activity("Generating content with LLM (using Pre-fetched Research Data)...")
            # Disable internal search since we already did it
            draft = gemini_text_gen.generate_text(prompt, enable_search=False)
            return draft
        except Exception as e:
            self.log_activity(f"LLM generation failed: {e}. Falling back to skeleton.")
            return self._generate_skeleton(brief, brand_guidelines)

    def _generate_skeleton(self, brief: Dict[str, Any], brand_guidelines: str) -> str:
        """Fallback method to generate a skeleton if LLM fails."""
        title = brief.get("title", "Untitled Article")
        outline = brief.get("outline", [])
        cta = brief.get("cta", "")
        
        content = f"# {title}\n\n"
        
        for section in outline:
            h2_title = section.get('h2_title', 'Untitled')
            content += f"## {h2_title}\n\n"
            
            if "premium_image" in section:
                 content += f"![{h2_title}](PREMIUM_PLACEHOLDER)\n\n"
                 
            for point in section.get("key_points", []):
                content += f"- {point}\n"
            content += "\n（此處應展開撰寫詳細內容，請參考 Key Points 並融入品牌語氣）\n\n"
            
        content += f"{cta}\n\n"
        content += "\n<!--\n" + brand_guidelines + "\n-->"
        return content

# Global instance
c01_content_writer = C01ContentWriter()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='C01 Content Writer')
    parser.add_argument("--brief_path", help="Path to the brief JSON file")
    parser.add_argument("--manual_reviews", help="JSON string of manual reviews list", default=None)
    args = parser.parse_args()

    writer = C01ContentWriter()
    result = writer.run(args.brief_path, args.manual_reviews)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "error":
        sys.exit(1)

