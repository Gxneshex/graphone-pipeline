
import logging
import asyncio
from datetime import datetime, timezone
from typing import List
import aiohttp
from bs4 import BeautifulSoup

from src.llm.schemas import Product, ProductContent, SourceMetadata, PricingModelEnum
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.products")

class ProductLaunchScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()
        # Cap high concurrency to protect target from aggressive traffic blocks
        self.semaphore = asyncio.Semaphore(5)

    async def _fetch_and_parse_page(self, session: aiohttp.ClientSession, page: int) -> List[Product]:
        """Worker task to fetch an individual directory page and extract cards securely."""
        products_on_page = []
        url = f"https://theresanaiforthat.com/page/{page}/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"}
        
        async with self.semaphore:
            try:
                logger.info(f"Scraping live product page from: {url}")
                async with session.get(url, headers=headers, timeout=15) as resp:
                    if resp.status != 200:
                        logger.error(f"HTTP Error {resp.status} on page {page}")
                        return []
                    html_text = await resp.text()
            except Exception as e:
                logger.error(f"Network request failed on page {page}: {e}")
                return []

            # Parse DOM elements using BeautifulSoup4
            soup = BeautifulSoup(html_text, "html.parser")
            cards = soup.select("div.ai_link") or soup.select(".ai_card") or soup.select("li.ai_item")
            
            # Simple selector backup array to catch modern site UI iterations dynamically
            if not cards:
                cards = soup.select("a.tasks_link") or soup.select(".ai_link_new")
                
            for card in cards[:20]:
                link_tag = card if card.name == "a" else card.select_one("a")
                name_tag = card.select_one(".ai_name") or card.select_one(".name") or card
                
                if not link_tag or not name_tag:
                    continue
                    
                raw_href = link_tag.get("href", "")
                if not raw_href:
                    continue
                    
                # Fix absolute paths if necessary
                p_url = raw_href if raw_href.startswith("http") else f"https://theresanaiforthat.com{raw_href}"
                
                if not self.dedupe_store.is_new(p_url):
                    continue

                try:
                    product_instance = Product(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceMetadata(name="There's An AI For That", url=p_url),
                        content=ProductContent(
                            startupName=name_tag.get_text(strip=True)[:50],
                            pricingModel=PricingModelEnum.FREEMIUM
                        ),
                        collectedAt=datetime.now(timezone.utc).isoformat()
                    )
                    products_on_page.append(product_instance)
                except Exception as validation_err:
                    logger.debug(f"Pydantic schema skip: {validation_err}")
                    
        return products_on_page

    async def scrape_concurrent_products(self, target_count: int = 100) -> List[Product]:
        """Main execution engine firing batch workers in parallel up to target limits."""
        final_products: List[Product] = []
        # Query pages sequentially using task batches to hit your target metrics
        pages_to_query = max(1, target_count // 5)
        
        logger.info(f"Launching legitimate HTML scraper against TheresAnAIForThat over {pages_to_query} pages...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_and_parse_page(session, p) for p in range(1, pages_to_query + 1)]
            results = await asyncio.gather(*tasks)
            
            for page_list in results:
                for item in page_list:
                    if len(final_products) < target_count:
                        final_products.append(item)
                        
        return final_products