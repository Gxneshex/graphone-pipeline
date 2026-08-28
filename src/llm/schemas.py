from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Startup(BaseModel):
    """Schema for tracking and evaluating early-stage companies."""
    company_name: str = Field(..., description="The official name of the startup company.")
    website: Optional[HttpUrl] = Field(None, description="Main landing page URL of the company.")
    one_liner: str = Field(..., description="A clear, concise one-sentence description of the startup.")
    description: Optional[str] = Field(None, description="Detailed background or product overview of the company.")
    industries: List[str] = Field(default_factory=list, description="List of target markets or industries (e.g., AI, SaaS, FinTech).")
    funding_stage: Optional[str] = Field(None, description="Current funding stage (e.g., Pre-seed, Seed, Series A, Bootstrapped).")
    location: Optional[str] = Field(None, description="Headquarters city, state, or country.")
    source_url: HttpUrl = Field(..., description="The direct URL where this startup profile was parsed.")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of when the record was processed.")


class Product(BaseModel):
    """Schema for tracking product launches across platform directories."""
    product_name: str = Field(..., description="The exact name of the product.")
    tagline: str = Field(..., description="The pitch or tagline used during launch.")
    description: Optional[str] = Field(None, description="Full description of capabilities and features.")
    primary_link: HttpUrl = Field(..., description="The main URL pointing to the product site or download path.")
    launch_platform: str = Field(..., description="The directory source platform (e.g., ProductHunt, YC Launch, AppSumo).")
    categories: List[str] = Field(default_factory=list, description="Tags or classifications assigned to the product.")
    upvotes: Optional[int] = Field(0, description="Count of positive community reactions, reviews, or votes.")
    source_url: HttpUrl = Field(..., description="The scraper lookup link containing this product profile.")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of tracking.")


class ResearchPaper(BaseModel):
    """Schema for processing academic literature and code repositories."""
    title: str = Field(..., description="The formal title of the academic paper.")
    authors: List[str] = Field(..., description="List of contributing researchers.")
    abstract: str = Field(..., description="The full or condensed summary text of the paper.")
    arxiv_url: HttpUrl = Field(..., description="Direct Link to the paper file path or landing index (typically arXiv).")
    code_url: Optional[HttpUrl] = Field(None, description="Associated open-source repository link (e.g., Papers with Code / GitHub).")
    published_date: Optional[str] = Field(None, description="The original release date of the paper.")
    primary_category: str = Field(..., description="The primary scientific domain code (e.g., cs.CL, cs.CV, stat.ML).")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="UTC tracking timestamp.")


class Job(BaseModel):
    """Schema for evaluating tech workspace employment trends."""
    job_title: str = Field(..., description="The official title of the open position.")
    company_name: str = Field(..., description="The hiring organization name.")
    location: str = Field(..., description="Work setting designation (e.g., 'San Francisco, CA', 'Remote', 'Hybrid').")
    salary_range: Optional[str] = Field(None, description="The listed pay scale range text if available.")
    experience_level: Optional[str] = Field(None, description="Target career level (e.g., Junior, Mid, Senior, Lead).")
    requirements: List[str] = Field(default_factory=list, description="Core tech stacks, languages, or skills required.")
    job_board_url: HttpUrl = Field(..., description="The original path linking back to the posting platform.")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="UTC processing timestamp.")
