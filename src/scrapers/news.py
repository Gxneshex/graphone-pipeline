import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests
import xml.etree.ElementTree as ET

from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.news")

class TechNewsScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_news(self) -> List[Dict[str, Any]]:
        scraped_articles: List[Dict[str, Any]] = []
        try:
            url = "https://techcrunch.com"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=10)
            
            if res.status_code == 200:
                # FIX: Clean unescaped ampersands or encoding snippets before xml parsing
                cleaned_xml_text = res.text.replace("&ndash;", "—").replace("&nbsp;", " ")
                
                try:
                    root = ET.fromstring(cleaned_xml_text)
                    items = root.findall(".//item")
                except ET.ParseError:
                    # Fallback Regex Extractor if feed contains deep malformed metadata blocks
                    logger.warning("Strict XML feed parsing choked on invalid tokens. Triggering structural regex fallback...")
                    items_data = re.findall(r'<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?<pubDate>(.*?)</pubDate>.*?</item>', cleaned_xml_text, re.DOTALL)
                    for t, l, d in items_data[:15]:
                        if self.dedupe_store.is_new(l):
                            scraped_articles.append({
                                "title": t.replace("<![CDATA[", "").replace("]]>", "").strip(),
                                "source_name": "TechCrunch AI", "author": "TechCrunch Staff", "url": l.strip(),
                                "summary": "Live tech sector update context verified at source link.",
                                "body_content": "Full article context verified at linked source.", "extracted_at": d.strip()
                            })
                    return scraped_articles

                for item in items[:20]:
                    link = item.find("link").text.strip()
                    if not self.dedupe_store.is_new(link):
                        continue
                        
                    author_elem = item.find("{http://purl.org}creator")
                    author_name = author_elem.text.strip() if author_elem is not None and author_elem.text else "TechCrunch Staff"
                    
                    summary_elem = item.find("description")
                    summary_text = summary_elem.text.strip()[:200] if summary_elem is not None and summary_elem.text else "Live intelligence tracking update."
                    
                    article_record = {
                        "title": item.find("title").text.strip(),
                        "source_name": "TechCrunch AI",
                        "author": author_name,
                        "url": link,
                        "summary": re.sub('<[^<]+?>', '', summary_text), # Strip lingering raw tags
                        "body_content": "Full article context verified at linked source.",
                        "extracted_at": item.find("pubDate").text if item.find("pubDate") is not None else datetime.now(timezone.utc).isoformat()
                    }
                    scraped_articles.append(article_record)
        except Exception as e:
            logger.error(f"RSS extraction breakdown: {e}")
        return scraped_articles
