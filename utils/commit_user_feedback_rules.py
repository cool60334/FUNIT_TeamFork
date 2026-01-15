
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
        "trigger": "Introduction / Opening Hook",
        "change": "Avoid 'Data-driven cruelty' formulaic openings",
        "bad": "這是一個殘酷的統計數據：對於旅遊愛好者來說...",
        "good": "走進這條老街的那一刻，時間彷彿慢了下來。這不是遊客打卡的熱門景點，而是在地人的秘密基地。",
        "tags": "tone, anti-ai"
    },
    {
        "trigger": "Audience Empathy / Hook",
        "change": "Avoid 'Generic Empathy Overkill' (Redundant AI-tasting empathy patterns)",
        "bad": "你可能也經歷過那種絕望——明明上網做了好多功課，到現場卻發現完全不是那麼回事。",
        "good": "做了一週功課，到現場卻發現網路評價都是業配？這種踩雷經驗，懂的人都懂。",
        "tags": "tone, anti-ai"
    },
    {
        "trigger": "Comparison Logic / Transition",
        "change": "Avoid 'Formulaic Symmetry' (If A is X, then B is Y)",
        "bad": "如果說大阪是在考驗你的「體力」與「荷包」，那麼京都就是一場徹頭徹尾的「文化苦旅」。",
        "good": "大阪玩的是熱鬧，京都品的是底蘊。想要玩得盡興，你得知道這兩座城市的玩法邏輯。",
        "tags": "tone, style, anti-ai"
    },
    {
        "trigger": "Recommendation Style",
        "change": "Prefer specific recommendations over generic advice",
        "bad": "這裡有很多美食值得一試。",
        "good": "巷口那家沒招牌的滷肉飯，排隊人龍就是最好的招牌。",
        "tags": "specificity, branding"
    }
]

print(f"Commiting {len(user_rules)} user feedback rules to style memory...")

for i, r in enumerate(user_rules, 1):
    print(f"\n[{i}/{len(user_rules)}] Planting: {r['trigger']}")
    gardener.plant(
        trigger=r['trigger'],
        change=r['change'],
        bad=r['bad'],
        good=r['good'],
        tags=r['tags']
    )

print("\nDone! Style memory updated with user feedback.")
