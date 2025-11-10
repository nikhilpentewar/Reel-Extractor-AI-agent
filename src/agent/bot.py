from __future__ import annotations
import asyncio
import os
from io import BytesIO
from typing import Optional

from telegram import Update, InputFile
from telegram.ext import (
	Application,
	ApplicationBuilder,
	CommandHandler,
	MessageHandler,
	ContextTypes,
	filters,
)

from .config import get_settings
from .logging_setup import configure_logging, logger
from .pipeline import process_reel_url
from .sheets import SheetsClient
from .utils import is_valid_reel_url


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await update.message.reply_text(
		"Hi! 👋\n\n"
		"Send me an Instagram Reel URL and I will extract items, enrich them, and append to the sheet.\n\n"
		"📋 Use /sheet to get your spreadsheet link\n"
		"📥 Use /download to download CSV backup\n"
		"📊 Use /summary [N] to see last N rows\n"
		"❓ Use /help for all commands"
	)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await update.message.reply_text(
		"Commands:\n/start - Start the bot\n/help - Show this help\n/sheet - Get spreadsheet link\n/download - Download CSV backup\n/summary [N] - Show last N rows\n/health - Check bot status\n\nSend a public Instagram Reel URL to process."
	)

async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	await update.message.reply_text("OK")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	settings = get_settings()
	n = 10
	if context.args:
		try:
			n = max(1, min(100, int(context.args[0])))
		except Exception:
			pass
	client = SheetsClient()
	rows = client.get_last_n_rows(n)
	lines = [", ".join(map(str, r[:8])) for r in rows[-n:]]
	await update.message.reply_text("Last rows:\n" + "\n".join(lines[-n:]))

async def download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	settings = get_settings()
	backup = os.path.join(settings.temp_dir, "backup.csv")
	if not os.path.exists(backup):
		await update.message.reply_text("No local backup yet.")
		return
	with open(backup, "rb") as f:
		await update.message.reply_document(document=InputFile(f, filename="backup.csv"))

async def sheet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	settings = get_settings()
	
	# Build message with all available sheet links
	message_parts = ["📊 Your Spreadsheet Links:\n"]
	has_sheets = False
	
	# Default sheet
	if settings.google_sheet_id:
		default_url = f"https://docs.google.com/spreadsheets/d/{settings.google_sheet_id}/edit"
		message_parts.append(f"📋 Default Sheet:\n{default_url}\n")
		has_sheets = True
	
	# Travel sheet
	if settings.sheet_travel_id:
		travel_url = f"https://docs.google.com/spreadsheets/d/{settings.sheet_travel_id}/edit"
		message_parts.append(f"✈️ Travel Sheet:\n{travel_url}\n")
		has_sheets = True
	
	# Products sheet
	if settings.sheet_products_id:
		products_url = f"https://docs.google.com/spreadsheets/d/{settings.sheet_products_id}/edit"
		message_parts.append(f"🛍️ Products Sheet:\n{products_url}\n")
		has_sheets = True
	
	if not has_sheets:
		# No sheets configured
		await update.message.reply_text(
			"⚠️ No spreadsheet configured. Please set GOOGLE_SHEET_ID in your environment variables."
		)
	else:
		message = "\n".join(message_parts)
		message += "\n💡 Tip: Click the links above to open your spreadsheets in Google Sheets."
		await update.message.reply_text(message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
	text = update.message.text or ""
	if not is_valid_reel_url(text):
		return
	await update.message.reply_text("Processing… This may take up to ~1-2 minutes.")
	try:
		start_idx, end_idx, items = process_reel_url(text)
		count = len(items)
		await update.message.reply_text(
			f"✅ Done — added {count} item(s) to sheet. Rows: {start_idx}-{end_idx}\n\n"
			f"📊 Use /sheet to view your spreadsheet"
		)
	except ValueError as e:
		logger.error("bot.process.validation.failed", error=str(e))
		await update.message.reply_text(f"⚠️ Validation error: {str(e)}")
	except PermissionError as e:
		logger.error("bot.process.permission.failed", error=str(e))
		# Send the helpful error message about sharing the sheet
		error_msg = str(e)
		await update.message.reply_text(f"⚠️ {error_msg[:1000]}")
	except FileNotFoundError as e:
		logger.error("bot.process.file_not_found", error=str(e))
		await update.message.reply_text("⚠️ File not found error. Check Docker logs for details.")
	except Exception as e:
		logger.error("bot.process.failed", error=str(e), error_type=type(e).__name__)
		error_msg = str(e)
		# Truncate long error messages but keep important parts
		if len(error_msg) > 500:
			error_msg = error_msg[:500] + "... (see logs for full error)"
		await update.message.reply_text(f"⚠️ Failed to process: {error_msg}")


async def run_telegram_bot() -> None:
	settings = get_settings()
	configure_logging(settings.log_level)
	if not settings.telegram_token:
		raise RuntimeError("TELEGRAM_TOKEN not set")
	app: Application = ApplicationBuilder().token(settings.telegram_token).build()
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler("help", help_cmd))
	app.add_handler(CommandHandler("health", health))
	app.add_handler(CommandHandler("summary", summary))
	app.add_handler(CommandHandler("download", download))
	app.add_handler(CommandHandler("sheet", sheet))
	app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
	logger.info("bot.starting")
	# Manage lifecycle within existing event loop
	max_retries = 3
	for attempt in range(max_retries):
		try:
			await app.initialize()
			# Make sure no webhook/updates conflict remains
			try:
				await app.bot.delete_webhook(drop_pending_updates=True)
			except Exception as e:
				logger.warn("bot.webhook.delete.failed", error=str(e))
			await app.start()
			await app.updater.start_polling()
			stop_event = asyncio.Event()
			try:
				await stop_event.wait()  # run until cancelled
			finally:
				await app.updater.stop()
				await app.stop()
				await app.shutdown()
			break
		except Exception as e:
			logger.error("bot.init.failed", attempt=attempt+1, error=str(e), error_type=type(e).__name__)
			if attempt < max_retries - 1:
				await asyncio.sleep(5 * (attempt + 1))
			else:
				raise
