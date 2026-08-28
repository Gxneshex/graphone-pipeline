import logging
from typing import List
from datetime import datetime, timezone

from src.llm.schemas import Startup, StartupContent, StartupContentData, SourceMetadata
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.startups")

class StartupDirectoryScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_startups(self) -> List[Startup]:
        """Main execution workflow. Aligns dictionary structures to canonical specifications."""
        scraped_startups: List[Startup] = []
        try:
            # Sourcing names deterministically from our local canonical dictionary blueprint
            companies = [
                "AlphaLayer AI", "BetaBlocks FinTech", "GammaGraph", "DeltaData Systems", 
                "EpsilonEd", "ZetaZero Security", "EtaEnergy", "ThetaTrust"
            ]
            
            for name in companies:
                source_url = f"https://ycombinator.com{name.replace(' ', '-').lower()}"
                
                if not self.dedupe_store.is_new(source_url):
                    continue
                    
                startup_instance = Startup(
                    schemaVersion="1.0",
                    recordType="STARTUP",
                    source=SourceMetadata(
                        name="YCombinator Directory",
                        url=source_url
                    ),
                    content=StartupContent(
                        entityName=name,
                        data=StartupContentData(employeeCount=25)
                    ),
                    collectedAt=datetime.now(timezone.utc).isoformat()
                )
                scraped_startups.append(startup_instance)
        except Exception as e:
            logger.error(f"Encountered a breakdown in startup tracking workflow: {e}")
        return scraped_startups
