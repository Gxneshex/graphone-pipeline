import logging
import requests
from typing import List
from datetime import datetime, timezone

from src.llm.schemas import Startup, StartupContent, StartupContentData, SourceMetadata
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.startups")

# YC's directory page (ycombinator.com/companies) is a React app backed by this
# public Algolia index. This app ID + search-only key are exposed in YC's own
# frontend JS bundle (search-only keys are meant to be public) — verify they
# still work before relying on them, since YC can rotate them.
YC_ALGOLIA_URL = "https://45bwzj1sgc-dsn.algolia.net/1/indexes/*/queries"
YC_ALGOLIA_APP_ID = "45BWZJ1SGC"
YC_ALGOLIA_SEARCH_KEY = "MjBjYjRiOTY5NjY5NTNhNjJlNzY5YTFlMzYyYzE0YWJlOWY..."  # placeholder — pull the real current key from the network tab on ycombinator.com/companies

class StartupDirectoryScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_startups(self, max_records: int = 1000, page_size: int = 100) -> List[Startup]:
        scraped_startups: List[Startup] = []
        headers = {
            "X-Algolia-Application-Id": YC_ALGOLIA_APP_ID,
            "X-Algolia-API-Key": YC_ALGOLIA_SEARCH_KEY,
            "Content-Type": "application/json",
        }
        page = 0
        while len(scraped_startups) < max_records:
            payload = {
                "requests": [{
                    "indexName": "YCCompany_production",
                    "params": f"query=&hitsPerPage={page_size}&page={page}"
                }]
            }
            try:
                resp = requests.post(YC_ALGOLIA_URL, json=payload, headers=headers, timeout=15)
                resp.raise_for_status()
                hits = resp.json()["results"][0]["hits"]
            except Exception as e:
                logger.error(f"YC directory fetch failed on page {page}: {e}")
                break

            if not hits:
                break  # ran out of real records — stop, don't pad

            for hit in hits:
                slug = hit.get("slug")
                name = hit.get("name")
                if not slug or not name:
                    continue
                source_url = f"https://www.ycombinator.com/companies/{slug}"
                if not self.dedupe_store.is_new(source_url):
                    continue

                scraped_startups.append(Startup(
                    schemaVersion="1.0",
                    recordType="STARTUP",
                    source=SourceMetadata(name="YCombinator Directory", url=source_url),
                    content=StartupContent(
                        entityName=name,
                        data=StartupContentData(employeeCount=hit.get("team_size"))
                    ),
                    collectedAt=datetime.now(timezone.utc).isoformat()
                ))
            page += 1

        return scraped_startups