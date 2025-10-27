"""
Configuration settings for the Laptop Price Intelligence System
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration"""
    
    # App settings
    APP_NAME = "Laptop Price Intelligence System"
    APP_VERSION = "1.0.0"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/tracker.db")
    
    # API Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    PASSWORD_MIN_LENGTH = 8
    SESSION_TIMEOUT_MINUTES = 30
    
    # Scraping settings
    SCRAPE_INTERVAL_HOURS = 6
    RATE_LIMIT_DELAY = 2  # seconds between requests
    MAX_RETRIES = 3
    
    # Alert settings
    ALERT_CHECK_INTERVAL_HOURS = 1
    DEFAULT_PRICE_THRESHOLD = 10  # percentage
    
    # ML Model settings
    PREDICTION_DAYS_AHEAD = 7
    MIN_TRAINING_DATA_POINTS = 30
    
    # UI settings
    CHARTS_COLOR_PALETTE = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
    MAX_CHAT_HISTORY = 50
    
    # Platform settings
    SUPPORTED_PLATFORMS = ['amazon', 'flipkart']
    SUPPORTED_BRANDS = ['Dell', 'HP', 'Lenovo', 'ASUS', 'Acer', 'Apple', 'MSI']
    
    # Feature flags
    ENABLE_AUTO_REFRESH = True
    ENABLE_EMAIL_ALERTS = False
    ENABLE_SMS_ALERTS = False
    DEBUG_MODE = os.getenv("DEBUG", "False").lower() == "true"

# Create config instance
config = Config()