
import sys
import os
sys.path.append(os.getcwd())
try:
    from agents.monitoring.style_gardener import AgentGardener
except ImportError:
    from .agents.monitoring.style_gardener import AgentGardener

gardener = AgentGardener()

user_rules = [
    {
        "trigger": "Mechanism Description / Opinion",
        "change": "Avoid AI personification/slang overkill",
        "bad": "這是環球影城最不講武德，也最受遊客歡迎的設施。",
        "good": "這是環球影城最受遊客歡迎的設施，也是能快速回本的核心原因。",
        "tags": "tone, anti-ai"
    },
    {
        "trigger": "Comparison of Exam Components",
        "change": "Use '分別獨立看待' instead of '孤島' or other dramatic metaphors",
        "bad": "大阪、京都、神戶是三座孤島。交通差，就只能死磕計程車。",
        "good": "大阪、京都、神戶的交通系統是分別獨立運作的。如果在這三個城市移動，建議搭配 JR Pass。",
        "tags": "tone, style, anti-ai"
    }
]

print(f"Commiting {len(user_rules)} more user feedback rules to style memory...")

for i, r in enumerate(user_rules, 1):
    print(f"\n[{i}/{len(user_rules)}] Planting: {r['trigger']}")
    gardener.plant(
        trigger=r['trigger'],
        change=r['change'],
        bad=r['bad'],
        good=r['good'],
        tags=r['tags']
    )

print("\nDone! Style memory updated with second round of user feedback.")
