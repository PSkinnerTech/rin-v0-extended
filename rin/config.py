import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Base paths
HOME_DIR = Path.home()
RIN_DIR = HOME_DIR / ".rin"
LOG_DIR = RIN_DIR / "logs"
AUDIO_DIR = RIN_DIR / "audio"

# Ensure directories exist
RIN_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# API keys and credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CLOUD_CREDENTIALS")

# Engine options
TTS_ENGINE = os.getenv("TTS_ENGINE", "google")
STT_ENGINE = os.getenv("STT_ENGINE", "whisper")

# Application settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")

# Default system prompt
SYSTEM_PROMPT = "You are Rin, a helpful personal assistant. Be concise but thorough."
