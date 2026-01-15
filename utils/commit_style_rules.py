
import sys
import os
sys.path.append(os.getcwd())
try:
    from agents.monitoring.style_gardener import AgentGardener
except ImportError:
    # If running as module
    from .agents.monitoring.style_gardener import AgentGardener

gardener = AgentGardener()

rules = [
    {
        "trigger": "Introduction / Article Start",
        "change": "Meta-talk -> Direct Engagement",
        "bad": "好的，我將以 Brand 的專業內容寫手身份...",
        "good": "這個問題你一定也遇過，對吧？",
        "tags": "tone, structure"
    },
    {
        "trigger": "Reference to Regulations or Official Entities",
        "change": "Generic Reference -> Authoritative Deep Link",
        "bad": "[官方連結](https://www.example.gov/)",
        "good": "[官方連結](https://www.example.gov/specific-page)",
        "tags": "fact-check, trust"
    },
    {
        "trigger": "Social Proof / Reviews",
        "change": "Generic Social Proof -> Curated & Brand-Owned Proof",
        "bad": "PTT 網友表示...",
        "good": "Dcard 網友分享... 品牌讀者案例...",
        "tags": "conversion, brand-voice"
    }
]

print(f"Starting to plant {len(rules)} style rules...")

for i, r in enumerate(rules, 1):
    print(f"\n[{i}/{len(rules)}] Planting: {r['trigger']}")
    gardener.plant(
        trigger=r['trigger'],
        change=r['change'],
        bad=r['bad'],
        good=r['good'],
        tags=r['tags']
    )

print("\nDone!")
