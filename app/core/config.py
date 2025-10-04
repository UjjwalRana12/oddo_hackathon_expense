from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    app_name: str = "Expense Reimbursement System"
    debug: bool = True
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str = "sqlite:///./expense_system.db"
    
    # External APIs
    countries_api_url: str = "https://restcountries.com/v3.1/all?fields=name,currencies"
    exchange_rate_api_url: str = "https://api.exchangerate-api.com/v4/latest"
    
    # Upload settings
    upload_dir: str = "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    class Config:
        env_file = ".env"

settings = Settings()