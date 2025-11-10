from __future__ import annotations
import json
import os
import subprocess
import tempfile
from typing import Optional, Dict, Any

from .config import get_settings
from .logging_setup import logger


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
	return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


def download_reel(url: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
	settings = get_settings()
	workdir = out_dir or settings.temp_dir
	os.makedirs(workdir, exist_ok=True)
	logger.info("download.start", url=url)

	# Try yt-dlp first
	out_tmpl = os.path.join(workdir, "%(id)s.%(ext)s")
	cmd = [
		"yt-dlp",
		"--no-call-home",
		"--no-progress",
		"--write-info-json",
		"-o", out_tmpl,
		url,
	]
	res = _run(cmd)
	if res.returncode == 0:
		logger.info("download.ytdlp.ok")
		# Find info json
		info_json = None
		for fn in os.listdir(workdir):
			if fn.endswith(".info.json"):
				info_json = os.path.join(workdir, fn)
				break
		video_path = None
		for fn in os.listdir(workdir):
			if fn.endswith((".mp4", ".mkv", ".webm")):
				video_path = os.path.join(workdir, fn)
				break
		meta = {}
		if info_json and os.path.exists(info_json):
			with open(info_json, "r", encoding="utf-8") as f:
				meta = json.load(f)
		caption = meta.get("description") or meta.get("title") or ""
		return {"video_path": video_path, "caption": caption, "metadata": meta}

	logger.warn("download.ytdlp.failed", stderr=res.stderr[:500])

	# Fallback: instaloader (may require public content)
	try:
		from instaloader import Instaloader, Post
		L = Instaloader(dirname_pattern=workdir, download_videos=False, save_metadata=True)
		shortcode = url.rstrip("/").split("/")[-1]
		post = Post.from_shortcode(L.context, shortcode)
		caption = post.caption or ""
		# instaloader video download
		L.download_post(post, target=shortcode)
		video_path = None
		for fn in os.listdir(workdir):
			if fn.endswith((".mp4", ".mkv", ".webm")):
				video_path = os.path.join(workdir, fn)
				break
		return {"video_path": video_path, "caption": caption, "metadata": {"shortcode": shortcode}}
	except Exception as e:
		logger.error("download.instaloader.failed", error=str(e))
		return {"video_path": None, "caption": None, "metadata": {}}
