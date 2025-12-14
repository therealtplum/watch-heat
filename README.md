# Watch Heat (Momentum Screener)

> **A daily momentum screener for luxury watch market analysis** that identifies hot watch references by combining real-time market data, price momentum, supply/demand dynamics, and profit calculations to help traders make informed buying decisions.

Daily screener for hot watch references (Rolex, Omega, Cartier, AP to start).
- Pulls **WatchCharts API v3** for current market snap (per reference).
- Pulls **eBay Browse API** counts as a demand proxy.
- Computes Δ7/14/30d, Z90, supply/DOM deltas (when available), and a composite **Heat Score**.
- Adds **Profit Overlay** with **Max Bid (8%)** and **Max Bid (10%)** based on fees/buffers.

## About

Watch Heat is a comprehensive momentum screener designed for luxury watch market analysis. It automates the process of identifying "hot" watch references by aggregating data from multiple sources, computing sophisticated momentum metrics, and providing actionable profit calculations.

**Key Capabilities:**
- **Real-time Market Data**: Pulls current market prices, active listings, and days-on-market metrics from WatchCharts API
- **Demand Signals**: Tracks eBay activity as a proxy for market demand
- **Momentum Analysis**: Calculates multi-timeframe price changes (7/14/30 days), rolling z-scores, and supply/demand deltas
- **Composite Heat Score**: Weighted algorithm combining price momentum, market dynamics, and demand signals
- **Profit Optimization**: Calculates maximum bid prices to achieve target margins (8-10%) after accounting for fees and costs
- **Interactive Reports**: Beautiful, sortable HTML reports with filtering and search capabilities

Perfect for watch traders, collectors, and market analysts who want to spot emerging trends and make data-driven buying decisions.

## Features

- **Automated Daily Screening**: Fetches latest market data and computes momentum metrics
- **Heat Score Calculation**: Composite score combining price momentum, supply/demand dynamics, and market signals
- **Profit Analysis**: Calculates maximum bid prices to achieve target margins (8-10%)
- **Interactive HTML Reports**: Sortable, filterable reports with modern UI
- **Robust Error Handling**: Retry logic with exponential backoff for API calls
- **Comprehensive Logging**: Detailed logs saved to `watch_heat.log`
- **Data Validation**: Validates inputs and handles edge cases gracefully
- **Flexible Configuration**: Command-line arguments for custom output directories and dates

## Quickstart

```bash
cd watch-heat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Create .env file with your API keys (see .env.template)
python main.py
```

### Command-Line Options

```bash
python main.py --help

Options:
  --output-dir DIR    Output directory for reports (default: data/)
  --date YYYY-MM-DD   Date to analyze (default: today or most recent available)
  --verbose, -v       Enable verbose logging
```

### API Setup

#### WatchCharts API
1. Sign up for WatchCharts Professional + API plan
2. Get your API key from the dashboard
3. Use `/v3/search/watch` to get `uuid`, then `/v3/watch/info` (send `x-api-key` header)
4. Add to `.env`: `WATCHCHARTS_API_KEY=your_key_here`

#### eBay Browse API
1. Create an app at [eBay Developers](https://developer.ebay.com/)
2. Get your App ID, Cert ID, and Dev ID
3. Generate an OAuth token using client credentials flow
4. Add to `.env`:
   ```
   EBAY_APP_ID=your_app_id
   EBAY_CERT_ID=your_cert_id
   EBAY_DEV_ID=your_dev_id
   EBAY_OAUTH_TOKEN=your_oauth_token
   ```

## Project Structure

```
watch-heat/
├── main.py                 # Main entry point
├── settings.py             # Configuration and API keys
├── universe.csv            # Watch references to track
├── requirements.txt        # Python dependencies
├── data_sources/
│   ├── watchcharts.py      # WatchCharts API client
│   ├── watchcharts_client.py  # Low-level WatchCharts API calls
│   └── ebay.py             # eBay Browse API client
├── analytics/
│   ├── metrics.py          # Heat score and momentum calculations
│   └── profit.py           # Profit overlay calculations
├── report/
│   └── render.py           # HTML report generation
├── cache/                  # Daily snapshot cache (auto-created)
└── data/                   # Output reports (auto-created)
```

## Configuration

Edit `settings.py` to customize:

- **MIN_LISTINGS**: Minimum active listings to include (default: 5)
- **HEAT_THRESHOLD**: Heat score threshold for "hot" watches (default: 0.75)
- **LOOKBACK_DAYS**: Historical data window (default: 90)
- **Profit Model**: Fees, margins, shipping costs (see `TARGET_MARGIN_*`, `*_FEE_RATE`, etc.)

## Heat Score Calculation

The heat score is a weighted composite of:

- **14-day price change** (35%): Short-term momentum
- **30-day price change** (25%): Medium-term trend
- **DOM delta** (20%): Days on market change (negative = faster sales = positive)
- **Supply delta** (20%): Active listings change (negative = lower supply = positive)
- **Z90 score** (10%): 90-day rolling z-score (capped at 3.0)
- **eBay momentum** (10%): 30-day normalized eBay activity change

## Output

The script generates two files in the `data/` directory:

1. **CSV file** (`watch_heat_YYYY-MM-DD.csv`): Raw data for analysis
2. **HTML file** (`watch_heat_YYYY-MM-DD.html`): Interactive report with:
   - Summary statistics
   - Sortable columns
   - Search/filter functionality
   - Color-coded heat scores
   - Hot watch highlighting

## Notes

- If your WatchCharts plan doesn't expose historical endpoints, the pipeline persists **daily snapshots** in `cache/`. Heat metrics improve after a few days of runs.
- The script includes automatic retry logic (3 attempts with exponential backoff) for API calls.
- All operations are logged to `watch_heat.log` for debugging.
- Missing data is handled gracefully with appropriate warnings in logs.

## Recent Improvements

- ✅ Added comprehensive logging and error handling
- ✅ Implemented retry logic with exponential backoff for API calls
- ✅ Enhanced HTML report with sorting, filtering, and modern UI
- ✅ Added command-line arguments for flexibility
- ✅ Improved metrics calculation with better edge case handling
- ✅ Added data validation throughout the pipeline
- ✅ Enhanced code documentation and type hints
- ✅ Better handling of missing/invalid data
