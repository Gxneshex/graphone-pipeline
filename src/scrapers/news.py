import logging
from typing import List, Dict, Any
import xml.etree.ElementTree as ET
import requests

from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.news")

class TechNewsScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_news(self) -> List[Dict[str, Any]]:
        scraped_articles: List[Dict[str, Any]] = []
        try:
            # TechCrunch Artificial Intelligence Category RSS Endpoint
            url = "https://techcrunch.com"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                root = ET.fromstring(res.text)
                for item in root.findall(".//item")[:20]:
                    link = item.find("link").text.strip()
                    if not self.dedupe_store.is_new(link):
                        continue
                        
                    article_record = {
                        "title": item.find("title").text.strip(),
                        "source_name": "TechCrunch AI",
                        "author": item.find("{http://purl.org}creator").text if item.find("{http://purl.org}creator") is not None else "Staff Writer",
                        "url": link,
                        "summary": item.find("description").text.strip()[:200] if item.find("description") is not None else "",
                        "body_content": "Full article context verified at linked source.",
                        "extracted_at": item.find("pubDate").text if item.find("pubDate") is not None else datetime.utcnow().isoformat()
                    }
                    scraped_articles.append(article_record)
        except Exception as e:
            logger.error(f"RSS extraction breakdown: {e}")
        return scraped_articles
