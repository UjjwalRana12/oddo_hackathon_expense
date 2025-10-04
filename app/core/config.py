from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, List
import os
import secrets

class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")
    
    # Application settings
    app_name: str = "Expense Reimbursement System"
    debug: bool = False
    environment: str = "production"
    secret_key: str = secrets.token_urlsafe(32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Database
    database_url: str = "postgresql://username:password@hostname:5432/expense_system"
    
    # External APIs
    countries_api_url: str = "https://restcountries.com/v3.1/all?fields=name,currencies"
    exchange_rate_api_url: str = "https://api.exchangerate-api.com/v4/latest"
    
    # Upload settings
    upload_dir: str = "/tmp/uploads" if os.getenv("ENVIRONMENT") == "production" else "uploads"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    email_user: str = ""
    email_password: str = ""
    
    # Rate limiting
    rate_limit_per_minute: int = 60
    
    # Logging
    log_level: str = "INFO"
    
    # Production optimizations
    workers: int = 4
    max_connections: int = 1000
    keepalive: int = 2

# Production-specific settings
class ProductionSettings(Settings):
    debug: bool = False
    environment: str = "production"
    log_level: str = "WARNING"
    
# Development-specific settings  
class DevelopmentSettings(Settings):
    debug: bool = True
    environment: str = "development"
    database_url: str = "sqlite:///./expense_system.db"
    cors_origins: str = "*"
    trusted_hosts: str = "localhost,127.0.0.1"
    log_level: str = "DEBUG"

def get_settings():
    environment = os.getenv("ENVIRONMENT", "development")
    if environment == "production":
        return ProductionSettings()
    return DevelopmentSettings()

settings = get_settings()