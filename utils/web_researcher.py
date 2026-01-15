import subprocess
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class WebResearcher:
    """
    A utility class to perform web searches using the googlesearch-python library
    via a subprocess call to a specific Python environment (Python 3.11).
    """
    
    PYTHON_PATH = "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"

    def search_reviews(self, brand_name: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Searches for reviews of the given brand on Dcard and PTT.
        Returns a list of dictionaries with 'title' and 'url'.
        """
        results = []
        queries = [
            f"site:dcard.tw {brand_name} 評價",
            f"site:ptt.cc {brand_name} 評價"
        ]

        for query in queries:
            try:
                search_results = self._perform_search(query, max_results)
                results.extend(search_results)
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")

        return results

    def _perform_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Executes a python script in a subprocess to run a custom scraper using requests/bs4.
        """
        script = f"""
import json
import sys
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random

def search_duckduckgo(query, num_results=3):
    headers = {{
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }}
    data = {{
        "q": query,
        "kl": "tw-zh", # Region: Taiwan
    }}
    
    try:
        response = requests.post("https://html.duckduckgo.com/html/", headers=headers, data=data, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        results = []
        
        for result in soup.select(".result"):
            if len(results) >= num_results:
                break
                
            link = result.select_one(".result__a")
            if link and link.get("href"):
                url = link["href"]
                title = link.get_text(strip=True)
                
                # DDG sometimes returns relative URLs or ads, filter them
                if url.startswith("http"):
                    results.append({{
                        "title": title,
                        "url": url
                    }})
        
        return results
    except Exception as e:
        return [{{"error": str(e)}}]

results = search_duckduckgo("{query}", {num_results})
print(json.dumps(results))
"""
        try:
            result = subprocess.run(
                [self.PYTHON_PATH, "-c", script],
                capture_output=True,
                text=True,
                check=True
            )
            
            output = result.stdout.strip()
            if not output:
                return []
                
            data = json.loads(output)
            # Check if the first item is an error dict
            if data and isinstance(data, list) and isinstance(data[0], dict) and "error" in data[0]:
                logger.error(f"Search error: {data[0]['error']}")
                return []
            
            return data
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Subprocess failed: {e.stderr}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from subprocess: {result.stdout}")
            return []

if __name__ == "__main__":
    # Test
    from config.settings import settings
    researcher = WebResearcher()
    results = researcher.search_reviews(settings.brand_name)
    print(json.dumps(results, indent=2, ensure_ascii=False))
