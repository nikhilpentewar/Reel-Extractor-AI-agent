from __future__ import annotations
import json
from typing import Any, Dict, List

from .config import get_settings
from .logging_setup import logger


SYSTEM_PROMPT = (
	"You are an expert data extraction engine. Given mixed source text (caption, hashtags, transcript, OCR, comments) from an Instagram Reel, detect distinct items. For each item, classify as one of: place, hotel, product, service, other. For places/hotels, extract name and location hints; for products, brand/category/price/link if available. Respond with a JSON list under key 'items', where each item has: item_index, type, item_name, brand_or_category, city, state, country, lat, lng, distance_km, price, price_source, purchase_link, key_specs, notes, confidence (0-1), processing_status (done|review|failed). If ambiguous or insufficient data, set processing_status=review and include notes."
)


def _fallback_extract(source_blob: str) -> List[Dict[str, Any]]:
	# Very naive fallback: return a single review item using source snippet
	snippet = (source_blob or "")[:160]
	if not snippet.strip():
		return []
	return [{
		"item_index": 1,
		"type": "other",
		"item_name": snippet.split("\n")[0][:60],
		"brand_or_category": None,
		"city": None,
		"state": None,
		"country": None,
		"lat": None,
		"lng": None,
		"distance_km": None,
		"price": None,
		"price_source": None,
		"purchase_link": None,
		"key_specs": None,
		"notes": "LLM disabled; manual review needed",
		"confidence": 0.3,
		"processing_status": "review",
	}]


def extract_items_with_llm(source_blob: str) -> List[Dict[str, Any]]:
	settings = get_settings()
	if not settings.use_llm or not settings.openai_api_key:
		logger.warn("llm.disabled", use_llm=settings.use_llm)
		return _fallback_extract(source_blob)
	try:
		from openai import OpenAI
		client = OpenAI(api_key=settings.openai_api_key)
		messages = [
			{"role": "system", "content": SYSTEM_PROMPT},
			{"role": "user", "content": source_blob[:18000]},
		]
		resp = client.chat.completions.create(
			model="gpt-4o-mini",
			messages=messages,
			temperature=0.2,
		)
		text = resp.choices[0].message.content
		try:
			data = json.loads(text)
			items = data.get("items") if isinstance(data, dict) else data
			if not isinstance(items, list):
				raise ValueError("Invalid items JSON")
			for i, it in enumerate(items, start=1):
				it.setdefault("item_index", i)
				it.setdefault("confidence", 0.5)
				it.setdefault("processing_status", "review")
			return items
		except Exception as e:
			logger.error("llm.parse.failed", error=str(e), text_sample=text[:200])
			return _fallback_extract(source_blob)
	except Exception as e:
		logger.error("llm.call.failed", error=str(e))
		return _fallback_extract(source_blob)
