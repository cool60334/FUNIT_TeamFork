
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def check_category_and_ranking():
    connector = WordPressConnector()
    print('--- Checking Category 477 ---')
    try:
        cat = connector.get(f'/wp-json/wp/v2/categories/477')
        if cat:
            print(f"Category 477: {cat['name']}")
        else:
            print("Category 477 not found.")
    except Exception as e:
        print(f"Error checking category: {e}")

    print('\n--- Searching for Ranking/Universities ---')
    try:
        queries = ['Ranking', '排名', 'University', '大學']
        for term in queries:
            posts = connector.get('/wp-json/wp/v2/posts', params={'search': term, 'per_page': 3})
            if posts:
                for p in posts:
                    print(f"Match '{term}': {p['title']['rendered']} -> {p['link']}")
    except Exception as e:
        print(f"Error searching ranking: {e}")

if __name__ == "__main__":
    check_category_and_ranking()
