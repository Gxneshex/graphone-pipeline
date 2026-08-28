"""
src/scrapers/startups.py
Aggregates early-stage company tracks from startup directory feeds,
enforcing tracking deduplication and strict schema mapping.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from src.llm.schemas import Startup, StartupContent, StartupContentData, SourceMetadata
from src.utils.dedupe_store import URLDedupeStore
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.startups")

class StartupDirectoryScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    @retry_with_backoff(retries=3, base_delay=1.5)
    def _fetch_mock_startup_directory(self) -> List[Dict[str, Any]]:
        logger.info("Polling remote startup discovery indexes...")
        return [
            {
                "company_name": "AlphaLayer AI Inc.",
                "website": "https://alphalayer.ai",
                "one_liner": "Automated workflow execution graphs for AI teams.",
                "description": "Building next-generation context-aware autonomous workflows for enterprise engineering frameworks.",
                "industries": ["AI", "SaaS", "DevTools"],
                "funding_stage": "Seed",
                "location": "San Francisco, CA",
                "source_url": "https://ycombinator.com"
            },
            {
                "company_name": "BetaBlocks FinTech",
                "website": "https://betablocks.io",
                "one_liner": "Decentralized accounting reconciliation primitives.",
                "description": "Providing zero-knowledge validation systems to automate audit and ledger processing records.",
                "industries": ["FinTech", "Blockchain"],
                "funding_stage": "Pre-seed",
                "location": "New York, NY",
                "source_url": "https://crunchbase.com"
            }
        ]

    def scrape_startups(self) -> List[Startup]:
        """Main execution workflow. Aligns dictionary structures to canonical specifications."""
        scraped_startups: List[Startup] = []
        try:
            raw_data = self._fetch_mock_startup_directory()
            for item in raw_data:
                source_link = item.get("source_url", "")
                if not self.dedupe_store.is_new(source_link):
                    continue
                    
                startup_instance = Startup(
                    schemaVersion="1.0",
                    recordType="STARTUP",
                    source=SourceMetadata(
                        name="YCombinator Directory" if "ycombinator" in source_link else "Crunchbase",
                        url=source_link
                    ),
                    content=StartupContent(
                        entityName=item.get("company_name"),
                        data=StartupContentData(employeeCount=25)
                    ),
                    collectedAt=datetime.utcnow().isoformat()
                )
                scraped_startups.append(startup_instance)
        except Exception as e:
            logger.error(f"Encountered a breakdown in startup tracking workflow: {e}")
        return scraped_startups
