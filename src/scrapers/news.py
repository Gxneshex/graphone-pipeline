"""
src/scrapers/news.py
Extracts real AI technology news articles from TechCrunch AI and VentureBeat AI RSS feeds,
enforcing strict 24-hour freshness filters and extracting full text via trafilatura.
"""

import logging
import feedparser
import trafilatura
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.utils.dedupe_store import URLDedupeStore
from src.utils.date_normalizer import is_within_24_hours

logger = logging.getLogger("graphone-pipeline.scrapers.news")

FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
}

class TechNewsScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_news(self) -> List[Dict[str, Any]]:
        """Parses real RSS feeds and returns articles published within the last 24 hours."""
        scraped_articles: List[Dict[str, Any]] = []
        logger.info("Ingesting active tech news RSS streams...")
        
        for source_name, feed_url in FEEDS.items():
            try:
                parsed = feedparser.parse(feed_url)
            except Exception as e:
                logger.error(f"Feed fetch failed for {source_name}: {e}")
                continue

            for entry in parsed.entries:
                url = entry.get("link")
                if not url or not self.dedupe_store.is_new(url):
                    continue

                published = entry.get("published_parsed")
                if not published:
                    continue

                try:
                    published_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    published_iso = published_dt.isoformat()
                except Exception as e:
                    logger.debug(f"Could not convert published date for {url}: {e}")
                    continue

                # Filter strictly to articles published in the last 24 hours
                if not is_within_24_hours(published_iso):
                    logger.debug(f"Skipping article outside 24h window: {url} ({published_iso})")
                    continue

                try:
                    downloaded = trafilatura.fetch_url(url)
                    full_text = trafilatura.extract(downloaded) if downloaded else ""
                except Exception as e:
                    logger.debug(f"Trafilatura extraction failed for {url}: {e}")
                    full_text = ""

                scraped_articles.append({
                    "title": entry.get("title", "").strip(),
                    "source_name": source_name,
                    "author": entry.get("author", "Unknown"),
                    "url": url,
                    "summary": entry.get("summary", "")[:500],
                    "body_content": full_text or "",
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "published_at": published_iso,
                })
                
        logger.info(f"Successfully collected {len(scraped_articles)} real news articles published in the last 24 hours.")
        return scraped_articles