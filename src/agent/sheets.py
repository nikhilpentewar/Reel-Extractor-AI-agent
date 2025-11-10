from __future__ import annotations
import csv
import io
import json
import os
from typing import List, Dict, Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from .config import get_settings
from .logging_setup import logger
from .utils import ensure_dir, SHEET_HEADERS


class SheetsClient:
	def __init__(self, sheet_id: str | None = None):
		self.settings = get_settings()
		self.sheet_id = sheet_id or self.settings.google_sheet_id
		if not self.sheet_id:
			raise RuntimeError("GOOGLE_SHEET_ID not configured")
		if not self.settings.google_sa_json_path:
			raise RuntimeError("GOOGLE_SA_JSON_PATH not configured")
		if not os.path.exists(self.settings.google_sa_json_path):
			# Provide helpful error message
			suggested_path = "/secrets/google-sa.json" if not self.settings.google_sa_json_path.startswith("/") else self.settings.google_sa_json_path
			raise FileNotFoundError(
				f"Service account JSON not found: {self.settings.google_sa_json_path}\n"
				f"Expected path in Docker: /secrets/google-sa.json\n"
				f"Make sure your .env has: GOOGLE_SA_JSON_PATH=/secrets/google-sa.json\n"
				f"And the file exists in your mounted secrets folder."
			)
		try:
			self.creds = Credentials.from_service_account_file(
				self.settings.google_sa_json_path,
				scopes=["https://www.googleapis.com/auth/spreadsheets"],
			)
			self.service = build("sheets", "v4", credentials=self.creds, cache_discovery=False)
			# Get service account email for error messages
			with open(self.settings.google_sa_json_path, 'r') as f:
				sa_data = json.load(f)
				self.service_account_email = sa_data.get('client_email', 'unknown')
		except Exception as e:
			logger.error("sheets.init.failed", error=str(e), path=self.settings.google_sa_json_path)
			raise

	def _ensure_headers(self, sheet_name: str = "Sheet1") -> bool:
		"""Check if headers exist, create/update them if not. Returns True if headers were created/updated."""
		try:
			# Check first row for headers
			result = (
				self.service.spreadsheets().values().get(
					spreadsheetId=self.sheet_id,
					range=f"{sheet_name}!A1:U1",
				)
				.execute()
			)
			values = result.get("values", [])
			
			# Check if headers exist and are correct
			headers_exist = False
			if values and len(values) > 0:
				existing_headers = values[0]
				# Check if first header is "Index" and we have at least a few headers
				if existing_headers and len(existing_headers) > 0:
					if existing_headers[0] == "Index" and len(existing_headers) >= 5:
						# Headers seem correct
						headers_exist = True
						logger.info("sheets.headers.exist", header_count=len(existing_headers))
			
			if not headers_exist:
				# Headers don't exist or are incorrect - create/update them
				logger.info("sheets.headers.creating_or_updating")
				header_body = {
					"values": [SHEET_HEADERS]
				}
				# Overwrite row 1 with correct headers
				self.service.spreadsheets().values().update(
					spreadsheetId=self.sheet_id,
					range=f"{sheet_name}!A1:U1",
					valueInputOption="RAW",
					body=header_body,
				).execute()
				logger.info("sheets.headers.created", header_count=len(SHEET_HEADERS))
				return True
			return False
		except Exception as e:
			logger.error("sheets.headers.check.failed", error=str(e))
			# Try to create headers anyway - this will overwrite row 1
			try:
				header_body = {
					"values": [SHEET_HEADERS]
				}
				self.service.spreadsheets().values().update(
					spreadsheetId=self.sheet_id,
					range=f"{sheet_name}!A1:U1",
					valueInputOption="RAW",
					body=header_body,
				).execute()
				logger.info("sheets.headers.created.retry", header_count=len(SHEET_HEADERS))
				return True
			except Exception as e2:
				logger.error("sheets.headers.create.failed", error=str(e2))
				# Continue anyway - append might still work
				return False

	def append_rows(self, values: List[List[Any]], sheet_name: str = "Sheet1") -> Dict[str, Any]:
		logger.info("sheets.append_rows.start", rows=len(values), sheet=sheet_name)
		
		# Ensure headers exist first
		self._ensure_headers(sheet_name)
		
		# Prepare data - ensure all rows have exactly 21 columns (matching headers)
		normalized_values = []
		for row in values:
			# Pad or truncate to exactly 21 columns
			normalized_row = list(row[:21])  # Take first 21
			while len(normalized_row) < 21:  # Pad with empty strings if needed
				normalized_row.append("")
			normalized_values.append(normalized_row)
		
		body = {
			"values": normalized_values
		}
		try:
			# Append to column A through U (21 columns total)
			result = (
				self.service.spreadsheets().values().append(
					spreadsheetId=self.sheet_id,
					range=f"{sheet_name}!A:U",  # Changed from A:Z to A:U (21 columns)
					valueInputOption="RAW",
					insertDataOption="INSERT_ROWS",
					body=body,
				)
				.execute()
			)
			updated_range = result.get("updates", {}).get("updatedRange", "unknown")
			logger.info("sheets.append_rows.done", updated_range=updated_range, rows=len(normalized_values))
			return result
		except Exception as e:
			error_msg = str(e)
			if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
				sa_email = getattr(self, 'service_account_email', 'service account')
				raise PermissionError(
					f"Permission denied: Service account '{sa_email}' does not have write access to the Google Sheet.\n"
					f"To fix this:\n"
					f"1. Open your Google Sheet: https://docs.google.com/spreadsheets/d/{self.sheet_id}\n"
					f"2. Click 'Share' button (top right)\n"
					f"3. Add this email as Editor: {sa_email}\n"
					f"4. The service account email is in your JSON file under 'client_email'\n"
					f"5. Retry the operation"
				)
			raise

	def get_last_n_rows(self, n: int = 10, sheet_name: str = "Sheet1") -> List[List[Any]]:
		resp = (
			self.service.spreadsheets().values().get(
				spreadsheetId=self.sheet_id,
				range=f"{sheet_name}!A:U",
			)
			.execute()
		)
		values = resp.get("values", [])
		if not values:
			return []
		# Skip header row if first row starts with "Index"
		if values and len(values) > 0 and values[0] and len(values[0]) > 0 and values[0][0] == "Index":
			data_rows = values[1:]  # Skip header
		else:
			data_rows = values
		# Return last N data rows
		return data_rows[-n:] if len(data_rows) > n else data_rows


def local_csv_backup(path: str, rows: List[List[Any]]) -> None:
	ensure_dir(os.path.dirname(path))
	write_header = not os.path.exists(path)
	with open(path, "a", newline="", encoding="utf-8") as f:
		writer = csv.writer(f)
		if write_header:
			writer.writerow(SHEET_HEADERS)
		writer.writerows(rows)
	logger.info("backup.csv.appended", path=path, rows=len(rows))
