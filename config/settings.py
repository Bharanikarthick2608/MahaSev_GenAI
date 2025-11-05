"""
Configuration settings for the application.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "")
    
    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # P-Score weights (customizable)
    P_SCORE_WEIGHTS: dict = {
        "hvi": float(os.getenv("P_SCORE_WEIGHT_HVI", "0.4")),
        "iss": float(os.getenv("P_SCORE_WEIGHT_ISS", "0.3")),
        "rcs": float(os.getenv("P_SCORE_WEIGHT_RCS", "0.3"))
    }
    
    # Application
    APP_NAME: str = "Cross-Sectoral Intelligence Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"


settings = Settings()

