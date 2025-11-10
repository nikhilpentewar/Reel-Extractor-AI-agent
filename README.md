## Telegram Reel Extractor AI Agent

A production-ready, modular, secure Telegram-based AI agent that accepts Instagram Reel links, extracts structured items (multiple per reel), enriches them (OpenStreetMap / product lookup), and appends each item to a Google Sheet.

### Features
- Accept an Instagram Reel URL in Telegram and process end-to-end
- Download reel (video + metadata), fall back to caption if private/unavailable
- Audio speech-to-text (local faster-whisper by default; OpenAI optional)
- Frame OCR (Tesseract)
- LLM-based item extraction (place/product/service/other) with confidence & notes
- Enrichment: OpenStreetMap (Nominatim) geocoding + distance; product price/link stub
- Append each item to a Google Sheet
- Commands: `/start`, `/help`, `/download`, `/summary [N]`, `/health`
- FastAPI health/summary/download endpoints (optional)
- Dockerized, logging + basic metrics, unit tests, sample data

### Repo Structure
```
.
├── Dockerfile
├── requirements.txt
├── main.py
├── src/
│   └── agent/
│       ├── api.py
│       ├── bot.py
│       ├── config.py
│       ├── downloader.py
│       ├── enrich.py
│       ├── llm.py
│       ├── logging_setup.py
│       ├── media.py
│       ├── pipeline.py
│       ├── sheets.py
│       └── utils.py
├── tests/
│   └── test_schema.py
├── data/
│   └── sample_reel.txt
└── examples/
    └── sample_output.json
```

### Environment Variables
Create a `.env` file:
```
TELEGRAM_TOKEN=xxxx
GOOGLE_SA_JSON_PATH=/secrets/google-service-account.json
GOOGLE_SHEET_ID=1AbcDEfGh...
# OpenAI is optional if you set WHISPER_BACKEND=openai or for LLM extraction
OPENAI_API_KEY=sk-xxx
# Google Maps is optional; not required when using Nominatim (default)
GOOGLE_MAPS_API_KEY=
# Whisper settings
WHISPER_BACKEND=local         # local | openai
WHISPER_LOCAL_MODEL=small     # tiny|base|small|medium|large-v3 (CPU-friendly: small)
WHISPER_MODEL=whisper-1       # only used when WHISPER_BACKEND=openai
TEMP_DIR=/tmp/ai_agent
BOT_MODE=both                 # bot | api | both
PORT=8080
SHEET_TRAVEL_ID=              # optional; leave empty to use GOOGLE_SHEET_ID
SHEET_PRODUCTS_ID=            # optional; leave empty to use GOOGLE_SHEET_ID
LOG_LEVEL=INFO
```

### Notes about Free Tools
- Geocoding uses OpenStreetMap Nominatim (no API key), with a required User-Agent header per OSM policy.
- Transcription uses faster-whisper locally by default. CPU works with compute_type=int8; choose `WHISPER_LOCAL_MODEL` by hardware.
- You can switch to OpenAI Whisper by setting `WHISPER_BACKEND=openai` and providing `OPENAI_API_KEY`.

### Google Cloud Setup (Sheets API)
1. Create a Google Cloud project and enable Google Sheets API.
2. Create a Service Account and download its JSON key. Mount it to `/secrets/google-service-account.json`.
3. Share your target Google Sheets document with the service account email.
4. Set `GOOGLE_SA_JSON_PATH` and `GOOGLE_SHEET_ID` (plus domain-specific sheet IDs if using multiple).

### Telegram Bot Setup
1. Talk to `@BotFather` to create a bot and get the token.
2. Set `TELEGRAM_TOKEN` in `.env`.

### Running Locally
```
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Docker
```
docker build -t reel-agent .
docker run --rm -it \
  -e TELEGRAM_TOKEN=... \
  -e OPENAI_API_KEY=... \
  -e GOOGLE_MAPS_API_KEY=... \
  -e GOOGLE_SA_JSON_PATH=/secrets/google-service-account.json \
  -e GOOGLE_SHEET_ID=... \
  -v $PWD/secrets:/secrets \
  -p 8080:8080 \
  reel-agent
```

### Usage
- Send a public Instagram Reel URL to the bot. It will reply with progress and final confirmation (row numbers or count).
- `/download` returns the current local CSV backup.
- `/summary [N]` returns the last N rows.
- `/health` returns service health JSON.

### Tests
```
pytest -q
```

### Sample Demo
Input reel: see `data/sample_reel.txt`.
Expected extracted items JSON: `examples/sample_output.json`.
Rows will be appended in your configured Google Sheet.

### Notes
- Ensure `ffmpeg` and `tesseract` are installed (Dockerfile handles this).
- Private reels may not download; the bot will ask for caption or a public link.
- The system is modular; extend `llm.py` parsing and `enrich.py` for new content types.
