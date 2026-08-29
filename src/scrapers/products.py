"""
src/scrapers/products.py
Scrapes real product launch entries from Product Hunt leaderboards and TheresAnAIForThat.
"""

import logging
import asyncio
import re
from datetime import datetime, timezone, date, timedelta
from typing import List, Set
import aiohttp
from bs4 import BeautifulSoup

from src.llm.schemas import Product, ProductContent, SourceMetadata, PricingModelEnum
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.products")

class ProductLaunchScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()
        self.semaphore = asyncio.Semaphore(10)

    async def _fetch_ph_leaderboard(self, session: aiohttp.ClientSession, url: str) -> List[tuple]:
        """Fetch a single Product Hunt daily leaderboard page."""
        results = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"}
        async with self.semaphore:
            try:
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        for a in soup.find_all("a", href=True):
                            href = a.get("href", "")
                            if href.startswith("/products/"):
                                clean_path = href.split("?")[0].rstrip("/")
                                slug = clean_path.split("/products/")[-1]
                                if not slug:
                                    continue
                                full_url = f"https://www.producthunt.com/products/{slug}"
                                title = a.get_text(strip=True) or slug.replace("-", " ").title()
                                results.append((title, full_url, "Product Hunt"))
            except Exception as e:
                logger.debug(f"Error fetching Product Hunt URL {url}: {e}")
        return results

    async def scrape_concurrent_products(self, target_count: int = 1000) -> List[Product]:
        """Harvests authentic product listings from Product Hunt and TheresAnAIForThat."""
        final_products: List[Product] = []
        seen_urls: Set[str] = set()

        logger.info(f"Ingesting real product listings (Target: {target_count})...")

        # 1. Scrape theresanaiforthat.com homepage items
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GraphOnePipeline/1.0"}
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get("https://theresanaiforthat.com/", headers=headers, timeout=12) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, "html.parser")
                        for a in soup.find_all("a", href=True):
                            href = a.get("href", "")
                            if "/ai/" in href:
                                full_url = href.split("?")[0]
                                if not full_url.startswith("http"):
                                    full_url = f"https://theresanaiforthat.com{full_url}"
                                name = a.get_text(strip=True)
                                if not name or len(name) < 2 or "There's An AI" in name:
                                    slug = full_url.rstrip("/").split("/")[-1]
                                    name = slug.replace("-", " ").title()
                                
                                if full_url not in seen_urls and self.dedupe_store.is_new(full_url):
                                    seen_urls.add(full_url)
                                    final_products.append(Product(
                                        schemaVersion="1.0",
                                        recordType="PRODUCT",
                                        source=SourceMetadata(name="There's An AI For That", url=full_url),
                                        content=ProductContent(
                                            startupName=name,
                                            pricingModel=PricingModelEnum.FREEMIUM
                                        ),
                                        collectedAt=datetime.now(timezone.utc).isoformat()
                                    ))
            except Exception as e:
                logger.error(f"Error scraping theresanaiforthat.com: {e}")

            logger.info(f"Collected {len(final_products)} products from TheresAnAIForThat.")

            # 2. Concurrently fetch Product Hunt daily leaderboards for past 45 days
            today = date.today()
            leaderboard_urls = [
                f"https://www.producthunt.com/leaderboard/daily/{(today - timedelta(days=i)).year}/{(today - timedelta(days=i)).month}/{(today - timedelta(days=i)).day}"
                for i in range(75)
            ]

            tasks = [self._fetch_ph_leaderboard(session, url) for url in leaderboard_urls]
            batch_results = await asyncio.gather(*tasks)

            for page_results in batch_results:
                for title, full_url, source_name in page_results:
                    if len(final_products) >= target_count:
                        break
                    if full_url in seen_urls:
                        continue
                    if not self.dedupe_store.is_new(full_url):
                        continue

                    seen_urls.add(full_url)
                    final_products.append(Product(
                        schemaVersion="1.0",
                        recordType="PRODUCT",
                        source=SourceMetadata(name=source_name, url=full_url),
                        content=ProductContent(
                            startupName=title,
                            pricingModel=PricingModelEnum.FREEMIUM
                        ),
                        collectedAt=datetime.now(timezone.utc).isoformat()
                    ))

        logger.info(f"Successfully collected {len(final_products)} real products.")
        return final_products