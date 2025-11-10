FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=180 \
    PIP_NO_CACHE_DIR=1 \
    CT2_USE_MMAP=0 \
    TESSERACT_CMD=/usr/bin/tesseract \
    PATH="/usr/bin:${PATH}"

# System deps: ffmpeg, tesseract, curl, libgomp1 (for ctranslate2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    tesseract-ocr \
    libgl1 \
    libgomp1 \
    curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
# Upgrade pip and core tooling, then install with higher timeout/retries
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --retries 10 --timeout 300 --progress-bar off -r requirements.txt

# Create dirs
RUN mkdir -p /app/src /app/data /tmp/ai_agent /secrets

COPY . /app

# Expose FastAPI port
EXPOSE 8080

ENV TEMP_DIR=/tmp/ai_agent

# Default command runs both Telegram bot and FastAPI
CMD ["python", "main.py"]
