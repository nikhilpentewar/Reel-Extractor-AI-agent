import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Mode: bot | api | both
MODE = os.getenv("BOT_MODE", "both").lower()

async def run_bot():
	from src.agent.bot import run_telegram_bot
	await run_telegram_bot()

async def run_api():
	import uvicorn
	from src.agent.api import app
	config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)), log_level="info")
	server = uvicorn.Server(config)
	await server.serve()

async def main():
	tasks = []
	if MODE in ("bot", "both"):
		tasks.append(asyncio.create_task(run_bot()))
	if MODE in ("api", "both"):
		tasks.append(asyncio.create_task(run_api()))
	if not tasks:
		print("Nothing to run. Set BOT_MODE to bot|api|both.")
		return
	await asyncio.gather(*tasks)

if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		pass
