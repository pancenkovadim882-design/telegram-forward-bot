"""
Message forwarding handler
Forwards text messages between configured groups
"""

import logging
from typing import List

from aiogram import Dispatcher, Bot
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram import F

from database import Database

logger = logging.getLogger(__name__)


async def handle_text_message(message: Message, bot: Bot, db: Database) -> None:
    """
    Handle incoming text messages and forward them
    
    Only forwards:
    - Text messages
    - From configured source groups
    - To configured destination groups
    """
    
    # Only process text messages
    if not message.text:
        return
    
    # Get source chat ID
    source_chat_id = message.chat.id
    
    # Get configured destinations for this source
    destinations = await db.get_forwardings(source_chat_id)
    
    if not destinations:
        # No forwarding configured for this chat
        return
    
    try:
        # Save group info
        group_name = message.chat.title or message.chat.first_name or f"Chat {source_chat_id}"
        await db.save_group_info(source_chat_id, group_name)
        
        # Forward to each destination
        for destination_id in destinations:
            try:
                await bot.send_message(
                    chat_id=destination_id,
                    text=message.text,
                    parse_mode="HTML",  # Preserve formatting
                    disable_web_page_preview=True
                )
                
                logger.debug(f"Message forwarded: {source_chat_id} -> {destination_id}")
                
            except Exception as e:
                logger.error(
                    f"Error forwarding message to {destination_id}: {e}",
                    exc_info=True
                )
                # Continue forwarding to other destinations
                continue
    
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)


async def handle_group_message(message: Message, bot: Bot, db: Database) -> None:
    """Handle messages from groups"""
    await handle_text_message(message, bot, db)


async def handle_private_message(message: Message) -> None:
    """Handle private messages"""
    if message.text and message.text.startswith('/'):
        # Command will be handled by command handlers
        return
    
    # Ignore non-command private messages
    logger.debug(f"Ignored private message from {message.from_user.id}")


def setup_message_handlers(dp: Dispatcher, db: Database) -> None:
    """Setup message forwarding handlers"""

    async def group_message_handler(message: Message, bot: Bot):
        await handle_group_message(message, bot, db)

    dp.message.register(
        group_message_handler,
        F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP})
    )

    dp.message.register(
        handle_private_message,
        F.chat.type == ChatType.PRIVATE
    )

    logger.info("Message handlers registered")
