import logging
from typing import List
from datetime import datetime, timezone

from src.llm.schemas import Job, JobContent
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.jobs")

class JobBoardScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_jobs(self) -> List[Job]:
        """Main execution workflow. Packs fields into valid nested content targets."""
        scraped_jobs: List[Job] = []
        try:
            mock_postings = [
                {"company": "AlphaLayer AI", "is_remote": True, "role": "Engineering"},
                {"company": "BetaBlocks FinTech", "is_remote": True, "role": "Engineering"},
                {"company": "GammaGraph", "is_remote": False, "role": "Data Intelligence"}
            ]
            
            for item in mock_postings:
                job_board_url = f"https://remoteok.com{item['company'].replace(' ', '-').lower()}-eng"
                
                if not self.dedupe_store.is_new(job_board_url):
                    continue
                    
                job_instance = Job(
                    schemaVersion="1.0",
                    recordType="JOB",
                    content=JobContent(
                        company=item["company"],
                        date=datetime.now(timezone.utc).isoformat(),
                        is_remote=item["is_remote"],
                        role_family=item["role"]
                    )
                )
                scraped_jobs.append(job_instance)
        except Exception as e:
            logger.error(f"Encountered a breakdown in job tracking workflow: {e}")
        return scraped_jobs
