
import sys
import os
from dotenv import load_dotenv

sys.path.insert(0, os.getcwd())
load_dotenv()

from agents.wordpress.connector import WordPressConnector

def check_pages_and_post():
    connector = WordPressConnector()
    print('--- Checking Pages for Keywords ---')

    queries = ['Level 1', 'Visa Fee', 'Cost', 'University List']
    for term in queries:
        try:
            pages = connector.get('/wp-json/wp/v2/pages', params={'search': term, 'per_page': 3})
            if pages:
                for p in pages:
                    print(f"PAGE Match '{term}': {p['title']['rendered']} -> {p['link']}")
            else:
                print(f"No pages found for '{term}'")
        except Exception as e:
            print(f"Error searching pages '{term}': {e}")

    print('\n--- Checking Current Status of Post 34436 ---')
    try:
        post = connector.get('/wp-json/wp/v2/posts/34436')
        if post and 'id' in post:
            print(f"ID: {post['id']}")
            print(f"Slug: {post['slug']}")
            print(f"Status: {post['status']}")
            print(f"Link: {post['link']}")
            print(f"Categories: {post['categories']}")
        else:
            print("Post 34436 not found or error.")
    except Exception as e:
        print(f"Error checking post 34436: {e}")

if __name__ == "__main__":
    check_pages_and_post()
