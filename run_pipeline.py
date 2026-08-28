import os
import logging
from datetime import datetime
import pandas as pd

# Structural module imports
from src.scrapers.papers import AcademicPaperScraper
from src.scrapers.products import ProductLaunchScraper
from src.scrapers.startups import StartupDirectoryScraper
from src.scrapers.jobs import JobBoardScraper
from src.scrapers.news import TechNewsScraper
from src.utils.dedupe_store import URLDedupeStore
from src.entity_resolution.resolver import EntityResolver
from src.utils.date_normalizer import normalize_publication_date, is_within_24_hours
from src.utils.logger import setup_global_logger

# Initialize central unified logging parameters
logger = setup_global_logger()

async def execute_unified_pipeline():
    logger.info("Initializing GraphOne / FrontierAtlas Unified Production Pipeline...")
    
    # 1. Component Setups
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    dedupe = URLDedupeStore()
    resolver = EntityResolver()
    
    # Initialize individual scraper engines
    paper_scraper = AcademicPaperScraper()
    product_scraper = ProductLaunchScraper(dedupe_store=dedupe)
    startup_scraper = StartupDirectoryScraper(dedupe_store=dedupe)
    job_scraper = JobBoardScraper(dedupe_store=dedupe)
    news_scraper = TechNewsScraper(dedupe_store=dedupe)
    
    entity_mapping_logs = []

    # 2. Execute Bulk Scrapers
    logger.info("Executing Phase I: Paginated Mass Extraction Workflows...")
    papers = paper_scraper.scrape_bulk_papers(target_count=1000)
    products = await product_scraper.scrape_concurrent_products(target_count=1000)
    startups = startup_scraper.scrape_startups()
    
    # 3. Execute Freshness Signals
    logger.info("Executing Phase II: Ingesting News and Job Freshness Streams...")
    raw_jobs = job_scraper.scrape_jobs()
    raw_news = news_scraper.scrape_news()
    
    # Apply strict 24h filters
    fresh_jobs = []
    for j in raw_jobs:
        normalized_date = normalize_publication_date(j.content.date)
        if normalized_date and is_within_24_hours(normalized_date):
            j.content.date = normalized_date
            fresh_jobs.append(j.model_dump())

    fresh_news = []
    for n in raw_news:
        normalized_date = normalize_publication_date(n.get("extracted_at"))
        if normalized_date and is_within_24_hours(normalized_date):
            n["extracted_at"] = normalized_date
            fresh_news.append(n)

    # 4. Phase IV: Corporate Entity Resolution Mapping Log Tracking
    logger.info("Executing Phase IV: Reconciling Corporate Named Entities...")
    flat_papers = []
    for p in papers:
        # Evaluate title vectors against seed startup logs
        resolved = resolver.resolve_company(p.content.title, threshold=0.55)
        if resolved != p.content.title:
            entity_mapping_logs.append({"raw_string": p.content.title, "canonical_entity": resolved})
        
        row = p.model_dump()
        row.update(row.pop("content"))  # Flatten for effortless Sheets view
        flat_papers.append(row)

    flat_products = []
    for pr in products:
        resolved = resolver.resolve_company(pr.content.startupName, threshold=0.55)
        if resolved != pr.content.startupName:
            entity_mapping_logs.append({"raw_string": pr.content.startupName, "canonical_entity": resolved})
            pr.content.startupName = resolved
            
        row = pr.model_dump()
        row.update(row.pop("content"))
        flat_products.append(row)

    # 5. Tabular Data Serialization Target Exports
    logger.info("Phase VIII: Compiling Spreadsheet tab deliverables arrays...")
    
    pd.DataFrame(flat_papers).to_csv(f"{output_dir}/papers.csv", index=False)
    pd.DataFrame(flat_products).to_csv(f"{output_dir}/products.csv", index=False)
    pd.DataFrame([s.model_dump() for s in startups]).to_csv(f"{output_dir}/startups.csv", index=False)
    if fresh_jobs: pd.DataFrame(fresh_jobs).to_csv(f"{output_dir}/jobs.csv", index=False)
    if fresh_news: pd.DataFrame(fresh_news).to_csv(f"{output_dir}/news.csv", index=False)
    pd.DataFrame(entity_mapping_logs).to_csv(f"{output_dir}/entity_mapping_log.csv", index=False)
    
    logger.info("Pipeline Execution Succeeded! All 6 CSV matrices flushed to data/output/.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(execute_unified_pipeline())
