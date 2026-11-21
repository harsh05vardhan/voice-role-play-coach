"""Central place for settings. Secrets come from environment variables (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
LLM_MODEL = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
STT_MODEL = os.getenv("STT_MODEL", "whisper-large-v3-turbo")
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-GuyNeural")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "roleplay_coach")

MAX_HISTORY_MESSAGES = 20  # how many past messages the LLM sees each turn
