from __future__ import annotations
import datetime as dt
import time
import logging
from typing import Iterable, Tuple, Dict, Any, Optional
import requests, pandas as pd
from settings import WATCHCHARTS_API_KEY, LOOKBACK_DAYS, CACHE_DIR

logger = logging.getLogger(__name__)
API_ROOT = "https://api.watchcharts.com/v3"
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds

def _hdrs():
    if not WATCHCHARTS_API_KEY:
        raise RuntimeError("WATCHCHARTS_API_KEY missing. Add it to .env")
    return {"x-api-key": WATCHCHARTS_API_KEY}

def lookup_uuid(brand: str, reference: str) -> Optional[str]:
    """Look up UUID for a watch by brand and reference.
    
    Args:
        brand: Watch brand name
        reference: Watch reference number
        
    Returns:
        UUID string if found, None otherwise
    """
    params = {"brand_name": brand, "reference": reference}
    
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(f"{API_ROOT}/search/watch", params=params, headers=_hdrs(), timeout=20)
            r.raise_for_status()
            js = r.json()
            if isinstance(js, dict) and js.get("results"):
                for item in js["results"]:
                    if str(item.get("reference","")).lower() == str(reference).lower():
                        return item.get("uuid")
                return js["results"][0].get("uuid")
            return None
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Error looking up UUID for {brand} {reference} (attempt {attempt + 1}/{MAX_RETRIES}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to lookup UUID for {brand} {reference} after {MAX_RETRIES} attempts: {e}")
                return None
    return None

def get_watch_info(uuid: str) -> Dict[str, Any]:
    """Get watch information by UUID.
    
    Args:
        uuid: Watch UUID
        
    Returns:
        Dictionary with watch information
        
    Raises:
        requests.exceptions.RequestException: If API call fails after retries
    """
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(f"{API_ROOT}/watch/info", params={"uuid": uuid}, headers=_hdrs(), timeout=20)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Error fetching watch info for UUID {uuid} (attempt {attempt + 1}/{MAX_RETRIES}): {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed to fetch watch info for UUID {uuid} after {MAX_RETRIES} attempts: {e}")
                raise

def build_snapshot_row(brand: str, reference: str, display_name: str|None=None) -> Optional[Dict[str, Any]]:
    """Build a snapshot row for a watch.
    
    Args:
        brand: Watch brand name
        reference: Watch reference number
        display_name: Optional display name for the watch
        
    Returns:
        Dictionary with snapshot data or None if lookup fails
    """
    try:
        uuid = lookup_uuid(brand, reference)
        if not uuid:
            logger.warning(f"Could not find UUID for {brand} {reference}")
            return None
        
        info = get_watch_info(uuid)
        market_price = info.get("market_price") or info.get("price", {}).get("market") or info.get("marketPrice")
        dom = info.get("days_on_market") or info.get("dom") or None
        listings = info.get("listings_active") or info.get("listings") or None
        today = dt.date.today()
        
        return {
            "date": today, "brand": brand, "reference": reference, "display_name": display_name,
            "median_price": float(market_price) if market_price is not None else None,
            "listings_active": int(listings) if listings is not None else None,
            "dom_median": int(dom) if dom is not None else None,
            "uuid": uuid
        }
    except Exception as e:
        logger.error(f"Error building snapshot for {brand} {reference}: {e}")
        return None

def persist_daily_snapshot(row: Dict[str, Any]):
    path = CACHE_DIR / f"{row['brand']}__{row['reference']}.csv"
    df = pd.DataFrame([row])
    if path.exists():
        old = pd.read_csv(path, parse_dates=["date"])
        old["date"] = old["date"].dt.date
        old = old[old["date"] != row["date"]]
        df = pd.concat([old, df], ignore_index=True)
    df.to_csv(path, index=False)

def load_cached_series(pairs: Iterable[Tuple[str, str]]) -> pd.DataFrame:
    frames = []
    for brand, ref in pairs:
        p = CACHE_DIR / f"{brand}__{ref}.csv"
        if p.exists():
            df = pd.read_csv(p, parse_dates=["date"])
            df["date"] = df["date"].dt.date
            frames.append(df[["date","brand","reference","median_price","listings_active","dom_median"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date","brand","reference","median_price","listings_active","dom_median"])
