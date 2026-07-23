"""
Configuration module for the bot
Loads environment variables from .env file
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()

# Database configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'bot_database.db')

# Validate required settings
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

if not ADMIN_ID:
    raise ValueError("ADMIN_ID is not set in .env file")

try:
    ADMIN_ID = int(ADMIN_ID)
except ValueError:
    raise ValueError("ADMIN_ID must be an integer")

# Log configuration loaded
logger = logging.getLogger(__name__)
logger.info(f"Configuration loaded successfully")
logger.info(f"Admin ID: {ADMIN_ID}")
logger.info(f"Log level: {LOG_LEVEL}")
logger.info(f"Database path: {DATABASE_PATH}")
