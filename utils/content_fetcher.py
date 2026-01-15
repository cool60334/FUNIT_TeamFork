import requests
from bs4 import BeautifulSoup
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ContentFetcher:
    """
    Simple utility to fetch and extract main text content from a URL.
    Used for P02 Refactoring Mode to analyze existing articles.
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def fetch(self, url: str) -> Optional[str]:
        """
        Fetches the URL and extracts the main text content.
        Returns the text content or None if failed.
        """
        try:
            logger.info(f"Fetching content from: {url}")
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
                
            # Get text
            text = soup.get_text(separator='\n')
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return clean_text
            
        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return None

if __name__ == "__main__":
    # Test
    fetcher = ContentFetcher()
    test_url = "https://example.com"
    print(fetcher.fetch(test_url))
