import logging
from typing import List
from datetime import datetime, timezone
import requests

from src.llm.schemas import Job, JobContent
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.jobs")

class JobBoardScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_jobs(self) -> List[Job]:
        scraped_jobs: List[Job] = []
        try:
            url = "https://remoteok.com"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(url, headers=headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                # Element 0 is an API disclaimer block; slice past it
                for item in data[1:30]:
                    job_url = item.get("url", "")
                    if not self.dedupe_store.is_new(job_url):
                        continue
                        
                    raw_date = item.get("date")
                    final_date_str = ""
                    
                    # FIX: Defensive timestamp parsing to handle both integer epochs and ISO string fields
                    try:
                        final_date_str = datetime.fromtimestamp(int(raw_date), tz=timezone.utc).isoformat()
                    except (ValueError, TypeError):
                        # If already an ISO string structure, retain the string directly
                        final_date_str = str(raw_date) if raw_date else datetime.now(timezone.utc).isoformat()
                        
                    instance = Job(
                        schemaVersion="1.0",
                        recordType="JOB",
                        content=JobContent(
                            company=item.get("company", "Tech Startup"),
                            date=final_date_str,
                            is_remote=True,
                            role_family="Engineering"
                        )
                    )
                    scraped_jobs.append(instance)
        except Exception as e:
            logger.error(f"RemoteOK API connection failed: {e}")
        return scraped_jobs
