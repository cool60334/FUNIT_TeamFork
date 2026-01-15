
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def find_links():
    connector = WordPressConnector()
    print('--- Deep Searching for URLs ---')

    # Search by slug substring
    slug_terms = ['level-1', 'visa-fee', 'student-visa-cost', 'universities', 'risk']
    
    print("\n--- Searching by Slug Substring (Manual Scan of recent 100 posts) ---")
    try:
        posts = connector.get('/wp-json/wp/v2/posts', params={'per_page': 100}) 
        if posts:
            for p in posts:
                slug = p['slug']
                for term in slug_terms:
                    if term in slug:
                        print(f"Match Slug '{term}': {p['title']['rendered']} -> {p['link']}")
    except Exception as e:
        print(f"Error fetching recent posts: {e}")

    # Search by keyword
    queries = [
        'Level 1',
        '學校名單',
        'Visa Fee',
        '簽證費用',
        'Risk Rating'
    ]

    print("\n--- Searching by Keyword (API Search) ---")
    for term in queries:
        try:
            posts = connector.get('/wp-json/wp/v2/posts', params={'search': term, 'per_page': 5})
            if posts:
                for p in posts:
                    print(f"Key '{term}': {p['title']['rendered']} -> {p['link']}")
        except Exception as e:
            print(f"Error searching '{term}': {e}")

if __name__ == "__main__":
    find_links()
