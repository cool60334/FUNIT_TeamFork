"""
Vector Database Manager using LanceDB
Migrated from ChromaDB for Python 3.14 compatibility.
"""

import lancedb
import pyarrow as pa
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Import custom embedding function
try:
    from utils.embedding_function import get_shared_embedding_function
    EMBEDDING_FUNCTION = get_shared_embedding_function()
except Exception as e:
    print(f"⚠ Could not load EmbeddingGemma: {e}")
    EMBEDDING_FUNCTION = None

from agents.core.brand_manager import get_current_brand
from config.settings import settings

# Schema definitions
STYLE_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("document", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 768)),
    pa.field("type", pa.string()),
    pa.field("trigger", pa.string()),
    pa.field("change", pa.string()),
    pa.field("section", pa.string()),
    pa.field("source", pa.string()),
    pa.field("status", pa.string()),
    pa.field("date", pa.string()),
    pa.field("modified", pa.string()),
])

CONTENT_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("document", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 768)),
    pa.field("type", pa.string()),
    pa.field("slug", pa.string()),
    pa.field("categories", pa.string()),  # JSON string
    pa.field("status", pa.string()),
    pa.field("date", pa.string()),
    pa.field("modified", pa.string()),
    pa.field("h2_headings", pa.string()),  # JSON string
])

FACTS_SCHEMA = pa.schema([
    pa.field("id", pa.string()),
    pa.field("document", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 768)),
    pa.field("source", pa.string()),
    pa.field("verified_date", pa.string()),
    pa.field("category", pa.string()),
])


