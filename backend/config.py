"""
Configuration management for vAIdya application.
Loads settings from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables."""
    
    # Application
    APP_NAME: str = os.getenv("APP_NAME", "vAIdya")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:8000"
    ).split(",")
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    MAX_UPLOAD_SIZE_BYTES: int = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    ALLOWED_AUDIO_FORMATS: List[str] = os.getenv(
        "ALLOWED_AUDIO_FORMATS", 
        ".m4a,.wav,.mp3,.ogg"
    ).split(",")
    
    # ML Models
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "Systran/faster-distil-whisper-large-v2")
    WHISPER_DEVICE: str = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    AUDIO_CHUNK_LENGTH_SECONDS: int = int(os.getenv("AUDIO_CHUNK_LENGTH_SECONDS", "20"))
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vaidya.db")
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    AUDIO_DIR: Path = BASE_DIR / os.getenv("AUDIO_DIR", "audio")
    TRANSCRIPTS_DIR: Path = BASE_DIR / os.getenv("TRANSCRIPTS_DIR", "transcripts")
    FRONTEND_DIR: Path = BASE_DIR / os.getenv("FRONTEND_DIR", "frontend")
    
    def __init__(self):
        """Ensure required directories exist."""
        self.AUDIO_DIR.mkdir(exist_ok=True)
        self.TRANSCRIPTS_DIR.mkdir(exist_ok=True)
        
    @property
    def max_upload_size_display(self) -> str:
        """Human-readable upload size limit."""
        return f"{self.MAX_UPLOAD_SIZE_MB}MB"

# Global settings instance
settings = Settings()
