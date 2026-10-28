"""
FYP Speech Processing Pipeline
"""

__version__ = "0.1.0"
__author__ = "M. Hassan Azmat & Wajeeha Islam & Kinza Aslam"

from .config import (
    TRANSLATION_CONFIG,
    TTS_CONFIG,
    PROJECT_ROOT,
    OUTPUT_DIR,
)

__all__ = [
    "TRANSLATION_CONFIG",
    "TTS_CONFIG",
    "PROJECT_ROOT",
    "OUTPUT_DIR",
]