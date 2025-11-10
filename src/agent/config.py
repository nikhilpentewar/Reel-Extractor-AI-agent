import os
from pydantic import BaseModel


class Settings(BaseModel):
	telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
	google_sa_json_path: str | None = os.getenv("GOOGLE_SA_JSON_PATH")
	google_sheet_id: str | None = os.getenv("GOOGLE_SHEET_ID")
	sheet_travel_id: str | None = os.getenv("SHEET_TRAVEL_ID")
	sheet_products_id: str | None = os.getenv("SHEET_PRODUCTS_ID")
	openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
	use_llm: bool = os.getenv("USE_LLM", "false").lower() in ("1", "true", "yes")
	google_maps_api_key: str | None = os.getenv("GOOGLE_MAPS_API_KEY")
	whisper_model: str = os.getenv("WHISPER_MODEL", "whisper-1")
	whisper_backend: str = os.getenv("WHISPER_BACKEND", "local")  # local | openai
	whisper_local_model: str = os.getenv("WHISPER_LOCAL_MODEL", "small")
	temp_dir: str = os.getenv("TEMP_DIR", "/tmp/ai_agent")
	admin_chat_id: str | None = os.getenv("ADMIN_CHAT_ID")
	log_level: str = os.getenv("LOG_LEVEL", "INFO")

	class Config:
		arbitrary_types_allowed = True


def get_settings() -> Settings:
	return Settings()
