"""
Admin commands handler
Commands: /connect, /disconnect, /status, /help
"""

import logging
from typing import Optional

from aiogram import Dispatcher, Bot
from aiogram.types import Message, User
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database import Database

logger = logging.getLogger(__name__)


class ForwardingStates(StatesGroup):
    """FSM states for forwarding setup"""
    waiting_for_source = State()
    waiting_for_destination = State()


async def check_admin(message: Message) -> bool:
    """Check if user is admin"""
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Access denied. Only admin can use this command.")
        logger.warning(f"Unauthorized access attempt from user {message.from_user.id}")
        return False
    return True


async def cmd_help(message: Message) -> None:
    """Help command"""
    if not await check_admin(message):
        return
    
    help_text = """
🤖 **Telegram Message Forwarder Bot**

**Available Commands:**

🔗 `/connect` - Start setting up message forwarding
   - You'll be asked to provide source and destination group IDs

🔌 `/disconnect` - Remove forwarding between groups
   - You'll need to provide source and destination group IDs

📊 `/status` - Show all active forwarding connections

❓ `/help` - Show this message

**How to Get Group IDs:**
1. Add bot to your groups
2. Forward a message from that group to Saved Messages
3. Open the forwarded message
4. Open Developer Tools (Browser Console)
5. Right-click the message → Inspect → Look for 'data-group-id' or message ID

Alternatively:
- Use @userinfobot or similar tools to get group IDs
- Group IDs are negative numbers (e.g., -1001234567890)

**Features:**
✅ Forwards only text messages
✅ Works 24/7
✅ Automatically restarts on failure
✅ Stores settings in database

**Need Help?**
Contact your system administrator.
"""
    
    await message.reply(help_text, parse_mode="markdown")
    logger.info(f"Help command used by admin {message.from_user.id}")


async def cmd_connect_start(message: Message, state: FSMContext) -> None:
    """Start connect command"""
    if not await check_admin(message):
        return
    
    await message.reply(
        "🔗 **Setting up message forwarding**\n\n"
        "Send me the ID of the **source group** (where messages come from):\n\n"
        "_Example: -1001234567890_",
        parse_mode="markdown"
    )
    
    await state.set_state(ForwardingStates.waiting_for_source)
    logger.info(f"Admin {message.from_user.id} started connect flow")


async def process_source_group(message: Message, state: FSMContext) -> None:
    """Process source group ID"""
    if not await check_admin(message):
        return
    
    try:
        source_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Invalid format. Please send a valid group ID (number).")
        return
    
    await state.update_data(source_id=source_id)
    
    await message.reply(
        f"✅ Source group: `{source_id}`\n\n"
        "Now send me the ID of the **destination group** (where messages will be forwarded to):\n\n"
        "_Example: -1009876543210_",
        parse_mode="markdown"
    )
    
    await state.set_state(ForwardingStates.waiting_for_destination)


