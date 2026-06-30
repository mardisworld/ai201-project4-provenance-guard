import os

from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "3000"))
RATE_LIMIT_SUBMIT = os.getenv("RATE_LIMIT_SUBMIT", "12 per 15 minutes")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
GROQ_API_URL = os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1/chat/completions")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "provenance_guard.db")