class VectorDBManager:
    def __init__(self):
        try:
            brand = get_current_brand()
            self.db_path = str(brand.base_dir / "data" / "lancedb")
        except Exception as e:
            print(f"⚠️ VectorDBManager: 無法取得當前品牌 ({e})，使用預設設定。")
            self.db_path = getattr(settings, 'lancedb_path', './data/lancedb')
        
        # Ensure directory exists
        os.makedirs(self.db_path, exist_ok=True)
        
        # Connect to LanceDB
        self.db = lancedb.connect(self.db_path)
        
        # Initialize tables
        self.style_table = self._get_or_create_table("style_rules", STYLE_SCHEMA)
        self.content_table = self._get_or_create_table("content_items", CONTENT_SCHEMA)
        self.facts_table = self._get_or_create_table("facts", FACTS_SCHEMA)
    
    def _get_or_create_table(self, name: str, schema: pa.Schema):
        """Get existing table or create new one with schema."""
        if name in self.db.table_names():
            return self.db.open_table(name)
        else:
            # Create empty table with schema
            return self.db.create_table(name, schema=schema)
    
    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        if EMBEDDING_FUNCTION:
            return EMBEDDING_FUNCTION.embed(texts) if hasattr(EMBEDDING_FUNCTION, 'embed') else EMBEDDING_FUNCTION(texts)
        else:
            # Fallback: random vectors (for testing only)
            import random
            return [[random.uniform(-1, 1) for _ in range(768)] for _ in texts]
    
    # === Style Collection Methods ===
    
    def add_style_rule(self, rule_id: str, text: str, metadata: Dict[str, Any]):
        """Add a style rule to the Style DB."""
        self.upsert_style_batch([{
            "id": rule_id,
            "document": text,
            "metadata": metadata
        }])
    
    def upsert_style_batch(self, items: List[Dict[str, Any]]):
        """
        Batch upsert style rules.
        items: List of dicts with keys: id, document, metadata
        """
        if not items:
            return

        documents = [item["document"] for item in items]
        vectors = self._embed_texts(documents)
        
        data = []
        for i, item in enumerate(items):
            metadata = item.get("metadata", {})
            data.append({
                "id": item["id"],
                "document": item["document"],
                "vector": vectors[i],
                "type": metadata.get("type", "guideline"),
                "trigger": metadata.get("trigger", ""),
                "change": metadata.get("change", ""),
                "section": metadata.get("section", ""),
                "source": metadata.get("source", ""),
                "status": metadata.get("status", "publish"),
                "date": metadata.get("date", datetime.now().isoformat()),
                "modified": metadata.get("modified", datetime.now().isoformat()),
            })
            
        # Delete existing IDs to avoid duplicates (LanceDB might not auto-dedup by ID on add)
        ids_to_delete = [f"'{item['id']}'" for item in items]
        if ids_to_delete:
            where_clause = f"id IN ({', '.join(ids_to_delete)})"
            try:
                self.style_table.delete(where_clause)
            except:
                pass
                
        self.style_table.add(data)
    
    def query_style_rules(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query style rules from the Style DB."""
        query_vector = self._embed_texts([query_text])[0]
        
        results = (
            self.style_table
            .search(query_vector)
            .limit(n_results)
            .to_list()
        )
        
        return self._format_results(results)
    
    # === Facts Collection Methods ===
    
    def add_fact(self, fact_id: str, text: str, metadata: Dict[str, Any]):
        """Add a verified fact to the Facts DB."""
        vector = self._embed_texts([text])[0]
        
        data = [{
            "id": fact_id,
            "document": text,
            "vector": vector,
            "source": metadata.get("source", ""),
            "verified_date": metadata.get("verified_date", datetime.now().isoformat()),
            "category": metadata.get("category", ""),
        }]
        
        try:
            self.facts_table.delete(f"id = '{fact_id}'")
        except:
            pass
        self.facts_table.add(data)
    
    def query_facts(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query verified facts from the Facts DB."""
        query_vector = self._embed_texts([query_text])[0]
        
        results = (
            self.facts_table
            .search(query_vector)
            .limit(n_results)
            .to_list()
        )
        
        return self._format_results(results)
    
    # === Content Collection Methods ===
    
    def add_content_structure(self, content_id: str, text: str, metadata: Dict[str, Any]):
        """Add content structure to the Content DB."""
        self.upsert_content_batch([{
            "id": content_id,
            "document": text,
            "metadata": metadata
        }])

    def upsert_content_batch(self, items: List[Dict[str, Any]]):
        """
        Batch upsert content items.
        items: List of dicts with keys: id, document, metadata
        """
        if not items:
            return

        documents = [item["document"] for item in items]
        vectors = self._embed_texts(documents)
        
        import json
        data = []
        for i, item in enumerate(items):
            metadata = item.get("metadata", {})
            categories = metadata.get("categories", [])
            h2_headings = metadata.get("h2_headings", [])
            
            data.append({
                "id": item["id"],
                "document": item["document"],
                "vector": vectors[i],
                "type": metadata.get("type", "post"),
                "slug": metadata.get("slug", ""),
                "categories": json.dumps(categories, ensure_ascii=False) if isinstance(categories, list) else str(categories),
                "status": metadata.get("status", "publish"),
                "date": metadata.get("date", datetime.now().isoformat()),
                "modified": metadata.get("modified", datetime.now().isoformat()),
                "h2_headings": json.dumps(h2_headings, ensure_ascii=False) if isinstance(h2_headings, list) else str(h2_headings),
            })

        # Delete existing IDs
        ids_to_delete = [f"'{item['id']}'" for item in items]
        if ids_to_delete:
            where_clause = f"id IN ({', '.join(ids_to_delete)})"
            try:
                self.content_table.delete(where_clause)
            except:
                pass
        
        self.content_table.add(data)
    
    def query_content(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query content from the Content DB."""
        query_vector = self._embed_texts([query_text])[0]
        
        results = (
            self.content_table
            .search(query_vector)
            .limit(n_results)
            .to_list()
        )
        
        return self._format_results(results)
    
    def query_content_with_filter(
        self, 
        query_text: str, 
        where: Optional[Dict[str, Any]] = None, 
        n_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Query content with metadata filters."""
        query_vector = self._embed_texts([query_text])[0]
        
        search = self.content_table.search(query_vector)
        
        # Apply filters if provided
        if where:
            filter_parts = []
            for key, value in where.items():
                if isinstance(value, dict):
                    # Handle composite operators
                    for op, val in value.items():
                        if op == "$contains" or op == "$like":
                            filter_parts.append(f"{key} LIKE '%{val}%'")
                        elif op == "$eq":
                            filter_parts.append(f"{key} = '{val}'" if isinstance(val, str) else f"{key} = {val}")
                elif isinstance(value, str):
                    filter_parts.append(f"{key} = '{value}'")
                else:
                    filter_parts.append(f"{key} = {value}")
            if filter_parts:
                search = search.where(" AND ".join(filter_parts))
        
        results = search.limit(n_results).to_list()
        return self._format_results(results)
    
    def get_content_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve content items by their IDs."""
        if not ids:
            return []
            
        # Format IDs for SQL-like IN clause
        # Escape single quotes in IDs if necessary (though usually they are safe strings)
        formatted_ids = [f"'{id_}'" for id_ in ids]
        where_clause = f"id IN ({', '.join(formatted_ids)})"
        
        results = (
            self.content_table
            .search()
            .where(where_clause)
            .limit(len(ids))
            .to_list()
        )
        
        return self._format_results(results)
    
    def _format_results(self, results: List[Dict]) -> List[Dict[str, Any]]:
        """Format LanceDB results to standard format."""
        formatted = []
        for row in results:
            formatted.append({
                "id": row.get("id", ""),
                "document": row.get("document", ""),
                "metadata": {k: v for k, v in row.items() if k not in ["id", "document", "vector", "_distance"]},
                "distance": row.get("_distance", None),
            })
        return formatted
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the tables."""
        return {
            "content_count": len(self.content_table),
            "facts_count": len(self.facts_table),
            "style_count": len(self.style_table),
        }
    
    def query_content_hybrid(
        self, 
        query_text: str, 
        keywords: List[str], 
        n_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining vector search and keyword matching."""
        # Vector search
        vector_results = self.query_content(query_text, n_results=n_results*2)
        
        # Keyword search (run multiple queries)
        keyword_results = []
        for kw in keywords[:3]:
            kw_res = self.query_content(kw, n_results=n_results)
            keyword_results.extend(kw_res)
        
        # RRF Merge
        def rrf_score(rank: int, k: int = 60) -> float:
            return 1.0 / (k + rank)
        
        scores: Dict[str, float] = {}
        id_to_doc: Dict[str, Dict] = {}
        
        for rank, res in enumerate(vector_results):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score(rank)
            id_to_doc[doc_id] = res
        
        for rank, res in enumerate(keyword_results):
            doc_id = res['id']
            scores[doc_id] = scores.get(doc_id, 0.0) + rrf_score(rank)
            if doc_id not in id_to_doc:
                id_to_doc[doc_id] = res
        
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [id_to_doc[doc_id] for doc_id in sorted_ids[:n_results]]


# Global instance
vector_db = VectorDBManager()
