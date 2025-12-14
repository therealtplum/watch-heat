from __future__ import annotations
import datetime as dt, pandas as pd
import logging
from typing import Iterable, Tuple
from settings import LOOKBACK_DAYS
from .watchcharts_client import build_snapshot_row, persist_daily_snapshot, load_cached_series

logger = logging.getLogger(__name__)

def fetch_watchcharts_daily(brand_ref_pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """Fetch daily WatchCharts data for given brand/reference pairs.
    
    Args:
        brand_ref_pairs: Iterable of (brand, reference) tuples
        
    Returns:
        DataFrame with historical watch data
    """
    pairs_list = list(brand_ref_pairs)
    logger.info(f"Fetching WatchCharts data for {len(pairs_list)} watches...")
    
    success_count = 0
    for brand, ref in pairs_list:
        try:
            snap = build_snapshot_row(brand, ref, display_name=None)
            if snap:
                persist_daily_snapshot(snap)
                success_count += 1
        except Exception as e:
            logger.error(f"Error processing {brand} {ref}: {e}")
    
    logger.info(f"Successfully fetched {success_count}/{len(pairs_list)} watches")
    
    df = load_cached_series(pairs_list)
    if not df.empty:
        maxd = df["date"].max()
        cutoff = dt.date.fromordinal(maxd.toordinal() - LOOKBACK_DAYS + 1)
        df = df[df["date"] >= cutoff].copy()
        logger.info(f"Loaded {len(df)} historical records (last {LOOKBACK_DAYS} days)")
    else:
        logger.warning("No cached data found")
    
    return df
