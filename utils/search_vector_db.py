
import os
import sys
import argparse
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.vector_db_manager import vector_db
from config.settings import settings

def main():
    parser = argparse.ArgumentParser(description="查詢向量資料庫 (Search Vector DB)")
    parser.add_argument("query", type=str, help="要查詢的關鍵字或句子")
    parser.add_argument("--collection", type=str, default="content", choices=["content", "facts", "style"], help="要查詢的集合 (預設: content)")
    parser.add_argument("--top_k", type=int, default=3, help="返回的結果數量 (預設: 3)")
    
    args = parser.parse_args()
    
    print(f"\n🔍 正在搜尋 [{args.collection}] 集合中的: \"{args.query}\"...")
    
    results = []
    if args.collection == "content":
        results = vector_db.query_content(args.query, n_results=args.top_k)
    elif args.collection == "facts":
        results = vector_db.query_facts(args.query, n_results=args.top_k)
    elif args.collection == "style":
        results = vector_db.query_style_rules(args.query, n_results=args.top_k)
        
    if not results:
        print("❌ 未找到相關資料。")
        return

    print(f"\n✅ 找到 {len(results)} 筆相關結果:\n" + "="*50)
    
    for i, res in enumerate(results, 1):
        metadata = res.get('metadata', {})
        title = metadata.get('title', metadata.get('slug', 'N/A'))
        type_ = metadata.get('type', 'N/A')
        
        print(f"【結果 {i}】")
        print(f"🔹 標題/來源: {title}")
        print(f"🔹 類型: {type_}")
        print(f"🔹 ID: {res['id']}")
        print(f"🔹 相似度評分 (Distance): {res.get('distance', 'N/A'):.4f}")
        print("-" * 20)
        
        # 顯示前 300 個字元
        doc = res.get('document', '')
        preview = doc[:500] + "..." if len(doc) > 500 else doc
        print(f"【內容摘要】\n{preview}")
        print("="*50)

if __name__ == "__main__":
    main()
