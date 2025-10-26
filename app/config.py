import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application configuration from environment variables"""

    # App
    app_name: str = "Receptionist AI"
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./receptionist_ai.db")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Google Calendar
    google_calendar_credentials: str = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "")
    google_calendar_id: str = os.getenv("GOOGLE_CALENDAR_ID", "")

    # Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_phone_number: str = os.getenv("TWILIO_PHONE_NUMBER", "")
    owner_phone_number: str = os.getenv("OWNER_PHONE_NUMBER", "")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
