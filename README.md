# FrontierAtlas Intelligence Ingestion Engine

A data aggregation and entity resolution pipeline that scrapes real startup, 
product, research paper, job, and news data, then structures it into a 
canonical JSON/CSV schema with entity deduplication.

## Setup & Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_pipeline.py
```

Output CSVs are written to `data/output/`: `startups.csv`, `products.csv`, 
`papers.csv`, `jobs.csv`, `news.csv`, `entity_mapping_log.csv`.

No API keys are required to run the pipeline as it currently stands — all 
scrapers hit public, unauthenticated endpoints.

## Data Sources (per category)

| Category | Source |
|---|---|
| Startups | Y Combinator's public Algolia directory index |
| Products | Product Hunt daily leaderboards + theresanaiforthat.com |
| Research Papers | Arxiv API, cross-referenced with GitHub's API for star counts |
| Jobs | RemoteOK API + Arbeitnow API |
| News | TechCrunch AI and VentureBeat AI RSS feeds (24-hour freshness filter) |

## Entity Resolution

`src/entity_resolution/resolver.py` fuzzy-matches scraped startup/product 
names against a canonical seed list (`canonical_seed.json`) to catch name 
variants (e.g. "Scale AI" → "Scale"). Matches are logged to 
`entity_mapping_log.csv`.

## Scaling to 500,000+ Records (Design)

The current implementation targets ~1,000 records per category for this 
trial. Scaling further is an infrastructure change, not a code change — see 
`architecture.pdf` for the full design, which covers:
- Distributed task queues (Kafka) partitioned by source domain
- Bloom filter + Redis-backed URL freshness tracking across distributed nodes
- PostgreSQL (structured records) + Neo4j (entity relationship graph) storage

These are architectural proposals for scale, not part of the current codebase.