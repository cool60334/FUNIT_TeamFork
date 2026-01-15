
import sys
import os
import json
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def list_block_types():
    connector = WordPressConnector()
    print("--- Listing Registered Block Types matching 'seopress' ---")
    try:
        # Note: block-types endpoint might require auth or be public depending on config. 
        # It's at /wp/v2/block-types/
        blocks = connector.get('/wp-json/wp/v2/block-types')
        
        found = False
        if isinstance(blocks, list):
            for block in blocks:
                name = block.get('name', '')
                if 'seopress' in name or 'faq' in name:
                    print(f"Found Block: {name}")
                    found = True
                    # Print attributes if possible to see structure
                    if 'attributes' in block:
                        print(f"  Attributes: {list(block['attributes'].keys())}")
        else:
            print(f"Unexpected response type: {type(blocks)}")
            
        if not found:
            print("No blocks matching 'seopress' or 'faq' found in registry.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_block_types()
