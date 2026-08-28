import logging
from typing import List, Dict, Any
from datetime import datetime

from src.llm.schemas import Product
from src.utils.dedupe_store import URLDedupeStore
from src.utils.retry import retry_with_backoff

logger = logging.getLogger("graphone-pipeline.scrapers.products")

class ProductLaunchScraper:
    def __init__(self, dedupe_store: URLDedupeStore = None):
        # Use provided tracking store or fall back to a default singleton instance
        self.dedupe_store = dedupe_store if dedupe_store else URLDedupeStore()

    @retry_with_backoff(retries=3, base_delay=1.5)
    def _fetch_mock_launch_feed(self) -> List[Dict[str, Any]]:
        """
        Simulates an API request or HTML parse of a product launch directory feed.
        Includes a variety of mock products to test ingestion performance.
        """
        logger.info("Polling remote product launch directories...")
        return [
            {
                "name": "AlphaLayer Studio",
                "tagline": "No-code AI workflow orchestrator for teams",
                "description": "An intuitive canvas interface to build, deploy, and monitor scalable AI agents.",
                "link": "https://alphalayer.ai",
                "platform": "ProductHunt",
                "categories": ["AI", "SaaS", "Developer Tools"],
                "upvotes": 342,
                "source": "https://producthunt.com"
            },
            {
                "name": "QuantumQuery Client",
                "tagline": "Natural language SQL terminal interface",
                "description": "Talk to your data pipeline warehouses using natural conversational commands.",
                "link": "https://quantumquery.dev",
                "platform": "YC Launch",
                "categories": ["Databases", "DevTools"],
                "upvotes": 128,
                "source": "https://ycombinator.com"
            },
            {
                "name": "AlphaLayer Studio",  # Intentional duplicate to test deduplication layer
                "tagline": "No-code AI workflow orchestrator",
                "description": "Duplicate item payload testing entity filtering routines.",
                "link": "https://alphalayer.ai",
                "platform": "ProductHunt",
                "categories": ["AI"],
                "upvotes": 345,
                "source": "https://producthunt.com"
            }
        ]

    def scrape_launches(self) -> List[Product]:
        """
        Main extraction workflow. Fetches the feed, strips out historically 
        processed landing links via the Dedupe Store, and parses clean Product schemas.
        """
        scraped_products: List[Product] = []
        
        try:
            raw_feed = self._fetch_mock_launch_feed()
            
            for item in raw_feed:
                source_url = item.get("source", "")
                
                # Enforce URL uniqueness checking across execution history
                if not self.dedupe_store.is_new(source_url):
                    logger.info(f"Skipping duplicate product listing: {item.get('name')}")
                    continue
                    
                logger.info(f"Ingesting new product entry: {item.get('name')}")
                
                # Bind target item data safely into our global structural model
                product_model = Product(
                    product_name=item.get("name"),
                    tagline=item.get("tagline"),
                    description=item.get("description"),
                    primary_link=item.get("link"),
                    launch_platform=item.get("platform"),
                    categories=item.get("categories", []),
                    upvotes=item.get("upvotes", 0),
                    source_url=source_url,
                    extracted_at=datetime.utcnow()
                )
                scraped_products.append(product_model)
                
        except Exception as e:
            logger.error(f"Encountered a breakdown in product tracking pipeline: {e}")
            
        return scraped_products
