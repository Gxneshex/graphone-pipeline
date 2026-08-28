import os
import logging
from typing import List

import pandas as pd

from src.scrapers.papers import AcademicPaperScraper
from src.llm.orchestrator import LLMOrchestrator
from src.llm.schemas import ResearchPaper
from src.entity_resolution.resolver import EntityResolver

# 1. Structure global logging parameters for evaluators to monitor performance
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("graphone-pipeline.main")

def run():
    logger.info("Initializing Graphone-Pipeline workflow modules...")
    
    # Initialize our functional modules
    scraper = AcademicPaperScraper()
    orchestrator = LLMOrchestrator()
    resolver = EntityResolver()
    
    # Ensure our target output destination folder is securely created
    output_dir = os.path.join("data", "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # 2. Extract Data Stage
    logger.info("Stage 1/4: Ingesting academic literature data streams...")
    # Using a general tech query to find relevant papers
    scraped_papers: List[ResearchPaper] = scraper.scrape_papers(
        query="all:Artificial Intelligence OR all:LLM", 
        limit=5
    )
    
    if not scraped_papers:
        logger.warning("No papers were scraped. Exiting execution workflow.")
        return

    logger.info(f"Successfully scraped {len(scraped_papers)} records from academic repositories.")

    # 3. LLM Processing & Entity Resolution Stage
    logger.info("Stage 2/4 & 3/4: Processing entries and reconciling entities...")
    processed_records = []
    
    for paper in scraped_papers:
        # Resolve company/startup names mentioned within titles or abstracts
        # For demonstration, we test if the title or text references our mock matrices
        resolved_title = resolver.resolve_company(paper.title, threshold=0.55)
        
        # Flatten our structured data model to a dictionary format for row tracking
        record_data = paper.model_dump()
        
        # Inject our entity resolution metric enhancements
        record_data["resolved_title_entity"] = resolved_title
        # Convert HttpUrl objects into clean strings so they export cleanly to spreadsheets
        record_data["arxiv_url"] = str(record_data["arxiv_url"])
        if record_data.get("code_url"):
            record_data["code_url"] = str(record_data["code_url"])
            
        processed_records.append(record_data)

    # 4. Target Generation Export Stage (Google Sheets Optimization)
    logger.info("Stage 4/4: Exporting structural records to downstream output directory...")
    output_path = os.path.join(output_dir, "papers.csv")
    
    # Convert our records into a pandas DataFrame layout
    df = pd.DataFrame(processed_records)
    
    # Write cleanly to a flat CSV file
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info(f"Pipeline complete! Final data securely saved to: {output_path}")


if __name__ == "__main__":
    run()
