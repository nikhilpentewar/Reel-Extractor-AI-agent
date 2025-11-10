from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
from typing import List, Dict, Any

import cv2
import pytesseract
from .config import get_settings
from .logging_setup import logger
from .utils import ensure_dir

# Set tesseract path - default to /usr/bin/tesseract (Docker/Linux) or use env var
_tess_cmd = os.getenv("TESSERACT_CMD")
if not _tess_cmd:
	# Try common Linux paths
	for path in ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]:
		if os.path.exists(path):
			_tess_cmd = path
			break
if _tess_cmd:
	pytesseract.pytesseract.tesseract_cmd = _tess_cmd
	logger.info("tesseract.path.set", path=_tess_cmd)
else:
	logger.warn("tesseract.not.found")

# Check for ffmpeg - try common paths
_ffmpeg_path = shutil.which("ffmpeg")
if not _ffmpeg_path:
	# Try common Linux paths
	for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
		if os.path.exists(path):
			_ffmpeg_path = path
			break
if _ffmpeg_path:
	logger.info("ffmpeg.path.set", path=_ffmpeg_path)
else:
	logger.warn("ffmpeg.not.found.in.path")


def extract_audio(video_path: str, out_dir: str) -> str | None:
	if not video_path or not os.path.exists(video_path):
		logger.error("extract_audio.video_not_found", path=video_path)
		return None
	ensure_dir(out_dir)
	audio_path = os.path.join(out_dir, "audio.wav")
	ffmpeg_cmd = _ffmpeg_path or "ffmpeg"
	cmd = [
		ffmpeg_cmd, "-y", "-i", video_path,
		"-vn", "-ac", "1", "-ar", "16000", "-f", "wav", audio_path
	]
	try:
		res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120)
		if res.returncode != 0:
			logger.error("ffmpeg.audio.failed", returncode=res.returncode, stderr=res.stderr[:200])
			return None
		if not os.path.exists(audio_path):
			logger.error("ffmpeg.audio.output_missing", path=audio_path)
			return None
		return audio_path
	except FileNotFoundError:
		logger.error("ffmpeg.command.not.found", cmd=ffmpeg_cmd)
		return None
	except subprocess.TimeoutExpired:
		logger.error("ffmpeg.audio.timeout")
		return None
	except Exception as e:
		logger.error("ffmpeg.audio.exception", error=str(e), error_type=type(e).__name__)
		return None


def transcribe_audio(audio_path: str) -> str:
	settings = get_settings()
	backend = settings.whisper_backend.lower()
	if backend == "openai":
		try:
			from openai import OpenAI
			client = OpenAI(api_key=settings.openai_api_key)
			with open(audio_path, "rb") as f:
				resp = client.audio.transcriptions.create(
					model=settings.whisper_model,
					file=f,
				)
			return resp.text or ""
		except Exception as e:
			logger.warn("whisper.openai.failed", error=str(e))
	# default: local faster-whisper
	try:
		from faster_whisper import WhisperModel
		model_size = settings.whisper_local_model
		model = WhisperModel(model_size, device="cpu", compute_type="int8")
		segments, info = model.transcribe(audio_path, beam_size=1)
		text_parts = [seg.text.strip() for seg in segments if getattr(seg, "text", "").strip()]
		return " ".join(text_parts)
	except Exception as e:
		logger.error("whisper.local.failed", error=str(e))
		return ""


def extract_keyframes(video_path: str, out_dir: str, max_frames: int = 8) -> List[str]:
	ensure_dir(out_dir)
	cap = cv2.VideoCapture(video_path)
	if not cap.isOpened():
		logger.warn("extract_keyframes.video_not_opened", path=video_path)
		return []
	frames = []
	length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
	interval = max(1, length // max_frames)
	idx = 0
	count = 0
	while count < max_frames:
		cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
		ok, frame = cap.read()
		if not ok:
			break
		# Use os.path.join and normalize path (handles Windows/Linux differences)
		frame_path = os.path.normpath(os.path.join(out_dir, f"frame_{count:02d}.png"))
		cv2.imwrite(frame_path, frame)
		if os.path.exists(frame_path):
			frames.append(frame_path)
		count += 1
		idx += interval
	cap.release()
	return frames


def ocr_images(image_paths: List[str]) -> str:
	texts = []
	for p in image_paths:
		try:
			text = pytesseract.image_to_string(p) or ""
			if text.strip():
				texts.append(text.strip())
		except Exception as e:
			logger.warn("ocr.image.failed", path=p, error=str(e))
	return "\n".join(texts)


def process_media(video_path: str, work_dir: str) -> Dict[str, Any]:
	audio_path = extract_audio(video_path, work_dir) if video_path else None
	transcript = ""
	if audio_path and os.path.exists(audio_path):
		try:
			transcript = transcribe_audio(audio_path)
		except Exception as e:
			logger.warn("whisper.failed", error=str(e))
	frames = extract_keyframes(video_path, work_dir) if video_path else []
	ocr_text = ocr_images(frames) if frames else ""
	return {
		"transcript": transcript,
		"ocr_text": ocr_text,
		"frames": frames,
		"audio_path": audio_path,
	}
