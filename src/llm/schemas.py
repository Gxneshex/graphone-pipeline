"""
src/llm/schemas.py
Strict canonical Pydantic structures mapping directly to the 
FrontierAtlas Intelligence Graph evaluation specification.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

# --- Common Reusable Sub-Models ---
class SourceMetadata(BaseModel):
    name: str = Field(..., description="Name of the source site.")
    url: str = Field(..., description="Original source URL path.")

# --- Product Specific Enums ---
class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"

# ==============================================================================
# 1. STARTUP SCHEMA
# ==============================================================================
class StartupContentData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees if available.")

class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name.")
    data: StartupContentData = Field(default_factory=StartupContentData)

class Startup(BaseModel):
    schemaVersion: str = Field("1.0", description="Versioning for the schema.")
    recordType: str = Field("STARTUP", literal=True)
    source: SourceMetadata
    content: StartupContent
    collectedAt: str = Field(..., description="ISO-8601 format compilation timestamp.")

# ==============================================================================
# 2. PRODUCT SCHEMA
# ==============================================================================
class ProductContent(BaseModel):
    startupName: str = Field(..., description="Canonical startup name.")
    pricingModel: PricingModelEnum = Field(..., description="FREE, FREEMIUM, PAID, or ENTERPRISE.")

class Product(BaseModel):
    schemaVersion: str = Field("1.0", description="Versioning for the schema.")
    recordType: str = Field("PRODUCT", literal=True)
    source: SourceMetadata
    content: ProductContent
    collectedAt: str = Field(..., description="ISO-8601 format compilation timestamp.")

# ==============================================================================
# 3. RESEARCH PAPER SCHEMA
# ==============================================================================
class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper.")
    authors: List[str] = Field(..., description="List of author names.")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page.")
    github_url: Optional[str] = Field(None, description="Link to the associated code repository.")
    github_stars: Optional[int] = Field(0, description="Current number of stars on the GitHub repository.")
    published_date: str = Field(..., description="ISO-8601 publication date.")

class ResearchPaper(BaseModel):
    schemaVersion: str = Field("1.0", description="Versioning for the schema.")
    recordType: str = Field("RESEARCH_PAPER", literal=True)
    content: ResearchPaperContent

# ==============================================================================
# 4. JOB SCHEMA
# ==============================================================================
class JobContent(BaseModel):
    company: str = Field(..., description="Canonical company name.")
    date: str = Field(..., description="ISO-8601 publication date.")
    is_remote: bool = Field(..., description="Remote eligibility status switch.")
    role_family: str = Field(..., description="Functional category (e.g., 'Engineering').")

class Job(BaseModel):
    schemaVersion: str = Field("1.0", description="Versioning for the schema.")
    recordType: str = Field("JOB", literal=True)
    content: JobContent

# ==============================================================================
# 5. NEWS SUMMARY SCHEMA
# ==============================================================================
class NewsArticleAnalysis(BaseModel):
    summary: str = Field(..., description="Executive summary of the news article.")
    key_facts: List[str] = Field(default_factory=list, description="Key extracted facts from the article.")

