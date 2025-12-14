from __future__ import annotations
import datetime as dt
import time
import logging
import requests, pandas as pd
from typing import Iterable
from settings import EBAY_OAUTH_TOKEN

logger = logging.getLogger(__name__)
BROWSE_SEARCH = "https://api.ebay.com/buy/browse/v1/item_summary/search"
MAX_RETRIES = 3
RETRY_DELAY = 1.0

def _hdrs():
    if not EBAY_OAUTH_TOKEN:
        raise RuntimeError("EBAY_OAUTH_TOKEN missing. Add it to .env")
    return {"Authorization": f"Bearer {EBAY_OAUTH_TOKEN}"}

def search_count(q: str) -> int:
    """Get search count for a query string.
    
    Args:
        q: Search query string
        
    Returns:
        Number of matching results, or 0 if error
    """
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(BROWSE_SEARCH, params={"q": q, "limit": 1, "offset": 0}, headers=_hdrs(), timeout=20)
            r.raise_for_status()
            js = r.json()
            return int(js.get("total") or js.get("totalMatched") or 0)
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Error searching eBay for '{q}' (attempt {attempt + 1}/{MAX_RETRIES}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to search eBay for '{q}' after {MAX_RETRIES} attempts: {e}")
                return 0
    return 0

def fetch_ebay_signal(brand_ref_pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """Fetch eBay activity signal for given brand/reference pairs.
    
    Args:
        brand_ref_pairs: Iterable of (brand, reference) tuples
        
    Returns:
        DataFrame with eBay activity counts
    """
    pairs_list = list(brand_ref_pairs)
    logger.info(f"Fetching eBay signals for {len(pairs_list)} watches...")
    
    today = dt.date.today()
    rows = []
    for brand, ref in pairs_list:
        try:
            query = f"{brand} {ref}"
            cnt = search_count(query)
            rows.append({"date": today, "brand": brand, "reference": ref, "ebay_activity": cnt})
        except Exception as e:
            logger.error(f"Error fetching eBay signal for {brand} {ref}: {e}")
            rows.append({"date": today, "brand": brand, "reference": ref, "ebay_activity": None})
    
    logger.info(f"Successfully fetched {len([r for r in rows if r['ebay_activity'] is not None])}/{len(rows)} eBay signals")
    return pd.DataFrame(rows)
