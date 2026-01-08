from __future__ import annotations
import logging
from typing import Iterable
import pandas as pd

# Use Chrono24 scraper instead of WatchCharts API ($1000/yr)
from .chrono24_scraper import fetch_chrono24_daily

logger = logging.getLogger(__name__)


def fetch_watchcharts_daily(brand_ref_pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """
    Fetch daily market data for given brand/reference pairs.
    
    NOTE: This now uses Chrono24 scraper instead of WatchCharts API.
    The function name is kept for backwards compatibility with main.py.
    
    Args:
        brand_ref_pairs: Iterable of (brand, reference) tuples
        
    Returns:
        DataFrame with historical watch data
    """
    logger.info("Using Chrono24 scraper (WatchCharts API is $1000/yr)")
    return fetch_chrono24_daily(brand_ref_pairs)
