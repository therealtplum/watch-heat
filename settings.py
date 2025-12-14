import os
from dotenv import load_dotenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env", override=False)

WATCHCHARTS_API_KEY = os.getenv("WATCHCHARTS_API_KEY", "")
EBAY_APP_ID = os.getenv("EBAY_APP_ID", "")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID", "")
EBAY_DEV_ID = os.getenv("EBAY_DEV_ID", "")
EBAY_OAUTH_TOKEN = os.getenv("EBAY_OAUTH_TOKEN", "")

# knobs
MIN_LISTINGS = 5           # lower until WatchCharts info returns listings; adjust later
HEAT_THRESHOLD = 0.75
LOOKBACK_DAYS = 90

# --- Profit model (8-10% target) ---
TARGET_MARGIN_MIN = 0.08
TARGET_MARGIN_MAX = 0.10
SELLING_FEE_RATE   = 0.065
PAYMENT_FEE_RATE   = 0.029
SHIPPING_INSURANCE = 100.0
MISC_BUFFER_RATE   = 0.01

CACHE_DIR = ROOT / "cache"
CACHE_DIR.mkdir(exist_ok=True)
