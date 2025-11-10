from __future__ import annotations
import os
from fastapi import FastAPI, Query, Response
from fastapi.responses import PlainTextResponse, StreamingResponse

from .config import get_settings
from .logging_setup import configure_logging
from .sheets import SheetsClient


settings = get_settings()
configure_logging(settings.log_level)
app = FastAPI(title="Reel Extractor AI Agent")


@app.get("/health")
def health():
	return {"status": "ok"}


@app.get("/summary", response_class=PlainTextResponse)
def summary(n: int = Query(10, ge=1, le=100)):
	client = SheetsClient()
	rows = client.get_last_n_rows(n)
	lines = [", ".join(map(str, r[:8])) for r in rows[-n:]]
	return "\n".join(lines[-n:])


@app.get("/download")
def download():
	backup = os.path.join(settings.temp_dir, "backup.csv")
	if not os.path.exists(backup):
		return Response(status_code=404, content="No local backup yet.")
	return StreamingResponse(open(backup, "rb"), media_type="text/csv", headers={
		"Content-Disposition": "attachment; filename=backup.csv"
	})
