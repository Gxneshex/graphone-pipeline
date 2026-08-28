import logging
from typing import List, Dict, Any
from datetime import datetime

from src.llm.schemas import Startup
from src.utils.dedupe_store import URLDedupeStore
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.startups")

class StartupDirectoryScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        # Bind unified tracking storage to check URL freshness
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    @retry_with_backoff(retries=3, base_delay=1.5)
    def _fetch_mock_startup_directory(self) -> List[Dict[str, Any]]:
        """
        Simulates an API request or HTML parsing routine from a startup aggregator hub.
        """
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
        """
        Main execution workflow. Polls data feeds, processes items through 
        uniqueness filters, and builds validated Startup instances.
        """
        scraped_startups: List[Startup] = []
        
        try:
            raw_data = self._fetch_mock_startup_directory()
            
            for item in raw_data:
                source_url = item.get("source_url", "")
                
                # Check for duplicate processing history
                if not self.dedupe_store.is_new(source_url):
                    logger.info(f"Skipping duplicate startup entry: {item.get('company_name')}")
                    continue
                    
                logger.info(f"Ingesting new startup entry: {item.get('company_name')}")
                
                # Standardize properties through our Pydantic structure
                startup_model = Startup(
                    company_name=item.get("company_name"),
                    website=item.get("website"),
                    one_liner=item.get("one_liner"),
                    description=item.get("description"),
                    industries=item.get("industries", []),
                    funding_stage=item.get("funding_stage"),
                    location=item.get("location"),
                    source_url=source_url,
                    extracted_at=datetime.utcnow()
                )
                scraped_startups.append(startup_model)
                
        except Exception as e:
            logger.error(f"Encountered a breakdown in startup tracking workflow: {e}")
            
        return scraped_startups
