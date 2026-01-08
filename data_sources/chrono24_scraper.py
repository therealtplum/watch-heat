"""
Chrono24 scraper using Playwright to bypass Cloudflare.

This replaces the WatchCharts API ($1000/yr) with free Chrono24 data.
"""
from __future__ import annotations
import datetime as dt
import random
import re
import statistics
import logging
import time
from typing import Dict, Any, List, Optional, Iterable
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, Browser, BrowserContext

from settings import CACHE_DIR, LOOKBACK_DAYS

logger = logging.getLogger(__name__)

# Rate limiting - Chrono24 is aggressive about bot detection
REQUEST_DELAY = 5.0  # seconds between requests

# Rotate user agents to appear more human
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class Chrono24Scraper:
    """Playwright-based Chrono24 scraper with bot detection evasion."""
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._request_count = 0
    
    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
            ]
        )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
    
    def _new_context(self) -> BrowserContext:
        """Create a fresh browser context with rotated user agent."""
        ua = random.choice(USER_AGENTS)
        context = self._browser.new_context(
            user_agent=ua,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
        )
        return context
    
    def scrape_watch(self, brand: str, reference: str, max_retries: int = 2) -> Optional[Dict[str, Any]]:
        """
        Scrape Chrono24 for a single watch reference.
        
        Args:
            brand: Watch brand (e.g., "Rolex")
            reference: Reference number (e.g., "126610LN")
            max_retries: Number of retry attempts
            
        Returns:
            Dict with scraped data or None if failed
        """
        if not self._browser:
            raise RuntimeError("Scraper not initialized. Use 'with' context manager.")
        
        query = f"{brand} {reference}"
        url = f"https://www.chrono24.com/search/index.htm?query={query.replace(' ', '+')}&dosearch=true"
        
        for attempt in range(max_retries + 1):
            # Create fresh context for each attempt to avoid fingerprinting
            context = self._new_context()
            page = context.new_page()
            
            try:
                logger.debug(f"Scraping {brand} {reference} (attempt {attempt + 1})")
                
                # Use 'load' instead of 'networkidle' - faster and more reliable
                page.goto(url, wait_until="load", timeout=60000)
                
                # Wait for Cloudflare challenge to clear and content to load
                # Look for price-containing elements as a signal that real content loaded
                try:
                    page.wait_for_selector('[class*="price"], [class*="listing"]', timeout=15000)
                except:
                    pass  # Continue even if selector not found
                
                page.wait_for_timeout(2000)  # Extra buffer for JS
                
                content = page.content()
                
                # Check if we got blocked or hit a challenge page
                if 'challenge' in content.lower() and len(content) < 20000:
                    logger.warning(f"Cloudflare challenge detected for {brand} {reference}")
                    page.close()
                    context.close()
                    if attempt < max_retries:
                        time.sleep(5)  # Wait before retry
                        continue
                    return None
                
                # Extract listing count and prices
                listing_count = self._extract_listing_count(content)
                prices = self._extract_prices(content)
                
                if not prices:
                    logger.warning(f"No prices found for {brand} {reference}")
                    page.close()
                    context.close()
                    if attempt < max_retries:
                        time.sleep(3)
                        continue
                    return None
                
                result = {
                    'date': dt.date.today(),
                    'brand': brand,
                    'reference': reference,
                    'listings_active': listing_count,
                    'median_price': statistics.median(prices) if prices else None,
                    'mean_price': statistics.mean(prices) if prices else None,
                    'min_price': min(prices) if prices else None,
                    'max_price': max(prices) if prices else None,
                    'price_count': len(prices),
                }
                
                logger.info(f"Scraped {brand} {reference}: {listing_count or '?'} listings, median ${result['median_price']:,.0f}")
                return result
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed for {brand} {reference}: {e}")
                if attempt < max_retries:
                    time.sleep(5)
                else:
                    logger.error(f"All attempts failed for {brand} {reference}")
                    return None
            finally:
                try:
                    page.close()
                    context.close()
                except:
                    pass
        
        return None
    
    def _extract_listing_count(self, html: str) -> Optional[int]:
        """Extract the number of listings from the page HTML."""
        # Pattern 1: Look for "X Watches" or "X watches" in the results header
        # This appears as "716 Watches for..." type text
        patterns = [
            r'<h1[^>]*>.*?([\d,]+)\s*(?:watches|listings)\b',  # In header
            r'>([\d,]+)\s*(?:watches|listings|offers)\s*(?:for|found|available)',  # In text
            r'Results:\s*([\d,]+)',  # Results count
        ]
        
        for pattern in patterns:
            match = re.search(pattern, html, re.I | re.S)
            if match:
                count = int(match.group(1).replace(',', ''))
                # Sanity check: should be less than 100k for a specific reference
                if count < 100000:
                    return count
        
        # Fallback: count unique price entries (approximation)
        return None
    
    def _extract_prices(self, html: str) -> List[int]:
        """Extract listing prices from the page HTML."""
        # Find all USD prices
        all_prices = re.findall(r'\$\s*([\d,]+)', html)
        
        prices = []
        for p_str in all_prices:
            try:
                price = int(p_str.replace(',', ''))
                # Filter: watches are typically $1k-$500k, not shipping fees ($29-$200)
                if 1000 < price < 500000:
                    prices.append(price)
            except ValueError:
                continue
        
        # Deduplicate while preserving order (listings often show price twice)
        seen = set()
        unique_prices = []
        for p in prices:
            if p not in seen:
                seen.add(p)
                unique_prices.append(p)
        
        return unique_prices


