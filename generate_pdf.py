"""
generate_pdf.py
Generates a structured, production-grade 2-page 'architecture.pdf' document 
for Phase VI of the FrontierAtlas evaluation brief with precise layout alignment.
"""

import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

def create_architecture_pdf():
    pdf_path = "architecture.pdf"
    print(f"Compiling aligned engineering blueprint documentation into {pdf_path}...")
    
    with PdfPages(pdf_path) as pdf:
        # ---------------------------------------------------------
        # PAGE 1: COVER, TITLE & VISUAL SYSTEM DIAGRAM
        # ---------------------------------------------------------
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')
        
        # Page Title Block
        ax.text(0.5, 0.95, "FrontierAtlas Ingestion Pipeline Architecture", 
                fontsize=18, weight='bold', ha='center', color='#1a365d')
        ax.text(0.5, 0.92, "Technical Production Design Document — Phase VI", 
                fontsize=12, style='italic', ha='center', color='#4a5568')
        
        # Section Header
        ax.text(0.05, 0.86, "1. Visual Infrastructure Flowchart Graph Map", 
                fontsize=14, weight='bold', color='#2c5282')
        
        # Styled Component Box Props
        bbox_props = dict(boxstyle="round,pad=0.5", fc="#ebf8ff", ec="#3182ce", lw=1.5)
        queue_props = dict(boxstyle="round,pad=0.6", fc="#faf5ff", ec="#805ad5", lw=1.5)
        worker_props = dict(boxstyle="round,pad=0.5", fc="#feebc8", ec="#dd6b20", lw=1.5)
        llm_props = dict(boxstyle="round,pad=0.5", fc="#e6fffa", ec="#319795", lw=1.5)
        storage_props = dict(boxstyle="round,pad=0.6", fc="#f7fafc", ec="#4a5568", lw=1.5)
        
        # Component Box Coordinate Nodes
        ax.text(0.25, 0.76, "Discovery Crawlers\n& Sitemap Monitors", bbox=bbox_props, ha='center', va='center', fontsize=10)
        ax.text(0.75, 0.76, "Tech News Streams\n& Job Board Feeds", bbox=bbox_props, ha='center', va='center', fontsize=10)
        
        ax.text(0.5, 0.64, "Distributed Messaging Ingestion Cluster\n[Apache Kafka / AWS SQS]", bbox=queue_props, ha='center', va='center', fontsize=11, weight='bold')
        
        ax.text(0.5, 0.52, "Stateless Horizontal Worker Pool\n[Concurrent asyncio / Async Playwright Drivers]", bbox=worker_props, ha='center', va='center', fontsize=10)
        
        ax.text(0.5, 0.38, "Multi-Tier LLM Resilient Extraction Cascade\n[Gemini 2.5 Flash -> Groq Llama 3 -> DeepSeek Chat]", bbox=llm_props, ha='center', va='center', fontsize=10)
        
        ax.text(0.25, 0.24, "Authoritative Relational Layer\n[PostgreSQL System Layout]", bbox=storage_props, ha='center', va='center', fontsize=9)
        ax.text(0.75, 0.24, "Analytical Context Graphs\n[Neo4j Dependency Maps]", bbox=storage_props, ha='center', va='center', fontsize=9)
        
        # Drawing Connective Flow Arrows
        arrow_props = dict(facecolor='#4a5568', edgecolor='#4a5568', shrink=0.08, width=1.5, headwidth=6)
        ax.annotate('', xy=(0.5, 0.68), xytext=(0.25, 0.72), arrowprops=arrow_props)
        ax.annotate('', xy=(0.5, 0.68), xytext=(0.75, 0.72), arrowprops=arrow_props)
        ax.annotate('', xy=(0.5, 0.56), xytext=(0.5, 0.60), arrowprops=arrow_props)
        ax.annotate('', xy=(0.5, 0.42), xytext=(0.5, 0.48), arrowprops=arrow_props)
        ax.annotate('', xy=(0.25, 0.28), xytext=(0.5, 0.34), arrowprops=arrow_props)
        ax.annotate('', xy=(0.75, 0.28), xytext=(0.5, 0.34), arrowprops=arrow_props)
        
        # Page Number Footer
        ax.text(0.5, 0.04, "Page 1 of 2", fontsize=10, ha='center', color='#718096')
        pdf.savefig(fig)
        plt.close()
        
        # ---------------------------------------------------------
        # PAGE 2: ALIGNED STRATEGY & PRODUCTION TEXT DETAILS
        # ---------------------------------------------------------
        fig, ax = plt.subplots(figsize=(8.5, 11))
        ax.axis('off')
        
        # Page Heading
        ax.text(0.05, 0.95, "Pipeline Scaling & Resiliency Blueprint Playbook", fontsize=16, weight='bold', color='#1a365d')
        
        # Plot Section 2
        ax.text(0.05, 0.89, "2. Horizontal Scaling Strategy (Goal: 500,000+ Records)", fontsize=12, weight='bold', color='#2c5282')
        sec2_text = (
            "• Decoupled Architecture: Ingestion feeds are cleanly decoupled from processing tasks using an\n"
            "  event-driven messaging topology via Apache Kafka topics partitioned by a hash of the source domain.\n"
            "• Stateless Processing: Containerized consumer nodes scale horizontally using Kubernetes HPA\n"
            "  profiles, avoiding vertical hardware performance degradation barriers during ingestion spikes."
        )
        ax.text(0.05, 0.80, sec2_text, fontsize=10, linespacing=1.6, color='#2d3748')
        
        # Plot Section 3
        ax.text(0.05, 0.72, "3. Mitigation Strategy for Payload (413) & Rate Limits (429)", fontsize=12, weight='bold', color='#2c5282')
        sec3_text = (
            "• Context Window Overflows (HTTP 413): Text streams go through token-aware chunking routines\n"
            "  capped strictly at 80% of a model's limits, reserving the remaining space for schemas and self-correction.\n"
            "• Thundering Herds (HTTP 429): Intercepted errors invoke an exponential backoff with full randomized\n"
            "  jitter parameters: Delay = min(Max_Delay, Base_Delay * 2^attempt) + Uniform_Jitter.\n"
            "• Multi-Tier Cascades: Automated error failovers jump from Gemini Flash directly to Groq or DeepSeek."
        )
        ax.text(0.05, 0.60, sec3_text, fontsize=10, linespacing=1.6, color='#2d3748')
        
        # Plot Section 4
        ax.text(0.05, 0.52, "4. Distributed Freshness & Duplicate Elimination", fontsize=12, weight='bold', color='#2c5282')
        sec4_text = (
            "• Probabilistic Filtering (Tier 1): Active lookups check incoming URLs against distributed Redis\n"
            "  Bloom Filters instantly, dropping duplicate assets with less than 2ms network latency.\n"
            "• Authoritative Locking (Tier 2): New targets are verified against a deterministic Redis Set\n"
            "  equipped with a strict 48-hour sliding Time-to-Live (TTL) matrix to eliminate processing deadlocks."
        )
        ax.text(0.05, 0.42, sec4_text, fontsize=10, linespacing=1.6, color='#2d3748')
        
        # Plot Section 5
        ax.text(0.05, 0.34, "5. Production Storage Framework Topology", fontsize=12, weight='bold', color='#2c5282')
        sec5_text = (
            "• Transactional Relational Database (PostgreSQL): Securely parses structural Pydantic tables into indexes\n"
            "  using highly optimized transactional native JSONB column query layouts.\n"
            "• Analytical Graph Network (Neo4j): Stores real relationships across ecosystem primitives seamlessly\n"
            "  (e.g., [Founder] -> CO_FOUNDED -> [Startup] -> LAUNCHED -> [Product])."
        )
        ax.text(0.05, 0.24, sec5_text, fontsize=10, linespacing=1.6, color='#2d3748')
        
        # Page Number Footer
        ax.text(0.5, 0.04, "Page 2 of 2", fontsize=10, ha='center', color='#718096')
        pdf.savefig(fig)
        plt.close()

    print("Success! Your aligned 'architecture.pdf' deliverable has been fully generated.")

if __name__ == "__main__":
    create_architecture_pdf()
