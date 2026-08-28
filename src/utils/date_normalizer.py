"""
src/utils/date_normalizer.py
Normalizes messy, relative timelines into formal ISO-8601 formatting,
enforcing strict 24-hour freshness filters across news and job boards.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional  # <--- Added this line to fix the NameError
import logging
import dateparser

logger = logging.getLogger("graphone-pipeline.date_normalizer")

def normalize_publication_date(date_string: str) -> Optional[str]:
    """
    Parses complex relative expressions using dateparser.
    Converts strings into uniform UTC ISO-8601 strings.
    """
    if not date_string:
        return None
        
    try:
        # Configure settings to prioritize relative time context mapping matching UTC
        settings = {'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True}
        parsed_dt = dateparser.parse(date_string, settings=settings)
        
        if parsed_dt:
            return parsed_dt.isoformat()
    except Exception as e:
        logger.debug(f"Failed parsing complex date string '{date_string}': {e}")
    return None

def is_within_24_hours(iso_date_string: str) -> bool:
    """
    Evaluates whether a normalized ISO date string was published 
    within the last 24 hours relative to the current timestamp.
    """
    if not iso_date_string:
        return False
        
    try:
        published_dt = datetime.fromisoformat(iso_date_string)
        now_utc = datetime.now(timezone.utc)
        
        # Determine strict 24-hour delta limits
        cutoff = now_utc - timedelta(hours=24)
        return published_dt >= cutoff
    except Exception as e:
        logger.error(f"Error checking 24-hour data freshness parameter bounds: {e}")
        return False
