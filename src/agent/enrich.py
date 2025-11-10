from __future__ import annotations
import math
import requests
from typing import Dict, Any

from .config import get_settings
from .logging_setup import logger


def _haversine(lat1, lon1, lat2, lon2):
	R = 6371.0
	phi1, phi2 = math.radians(lat1), math.radians(lat2)
	dphi = math.radians(lat2 - lat1)
	dlam = math.radians(lon2 - lon1)
	a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
	c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
	return R * c


def enrich_place(item: Dict[str, Any], origin_lat: float | None = None, origin_lng: float | None = None) -> Dict[str, Any]:
	settings = get_settings()
	name = (item.get("item_name") or "").strip()
	if not name:
		return item
	try:
		params = {
			"q": name,
			"format": "json",
			"limit": 1,
		}
		r = requests.get(
			"https://nominatim.openstreetmap.org/search",
			params=params,
			timeout=15,
			headers={"User-Agent": "reel-extractor-ai-agent/1.0 (contact: admin@example.com)"},
		)
		if r.status_code != 200:
			logger.warn("nominatim.search.failed", code=r.status_code)
			return item
		results = r.json() or []
		if not results:
			return item
		best = results[0]
		lat = float(best.get("lat"))
		lng = float(best.get("lon"))
		item["lat"], item["lng"] = lat, lng
		# Optional reverse to get address components
		rv = requests.get(
			"https://nominatim.openstreetmap.org/reverse",
			params={"lat": lat, "lon": lng, "format": "json", "zoom": 14},
			headers={"User-Agent": "reel-extractor-ai-agent/1.0 (contact: admin@example.com)"},
			timeout=15,
		)
		if rv.status_code == 200:
			addr = (rv.json() or {}).get("address", {})
			item.setdefault("city", addr.get("city") or addr.get("town") or addr.get("village"))
			item.setdefault("state", addr.get("state"))
			item.setdefault("country", addr.get("country"))
		if origin_lat and origin_lng:
			item["distance_km"] = round(_haversine(origin_lat, origin_lng, lat, lng), 2)
		item["processing_status"] = item.get("processing_status", "done")
		item["confidence"] = max(float(item.get("confidence", 0.5)), 0.7)
	except Exception as e:
		logger.warn("nominatim.error", error=str(e))
	return item


def enrich_product(item: Dict[str, Any]) -> Dict[str, Any]:
	# Placeholder: set price source and leave lookup for future web-scrape
	if not item.get("price"):
		item["price_source"] = "web-scrape"
		item.setdefault("processing_status", "review")
		item["confidence"] = float(item.get("confidence", 0.5))
	return item


def enrich_item(item: Dict[str, Any], origin_lat: float | None = None, origin_lng: float | None = None) -> Dict[str, Any]:
	type_ = (item.get("type") or "").lower()
	if type_ in ("place", "hotel"):
		return enrich_place(item, origin_lat, origin_lng)
	elif type_ == "product":
		return enrich_product(item)
	return item
