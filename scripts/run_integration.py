#!/usr/bin/env python3
import sys
import os
import json
import logging
import traceback
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Setup Path to include project root
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.core import PathResolver

# Setup Logger
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("Orchestrator")

class PipelineManager:
    """Manages the execution of the content automation pipeline."""
    
    def __init__(self, topic: str, brand: str = "FUNIT", resume: bool = True):
        self.topic = topic
        self.brand = brand
        self.resolver = PathResolver()
        
        # State file path
        self.state_file = self.resolver.resolve("outputs/{BRAND_NAME}/.pipeline_state_{TOPIC_SLUG}.json", 
                                              TOPIC_SLUG=self._slugify(topic))
        logger.info(f"Pipeline State File: {self.state_file}")
        self.state = self._load_state() if resume else {"completed_steps": [], "results": {}}
        self.state["topic"] = topic
        self.state["brand"] = brand

    def _slugify(self, text: str) -> str:
        return text.replace(" ", "_").replace("/", "_")

    def _load_state(self) -> Dict[str, Any]:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}. Starting fresh.")
        return {"completed_steps": [], "results": {}}

    class SetEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, set):
                return list(obj)
            if isinstance(obj, Path):
                return str(obj)
            return super().default(obj)

    def _save_state(self):
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2, cls=self.SetEncoder)
            logger.info(f"Successfully saved pipeline state to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")

    def run_step(self, step_id: str, agent_class, input_mapper, output_handler=None):
        """Runs a single step in the pipeline if it hasn't been completed."""
        if step_id in self.state["completed_steps"]:
            logger.info(f">>> Step '{step_id}' already completed. Skipping.")
            return True

        logger.info(f"--- Running Step: {step_id} ---")
        try:
            agent = agent_class()
            input_data = input_mapper(self.state)
            
            start_time = datetime.now()
            result = agent.run(input_data)
            duration = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Step '{step_id}' finished in {duration:.2f}s")
            
            self.state["results"][step_id] = result
            if output_handler:
                output_handler(self.state, result)
            
            self.state["completed_steps"].append(step_id)
            self._save_state()
            return True
        except Exception as e:
            logger.error(f"Step '{step_id}' failed: {e}")
            traceback.print_exc()
            return False

def main():
    parser = argparse.ArgumentParser(description="AI Content Team Pipeline Orchestrator")
    parser.add_argument("--topic", type=str, required=True, help="Main topic for content generation")
    parser.add_argument("--brand", type=str, default="FUNIT", help="Brand name (default: FUNIT)")
    parser.add_argument("--no-resume", action="store_true", help="Start from scratch (ignore previous state)")
    args = parser.parse_args()

    # Set Brand in env for global access
    os.environ["BRAND_NAME"] = args.brand

    pm = PipelineManager(topic=args.topic, brand=args.brand, resume=not args.no_resume)

    # --- Pipeline Definitions ---

    # 1. Strategy Step (P01)
    def p01_input(state):
        return {"topic": state["topic"]}

    def p01_output(state, res):
        # Determine strategy file path
        # P01 typically saves its own results, but we want the path for the next step
        resolver = PathResolver()
        # Match P01 logic: lower(), replace ' ' with '-'
        topic_slug = state["topic"].replace(" ", "-").lower()
        strategy_path = resolver.resolve("outputs/{BRAND_NAME}/strategies/topic_cluster_{TOPIC_SLUG}.json", 
                                        TOPIC_SLUG=topic_slug)
        state["strategy_path"] = str(strategy_path)

    from agents.planning.p01_keyword_strategist import P01KeywordStrategist
    if not pm.run_step("strategy", P01KeywordStrategist, p01_input, p01_output):
        sys.exit(1)

    # 2. Planning Step (P02)
    def p02_input(state):
        return {
            "topic": state["topic"],
            "strategy_path": state.get("strategy_path")
        }

    def p02_output(state, res):
        if res.get("status") == "success" and res.get("generated_briefs"):
            state["slugs"] = res["generated_briefs"]
            logger.info(f"Generated briefs for slugs: {state['slugs']}")

    from agents.planning.p02_content_architect import P02ContentArchitect
    if not pm.run_step("planning", P02ContentArchitect, p02_input, p02_output):
        sys.exit(1)

    # 3. Production Steps (C01, C02a, C02, C05)
    # Note: We loop through each slug (Pillar & Clusters)
    slugs = pm.state.get("results", {}).get("planning", {}).get("generated_briefs", [])
    
    for slug in slugs:
        logger.info(f"====== Processing Article: {slug} ======")
        
        # 3.1 Content Writer (C01)
        def c01_input(state):
            return {"slug": slug}
            
        def c01_output(state, res):
            # Save draft path for this specific article
            if "article_drafts" not in state: state["article_drafts"] = {}
            state["article_drafts"][slug] = res.get("draft_path") or res.get("output_path")

        from agents.production.c01_content_writer import C01ContentWriter
        if not pm.run_step(f"writer_{slug}", C01ContentWriter, c01_input, c01_output):
            continue # Try next article if one fails

        # Get the draft path for following steps
        draft_path = pm.state.get("article_drafts", {}).get(slug)
        if not draft_path:
            logger.error(f"No draft path found for {slug}, skipping remaining steps for this article.")
            continue

        # 3.2 Fact Checker (C02a)
        def c02a_input(state):
            return {"draft_path": draft_path, "slug": slug}

        from agents.production.c02a_fact_checker import FactChecker
        pm.run_step(f"fact_check_{slug}", FactChecker, c02a_input)

        # 3.3 SEO Optimizer (C02)
        def c02_input(state):
            return {"draft_path": draft_path, "slug": slug}

        from agents.production.c02_seo_optimizer import C02SEOOptimizer
        pm.run_step(f"seo_opt_{slug}", C02SEOOptimizer, c02_input)

        # 3.4 Publisher (C05) - Draft mode
        def c05_input(state):
            return {
                "draft_path": draft_path, 
                "publish_status": "draft", 
                "slug": slug
            }

        from agents.production.c05_publisher import C05Publisher
        pm.run_step(f"publish_{slug}", C05Publisher, c05_input)

    logger.info("Pipeline Execution Complete!")
    print("<promise>SYSTEM_OK</promise>")

if __name__ == "__main__":
    main()
