import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, List
from crawl4ai import AsyncWebCrawler

class WebCrawler:
    def __init__(self, output_dir: str = "outputs/temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def process_urls(self, urls: List[str]) -> Dict[str, Any]:
        """
        Crawls a list of URLs and saves content.
        """
        results = []
        
        async with AsyncWebCrawler(verbose=True) as crawler:
            for url in urls:
                try:
                    print(f"Crawling: {url}")
                    result = await crawler.arun(url=url)
                    
                    if result.success:
                        # Save content
                        filename = self._url_to_filename(url)
                        output_file = self.output_dir / f"{filename}.txt"
                        
                        content = f"URL: {url}\n\n{result.markdown}"
                        output_file.write_text(content, encoding="utf-8")
                        
                        results.append({
                            "status": "success",
                            "url": url,
                            "file_path": str(output_file),
                            "title": result.metadata.get("title", "No Title")
                        })
                    else:
                        results.append({
                            "status": "error",
                            "url": url,
                            "message": result.error_message
                        })
                        
                except Exception as e:
                    results.append({
                        "status": "error",
                        "url": url,
                        "message": str(e)
                    })
        
        return {"results": results}

    def _url_to_filename(self, url: str) -> str:
        """Converts URL to a safe filename."""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        path = parsed.path.replace("/", "_").strip("_")
        if not path:
            path = "home"
        return f"{domain}_{path}"

def main():
    parser = argparse.ArgumentParser(description="Web Crawler using Crawl4AI")
    parser.add_argument("--urls", nargs="+", required=True, help="List of URLs to crawl")
    parser.add_argument("--output_dir", default="outputs/temp", help="Output directory")
    
    args = parser.parse_args()
    
    crawler = WebCrawler(output_dir=args.output_dir)
    
    # Run async main
    result = asyncio.run(crawler.process_urls(args.urls))
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
