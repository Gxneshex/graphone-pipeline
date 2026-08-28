"""
src/scrapers/papers.py
A paginated, high-volume academic paper scraper. Harvests real entries from the 
arXiv API, maps official repositories through Papers with Code, correlates live 
GitHub star metrics, and stream-flushes data to disk in JSONL format.
"""

import os
import time
import json
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any

# Added these two core modules to override the local Windows/Python SSL certificate lock
import ssl
import certifi

import requests
from src.llm.schemas import ResearchPaper, ResearchPaperContent
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.papers")

class AcademicPaperScraper:
    def __init__(self, raw_backup_path: str = "data/output/raw_papers_cache.jsonl"):
        self.arxiv_base_url = "http://arxiv.org?"
        self.pwc_search_url = "https://paperswithcode.com"
        self.raw_backup_path = raw_backup_path
        
        # Ensure our target pipeline directory exists right away
        dir_name = os.path.dirname(self.raw_backup_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _stream_append_to_jsonl(self, data_dict: Dict[str, Any]):
        """Streams a single raw payload line safely onto disk to safeguard historical progress."""
        try:
            with open(self.raw_backup_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data_dict, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed writing raw line cache stream to disk: {e}")

    @retry_with_backoff(retries=4, base_delay=3.0, max_delay=30.0)
    def _execute_network_request(self, url: str, is_xml: bool = False, timeout: int = 15) -> Any:
        """Executes a network request with retry capabilities to protect against 429 exceptions."""
        if is_xml:
            # Overrides the local system network stack with verified certifi root authorities
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            with urllib.request.urlopen(url, timeout=timeout, context=ssl_context) as response:
                return response.read().decode("utf-8")
        else:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 429:
                raise RuntimeError("API Rate Limit Hit (429)")
            return response

    def _fetch_github_stars(self, repo_url: str) -> int:
        """Parses git paths and queries GitHub's REST API for stargazers counts."""
        if not repo_url or "github.com" not in repo_url.lower():
            return 0
        try:
            cleaned_path = repo_url.rstrip("/").split("github.com/")[-1]
            parts = cleaned_path.split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                api_url = f"https://github.com{owner}/{repo}"
                
                # Setup basic headers to access public GitHub telemetry
                headers = {"User-Agent": "GraphOne-Intelligence-Pipeline-Bot"}
                res = requests.get(api_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    return int(res.json().get("stargazers_count", 0))
        except Exception as e:
            logger.debug(f"GitHub telemetry lookup skipped for {repo_url}: {e}")
        return 0

    def _find_code_repository(self, title: str) -> Optional[str]:
        """Queries the official Papers with Code directory to find repository matches."""
        try:
            encoded_title = urllib.parse.quote(title)
            url = f"{self.pwc_search_url}?q={encoded_title}"
            res = self._execute_network_request(url, is_xml=False, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results and isinstance(results, list):
                    # Check first matching asset item index block
                    paper_id = results[0].get("id")
                    if paper_id:
                        repo_url = f"{self.pwc_search_url}{paper_id}/repositories/"
                        repo_res = requests.get(repo_url, timeout=10)
                        if repo_res.status_code == 200:
                            repos = repo_res.json().get("results", [])
                            if repos:
                                return repos[0].get("url")
        except Exception as e:
            logger.debug(f"PapersWithCode correlation skipped for '{title[:30]}': {e}")
        return None

    def scrape_bulk_papers(self, target_count: int = 1000, page_size: int = 250) -> List[ResearchPaper]:
        """
        Executes highly paginated search fetches, pulling categories (cs.AI, cs.LG) 
        until reaching the target layout count constraints.
        """
        final_validated_models: List[ResearchPaper] = []
        current_start = 0
        
        # Target massive core domains for high matching densities
        search_query = "cat:cs.AI OR cat:cs.LG"
        
        logger.info(f"Initiating bulk extraction. Target: {target_count} records via {page_size}-item chunks...")
        
        while len(final_validated_models) < target_count:
            params = {
                "search_query": search_query,
                "start": current_start,
                "max_results": page_size,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }
            query_url = self.arxiv_base_url + urllib.parse.urlencode(params)
            
            try:
                logger.info(f"Querying page chunk starting at row index offset: {current_start}")
                raw_xml = self._execute_network_request(query_url, is_xml=True)
                
                root = ET.fromstring(raw_xml)
                ns = {"atom": "http://w3.org"}
                entries = root.findall("atom:entry", ns)
                
                if not entries:
                    logger.warning("Empty records feed received. Terminating lookup thread cascade loops.")
                    break
                    
                for entry in entries:
                    if len(final_validated_models) >= target_count:
                        break
                        
                    title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    arxiv_url = entry.find("atom:id", ns).text.strip()
                    published_date = entry.find("atom:published", ns).text.strip()
                    authors = [a.find("atom:name", ns).text.strip() for a in entry.findall("atom:author", ns)]
                    
                    # 1. Immediately backup raw data to prevent loss in mid-run crashes
                    raw_payload = {
                        "title": title, "arxiv_url": arxiv_url, 
                        "published_date": published_date, "authors": authors,
                        "scraped_at": datetime.utcnow().isoformat()
                    }
                    self._stream_append_to_jsonl(raw_payload)
                    
                    # 2. Cross-reference repository components
                    git_url = self._find_code_repository(title)
                    star_count = self._fetch_github_stars(git_url) if git_url else 0
                    
                    # 3. Shape structures tightly into the target validation layout
                    paper_instance = ResearchPaper(
                        schemaVersion="1.0",
                        recordType="RESEARCH_PAPER",
                        content=ResearchPaperContent(
                            title=title,
                            authors=authors,
                            paper_url=arxiv_url,
                            github_url=git_url,
                            github_stars=star_count,
                            published_date=published_date
                        )
                    )
                    final_validated_models.append(paper_instance)
                
                # Respect arXiv terms of service by adding a polite delay between pages
                logger.info(f"Progress checkpoint: Packed {len(final_validated_models)} / {target_count} models.")
                current_start += page_size
                time.sleep(3.0)
                
            except Exception as e:
                logger.error(f"Critical error on query offset chunk row {current_start}: {e}")
                time.sleep(5.0)  # Cool down before retrying the next batch
                break

        return final_validated_models
