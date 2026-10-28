"""
FYP Project Configuration
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# ========================================
# API CONFIGURATION
# ========================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in .env file")


# ========================================
# TRANSLATION CONFIGURATION
# ========================================

TRANSLATION_CONFIG = {
    "model": "llama-3.3-70b-versatile",
    "temperature": 0.1,             # Lower = more consistent
    "max_tokens": 500,
    "api_key": GROQ_API_KEY,
}

# ========================================
# TTS CONFIGURATION
# ========================================

TTS_CONFIG = {
    "model_name": "facebook/mms-tts-eng",
    "device": "cuda",               # cuda or cpu
    "sample_rate": 16000,
}

# ========================================
# PATHS
# ========================================

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
AUDIO_DIR = DATA_DIR / "audio"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLE_AUDIO_DIR = PROJECT_ROOT / "sample_audio"
MODELS_DIR = PROJECT_ROOT / "models" / "cache"

# Create directories if they don't exist
for directory in [DATA_DIR, AUDIO_DIR, OUTPUT_DIR, SAMPLE_AUDIO_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

