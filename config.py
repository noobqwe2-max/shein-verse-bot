"""
Configuration for Shein Verse Bot
"""

import os
import random

class Config:
    # Telegram Configuration
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
    
    # Shein URLs
    SHEIN_VERSE_URL = "https://www.shein.in/c/sverse-5939-37961"
    SHEIN_MEN_URL = "https://www.shein.in/shein-verse-men-c-2513.html"
    
    # Bot Settings
    CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '5'))  # minutes
    ENABLE_ANTI_DETECTION = True
    MAX_RETRIES = 3
    
    # Anti-Detection Settings
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'
    ]
    
    # Database
    DB_PATH = "shein_products.db"
    
    @staticmethod
    def get_random_user_agent():
        return random.choice(Config.USER_AGENTS)
    
    @staticmethod
    def get_random_delay():
        return random.uniform(2, 5)
