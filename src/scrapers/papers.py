import os
import time
import json
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Optional, Dict, Any
import ssl
import certifi
import requests

from src.llm.schemas import ResearchPaper, ResearchPaperContent
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.papers")

class AcademicPaperScraper:
    def __init__(self, raw_backup_path: str = "data/output/raw_papers_cache.jsonl"):
        # FIX 3: Point to the accurate XML gateway interface
        self.arxiv_base_url = "http://export.arxiv.org/api/query?"
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
    def _execute_network_request(self, url: str, is_xml: bool = False, timeout: int = 15) -> Any:
        if is_xml:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'GraphOnePipeline/1.0'})
                ssl_context = ssl.create_default_context(cafile=certifi.where())
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    return response.read().decode("utf-8")
            except Exception:
                ssl_context = ssl._create_unverified_context()
                req = urllib.request.Request(url, headers={'User-Agent': 'GraphOnePipeline/1.0'})
                with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
                    return response.read().decode("utf-8")
        else:
            headers = {'User-Agent': 'GraphOnePipeline/1.0'}
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code == 429:
                raise RuntimeError("API Rate Limit Hit (429)")
            return response

    def _fetch_github_stars(self, repo_url: str) -> int:
        if not repo_url or "github.com" not in repo_url.lower():
            return 0
        try:
            cleaned_path = repo_url.rstrip("/").split("github.com/")[-1]
            parts = cleaned_path.split("/")
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]
                # FIX 5: Repair string structure
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                headers = {"User-Agent": "GraphOne-Intelligence-Pipeline-Bot"}
                res = requests.get(api_url, headers=headers, timeout=5)
                if res.status_code == 200:
                    return int(res.json().get("stargazers_count", 0))
        except Exception as e:
            logger.debug(f"GitHub stars verification failed for {repo_url}: {e}")
        return 0

    def _find_code_repository(self, title: str) -> Optional[str]:
        try:
            # FIX 6: Target the formal search endpoint 
            encoded_title = urllib.parse.quote(title)
            url = f"{self.pwc_search_url}?q={encoded_title}"
            res = self._execute_network_request(url, is_xml=False, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results and isinstance(results, list):
                    paper_data = results[0].get("paper", {})
                    repo_url = paper_data.get("repository", {}).get("url")
                    if repo_url:
                        return repo_url
        except Exception as e:
            logger.debug(f"PapersWithCode correlation skipped for '{title[:30]}': {e}")
        return None

    def scrape_bulk_papers(self, target_count: int = 100, page_size: int = 50) -> List[ResearchPaper]:
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
                
                # FIX 4: Correct the Atom XML Syndication Format Namespace
                ns = {"atom": "http://www.w3.org/2005/Atom"}
                entries = root.findall("atom:entry", ns)
                
                if not entries:
                    break
                    
                for entry in entries:
                    if len(final_validated_models) >= target_count:
                        break
                        
                    title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                    arxiv_url = entry.find("atom:id", ns).text.strip()
                    published_date = entry.find("atom:published", ns).text.strip()
                    authors = [a.find("atom:name", ns).text.strip() for a in entry.findall("atom:author", ns)]
                    
                    self._stream_append_to_jsonl({"title": title, "arxiv_url": arxiv_url})
                    git_url = self._find_code_repository(title)
                    star_count = self._fetch_github_stars(git_url)
                    
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
                
                current_start += page_size
                time.sleep(2.0)
                
            except Exception as e:
                logger.error(f"Error processing arXiv block chunk: {e}")
                break

        return final_validated_models
