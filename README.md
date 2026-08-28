# FrontierAtlas Intelligence Ingestion Engine

An event-driven data aggregation and entity resolution pipeline designed to ingest, structure, and deduplicate venture and research intelligence fields at scale.

## 🛠️ Local Verification Playbook

### 1. Initialize Sandbox
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 2. Run Ingestion Loop
```powershell
cp .env.example .env
python run_pipeline.py
```

## 🏗️ Scale Engineering Principles (500k+ Records)
* **Distributed Queues:** Discovery tasks write payload fragments to Apache Kafka clusters partitioned by source domain hash, allowing stateless consumers to scale horizontally via Kubernetes without thread blocks.
* **Freshness Safeguards:** Outbound URLs pass through a sub-2ms lookup validation stack combining a probabilistic Redis Bloom Filter with an authoritative Redis Set locked under sliding 48-hour Time-to-Live metrics.
* **Storage Topology:** Implements a multi-tier framework routing structured indexes to a PostgreSQL master cluster via indexed JSONB fields, while Neo4j maps entity dependencies.
