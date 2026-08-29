import logging
import requests
from datetime import datetime, timezone
from typing import List

from src.llm.schemas import Job, JobContent
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.jobs")

REMOTEOK_API = "https://remoteok.com/api"

class JobBoardScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    def scrape_jobs(self, tags=("ai", "machine-learning", "ml")) -> List[Job]:
        scraped_jobs: List[Job] = []
        headers = {"User-Agent": "Mozilla/5.0 (compatible; GraphOnePipeline/1.0)"}
        try:
            resp = requests.get(REMOTEOK_API, headers=headers, timeout=15)
            resp.raise_for_status()
            listings = resp.json()
        except Exception as e:
            logger.error(f"RemoteOK fetch failed: {e}")
            return scraped_jobs

        # First element is metadata, not a job — RemoteOK's own API quirk
        for item in listings[1:]:
            item_tags = [t.lower() for t in item.get("tags", [])]
            if not any(t in item_tags for t in tags):
                continue

            job_url = item.get("url")
            if not job_url or not self.dedupe_store.is_new(job_url):
                continue

            posted_at = item.get("date")  # RemoteOK gives real ISO-8601 already
            scraped_jobs.append(Job(
                schemaVersion="1.0",
                recordType="JOB",
                content=JobContent(
                    company=item.get("company", "Unknown"),
                    date=posted_at or datetime.now(timezone.utc).isoformat(),
                    is_remote=True,  # RemoteOK is remote-only by definition
                    role_family=item.get("position", "Engineering")
                )
            ))
        return scraped_jobs