"""
Main Telegram Bot Module
Forwards text messages between configured groups
"""

import asyncio
import logging
import sys
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.types import Message, User
from aiogram.filters import Command
from aiogram.enums import ChatType
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_ID, LOG_LEVEL
from database import Database
from admin import setup_admin_handlers
from messages import setup_message_handlers

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot, db: Database) -> None:
    """Called when bot starts"""
    logger.info("Bot is starting up...")
    
    try:
        # Check bot connection
        bot_info = await bot.get_me()
        logger.info(f"Bot connected: {bot_info.username} (@{bot_info.username})")
        
        # Initialize database
        await db.init()
        logger.info("Database initialized successfully")
        
        # Send notification to admin
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text="🟢 Bot started successfully!\n\nUse /help for available commands."
            )
        except Exception as e:
            logger.warning(f"Could not send startup notification to admin: {e}")
            
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


async def on_shutdown(bot: Bot, db: Database) -> None:
    """Called when bot shuts down"""
    logger.info("Bot is shutting down...")
    await bot.session.close()
    await db.close()
    logger.info("Bot shutdown complete")


async def main() -> None:
    """Main bot function"""
    try:
        # Initialize components
        db = Database()
        bot = Bot(token=BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        
        # Setup startup and shutdown
        await on_startup(bot, db)
        
        # Register handlers
        setup_admin_handlers(dp, db)
        setup_message_handlers(dp, db)
        
        # Start polling
        logger.info("Starting polling...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            on_startup=lambda: on_startup(bot, db),
            skip_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, db)


if __name__ == "__main__":
    asyncio.run(main())
