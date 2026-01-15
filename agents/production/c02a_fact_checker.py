"""
Fact Checker Agent - 自動事實查核與修正
使用 Hybrid 策略：AI Agent Search (Gemini Grounding) + Python Targeted Search (DDG) + Deep Fetch
"""

import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
import argparse
import sys
from pathlib import Path
import datetime

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from agents.core import BaseAgent
from utils.gemini_text_gen import GeminiTextGenerator
from utils.ddg_searcher import DDGSearcher
from utils.prompt_assets import load_rules_text

# Try to import FactMemoryManager
try:
    from utils.fact_memory_manager import FactMemoryManager
    FACT_MEMORY_AVAILABLE = True
except ImportError:
    try:
        from ...utils.fact_memory_manager import FactMemoryManager
        FACT_MEMORY_AVAILABLE = True
    except ImportError:
        FACT_MEMORY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Claim:
    text: str
    category: str # "date", "cost", "policy", "link", "unlinked_community_ref", etc.
    context: str # The sentence or paragraph containing the claim
    status: str = "pending" # pending, verified, incorrect, uncertain
    correction: Optional[str] = None
    source: Optional[str] = None

class FactChecker(BaseAgent):
    def __init__(self):
        super().__init__(name="C02a_FactChecker")
        self.brand_name = self.brand.slug
        self.llm = GeminiTextGenerator()
        self.searcher = DDGSearcher(max_retries=3, delay_seconds=1.5)
        self.base_dir = os.getcwd()
        self.rules_content = load_rules_text("c02a")

        # Initialize Fact Memory if available
        if FACT_MEMORY_AVAILABLE:
            self.fact_memory = FactMemoryManager()
        else:
            self.fact_memory = None
            logger.warning("Fact Memory not available.")

    def _load_brand_profile(self):
        """Loads the brand profile JSON."""
        if hasattr(self, "brand") and getattr(self, "brand", None):
            return self.brand.brand_config or {}
        return {}

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes fact checking for a given article slug.
        """
        slug = input_data.get("slug", "")
        if not slug:
            return {"status": "error", "message": "Slug is required"}

        self.log_activity(f"Starting Fact Check for: {slug}")
        
        # 1. Load Data (Check final folder from C02)
        base_dir = f"outputs/{self.brand_name}"
        input_path = f"{base_dir}/final/{slug}.md"
        
        if not os.path.exists(input_path):
             return {"status": "error", "message": f"Input file not found at {input_path}"}
        
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # 2. Check and Fix
        try:
            new_content = self.check_and_fix(content)
        except Exception as e:
            self.log_activity(f"Fact Check failed: {e}")
            return {"status": "error", "message": str(e)}
            
        # 3. Save Output
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        self.log_activity(f"Fact check complete. Updated {input_path}")
        
        return {
            "status": "success",
            "output_path": input_path
        }

    def check_and_fix(self, content_md: str) -> str:
        """主流程：提取 -> 查核 -> 修正"""
        logger.info("Starting fact check process...")
        
        # 1. 提取需查核的事實
        claims = self._extract_claims(content_md)
        if not claims:
            logger.info("No verifiable claims found.")
            return content_md
            
        logger.info(f"Extracted {len(claims)} claims for verification.")
        
        # 2. 搜尋並驗證
        verified_claims = []
        for claim in claims:
            result = self._verify_claim(claim)
            verified_claims.append(result)
            
        # 3. 過濾出需要修正的項目 (包含錯誤事實與缺連結的事實)
        claims_to_fix = [c for c in verified_claims if c.correction]
        
        if not claims_to_fix:
            logger.info("No corrections needed.")
            return content_md
            
        logger.info(f"Found {len(claims_to_fix)} claims to fix. Applying corrections...")
        
        # 4. 自動修正內容
        new_content = self._apply_corrections(content_md, claims_to_fix)
        
        # 5. [NEW] 記憶除錯結果 (RAG Update)
        if self.fact_memory:
            self._memorize_corrections(claims_to_fix)
            
        # 6. 生成報告
        self._save_report(verified_claims)
        
        return new_content

    def _extract_claims(self, content: str) -> List[Claim]:
        """使用 LLM 提取需要查核的事實，包含專有名詞、法規連結、及社群引用"""
        prompt = f"""
        {self.rules_content}

        You are a strict Fact Checker. Extract strictly factual claims from the text below that MUST be verified.
        
        Focus on these High-Risk Categories:
        1. Dates (deadlines, reform dates, years)
        2. Costs/Money (fees, tuition, prices)
        3. Statistics/Numbers (ratings, scores, percentages)
        4. Official Policies (visa rules, university requirements)
        5. Proper Nouns & Official Names (Institution names, specific course names like "ELICOS", "Direct Entry Program")
        6. External Links/URLs (Any URL mentioned or markdown link)
        7. **Unlinked Community References** (缺少連結的社群引用):
           - Any sentence that mentions community discussions, forums, or social media WITHOUT a Markdown link.
           - Keywords to detect: 網友, 論壇, Dcard, PTT, 社群, 留言, 討論區, FB社團, Threads, 經驗分享, 心得, 大家都說, 常有人問
           - Example: "在 Dcard 留學板上，常有學生詢問..." (NO link = must flag)
           - If it already has a Markdown link like [Dcard](URL), it's NOT unlinked.
        
        Ignore subjective opinions ("good school", "hard exam").
        
        Text content:
        {content[:15000]}
        
        Return JSON list:
        [
            {{
                "text": "Taiwan high speed rail prices increased by 10% in 2025",
                "category": "cost",
                "context": "The sentence containing this claim"
            }},
            {{
                "text": "在 Dcard 留學板上常有人討論...",
                "category": "unlinked_community_ref",
                "context": "Complete sentence that needs a link"
            }}
        ]
        """
        
        try:
            response = self.llm.generate_text(prompt)
            json_str = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            return [Claim(**item) for item in data]
        except Exception as e:
            logger.error(f"Claim extraction failed: {e}")
            return []

    def _verify_claim(self, claim: Claim) -> Claim:
        """主核心：使用 Hybrid 策略進行驗證"""
        logger.info(f"Verifying Claim: {claim.text[:100]}...")
        
        # Layer 1: AI Agent Search (Gemini Google Search Grounding)
        # 讓 AI 代理人直接進行第一輪研究
        claim = self._layer1_ai_agent_search(claim)
        
        if claim.status != "uncertain":
            return claim
            
        # Layer 2: Python Targeted Search (DuckDuckGo)
        # 如果第一層不確定，執行針對性的 Python 搜尋
        logger.info(f"Layer 1 uncertain, falling back to Layer 2 (Python Search)...")
        claim = self._layer2_python_search(claim)
        
        if claim.status != "uncertain":
            return claim
            
        # Layer 3: Deep Fetch (抓取網頁內容分析)
        # 如果搜尋摘要不足以判定，嘗試直接抓取網址內容
        logger.info(f"Layer 2 uncertain, attempting Layer 3 (Deep Fetch)...")
        claim = self._layer3_deep_fetch(claim)
        
        return claim

    def _layer1_ai_agent_search(self, claim: Claim) -> Claim:
        """Layer 1: 使用 Gemini 的 Google Search Grounding 功能"""
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        你是一位專業的事實查核代理人。請使用 Google 搜尋驗證以下聲明。
        
        聲明: "{claim.text}"
        上下文: "{claim.context}"
        類別: "{claim.category}"
        今日日期: {current_date_str}
        
        任務:
        1. 使用 Google 搜尋查證該聲明的準確性。
        2. 檢查過時資訊（例如 2024 vs 2025 的政策差異）。
        3. 如果是「unlinked_community_ref」，請找出最相關的論壇連結 (Dcard/PTT/Threads)。
        
        請用繁體中文回覆，僅回傳 JSON:
        {{
            "status": "correct/incorrect/uncertain",
            "reasoning": "簡短說明理由",
            "correction": "如果錯誤，提供正確資訊；若正確則為 null",
            "source": "最權威的來源 URL"
        }}
        """
        
        try:
            # 開啟 enable_search = True (AI Agent Mode)
            response = self.llm.generate_text(prompt, enable_search=True)
            result = self._parse_hybrid_json(response)
            
            if result:
                claim.status = result.get('status', 'uncertain')
                if claim.status == 'incorrect' or (claim.category == 'unlinked_community_ref' and result.get('source')):
                    claim.correction = result.get('correction')
                    claim.source = result.get('source')
                    
                    if claim.category == 'unlinked_community_ref' and not claim.correction:
                        claim.correction = self._generate_linked_text(claim.context, claim.source)
                
                logger.info(f"  Layer 1 Result: {claim.status}")
            return claim
        except Exception as e:
            logger.warning(f"Layer 1 failed: {e}")
            return claim

    def _layer2_python_search(self, claim: Claim) -> Claim:
        """Layer 2: 使用 DuckDuckGo 進行 Python 程式化搜尋"""
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # 執行基礎搜尋
        if claim.category == 'unlinked_community_ref':
            search_results = self.searcher.search_community(claim.text, max_results=5)
        else:
            search_results = self.searcher.search(claim.text, max_results=3)
        
        if not search_results:
            return claim
            
        search_context = "\n".join([
            f"- [{r['title']}]({r['href']}): {r['body'][:300]}"
            for r in search_results
        ])
        
        analysis_prompt = f"""
        根據搜尋結果片段驗證聲明。
        聲明: "{claim.text}"
        類別: "{claim.category}"
        搜尋結果:
        {search_context}
        
        請回傳 JSON (status/correction/source)。
        """
        
        try:
            # 輔助分析（不開搜尋）
            response = self.llm.generate_text(analysis_prompt, enable_search=False)
            result = self._parse_hybrid_json(response)
            
            if result:
                claim.status = result.get('status', 'uncertain')
                claim.correction = result.get('correction')
                claim.source = result.get('source')
                
                # 儲存結果供 Layer 3 參考（如果有網址但狀態仍不確定）
                self._temp_search_results = search_results
                
            return claim
        except Exception as e:
            logger.warning(f"Layer 2 failed: {e}")
            return claim

    def _layer3_deep_fetch(self, claim: Claim) -> Claim:
        """Layer 3: 抓取網頁內容進行深度分析"""
        # 如果有來源網址但摘要不夠判定，直接去抓內容
        url = getattr(claim, 'source', None) or (self._temp_search_results[0]['href'] if hasattr(self, '_temp_search_results') and self._temp_search_results else None)
        
        if not url or not url.startswith("http"):
            return claim
            
        logger.info(f"Deep Fetching URL: {url}")
        
        try:
            # 使用 read_url_content 的底層逻辑 (暫時模擬，實際應呼叫 tool 或 library)
            # 這裡我們用一個簡化的方式：透過 LLM 解讀我們能獲取的更多內容（如果未來有 Browser Tool 則改用 browser）
            # 目前我們先強化 Layer 2 的判定邏輯
            return claim
        except Exception as e:
            logger.error(f"Layer 3 failed: {e}")
            return claim

    def _parse_hybrid_json(self, response: str) -> Optional[Dict]:
        """解析 JSON 的輔助函式"""
        try:
            json_str = response.replace("```json", "").replace("```", "").strip()
            # 尋找第一個 { 和最後一個 }
            start = json_str.find("{")
            end = json_str.rfind("}")
            if start != -1 and end != -1:
                json_str = json_str[start:end+1]
                return json.loads(json_str)
        except:
            return None
        return None

    def _extract_search_keywords(self, context: str) -> str:
        # Deprecated but kept to avoid breaking other legacy calls if any
        return context

    def _build_community_search_query(self, context: str, keywords: str) -> str:
        # Deprecated
        return context

    def _find_best_community_link(self, results: List[Dict]) -> Optional[str]:
        """Find the best community/forum link from search results."""
        # Priority order for community platforms
        priority_domains = [
            "dcard.tw",
            "ptt.cc",
            "threads.net",
            "facebook.com/groups",
            "mobile01.com",
            "reddit.com"
        ]
        
        # First pass: look for priority domains
        for domain in priority_domains:
            for r in results:
                url = r.get('url', '')
                if domain in url:
                    return url
        
        # Second pass: any result that looks like discussion/forum
        discussion_keywords = ["討論", "心得", "經驗", "分享", "問", "請益", "留學"]
        for r in results:
            title = r.get('title', '')
            if any(kw in title for kw in discussion_keywords):
                return r.get('url')
        
        # Fallback: return first result if available
        return results[0].get('url') if results else None

    def _generate_linked_text(self, original_context: str, url: str) -> str:
        """Generate corrected text with embedded link."""
        # Try to find a good anchor point in the original text
        # Look for platform mentions or discussion keywords
        platforms = ["Dcard", "PTT", "FB", "Facebook", "Threads", "論壇", "社群", "討論區"]
        
        for platform in platforms:
            if platform in original_context:
                # Replace platform mention with linked version
                linked = original_context.replace(
                    platform, 
                    f"[{platform}]({url})", 
                    1  # Only replace first occurrence
                )
                return linked
        
        # If no platform found, add link at the end
        return f"{original_context} ([相關討論]({url}))"

    def _apply_corrections(self, content: str, claims: List[Claim]) -> str:
        """使用 LLM 修正文章內容"""
        
        corrections_prompt = "Apply the following corrections to the article:\n\n"
        for c in claims:
            corrections_prompt += f"Original: {c.context}\nCorrected: {c.correction}\nSource: {c.source}\n\n"
            
        prompt = f"""
        You are an editor. Apply the corrections to the article below.
        
        Corrections:
        {corrections_prompt}
        
        Article Content:
        {content}
        
        Rules:
        1. Replace the original text with the corrected text EXACTLY.
        2. Keep all other content unchanged.
        3. Output the full corrected content in Markdown format (excluding Frontmatter).
        4. CRITICAL: Preserve ALL HTML comments exactly as they appear, especially WordPress block markers like <!-- wp:rank-math/faq-block --> and <!-- /wp:rank-math/faq-block -->. Do NOT remove or modify these comments.
        """
        
        # Split Frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
        if frontmatter_match:
            frontmatter_part = f"---\n{frontmatter_match.group(1)}\n---\n"
            body_part = frontmatter_match.group(2)
        else:
            frontmatter_part = ""
            body_part = content

        prompt = f"""
        You are an editor. Apply the corrections to the article content below.
        
        Corrections:
        {corrections_prompt}
        
        Article Content (Body only):
        {body_part}
        
        Rules:
        1. Replace the original text with the corrected text EXACTLY.
        2. Keep all other content unchanged.
        3. Output only the corrected body content. Do not add frontmatter.
        4. CRITICAL: Preserve ALL HTML comments exactly as they appear.
        """
        
        try:
            corrected_body = self.llm.generate_text(prompt)
            corrected_body = corrected_body.replace("```markdown", "").replace("```", "").strip()
            
            # Double check: Remove frontmatter from LLM output if it hallucinated it
            # Double check: Remove frontmatter from LLM output if it hallucinated it
            # Logic verified in debug_regex.py
            
            # 1. Loop to strip frontmatter blocks at the start
            while True:
                # Regex matches: ^--- ... --- (Body)
                match = re.match(r'^---\s*\n.*?\n---\s*\n(.*)$', corrected_body, re.DOTALL)
                if match:
                    corrected_body = match.group(1).strip()
                else:
                    break
            
            # 2. Strip pre-header trash (Chat fillers, extra dividers)
            h1_match = re.search(r'^#\s+', corrected_body, re.MULTILINE)
            if h1_match:
                h1_pos = h1_match.start()
                pre_h1 = corrected_body[:h1_pos]
                # If text before H1 contains dividers or is just conversational filler
                if "---" in pre_h1 or len(pre_h1) < 500: 
                     corrected_body = corrected_body[h1_pos:]

            return frontmatter_part + corrected_body
            
            return frontmatter_part + corrected_body
        except Exception as e:
            logger.error(f"Correction application failed: {e}")
            return content

    def _save_report(self, claims: List[Claim]):
        """存儲查核報告（中文版）"""
        report_dir = os.path.join(self.base_dir, "outputs", self.brand_name, "reports")
        os.makedirs(report_dir, exist_ok=True)
        
        # 類別翻譯對照表
        category_map = {
            "dates": "📅 日期時間",
            "costs_money": "💰 金額費用",
            "statistics_numbers": "📊 統計數據",
            "official_policies": "📜 官方政策",
            "proper_nouns": "🏛️ 專有名詞",
            "external_links": "🔗 外部連結",
            "unlinked_community_ref": "💬 社群引用（缺連結）",
            "link": "🔗 連結",
            "date": "📅 日期",
            "cost": "💰 費用",
            "policy": "📜 政策"
        }
        
        # 狀態翻譯對照表
        status_map = {
            "correct": "✅ 正確",
            "incorrect": "❌ 錯誤",
            "uncertain": "⚠️ 待確認",
            "pending": "⏳ 待查核"
        }
        
        report_data = [
            {
                "聲明內容": c.text,
                "類別": category_map.get(c.category, c.category),
                "查核結果": status_map.get(c.status, c.status),
                "修正說明": c.correction,
                "來源連結": c.source
            }
            for c in claims
        ]
        
        path = os.path.join(report_dir, "latest_fact_check.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Report saved to {path}")

    def _memorize_corrections(self, claims: List[Claim]):
        """將修正後的事實存入 Vector DB (Fact Memory)"""
        if not self.fact_memory:
            return
            
        logger.info(f"Memorizing {len(claims)} corrections to Fact Memory...")
        count = 0
        for c in claims:
            # 只儲存有明確修正內容的項目
            if c.status == 'incorrect' and c.correction:
                try:
                    self.fact_memory.add_fact(
                        context=c.context,
                        claim=c.text,
                        correction=c.correction,
                        source=c.source or "Self-Correction"
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to memorize claim '{c.text}': {e}")
                    
        logger.info(f"Successfully memorized {count} facts.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='C02a Fact Checker')
    parser.add_argument('--slug', type=str, required=True, help='Slug of the article')
    args = parser.parse_args()
    
    checker = FactChecker()
    try:
        result = checker.run({"slug": args.slug})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False))
        sys.exit(1)
