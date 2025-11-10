from __future__ import annotations
import os
from typing import Any, Dict, List, Tuple

from .config import get_settings
from .logging_setup import logger
from .downloader import download_reel
from .media import process_media
from .llm import extract_items_with_llm
from .enrich import enrich_item
from .sheets import SheetsClient, local_csv_backup
from .utils import now_iso, ensure_dir


def item_to_row(global_index: int, timestamp: str, reel_url: str, item: Dict[str, Any]) -> List[Any]:
	return [
		global_index,
		timestamp,
		reel_url,
		item.get("item_index"),
		item.get("type"),
		item.get("item_name"),
		item.get("brand_or_category"),
		item.get("city"),
		item.get("state"),
		item.get("country"),
		item.get("lat"),
		item.get("lng"),
		item.get("distance_km"),
		item.get("price"),
		item.get("price_source"),
		item.get("purchase_link"),
		item.get("key_specs"),
		item.get("notes"),
		item.get("confidence"),
		item.get("source_text"),
		item.get("processing_status"),
	]


def process_reel_url(reel_url: str, origin_lat: float | None = None, origin_lng: float | None = None) -> Tuple[int, int, List[Dict[str, Any]]]:
	settings = get_settings()
	ensure_dir(settings.temp_dir)
	try:
		meta = download_reel(reel_url, settings.temp_dir)
	except Exception as e:
		logger.error("pipeline.download.failed", error=str(e))
		raise
	caption = meta.get("caption") or ""
	video_path = meta.get("video_path")
	media = {"transcript": "", "ocr_text": ""}
	if video_path and os.path.exists(video_path):
		try:
			media = process_media(video_path, settings.temp_dir)
		except Exception as e:
			logger.error("pipeline.media.failed", error=str(e), error_type=type(e).__name__)
			# Continue with empty media if processing fails
			media = {"transcript": "", "ocr_text": ""}
	
	source_blob = "\n\n".join(filter(None, [
		f"caption: {caption}",
		f"transcript: {media.get('transcript','')}" if media.get('transcript') else "",
		f"ocr: {media.get('ocr_text','')}" if media.get('ocr_text') else "",
	]))

	try:
		items = extract_items_with_llm(source_blob)
	except Exception as e:
		logger.error("pipeline.llm.failed", error=str(e))
		items = []
	
	if not items:
		raise ValueError("No items extracted from reel")
	
	for it in items:
		it["source_text"] = (caption or "")[:200]
		try:
			it = enrich_item(it, origin_lat, origin_lng)
		except Exception as e:
			logger.warn("pipeline.enrich.failed", item=it.get("item_name"), error=str(e))

	# Choose sheet by domain
	sheet_id = settings.google_sheet_id
	if any((it.get("type") or "").lower() in ("place", "hotel") for it in items) and settings.sheet_travel_id:
		sheet_id = settings.sheet_travel_id
	elif any((it.get("type") or "").lower() == "product" for it in items) and settings.sheet_products_id:
		sheet_id = settings.sheet_products_id

	if not sheet_id:
		raise ValueError("No Google Sheet ID configured")

	# Build rows with correct global Index
	timestamp = now_iso()
	
	# Get client and calculate next index
	client = SheetsClient(sheet_id=sheet_id)
	next_index = 1
	
	try:
		# Try to get the last row to calculate next index
		last_rows = client.get_last_n_rows(n=1, sheet_name="Sheet1")
		if last_rows and len(last_rows) > 0:
			# Skip header row if it exists
			if last_rows[0] and len(last_rows[0]) > 0:
				# Check if first cell is a number (not "Index" header)
				try:
					last_index = int(last_rows[0][0]) if last_rows[0][0] else 0
					next_index = last_index + 1
				except (ValueError, IndexError):
					# Header row or invalid data - start from 1
					next_index = 1
	except Exception as e:
		logger.warn("pipeline.index.calc.failed", error=str(e))
		# Start from 1 if we can't calculate
		next_index = 1
	
	rows = []
	for i, it in enumerate(items, start=0):
		global_idx = next_index + i
		rows.append(item_to_row(global_idx, timestamp, reel_url, it))

	try:
		result = client.append_rows(rows, sheet_name="Sheet1")
		updates = result.get("updates", {})
		updated_range = updates.get("updatedRange", "unknown")
		logger.info("pipeline.sheets.success", range=updated_range, rows=len(rows))
	except Exception as e:
		logger.error("pipeline.sheets.failed", error=str(e))
		# Still backup locally
		backup_path = os.path.join(settings.temp_dir, "backup.csv")
		local_csv_backup(backup_path, rows)
		raise
	
	# Fallback/local backup
	backup_path = os.path.join(settings.temp_dir, "backup.csv")
	local_csv_backup(backup_path, rows)

	# Return start and end index
	return (next_index, next_index + len(rows) - 1, items)
