#!/usr/bin/env python3
"""
Package Skill Tool - 技能打包工具
Automates the creation and validation of SKILL.md files from workflow documents.

Rules:
1. Each skill must reside in .gemini/skills/[Skill Name]/SKILL.md
2. YAML frontmatter: name, description (only).
3. Description style: Instructional (e.g., "撰寫...時使用").
4. Brand: FUNIT only.
"""

import os
import sys
import argparse
import yaml
import re
from pathlib import Path

def create_skill(workflow_path: str, skill_name: str):
    """Converts a workflow MD to a SKILL.md file."""
    wf_path = Path(workflow_path)
    if not wf_path.exists():
        print(f"❌ Workflow file not found: {workflow_path}")
        return

    # Extract info from workflow
    with open(wf_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple name extraction from filename if not provided
    if not skill_name:
        skill_name = wf_path.stem.replace('_', ' ').title()

    # Standard description template
    description = f"執行 {skill_name} 工作流程；當需要時使用。"

    # Prepare SKILL.md content
    skill_dir = Path(".gemini/skills") / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    
    skill_file = skill_dir / "SKILL.md"
    
    # Strip existing frontmatter from workflow to avoid confusion
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    skill_content = f"""---
name: {skill_name.lower().replace(' ', '-')}
description: {description}
---

> **來源**: 本技能源自 `{wf_path.name}`。

{body}
"""

    with open(skill_file, "w", encoding="utf-8") as f:
        f.write(skill_content)
    
    print(f"✅ Skill packaged at: {skill_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Package Skill Tool")
    parser.add_argument("--wf", required=True, help="Path to the workflow .md file")
    parser.add_argument("--name", help="Name of the skill")
    
    args = parser.parse_args()
    create_skill(args.wf, args.name)
