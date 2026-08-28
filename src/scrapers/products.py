import logging
import asyncio
from datetime import datetime
from typing import List
import aiohttp

from src.llm.schemas import Product, ProductContent, SourceMetadata, PricingModelEnum
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.products")

class ProductLaunchScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()
        self.semaphore = asyncio.Semaphore(20)

    async def scrape_concurrent_products(self, target_count: int = 50) -> List[Product]:
        final_products: List[Product] = []
        # Target verifiable static repository feeds 
        test_url = "https://githubusercontent.com"
        
        async with self.semaphore:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(test_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            for item in data[:target_count]:
                                p_url = item.get("homepage_url", "https://producthunt.com")
                                if not self.dedupe_store.is_new(p_url):
                                    continue
                                    
                                instance = Product(
                                    schemaVersion="1.0",
                                    recordType="PRODUCT",
                                    source=SourceMetadata(name="Ecosystem Directory", url=p_url),
                                    content=ProductContent(
                                        startupName=item.get("name", "Unknown Corp"),
                                        pricingModel=PricingModelEnum.FREE
                                    ),
                                    collectedAt=datetime.utcnow().isoformat()
                                )
                                final_products.append(instance)
                except Exception as e:
                    logger.debug(f"Product ingestion pass skipped: {e}")
        return final_products
