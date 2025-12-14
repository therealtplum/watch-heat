from __future__ import annotations
import pandas as pd
import logging
from settings import TARGET_MARGIN_MIN, TARGET_MARGIN_MAX, SELLING_FEE_RATE, PAYMENT_FEE_RATE, SHIPPING_INSURANCE, MISC_BUFFER_RATE

logger = logging.getLogger(__name__)

def add_profit_overlay(df: pd.DataFrame) -> pd.DataFrame:
    """Add profit calculation overlay to dataframe.
    
    Calculates:
    - Net proceeds after all fees
    - Maximum bid prices to achieve 8% and 10% margins
    
    Args:
        df: DataFrame with median_price column
        
    Returns:
        DataFrame with additional profit columns
    """
    df = df.copy()
    fee_rate = SELLING_FEE_RATE + PAYMENT_FEE_RATE + MISC_BUFFER_RATE
    
    # Calculate net proceeds after fees
    df["resale_net_after_fees"] = (
        df["median_price"] * (1 - fee_rate) - SHIPPING_INSURANCE
    )
    
    # Calculate max bid prices for target margins
    # Formula: max_bid = net_proceeds * (1 - target_margin)
    df["max_bid_for_8pct"] = df["resale_net_after_fees"] * (1 - TARGET_MARGIN_MIN)
    df["max_bid_for_10pct"] = df["resale_net_after_fees"] * (1 - TARGET_MARGIN_MAX)
    
    # Handle cases where price is missing
    missing_price_count = df["median_price"].isna().sum()
    if missing_price_count > 0:
        logger.warning(f"{missing_price_count} watches missing price data")
        df.loc[df["median_price"].isna(), "resale_net_after_fees"] = pd.NA
        df.loc[df["median_price"].isna(), "max_bid_for_8pct"] = pd.NA
        df.loc[df["median_price"].isna(), "max_bid_for_10pct"] = pd.NA
    
    logger.debug("Added profit overlay calculations")
    return df
