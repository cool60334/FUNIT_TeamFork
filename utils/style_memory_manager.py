
import logging
from typing import List, Dict, Any, Optional
import uuid
import datetime
from utils.vector_db_manager import vector_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StyleMemoryManager:
    """
    Manages the 'Style Memory' in ChromaDB.
    Wraps VectorDBManager to provide higher-level style management.
    """
    
    def __init__(self):
        # We leverage the existing global vector_db instance
        pass
        
    def add_example(self, trigger_scenario: str, style_change: str, bad_example: str, good_example: str, tags: List[str]) -> str:
        """
        Adds a style example to the vector database.
        """
        ex_id = str(uuid.uuid4())
        timestamp = datetime.datetime.now().isoformat()
        
        # Construct the text to be embedded
        document_text = f"Trigger: {trigger_scenario}\nBad: {bad_example}\nGood: {good_example}"
        
        metadata = {
            "type": "style_rule",
            "trigger": trigger_scenario,
            "change": style_change,
            "tags": ",".join(tags),
            "added_at": timestamp
        }
        
        try:
            # Use the method provided by VectorDBManager
            vector_db.add_style_rule(
                rule_id=ex_id,
                text=document_text,
                metadata=metadata
            )
            logger.info(f"Successfully added style rule {ex_id}")
            return ex_id
        except Exception as e:
            logger.error(f"Failed to add style rule: {e}")
            return None

    def retrieve_examples(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieves relevant style rules based on a query.
        """
        try:
            # Use the method provided by VectorDBManager
            formatted_results = vector_db.query_style_rules(
                query_text=query,
                n_results=k
            )
            
            # Add 'good_example' parsing for convenience
            for res in formatted_results:
                doc = res.get('document', '')
                if "Good: " in doc:
                    res['good_example'] = doc.split("Good: ")[1].strip()
                else:
                    res['good_example'] = ""
                    
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve style rules: {e}")
            return []
