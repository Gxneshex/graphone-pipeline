"""
src/scrapers/jobs.py
Extracts real engineering and tech job postings directly via RemoteOK's official REST API 
and Arbeitnow's open jobs API.
"""

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

    def scrape_jobs(self, target_count: int = 1000) -> List[Job]:
        """Scrapes real job postings from RemoteOK API and Arbeitnow API."""
        scraped_jobs: List[Job] = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"}

        # 1. Scrape RemoteOK JSON API
        try:
            logger.info("Ingesting active listings from RemoteOK API...")
            res = requests.get("https://remoteok.com/api", headers=headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json()
                # Skip first item if it contains metadata/legal disclosure
                items = data[1:] if len(data) > 1 and isinstance(data[0], dict) and "legal" in data[0] else data
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                        
                    job_url = item.get("url", "").strip()
                    if not job_url:
                        job_id = item.get("id")
                        if job_id:
                            job_url = f"https://remoteok.com/remote-jobs/{job_id}"
                            
                    if not job_url or not self.dedupe_store.is_new(job_url):
                        continue
                        
                    company = item.get("company", "").strip() or "Tech Venture"
                    pub_date = item.get("date", "").strip()
                    if not pub_date:
                        epoch = item.get("epoch")
                        if epoch:
                            pub_date = datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat()
                        else:
                            continue
                            
                    position = item.get("position", "")
                    tags = item.get("tags", [])
                    role_family = "Engineering"
                    if any(t in str(tags).lower() for t in ["ai", "machine learning", "data", "python"]):
                        role_family = "AI / Data Engineering"

                    scraped_jobs.append(Job(
                        schemaVersion="1.0",
                        recordType="JOB",
                        content=JobContent(
                            company=company,
                            date=pub_date,
                            is_remote=True,
                            role_family=role_family
                        )
                    ))
            else:
                logger.warning(f"RemoteOK API returned status code {res.status_code}")
        except Exception as e:
            logger.error(f"RemoteOK scraper encountered an error: {e}")

        # 2. Scrape Arbeitnow API as second real data source
        try:
            logger.info("Ingesting active listings from Arbeitnow API...")
            res = requests.get("https://www.arbeitnow.com/api/job-board-api", headers=headers, timeout=12)
            
            if res.status_code == 200:
                data = res.json().get("data", [])
                for item in data:
                    if len(scraped_jobs) >= target_count:
                        break
                        
                    job_url = item.get("url", "").strip()
                    if not job_url or not self.dedupe_store.is_new(job_url):
                        continue
                        
                    company = item.get("company_name", "").strip() or "Tech Enterprise"
                    created_at = item.get("created_at")
                    if isinstance(created_at, int):
                        pub_date = datetime.fromtimestamp(created_at, tz=timezone.utc).isoformat()
                    elif isinstance(created_at, str) and created_at:
                        pub_date = created_at
                    else:
                        continue
                        
                    role_family = "Engineering"
                    tags = item.get("tags", [])
                    if any(t in str(tags).lower() for t in ["ai", "data", "python", "machine learning"]):
                        role_family = "AI / Data Engineering"
                        
                    scraped_jobs.append(Job(
                        schemaVersion="1.0",
                        recordType="JOB",
                        content=JobContent(
                            company=company,
                            date=pub_date,
                            is_remote=item.get("remote", True),
                            role_family=role_family
                        )
                    ))
        except Exception as e:
            logger.error(f"Arbeitnow scraper encountered an error: {e}")

        logger.info(f"Successfully collected {len(scraped_jobs)} real job listings.")
        return scraped_jobs
