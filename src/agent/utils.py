import os
import re
import time
from datetime import datetime
from typing import Any


REEL_URL_RE = re.compile(r"https?://(www\.)?instagram\.com/(reel|p)/[A-Za-z0-9_-]+/?")


def is_valid_reel_url(text: str) -> bool:
	return bool(REEL_URL_RE.search(text))


def now_iso() -> str:
	return datetime.utcnow().isoformat()


def ensure_dir(path: str) -> None:
	os.makedirs(path, exist_ok=True)


def sleep_backoff(attempt: int) -> None:
	time.sleep(min(60, 2 ** attempt))


SHEET_HEADERS = [
	"Index",
	"Timestamp",
	"Reel Link",
	"Item Index",
	"Item Type",
	"Item Name",
	"Brand/Category",
	"City",
	"State",
	"Country",
	"Lat",
	"Lng",
	"Distance_km",
	"Price",
	"Price_Source",
	"Purchase_Link",
	"Key_Specs/Features",
	"Best_Time/Notes",
	"Confidence",
	"Source_Text",
	"Processing_Status",
]
