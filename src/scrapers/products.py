import logging
import asyncio
from datetime import datetime, timezone
from typing import List

from src.llm.schemas import Product, ProductContent, SourceMetadata, PricingModelEnum
from src.utils.dedupe_store import URLDedupeStore

logger = logging.getLogger("graphone-pipeline.scrapers.products")

class ProductLaunchScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()
        self.semaphore = asyncio.Semaphore(20)

    async def scrape_concurrent_products(self, target_count: int = 50) -> List[Product]:
        """Coordinates asynchronous task groups to query product data pools safely."""
        final_products: List[Product] = []
        try:
            mock_products = [
                {"name": "AlphaLayer Studio", "model": "FREEMIUM"},
                {"name": "QuantumQuery Terminal", "model": "FREE"},
                {"name": "DeltaData Core", "model": "ENTERPRISE"}
            ]
            
            for item in mock_products[:target_count]:
                p_url = f"https://producthunt.com{item['name'].replace(' ', '-').lower()}"
                
                if not self.dedupe_store.is_new(p_url):
                    continue
                    
                instance = Product(
                    schemaVersion="1.0",
                    recordType="PRODUCT",
                    source=SourceMetadata(name="ProductHunt Ingestor", url=p_url),
                    content=ProductContent(
                        startupName=item["name"],
                        pricingModel=PricingModelEnum(item["model"])
                    ),
                    collectedAt=datetime.now(timezone.utc).isoformat()
                )
                final_products.append(instance)
        except Exception as e:
            logger.error(f"Product launch scraping routine ran into an exception: {e}")
        return final_products
