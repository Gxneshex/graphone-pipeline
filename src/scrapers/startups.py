"""
src/scrapers/startups.py
Scrapes real startup profiles from Y Combinator's official directory using live Algolia index.
"""

import logging
import re
import json
from typing import List
from datetime import datetime, timezone
import requests

from src.llm.schemas import Startup, StartupContent, StartupContentData, SourceMetadata
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.startups")

DEFAULT_ALGOLIA_APP = "45BWZJ1SGC"
DEFAULT_ALGOLIA_KEY = "NzllNTY5MzJiZGM2OTY2ZTQwMDEzOTNhYWZiZGRjODlhYzVkNjBmOGRjNzJiMWM4ZTU0ZDlhYTZjOTJiMjlhMWFuYWx5dGljc1RhZ3M9eWNkYyZyZXN0cmljdEluZGljZXM9WUNDb21wYW55X3Byb2R1Y3Rpb24lMkNZQ0NvbXBhbnlfQnlfTGF1bmNoX0RhdGVfcHJvZHVjdGlvbiZ0YWdGaWx0ZXJzPSU1QiUyMnljZGNfcHVibGljJTIyJTVE"

class StartupDirectoryScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def _get_algolia_credentials(self):
        """Dynamically extract Algolia App ID and Search API Key from YC companies page."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"}
            res = requests.get("https://www.ycombinator.com/companies", headers=headers, timeout=10)
            if res.status_code == 200:
                match = re.search(r'window\.AlgoliaOpts\s*=\s*(\{.*?\});', res.text)
                if match:
                    opts = json.loads(match.group(1))
                    app = opts.get("app")
                    key = opts.get("key")
                    if app and key:
                        return app, key
        except Exception as e:
            logger.warning(f"Could not extract dynamic Algolia credentials from https://www.ycombinator.com/companies: {e}. Using defaults.")
        return DEFAULT_ALGOLIA_APP, DEFAULT_ALGOLIA_KEY

    def scrape_startups(self, target_count: int = 1000) -> List[Startup]:
        """Extracts real Y Combinator companies from Algolia directory API."""
        scraped_startups: List[Startup] = []
        app_id, api_key = self._get_algolia_credentials()
        
        logger.info(f"Ingesting real YC startups via Algolia API (Target: {target_count})...")
        endpoint = f"https://{app_id}-dsn.algolia.net/1/indexes/YCCompany_production/query"
        headers = {
            "X-Algolia-API-Key": api_key,
            "X-Algolia-Application-Id": app_id,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"
        }
        
        hits_per_page = 100
        page = 0
        max_pages = (target_count + hits_per_page - 1) // hits_per_page
        
        while len(scraped_startups) < target_count and page < max_pages:
            try:
                payload = {"params": f"hitsPerPage={hits_per_page}&page={page}"}
                res = requests.post(endpoint, json=payload, headers=headers, timeout=12)
                
                if res.status_code != 200:
                    logger.error(f"Algolia query call to {endpoint} (page {page}) failed with status code {res.status_code}")
                    break
                    
                data = res.json()
                hits = data.get("hits", [])
                if not hits:
                    break
                    
                for item in hits:
                    if len(scraped_startups) >= target_count:
                        break
                        
                    name = item.get("name", "").strip()
                    slug = item.get("slug", "").strip()
                    if not name or not slug:
                        continue
                        
                    source_url = f"https://www.ycombinator.com/companies/{slug}"
                    
                    if not self.dedupe_store.is_new(source_url):
                        continue
                        
                    team_size = item.get("team_size")
                    try:
                        employee_count = int(team_size) if team_size is not None else 1
                    except (ValueError, TypeError):
                        employee_count = 1
                        
                    startup_instance = Startup(
                        schemaVersion="1.0",
                        recordType="STARTUP",
                        source=SourceMetadata(
                            name="Y Combinator Directory",
                            url=source_url
                        ),
                        content=StartupContent(
                            entityName=name,
                            data=StartupContentData(employeeCount=employee_count)
                        ),
                        collectedAt=datetime.now(timezone.utc).isoformat()
                    )
                    scraped_startups.append(startup_instance)
                    
                page += 1
            except Exception as e:
                logger.error(f"Algolia scraper network call to {endpoint} (page {page}) failed with error: {e}")
                break
                
        logger.info(f"Successfully collected {len(scraped_startups)} real YC startups.")
        return scraped_startups
