
import os
import sys
from datetime import datetime
from typing import List, Dict

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from utils.vector_db_manager import vector_db
from config.settings import settings

def ingest_reference_files():
    """
    Ingest specific collected reference markdown files into the Vector DB (Content Collection).
    These serve as standard answer references for RAG.
    """
    print(f"🚀 Starting Reference Ingestion for: {settings.brand_name}")
    
    # 檔案列表
    files_to_ingest = []
    
    ids = []
    documents = []
    metadatas = []
    
    for relative_path in files_to_ingest:
        file_path = os.path.abspath(relative_path)
        
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            continue
            
        print(f"📄 Processing: {relative_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract title (first line)
        lines = content.splitlines()
        title = lines[0].replace("# ", "").strip() if lines else "Untitled Reference"
        
        # ID generation (basename without extension)
        filename = os.path.basename(file_path)
        doc_id = f"ref_{os.path.splitext(filename)[0]}"
        
        # Metadata
        metadata = {
            "type": "reference",
            "source": "manual_ingest",
            "title": title,
            "filename": filename,
            "ingested_at": datetime.now().isoformat(),
            "brand": settings.brand_name
        }
        
        ids.append(doc_id)
        documents.append(content)
        metadatas.append(metadata)
        
    if ids:
        print(f"🔄 Upserting {len(ids)} documents to Content Collection...")
        try:
            vector_db.content_collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print("✅ Ingestion execution completed successfully.")
        except Exception as e:
            print(f"❌ Error during upsert: {e}")
    else:
        print("⚠️ No valid files found to ingest.")

if __name__ == "__main__":
    ingest_reference_files()