def fetch_chrono24_daily(brand_ref_pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """
    Fetch daily Chrono24 data for given brand/reference pairs.
    
    This is the main entry point, replacing fetch_watchcharts_daily().
    
    Args:
        brand_ref_pairs: Iterable of (brand, reference) tuples
        
    Returns:
        DataFrame with historical watch data
    """
    pairs_list = list(brand_ref_pairs)
    logger.info(f"Fetching Chrono24 data for {len(pairs_list)} watches...")
    
    success_count = 0
    
    with Chrono24Scraper() as scraper:
        for i, (brand, ref) in enumerate(pairs_list):
            try:
                snap = scraper.scrape_watch(brand, ref)
                if snap:
                    persist_daily_snapshot(snap)
                    success_count += 1
                
                # Rate limiting between requests
                if i < len(pairs_list) - 1:
                    time.sleep(REQUEST_DELAY)
                    
            except Exception as e:
                logger.error(f"Error processing {brand} {ref}: {e}")
    
    logger.info(f"Successfully fetched {success_count}/{len(pairs_list)} watches")
    
    # Load cached historical data
    df = load_cached_series(pairs_list)
    
    if not df.empty:
        maxd = df["date"].max()
        cutoff = dt.date.fromordinal(maxd.toordinal() - LOOKBACK_DAYS + 1)
        df = df[df["date"] >= cutoff].copy()
        logger.info(f"Loaded {len(df)} historical records (last {LOOKBACK_DAYS} days)")
    else:
        logger.warning("No cached data found")
    
    return df


def persist_daily_snapshot(row: Dict[str, Any]):
    """Save a daily snapshot to the cache."""
    path = CACHE_DIR / f"{row['brand']}__{row['reference']}.csv"
    
    # Keep only the columns we need for the cache
    cache_row = {
        'date': row['date'],
        'brand': row['brand'],
        'reference': row['reference'],
        'median_price': row.get('median_price'),
        'listings_active': row.get('listings_active'),
        'dom_median': None,  # Chrono24 doesn't provide DOM
    }
    
    df = pd.DataFrame([cache_row])
    
    if path.exists():
        old = pd.read_csv(path, parse_dates=["date"])
        old["date"] = old["date"].dt.date
        # Remove any existing entry for today
        old = old[old["date"] != row["date"]]
        df = pd.concat([old, df], ignore_index=True)
    
    df.to_csv(path, index=False)
    logger.debug(f"Persisted snapshot for {row['brand']} {row['reference']}")


def load_cached_series(pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """Load cached historical data for given watch pairs."""
    frames = []
    
    for brand, ref in pairs:
        p = CACHE_DIR / f"{brand}__{ref}.csv"
        if p.exists():
            df = pd.read_csv(p, parse_dates=["date"])
            df["date"] = df["date"].dt.date
            frames.append(df[["date", "brand", "reference", "median_price", "listings_active", "dom_median"]])
    
    if frames:
        return pd.concat(frames, ignore_index=True)
    
    return pd.DataFrame(columns=["date", "brand", "reference", "median_price", "listings_active", "dom_median"])


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    test_pairs = [
        ("Rolex", "126610LN"),
        ("Rolex", "126710BLRO"),
    ]
    
    df = fetch_chrono24_daily(test_pairs)
    print(df)
