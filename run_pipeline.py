import os
import logging
from datetime import datetime, timezone
import asyncio
import pandas as pd

from src.scrapers.papers import AcademicPaperScraper
from src.scrapers.products import ProductLaunchScraper
from src.scrapers.startups import StartupDirectoryScraper
from src.scrapers.jobs import JobBoardScraper
from src.scrapers.news import TechNewsScraper
from src.utils.dedupe_store import URLDedupeStore
from src.entity_resolution.resolver import EntityResolver
from src.utils.logger import setup_global_logger

logger = setup_global_logger()

async def execute_unified_pipeline():
    logger.info("Initializing FrontierAtlas Production Data Engine...")
    output_dir = "data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    dedupe = URLDedupeStore()
    resolver = EntityResolver()
    
    # Initialize scrapers
    paper_scraper = AcademicPaperScraper()
    product_scraper = ProductLaunchScraper(dedupe_store=dedupe)
    startup_scraper = StartupDirectoryScraper(dedupe_store=dedupe)
    job_scraper = JobBoardScraper(dedupe_store=dedupe)
    news_scraper = TechNewsScraper(dedupe_store=dedupe)
    
    entity_mapping_logs = []

    # 1. Harvest Data Vectors
    logger.info("Stage 1/4: Ingesting active data streams from real sources...")
    papers = paper_scraper.scrape_bulk_papers(target_count=1000)
    products = await product_scraper.scrape_concurrent_products(target_count=1000)
    startups = startup_scraper.scrape_startups(target_count=1000)
    raw_jobs = job_scraper.scrape_jobs(target_count=1000)
    raw_news = news_scraper.scrape_news()

    # 2. Serialize Startups
    flat_startups = []
    for s in startups:
        flat_startups.append({
            "schemaVersion": s.schemaVersion, "recordType": s.recordType,
            "source_name": s.source.name, "source_url": s.source.url,
            "content_entityName": s.content.entityName, "content_employeeCount": s.content.data.employeeCount,
            "collectedAt": s.collectedAt
        })
    logger.info(f"Startups collected: {len(flat_startups)}")

    # 3. Serialize Products
    flat_products = []
    for pr in products:
        flat_products.append({
            "schemaVersion": pr.schemaVersion, "recordType": pr.recordType,
            "source_name": pr.source.name, "source_url": pr.source.url,
            "content_startupName": pr.content.startupName, "content_pricingModel": pr.content.pricingModel.value,
            "collectedAt": pr.collectedAt
        })
    logger.info(f"Products collected: {len(flat_products)}")

    # 4. Serialize Research Papers
    flat_papers = []
    for p in papers:
        resolved = resolver.resolve_company(p.content.title, threshold=0.55)
        if resolved != p.content.title:
            entity_mapping_logs.append({"raw_string": p.content.title, "canonical_entity": resolved})
            
        flat_papers.append({
            "schemaVersion": p.schemaVersion, "recordType": p.recordType,
            "content_title": p.content.title, "content_authors": ", ".join(p.content.authors),
            "content_paper_url": p.content.paper_url, "content_github_url": p.content.github_url or "",
            "content_github_stars": p.content.github_stars, "content_published_date": p.content.published_date
        })
    logger.info(f"Papers collected: {len(flat_papers)}")

    # 5. Serialize Jobs
    flat_jobs = []
    for j in raw_jobs:
        flat_jobs.append({
            "schemaVersion": j.schemaVersion, "recordType": j.recordType,
            "content_company": j.content.company, "content_date": j.content.date,
            "content_is_remote": j.content.is_remote, "content_role_family": j.content.role_family
        })
    logger.info(f"Jobs collected: {len(flat_jobs)}")

    # 6. Export to Target Clean Sheets Templates
    logger.info("Stage 4/4: Flashing all completed tables to hard drive cache...")
    pd.DataFrame(flat_startups).to_csv(f"{output_dir}/startups.csv", index=False)
    pd.DataFrame(flat_products).to_csv(f"{output_dir}/products.csv", index=False)
    pd.DataFrame(flat_papers).to_csv(f"{output_dir}/papers.csv", index=False)
    pd.DataFrame(flat_jobs).to_csv(f"{output_dir}/jobs.csv", index=False)
    pd.DataFrame(raw_news).to_csv(f"{output_dir}/news.csv", index=False)
    
    pd.DataFrame(entity_mapping_logs, columns=["raw_string", "canonical_entity"]).to_csv(
        f"{output_dir}/entity_mapping_log.csv", index=False
    )
    
    logger.info(
        f"Pipeline execution completed cleanly. Honest row counts achieved: "
        f"Startups={len(flat_startups)}, Products={len(flat_products)}, "
        f"Papers={len(flat_papers)}, Jobs={len(flat_jobs)}, News={len(raw_news)}"
    )

if __name__ == "__main__":
    asyncio.run(execute_unified_pipeline())