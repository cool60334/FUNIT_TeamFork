#!/usr/bin/env python3
"""
PDF to Fact Memory Ingestion Script
Extracts text from a PDF and stores it in the Fact Memory vector database.
"""

import sys
import os
import uuid
import datetime
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pdfplumber
except ImportError:
    print("❌ pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

from utils.vector_db_manager import vector_db


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text from PDF, organized by pages.
    Returns a list of dicts with page number and content.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    pages = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            
            # Clean up the text
            if text:
                text = text.strip()
                pages.append({
                    "page": page_num + 1,
                    "content": text
                })
    
    return pages


def chunk_by_sections(pages: list[dict], chunk_size: int = 1500) -> list[dict]:
    """
    Chunk the extracted text into smaller pieces for vector storage.
    Tries to break at section headers or paragraph boundaries.
    """
    chunks = []
    current_chunk = ""
    current_page = 1
    
    for page in pages:
        content = page["content"]
        page_num = page["page"]
        
        # Split by double newlines (paragraphs)
        paragraphs = re.split(r'\n\s*\n', content)
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds chunk size, save current chunk
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "content": current_chunk.strip(),
                    "start_page": current_page,
                    "end_page": page_num
                })
                current_chunk = ""
                current_page = page_num
            
            current_chunk += para + "\n\n"
    
    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "start_page": current_page,
            "end_page": pages[-1]["page"] if pages else 1
        })
    
    return chunks


def store_in_fact_memory(chunks: list[dict], source_name: str):
    """
    Store each chunk in the Fact Memory vector database.
    """
    timestamp = datetime.datetime.now().isoformat()
    
    for i, chunk in enumerate(chunks):
        fact_id = str(uuid.uuid4())
        
        # Format as a fact document
        document_text = f"Context: Official Travel Guide Standard\n" \
                       f"Source: {source_name} (Pages {chunk['start_page']}-{chunk['end_page']})\n" \
                       f"Content:\n{chunk['content']}"
        
        metadata = {
            "type": "official_standard",
            "source": source_name,
            "added_at": timestamp,
            "page_range": f"{chunk['start_page']}-{chunk['end_page']}",
            "chunk_index": i + 1,
            "total_chunks": len(chunks)
        }
        
        vector_db.add_fact(fact_id=fact_id, text=document_text, metadata=metadata)
        print(f"  ✓ Stored chunk {i+1}/{len(chunks)} (Pages {chunk['start_page']}-{chunk['end_page']})")
    
    return len(chunks)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract PDF and store in Fact Memory")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--chunk-size", type=int, default=1500, help="Max characters per chunk")
    parser.add_argument("--dry-run", action="store_true", help="Preview without storing")
    
    args = parser.parse_args()
    
    print(f"📄 Processing: {args.pdf_path}")
    
    # Step 1: Extract text
    print("Step 1: Extracting text from PDF...")
    pages = extract_text_from_pdf(args.pdf_path)
    print(f"  → Extracted {len(pages)} pages")
    
    # Step 2: Chunk the text
    print(f"Step 2: Chunking text (max {args.chunk_size} chars per chunk)...")
    chunks = chunk_by_sections(pages, args.chunk_size)
    print(f"  → Created {len(chunks)} chunks")
    
    # Step 3: Store in vector database
    if args.dry_run:
        print("\n🔍 DRY RUN - Preview of chunks:")
        for i, chunk in enumerate(chunks):
            print(f"\n--- Chunk {i+1} (Pages {chunk['start_page']}-{chunk['end_page']}) ---")
            print(chunk['content'][:300] + "..." if len(chunk['content']) > 300 else chunk['content'])
    else:
        print("Step 3: Storing in Fact Memory...")
        source_name = os.path.basename(args.pdf_path)
        count = store_in_fact_memory(chunks, source_name)
        print(f"\n✅ Successfully stored {count} chunks from '{source_name}' into Fact Memory!")
        print("   Future queries about travel guides will now retrieve this data.")


if __name__ == "__main__":
    main()