async def process_destination_group(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    """Process destination group ID and create forwarding"""
    if not await check_admin(message):
        return
    
    try:
        destination_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Invalid format. Please send a valid group ID (number).")
        return
    
    data = await state.get_data()
    source_id = data.get('source_id')
    
    if source_id == destination_id:
        await message.reply("❌ Source and destination groups cannot be the same!")
        await state.clear()
        return
    
    # Try to verify bot can access groups
    try:
        source_chat = await bot.get_chat(source_id)
        dest_chat = await bot.get_chat(destination_id)
        
        source_name = source_chat.title or f"Group {source_id}"
        dest_name = dest_chat.title or f"Group {destination_id}"
        
        # Save group info
        await db.save_group_info(source_id, source_name)
        await db.save_group_info(destination_id, dest_name)
        
    except Exception as e:
        logger.warning(f"Could not verify groups: {e}")
        source_name = f"Group {source_id}"
        dest_name = f"Group {destination_id}"
    
    # Add forwarding
    success = await db.add_forwarding(source_id, destination_id)
    
    if success:
        await message.reply(
            f"✅ **Forwarding created!**\n\n"
            f"📤 From: `{source_name}`\n"
            f"📥 To: `{dest_name}`\n\n"
            f"Text messages from source group will now be forwarded.",
            parse_mode="markdown"
        )
        logger.info(f"Forwarding created by admin {message.from_user.id}: {source_id} -> {destination_id}")
    else:
        await message.reply(
            "⚠️ **Forwarding already exists** for this pair!\n"
            "No changes were made."
        )
        logger.warning(f"Duplicate forwarding attempt: {source_id} -> {destination_id}")
    
    await state.clear()


async def cmd_disconnect(message: Message, state: FSMContext) -> None:
    """Start disconnect command"""
    if not await check_admin(message):
        return
    
    await message.reply(
        "🔌 **Removing forwarding connection**\n\n"
        "Send the ID of the **source group**:\n\n"
        "_Example: -1001234567890_",
        parse_mode="markdown"
    )
    
    await state.set_state(ForwardingStates.waiting_for_source)
    logger.info(f"Admin {message.from_user.id} started disconnect flow")


async def process_disconnect_destination(message: Message, state: FSMContext, db: Database) -> None:
    """Process destination group for disconnect"""
    if not await check_admin(message):
        return
    
    try:
        destination_id = int(message.text.strip())
    except ValueError:
        await message.reply("❌ Invalid format. Please send a valid group ID (number).")
        return
    
    data = await state.get_data()
    source_id = data.get('source_id')
    
    success = await db.remove_forwarding(source_id, destination_id)
    
    if success:
        source_name = await db.get_group_name(source_id)
        dest_name = await db.get_group_name(destination_id)
        
        await message.reply(
            f"✅ **Forwarding removed!**\n\n"
            f"📤 From: `{source_name}`\n"
            f"📥 To: `{dest_name}`\n\n"
            f"Messages will no longer be forwarded.",
            parse_mode="markdown"
        )
        logger.info(f"Forwarding removed by admin {message.from_user.id}: {source_id} -> {destination_id}")
    else:
        await message.reply(
            "❌ **Forwarding connection not found!**\n\n"
            "Check that the group IDs are correct."
        )
    
    await state.clear()


async def cmd_status(message: Message, db: Database) -> None:
    """Show bot status"""
    if not await check_admin(message):
        return
    
    try:
        status = await db.get_status()
        all_forwardings = await db.get_all_forwardings()
        
        status_text = f"""
📊 **Bot Status**

🔗 Active Forwarding Connections: **{status['active_forwardings']}**
📍 Tracked Groups: **{status['tracked_groups']}**

"""
        
        if all_forwardings:
            status_text += "**Active Forwardings:**\n"
            for source_id, dest_id in all_forwardings:
                source_name = await db.get_group_name(source_id)
                dest_name = await db.get_group_name(dest_id)
                status_text += f"• `{source_name}` → `{dest_name}`\n"
        else:
            status_text += "_No active forwardings configured._"
        
        status_text += "\n✅ Bot is running normally"
        
        await message.reply(status_text, parse_mode="markdown")
        logger.info(f"Status command used by admin {message.from_user.id}")
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await message.reply("❌ Error getting status. Check logs.")


def setup_admin_handlers(dp: Dispatcher, db: Database) -> None:
    """Setup admin command handlers"""
    
    # Help command
    dp.message.register(cmd_help, Command("help"))
    
    # Connect command - start flow
dp.message.register(
    cmd_connect_start,
    Command("connect")
)

# Connect flow - source group
dp.message.register(
    process_source_group,
    ForwardingStates.waiting_for_source
)

# Connect flow - destination group
async def destination_handler(message: Message, state: FSMContext, bot: Bot):
    await process_destination_group(message, state, db, bot)

dp.message.register(
    destination_handler,
    ForwardingStates.waiting_for_destination
)
    
    # Disconnect command - start flow
    dp.message.register(
        lambda msg, state: cmd_disconnect(msg, state),
        Command("disconnect")
    )
    
    # Disconnect flow - destination group
    dp.message.register(
        lambda msg, state: process_disconnect_destination(msg, state, db),
        ForwardingStates.waiting_for_destination
    )
    
    # Status command
    dp.message.register(
        lambda msg: cmd_status(msg, db),
        Command("status")
    )
    
    logger.info("Admin handlers registered")
