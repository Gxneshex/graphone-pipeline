import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Optional
import requests

from src.llm.schemas import ResearchPaper
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.papers")

class AcademicPaperScraper:
    def __init__(self):
        self.arxiv_base_url = "http://export.arxiv.org/api/query?"
        self.pwc_base_url = "https://paperswithcode.com"

    @retry_with_backoff(retries=3, base_delay=2.0)
    def _fetch_arxiv_xml(self, search_query: str, max_results: int) -> str:
        """Helper to fetch raw XML string from the arXiv endpoint."""
        params = {
            "search_query": search_query,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        url = self.arxiv_base_url + urllib.parse.urlencode(params)
        logger.info(f"Querying arXiv API: {url}")
        
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.read().decode("utf-8")

    def _get_pwc_code_url(self, title: str) -> Optional[str]:
        """Queries Papers with Code API to find an associated open-source repository."""
        try:
            # Query PWC API searching by paper title string
            pwc_search_url = "https://paperswithcode.com"
            response = requests.get(pwc_search_url, params={"q": title}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    # Snag the first match's code repository if linked
                    paper_id = results[0].get("id")
                    # Fetch code links associated directly with this paper ID
                    code_res = requests.get(f"{pwc_search_url}{paper_id}/repositories/", timeout=10)
                    if code_res.status_code == 200:
                        code_data = code_res.json()
                        repos = code_data.get("results", [])
                        if repos:
                            return repos[0].get("url")
        except Exception as e:
            logger.debug(f"PWC lookup skipped or failed for '{title}': {e}")
        return None

    def scrape_papers(self, query: str = "all:AI OR all:Machine Learning", limit: int = 5) -> List[ResearchPaper]:
        """
        Main execution workflow. Scrapes latest papers, parses the Atom XML feeds,
        decorates entries with GitHub repos from Papers with Code, and validates using Pydantic.
        """
        scraped_entries: List[ResearchPaper] = []
        
        try:
            raw_xml = self._fetch_arxiv_xml(query, limit)
            root = ET.fromstring(raw_xml)
            
            # Atom XML standard namespace parsing
            ns = {
                "atom": "http://w3.org",
                "arxiv": "http://arxiv.org/schemas/atom"
            }
            
            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
                abstract = entry.find("atom:summary", ns).text.strip()
                arxiv_url = entry.find("atom:id", ns).text.strip()
                published_date = entry.find("atom:published", ns).text.strip()
                
                # Extract all contributing authors
                authors = [author.find("atom:name", ns).text.strip() for author in entry.findall("atom:author", ns)]
                
                # Fetch primary domain category (e.g. cs.LG, cs.AI)
                category_elem = entry.find("arxiv:primary_category", ns)
                primary_category = category_elem.attrib.get("term") if category_elem is not None else "unknown"
                
                logger.info(f"Processing scraped paper: {title[:40]}...")
                
                # Cross-reference with Papers with Code for git repository attachment
                code_url = self._get_pwc_code_url(title)
                
                # Construct data through our consistent structural template
                paper_model = ResearchPaper(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    arxiv_url=arxiv_url,
                    code_url=code_url,
                    published_date=published_date,
                    primary_category=primary_category
                )
                scraped_entries.append(paper_model)
                
        except Exception as global_err:
            logger.error(f"Failed to execute entire paper scraping routine: {global_err}")
            
        return scraped_entries
