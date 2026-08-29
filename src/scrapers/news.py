import logging
import feedparser
import trafilatura
from datetime import datetime, timezone
from typing import List, Dict, Any

from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.news")

FEEDS = {
    "TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI": "https://venturebeat.com/category/ai/feed/",
}

class TechNewsScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_news(self) -> List[Dict[str, Any]]:
        scraped_articles: List[Dict[str, Any]] = []
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

                # real published timestamp from the feed, not a fabricated "now"
                published = entry.get("published_parsed")
                published_iso = (
                    datetime(*published[:6], tzinfo=timezone.utc).isoformat()
                    if published else None
                )

                full_text = trafilatura.extract(trafilatura.fetch_url(url)) or ""

                scraped_articles.append({
                    "title": entry.get("title", ""),
                    "source_name": source_name,
                    "author": entry.get("author", "Unknown"),
                    "url": url,
                    "summary": entry.get("summary", "")[:500],
                    "body_content": full_text,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                    "published_at": published_iso,
                })
        return scraped_articles