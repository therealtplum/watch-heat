from __future__ import annotations
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def pct_change(s: pd.Series, periods: int) -> pd.Series:
    """Calculate percentage change over specified periods.
    
    Args:
        s: Series of values
        periods: Number of periods to look back
        
    Returns:
        Series of percentage changes (multiplied by 100)
    """
    if len(s) < periods + 1:
        return pd.Series([pd.NA] * len(s), index=s.index)
    return s.pct_change(periods=periods) * 100.0

def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """Calculate rolling z-score over a window.
    
    Args:
        series: Series of values
        window: Window size for rolling calculation
        
    Returns:
        Series of z-scores
    """
    if len(series) < window:
        return pd.Series([pd.NA] * len(series), index=series.index)
    
    m = series.rolling(window, min_periods=1).mean()
    s = series.rolling(window, min_periods=1).std()
    # Avoid division by zero
    s = s.replace(0, pd.NA)
    z = (series - m) / s
    return z

def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Compute momentum and heat metrics for watch data.
    
    Args:
        df: DataFrame with columns: date, brand, reference, median_price, 
            listings_active, dom_median, ebay_activity (optional)
            
    Returns:
        DataFrame with additional metric columns
    """
    if df.empty:
        logger.warning("Empty dataframe passed to compute_metrics")
        return df
    
    df = df.sort_values(["brand","reference","date"]).copy()
    
    # Ensure required columns exist
    for col in ["median_price","listings_active","dom_median"]:
        if col not in df.columns:
            df[col] = pd.NA
            logger.warning(f"Missing column {col}, filling with NA")
    
    # Price percentage changes
    logger.debug("Computing price percentage changes...")
    df["pct_7"] = df.groupby(["brand","reference"])["median_price"].transform(
        lambda s: pct_change(s, 7) if len(s) > 7 else pd.Series([pd.NA] * len(s), index=s.index)
    )
    df["pct_14"] = df.groupby(["brand","reference"])["median_price"].transform(
        lambda s: pct_change(s, 14) if len(s) > 14 else pd.Series([pd.NA] * len(s), index=s.index)
    )
    df["pct_30"] = df.groupby(["brand","reference"])["median_price"].transform(
        lambda s: pct_change(s, 30) if len(s) > 30 else pd.Series([pd.NA] * len(s), index=s.index)
    )
    
    # Rolling z-score (90-day)
    logger.debug("Computing rolling z-scores...")
    df["z90"] = df.groupby(["brand","reference"])["median_price"].transform(
        lambda s: rolling_zscore(s, 90)
    )
    
    # Supply and DOM deltas (negative because decreasing supply/DOM is positive)
    logger.debug("Computing supply and DOM deltas...")
    df["supply_delta_14"] = -df.groupby(["brand","reference"])["listings_active"].transform(
        lambda s: pct_change(s, 14) if len(s) > 14 else pd.Series([pd.NA] * len(s), index=s.index)
    )
    df["dom_delta_14"] = -df.groupby(["brand","reference"])["dom_median"].transform(
        lambda s: pct_change(s, 14) if len(s) > 14 and s.notna().sum() > 14 else pd.Series([pd.NA] * len(s), index=s.index)
    )
    
    # eBay momentum (30-day normalized change)
    if "ebay_activity" in df.columns:
        logger.debug("Computing eBay momentum...")
        def norm30(s: pd.Series) -> pd.Series:
            """Normalized 30-day momentum for eBay activity."""
            if len(s) < 30:
                return pd.Series([pd.NA] * len(s), index=s.index)
            result = pd.Series([pd.NA] * len(s), index=s.index, dtype=float)
            for i in range(29, len(s)):
                window = s.iloc[i-29:i+1]
                if window.notna().sum() < 2:
                    continue
                window_clean = window.dropna()
                if len(window_clean) < 2:
                    continue
                ptp = window_clean.max() - window_clean.min()
                if ptp > 1e-6:
                    result.iloc[i] = (window_clean.iloc[-1] - window_clean.iloc[0]) / ptp
            return result
        
        df["ebay_mom_30"] = df.groupby(["brand","reference"])["ebay_activity"].transform(norm30)
    else:
        df["ebay_mom_30"] = pd.NA
        logger.debug("No eBay activity column found")
    
    logger.info(f"Computed metrics for {len(df)} records")
    return df

def heat_score(row: pd.Series) -> float:
    """Calculate composite heat score for a watch.
    
    Heat score is a weighted combination of:
    - 14-day price change (35%)
    - 30-day price change (25%)
    - DOM delta (20%)
    - Supply delta (20%)
    - Z90 score (10%, capped at 3.0)
    - eBay momentum (10%, normalized to [-1, 1])
    
    Args:
        row: Series with metric columns
        
    Returns:
        Heat score between 0 and ~1.0 (can exceed 1.0 for very strong signals)
    """
    comps = []
    
    # Price momentum components (weighted by 10% normalization)
    for w, col in [(0.35, "pct_14"), (0.25, "pct_30"), (0.20, "dom_delta_14"), (0.20, "supply_delta_14")]:
        val = row.get(col, pd.NA)
        if pd.notna(val) and val != "":
            try:
                # Normalize percentage changes (divide by 10 to scale to reasonable range)
                normalized = float(val) / 10.0
                comps.append(w * normalized)
            except (ValueError, TypeError):
                pass
    
    # Z90 score (capped at 3.0, contributes up to 10%)
    z = row.get("z90", pd.NA)
    if pd.notna(z) and z != "":
        try:
            z_val = float(z)
            # Cap at 3.0 and normalize to [0, 1]
            z_normalized = max(0.0, min(z_val, 3.0)) / 3.0
            comps.append(0.10 * z_normalized)
        except (ValueError, TypeError):
            pass
    
    # eBay momentum (normalized to [-1, 1], contributes up to 10%)
    eb = row.get("ebay_mom_30", pd.NA)
    if pd.notna(eb) and eb != "":
        try:
            eb_val = float(eb)
            # Clamp to [-1, 1] range
            eb_clamped = max(-1.0, min(eb_val, 1.0))
            comps.append(0.10 * eb_clamped)
        except (ValueError, TypeError):
            pass
    
    return float(sum(comps)) if comps else 0.0
