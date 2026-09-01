import os
import tempfile
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "RevenueGuard AI"
    APP_TAGLINE: str = "Permissioned Autonomous Merchant Agent"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Environment Mode: "DEMO_SANDBOX" or "RAZORPAY_TEST_MODE"
    ENVIRONMENT_MODE: str = "DEMO_SANDBOX"
    
    # Razorpay Test Mode Credentials (Optional - if omitted, runs in DEMO SANDBOX)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    
    # Optional LLM API Key
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    
    # Safety Engine Policy Limits
    MAX_RECOVERY_AMOUNT_INR: float = 50000.0  # Max ceiling ₹50,000 per recovery action
    RECOVERY_WINDOW_DAYS: int = 7             # Max age of failed order eligible for recovery
    REQUIRE_MERCHANT_APPROVAL: bool = True    # Mandatory human gate
    MAX_SIMULTANEOUS_RETRIES: int = 3         # Circuit breaker threshold
    
    # SQLite Database File (Uses /tmp on Vercel/serverless environments)
    DATABASE_PATH: str = os.path.join("/tmp", "revenueguard.db") if os.environ.get("VERCEL") else "revenueguard.db"

settings = Settings()

# Automatically switch environment mode if real Razorpay test keys are present
if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
    settings.ENVIRONMENT_MODE = "RAZORPAY_TEST_MODE"
else:
    settings.ENVIRONMENT_MODE = "DEMO_SANDBOX"
