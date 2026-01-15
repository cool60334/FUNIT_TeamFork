
import logging
from typing import List, Dict, Any, Optional
import uuid
import datetime
from utils.vector_db_manager import vector_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FactMemoryManager:
    """
    Manages the 'Fact Memory' in ChromaDB.
    Wraps VectorDBManager to provide higher-level fact management.
    """
    
    def __init__(self):
        # We leverage the existing global vector_db instance
        pass
        
    def add_fact(self, context: str, claim: str, correction: str, source: str) -> str:
        """
        Adds a verified fact/correction to the vector database.
        
        Args:
            context: The context sentence where the error happened.
            claim: The incorrect claim (or the subject).
            correction: The corrected fact.
            source: The source URL or verification method.
        """
        fact_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Construct the text to be embedded
        # We want the embedding to match future similar contexts
        document_text = f"Context: {context}\nIncorrect Claim: {claim}\nVerified Fact: {correction}"
        
        metadata = {
            "type": "correction",
            "source": source,
            "added_at": timestamp,
            "claim_preview": claim[:50],
            "correction_preview": correction[:50]
        }
        
        try:
            vector_db.add_fact(
                fact_id=fact_id,
                text=document_text,
                metadata=metadata
            )
            logger.info(f"Successfully added fact memory {fact_id}")
            return fact_id
        except Exception as e:
            logger.error(f"Failed to add fact memory: {e}")
            return None

    def retrieve_facts(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant verified facts based on a query.
        """
        try:
            formatted_results = vector_db.query_facts(
                query_text=query,
                n_results=k
            )
            
            # parse 'Verified Fact'
            for res in formatted_results:
                doc = res.get('document', '')
                if "Verified Fact: " in doc:
                    try:
                        res['verified_fact'] = doc.split("Verified Fact: ")[1].split("\n")[0] # approximate parsing
                        if not res['verified_fact']:
                             res['verified_fact'] = doc.split("Verified Fact: ")[1] # Take till end if no newline
                    except:
                         res['verified_fact'] = doc
                else:
                    res['verified_fact'] = ""
                    
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve fact memory: {e}")
            return []
