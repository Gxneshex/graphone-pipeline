import os
import time
import json
import logging
import urllib.request
import urllib.parse
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
import ssl
import certifi
import requests
from bs4 import BeautifulSoup
import concurrent.futures

from src.llm.schemas import ResearchPaper, ResearchPaperContent
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.papers")

class AcademicPaperScraper:
    def __init__(self, raw_backup_path: str = "data/output/raw_papers_cache.jsonl"):
        self.arxiv_base_url = "https://export.arxiv.org/api/query?"
        self.pwc_search_url = "https://paperswithcode.com/api/v1/search/"
        self.raw_backup_path = raw_backup_path
        
        dir_name = os.path.dirname(self.raw_backup_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    def _stream_append_to_jsonl(self, data_dict: Dict[str, Any]):
        try:
            with open(self.raw_backup_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data_dict, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed writing raw line cache stream to disk: {e}")

    @retry_with_backoff(retries=4, base_delay=3.0, max_delay=30.0)
    def _execute_network_request(self, url: str, is_xml: bool = False, timeout: int = 30) -> Any:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=timeout)
        if response.status_code == 429:
            raise RuntimeError("API Rate Limit Hit (429)")
        if is_xml:
            return response.text
        return response

    def _fetch_github_stars(self, repo_url: str) -> int:
        if not repo_url or "github.com" not in repo_url.lower():
            return 0
        try:
            cleaned_path = repo_url.rstrip("/").split("github.com/")[-1]
            parts = cleaned_path.split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                res = requests.get(api_url, headers=headers, timeout=3)
                if res.status_code == 200:
                    return int(res.json().get("stargazers_count", 0))
        except Exception as e:
            logger.debug(f"GitHub stars verification failed for {repo_url}: {e}")
        return 0

    def _find_code_repository(self, title: str, arxiv_url: Optional[str] = None) -> Optional[str]:
        if not title:
            return None

        clean_title = re.sub(r'[^a-zA-Z0-9\s]', ' ', title).strip()
        words = [w for w in clean_title.split() if len(w) > 2]
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

        # Query GitHub Search API for matching paper repository
        if words:
            try:
                short_q = ' '.join(words[:6])
                url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(short_q)}&sort=stars"
                res = requests.get(url, headers=headers, timeout=2.0)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get("items", [])
                    for top in items[:5]:
                        repo_name = top.get("name", "").lower().replace("-", " ").replace("_", " ")
                        desc = (top.get("description") or "").lower()
                        repo_words = set(repo_name.split() + desc.split())
                        matching_words = [w.lower() for w in words if w.lower() in repo_words]
                        
                        if len(matching_words) >= min(3, len(words)):
                            return top.get("html_url")
            except Exception as e:
                logger.debug(f"GitHub repository search skipped for '{title[:30]}': {e}")

        return None

    def _process_single_entry(self, entry, ns) -> ResearchPaper:
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        arxiv_url = entry.find("atom:id", ns).text.strip()
        published_date = entry.find("atom:published", ns).text.strip()
        authors = [a.find("atom:name", ns).text.strip() for a in entry.findall("atom:author", ns)]
        
        self._stream_append_to_jsonl({"title": title, "arxiv_url": arxiv_url})
        git_url = self._find_code_repository(title, arxiv_url=arxiv_url)
        star_count = self._fetch_github_stars(git_url) if git_url else 0
        
        return ResearchPaper(
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

    def scrape_bulk_papers(self, target_count: int = 1000, page_size: int = 50) -> List[ResearchPaper]:
        final_validated_models: List[ResearchPaper] = []
        current_start = 0
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
                raw_xml = self._execute_network_request(query_url, is_xml=True)
                root = ET.fromstring(raw_xml)
                
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)
                
                if not entries:
                    break
                    
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = [executor.submit(self._process_single_entry, entry, ns) for entry in entries]
                    for future in concurrent.futures.as_completed(futures):
                        if len(final_validated_models) < target_count:
                            paper_instance = future.result()
                            final_validated_models.append(paper_instance)
                
                current_start += page_size
                time.sleep(3.0)
                
            except Exception as e:
                logger.error(f"Error processing arXiv block chunk: {e}")
                time.sleep(3.0)
                continue

        return final_validated_models
