import logging
from typing import List
from datetime import datetime
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
            url = "https://remoteok.com/api"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            res = requests.get(url, headers=headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                # Elements index 0 is an API metadata object; slice past it
                for item in data[1:30]:
                    job_url = item.get("url", "")
                    if not self.dedupe_store.is_new(job_url):
                        continue
                        
                    instance = Job(
                        schemaVersion="1.0",
                        recordType="JOB",
                        content=JobContent(
                            company=item.get("company", "Tech Startup"),
                            date=datetime.fromtimestamp(int(item.get("date"))).isoformat() if item.get("date") else datetime.utcnow().isoformat(),
                            is_remote=True,
                            role_family="Engineering"
                        )
                    )
                    scraped_jobs.append(instance)
        except Exception as e:
            logger.error(f"RemoteOK API connection failed: {e}")
        return scraped_jobs
