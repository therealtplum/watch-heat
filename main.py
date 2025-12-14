from __future__ import annotations
import sys
import logging
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import datetime as dt

from settings import MIN_LISTINGS, HEAT_THRESHOLD
from data_sources.watchcharts import fetch_watchcharts_daily
from data_sources.ebay import fetch_ebay_signal
from analytics.metrics import compute_metrics, heat_score
from analytics.profit import add_profit_overlay
from report.render import render_html

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ROOT / 'watch_heat.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_universe(path: Path) -> pd.DataFrame:
    """Load watch universe from CSV file.
    
    Args:
        path: Path to universe CSV file
        
    Returns:
        DataFrame with brand, reference, and display_name columns
        
    Raises:
        FileNotFoundError: If universe file doesn't exist
        ValueError: If required columns are missing
    """
    if not path.exists():
        raise FileNotFoundError(f"Universe file not found: {path}")
    
    try:
        u = pd.read_csv(path)
        required_cols = ["brand", "reference"]
        missing = [col for col in required_cols if col not in u.columns]
        if missing:
            raise ValueError(f"Missing required columns in universe: {missing}")
        
        u["brand"] = u["brand"].astype(str)
        u["reference"] = u["reference"].astype(str)
        logger.info(f"Loaded {len(u)} watches from universe file")
        return u
    except Exception as e:
        logger.error(f"Error loading universe file: {e}")
        raise

def run(output_dir: Path, run_date: dt.date | None = None) -> tuple[Path, Path, pd.DataFrame]:
    """Run the watch heat analysis pipeline.
    
    Args:
        output_dir: Directory to save output files
        run_date: Optional date to use instead of today's date
        
    Returns:
        Tuple of (csv_path, html_path, dataframe)
    """
    logger.info("Starting watch heat analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        universe = load_universe(ROOT / "universe.csv")
        pairs = list(universe[["brand","reference"]].itertuples(index=False, name=None))
        logger.info(f"Processing {len(pairs)} watch references")

        logger.info("Fetching WatchCharts data...")
        wc_df = fetch_watchcharts_daily(pairs)
        logger.info(f"WatchCharts: {len(wc_df)} records")
        
        # Validate WatchCharts data
        if wc_df.empty:
            logger.warning("No WatchCharts data retrieved")
        else:
            required_cols = ["date", "brand", "reference"]
            missing = [col for col in required_cols if col not in wc_df.columns]
            if missing:
                raise ValueError(f"WatchCharts data missing required columns: {missing}")

        logger.info("Fetching eBay signal data...")
        eb_df = fetch_ebay_signal(pairs)
        logger.info(f"eBay: {len(eb_df)} records")
        
        # Validate eBay data
        if not eb_df.empty:
            required_cols = ["date", "brand", "reference"]
            missing = [col for col in required_cols if col not in eb_df.columns]
            if missing:
                logger.warning(f"eBay data missing columns: {missing}")

        # Merge data
        if wc_df.empty:
            raise ValueError("Cannot proceed without WatchCharts data")
        
        df = wc_df.merge(eb_df, on=["date","brand","reference"], how="left")
        
        # Validate merged data
        if df.empty:
            raise ValueError("Merged dataframe is empty")
        
        logger.info(f"Merged data: {len(df)} records")
        logger.info("Computing metrics...")
        df = compute_metrics(df)

        if df.empty:
            logger.warning("No data available after merging and computing metrics")
            raise ValueError("No data available for analysis")

        last_date = df["date"].max() if run_date is None else run_date
        logger.info(f"Using date: {last_date}")
        
        snap = df[df["date"] == last_date].copy()
        if snap.empty:
            logger.warning(f"No data found for date {last_date}")
            # Try to use the most recent available date
            last_date = df["date"].max()
            snap = df[df["date"] == last_date].copy()
            logger.info(f"Using most recent available date: {last_date}")
        
        snap = snap.merge(universe, on=["brand","reference"], how="left")
        
        # Validate and clean data
        if "listings_active" not in snap.columns:
            logger.warning("listings_active column missing, creating with default value")
            snap["listings_active"] = 0
        else:
            snap["listings_active"] = pd.to_numeric(snap["listings_active"], errors="coerce").fillna(0)
        
        # Validate price data
        if "median_price" not in snap.columns:
            logger.warning("median_price column missing")
            snap["median_price"] = pd.NA
        else:
            snap["median_price"] = pd.to_numeric(snap["median_price"], errors="coerce")
        
        initial_count = len(snap)
        snap = snap[snap["listings_active"] >= MIN_LISTINGS].copy()
        filtered_count = initial_count - len(snap)
        if filtered_count > 0:
            logger.info(f"Filtered out {filtered_count} watches with < {MIN_LISTINGS} listings")
        
        if snap.empty:
            raise ValueError(f"No watches meet minimum listing requirement ({MIN_LISTINGS})")
        
        logger.info("Computing heat scores...")
        snap["heat"] = snap.apply(heat_score, axis=1)
        snap["is_hot"] = snap["heat"] >= HEAT_THRESHOLD
        
        hot_count = snap["is_hot"].sum()
        logger.info(f"Found {hot_count} hot watches (heat >= {HEAT_THRESHOLD})")
        
        snap_sorted = snap.sort_values(["is_hot","heat"], ascending=[False, False])

        logger.info("Adding profit overlay...")
        snap_sorted = add_profit_overlay(snap_sorted)

        csv_path = output_dir / f"watch_heat_{last_date}.csv"
        snap_sorted.to_csv(csv_path, index=False)
        logger.info(f"Saved CSV: {csv_path}")

        rows = snap_sorted.fillna("").to_dict(orient="records")
        html_path = output_dir / f"watch_heat_{last_date}.html"
        render_html(rows, html_path, run_date=str(last_date))
        logger.info(f"Saved HTML: {html_path}")
        
        return csv_path, html_path, snap_sorted
    except Exception as e:
        logger.error(f"Error in run(): {e}", exc_info=True)
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watch Heat Momentum Screener")
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: data/)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to analyze (YYYY-MM-DD, default: today or most recent available)"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "data"
    run_date = dt.datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    
    try:
        csv_path, html_path, snap = run(output_dir, run_date)
        print(f"\n✓ Analysis complete!")
        print(f"  CSV:  {csv_path}")
        print(f"  HTML: {html_path}")
        print(f"  Watches analyzed: {len(snap)}")
        print(f"  Hot watches: {snap['is_hot'].sum()}")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
