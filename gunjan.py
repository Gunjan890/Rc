import logging
import html
import requests
import json
import os
import asyncio
import random
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode
from telegram.error import TelegramError, Forbidden, BadRequest
from bs4 import BeautifulSoup
import urllib3

# Suppress InsecureRequestWarning from requests verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(name)

# Configuration
BOT_TOKEN = '7556128194:AAGFCkn4ubagA4vFVkNehOd1fG6CBwtRBcw-W8'
# Updated API URLs with tokens
PHONE_API_URL = 'https://api.shahad.top/number.php?mobile={number}'
VEHICLE_API_URL = 'https://rc-info-ng.vercel.app/?rc={number}'
ADHAAR_API_URL = 'AADHAR_API'
LOG_FILE = 'logs.json'
TAG = "api by:- Gunjan singh"
BOT_NAME = "Gunjan"

# Admin user IDs (replace with actual admin IDs)
ADMIN_IDS = 7599385056

# Channels to check for subscription
CHANNELS = [
    {'name': 'Channel 1', 'url': 'https://t.me/+zIq1NFrdwxFkMTQ1', 'id': -1003100607330},
    {'name': 'Channel 2', 'url': 'https://t.me/+zIq1NFrdwxFkMTQ1', 'id': -1003100607330},
]

def load_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_log(user_id, username, command, response, chat_id):
    logs = load_logs()
    user_key = str(user_id)
    chat_key = str(chat_id)

    if chat_key not in logs:
        logs[chat_key] = {}
    if user_key not in logs[chat_key]:
        logs[chat_key][user_key] = {'username': username, 'searches': []}
    
    is_duplicate = any(search['command'] == command and search['response'] == response for search in logs[chat_key][user_key]['searches'])

    if not is_duplicate:
        logs[chat_key][user_key]['searches'].append({
            'timestamp': datetime.now().isoformat(),
            'command': command,
            'response': response
        })

    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)

async def check_user_joined_all_channels(user_id, context: ContextTypes.DEFAULT_TYPE):
    for channel in CHANNELS:
        try:
            member = await context.bot.get_chat_member(channel['id'], user_id)
            if member.status not in ['administrator', 'creator', 'member']:
                return False
        except TelegramError as e:
            logger.error(f"Error checking channel {channel['id']} for user {user_id}: {e}")
            return False
    return True

async def check_bot_is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if update.effective_chat.type in ['group', 'supergroup']:
        try:
            bot_member = await update.effective_chat.get_member(context.bot.id)
            if bot_member.status in ['administrator', 'creator']:
                return True
            else:
                await update.message.reply_text("❌ I need to be an administrator in this group to work properly. Please grant me admin rights.")
                return False
        except TelegramError as e:
            logger.error(f"Error checking bot's admin status in group {update.effective_chat.id}: {e}")
            await update.message.reply_text("❌ An error occurred while checking my permissions. Please ensure I have administrator rights.")
            return False
    return True

# --- Helper Functions (New & Updated) ---

async def get_add_bot_button(context: ContextTypes.DEFAULT_TYPE) -> InlineKeyboardMarkup:
    """Creates an InlineKeyboardMarkup with a button to add the bot to a group."""
    bot_username = (await context.bot.get_me()).username
    add_bot_url = f"https://t.me/{bot_username}?startgroup=true&admin=all_rights"
    keyboard = [[InlineKeyboardButton("➕ Add Bot to Your Group ➕", url=add_bot_url)]]
    return InlineKeyboardMarkup(keyboard)

async def send_join_channels_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message with channel links and a verify button."""
    keyboard = [
        [InlineKeyboardButton(c['name'], url=c['url']) for c in CHANNELS],
        [InlineKeyboardButton("✅ Verify", callback_data="check_join")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "<b>❌ Access Denied!</b>\n\n"
        "To use this command, you must join our channels first. After joining, click the <b>'✅ Verify'</b> button."
    )
    
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(message_text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

def get_commands_text():
    """Returns the formatted string of bot commands."""
    return (
        "<b>🤖 R4MODS OSINT BOT Commands</b>\n\n"
        "Here's what I can do:\n\n"
        "<b><u>INFORMATION</u></b>\n"
        "🔹 <code>/num &lt;number&gt;</code> - Search for details using a phone number.\n"
        "   <i>Example:</i> <code>/num 9876543210</code>\n\n"
        "🔹 <code>/vehicle &lt;registration&gt;</code> - Search for vehicle details.\n"
        "   <i>Example:</i> <code>/vehicle DL10ABC1234</code>\n\n"
        "🔹 <code>/adhar &lt;adhar_number&gt;</code> - Search for details using an Aadhaar number.\n"
        "   <i>Example:</i> <code>/adhar 123456789012</code>\n"
    )

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the list of available commands."""
    is_private = update.effective_chat.type == "private"
    commands_text = get_commands_text()
    
    reply_markup = None
    if is_private:
        reply_markup = await get_add_bot_button(context)

    await update.message.reply_text(commands_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# --- Command Handlers (Updated & New) ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    is_private = update.effective_chat.type == "private"

    is_joined = await check_user_joined_all_channels(user.id, context)

    if not is_joined:
        await send_join_channels_message(update, context)
        return

    if is_private:
        await update.message.reply_text(f"👋 Welcome, {user.first_name}!")
        await show_commands(update, context)
    else: # In a group
        await show_commands(update, context)

async def commands_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /commands command."""
    await show_commands(update, context)

async def check_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    is_joined = await check_user_joined_all_channels(user_id, context)
    
    if is_joined:
        await query.edit_message_text(
            "✅ Great! You have joined all the channels. You can now use the bot.",
            parse_mode=ParseMode.HTML
        )
        # Create a mock update object to pass to show_commands
        from unittest.mock import Mock
        mock_message = Mock()
        mock_message.reply_text = query.message.reply_text
        mock_message.chat = query.message.chat
        mock_message.effective_chat = query.message.chat

mock_update = Mock()
        mock_update.message = mock_message
        mock_update.effective_chat = query.message.chat
        
        await show_commands(mock_update, context)
    else:
        await query.answer("❌ You haven't joined all channels yet. Please join and try again.", show_alert=True)

async def handle_num_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await start(update, context)
        return
    if not await check_bot_is_admin(update, context):
        return
    user_id = update.effective_user.id
    if not await check_user_joined_all_channels(user_id, context):
        await send_join_channels_message(update, context)
        return

    try:
        command_parts = context.args
        if not command_parts:
            await update.message.reply_text("<b>❌ Please provide a phone number.</b>\nExample: <code>/num 9876543210</code>", parse_mode=ParseMode.HTML)
            return

        number = command_parts[0]
        if not re.match(r'^\d{10,12}$', number):
            await update.message.reply_text("<b>❌ Invalid number format. Please enter a valid 10-12 digit number.</b>", parse_mode=ParseMode.HTML)
            return

        await update.message.reply_text("🔍 Searching for number details...")
        response = requests.get(PHONE_API_URL.format(Number=number), verify=False)
        data = response.json()

        if data:
            results_per_message = 3
            total_results = len(data)

            if total_results == 0:
                await update.message.reply_text("❌ No details found for this number.", parse_mode=ParseMode.HTML)
                return

            for i in range(0, total_results, results_per_message):
                batch = data[i:i + results_per_message]
                response_text = f"<b>✅ Number Details Found:</b>\n\n"
                
                for user_info in batch:
                    response_text += (
                        f"<b>Name:</b> {user_info.get('name', 'N/A')}\n"
                        f"<b>Father Name:</b> {user_info.get('father_name', 'N/A')}\n"
                        f"<b>Email:</b> {user_info.get('email', 'N/A')}\n"
                        f"<b>Alternate Mobile:</b> {user_info.get('alternate_mobile', 'N/A')}\n"
                        f"<b>Circle:</b> {user_info.get('circle', 'N/A')}\n"
                        f"<b>Address:</b> {user_info.get('address', 'N/A')}\n"
                        f"<b>Adhar Num:</b> {user_info.get('id_number', 'N/A')}\n"
                        "------------------------------------------\n"
                    )
                
                response_text += f"\n<i>{TAG}</i>"
                reply_markup = await get_add_bot_button(context)
                await update.message.reply_text(response_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
                save_log(user_id, update.effective_user.username, f"/num {number}", response_text, update.effective_chat.id)

        else:
            await update.message.reply_text("❌ No details found for this number.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in handle_num_command: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")

async def handle_vehicle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await start(update, context)
        return
    if not await check_bot_is_admin(update, context):
        return
    user_id = update.effective_user.id
    if not await check_user_joined_all_channels(user_id, context):
        await send_join_channels_message(update, context)
        return

    try:
        command_parts = context.args
        if not command_parts:
            await update.message.reply_text("<b>❌ Please provide a vehicle registration number.</b>\nExample: <code>/vehicle DL10ABC1234</code>", parse_mode=ParseMode.HTML)
            return

vehicle_num = "".join(command_parts).upper()
        await update.message.reply_text("🔍 Searching for vehicle details...")
        response = requests.get(VEHICLE_API_URL.format(Vehicle_num=vehicle_num), verify=False)
        data = response.json()

        if data.get("Owner Name"):
            response_text = "<b>✅ Vehicle Details Found:</b>\n\n"
            for key, value in data.items():
                formatted_value = "N/A" if value is None else value
                response_text += f"<b>{key}:</b> {formatted_value}\n"
            
            response_text += f"\n<i>{TAG}</i>"
            reply_markup = await get_add_bot_button(context)
            save_log(user_id, update.effective_user.username, f"/vehicle {vehicle_num}", response_text, update.effective_chat.id)
            await update.message.reply_text(response_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ No details found for this vehicle number.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in handle_vehicle_command: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")

async def handle_adhar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await start(update, context)
        return
    if not await check_bot_is_admin(update, context):
        return
    user_id = update.effective_user.id
    if not await check_user_joined_all_channels(user_id, context):
        await send_join_channels_message(update, context)
        return

    try:
        command_parts = context.args
        if not command_parts:
            await update.message.reply_text("<b>❌ Please provide an Aadhaar number.</b>\nExample: <code>/adhar 123456789012</code>", parse_mode=ParseMode.HTML)
            return

        adhar_number = command_parts[0]
        if not re.match(r'^\d{12}$', adhar_number):
            await update.message.reply_text("<b>❌ Invalid Aadhaar number format. Please enter a valid 12-digit number.</b>", parse_mode=ParseMode.HTML)
            return

        await update.message.reply_text("🔍 Searching for Aadhaar details...")
        response = requests.get(ADHAAR_API_URL.format(adhar=adhar_number), verify=False)
        data = response.json()

        if data.get("status") == "success" and data.get("data"):
            response_text = f"<b>✅ Aadhaar Details Found:</b>\n\n"
            for user_info in data['data']:
                response_text += (
                    f"<b>Name:</b> {user_info.get('name', 'N/A')}\n"
                    f"<b>Father Name:</b> {user_info.get('fname', 'N/A')}\n"
                    f"<b>Mobile:</b> {user_info.get('mobile', 'N/A')}\n"
                    f"<b>Circle:</b> {user_info.get('circle', 'N/A')}\n"
                    f"<b>Address:</b> {user_info.get('address', 'N/A')}\n"
                    f"<b>ID:</b> {user_info.get('id', 'N/A')}\n"
                    "------------------------------------------\n"
                )
            
            response_text += f"\n<i>{TAG}</i>"
            reply_markup = await get_add_bot_button(context)
            save_log(user_id, update.effective_user.username, f"/adhar {adhar_number}", response_text, update.effective_chat.id)
            await update.message.reply_text(response_text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        else:
            await update.message.reply_text("❌ No details found for this Aadhaar number.", parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error in handle_adhar_command: {e}")
        await update.message.reply_text("❌ An error occurred while processing your request.")


# --- Admin Panel (Advanced) ---

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not an admin.")
        return

keyboard = [
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="broadcast_options")],
        [InlineKeyboardButton("📊 Bot Stats", callback_data="get_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("<b>👑 Admin Panel</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id not in ADMIN_IDS:
        await query.message.reply_text("❌ You are not authorized to use this function.")
        return

    action = query.data

    if action == 'broadcast_options':
        keyboard = [
            [InlineKeyboardButton("To All Users", callback_data="broadcast_users")],
            [InlineKeyboardButton("To All Groups", callback_data="broadcast_groups")],
            [InlineKeyboardButton("To Users & Groups", callback_data="broadcast_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select broadcast target:", reply_markup=reply_markup)
    
    elif action.startswith('broadcast_'):
        target = action.split('_')[1]
        context.user_data['broadcast_target'] = target
        context.user_data['state'] = 'awaiting_broadcast_message'
        await query.edit_message_text(f"Please reply to this message with the text for <b>{target.title()}</b>.", parse_mode=ParseMode.HTML)

    elif action == 'get_stats':
        logs = load_logs()
        total_groups = len({gid for gid in logs.keys() if gid.startswith('-')})
        all_users = {uid for group in logs.values() for uid in group.keys()}
        total_searches = sum(len(user.get('searches', [])) for group in logs.values() for user in group.values())

        stats_text = (
            f"<b>📊 Bot Statistics</b>\n\n"
            f"<b>Total Searches:</b> {total_searches}\n"
            f"<b>Unique Users:</b> {len(all_users)}\n"
            f"<b>Active Groups:</b> {total_groups}\n"
        )
        await query.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS or context.user_data.get('state') != 'awaiting_broadcast_message':
        return

    broadcast_text = update.message.text
    target = context.user_data.get('broadcast_target', 'all')
    
    logs = load_logs()
    group_ids = {gid for gid in logs.keys() if gid.startswith('-')}
    user_ids = {uid for group in logs.values() for uid in group.keys()}

    target_ids = set()
    if target == 'users': target_ids = user_ids
    elif target == 'groups': target_ids = group_ids
    elif target == 'all': target_ids = user_ids.union(group_ids)

    if not target_ids:
        await update.message.reply_text("No targets found to broadcast to.")
        context.user_data.clear()
        return

    await update.message.reply_text(f"🚀 Starting broadcast to {len(target_ids)} chats...")
    success_count, fail_count = 0, 0
    for chat_id in target_ids:
        try:
            await context.bot.send_message(chat_id=int(chat_id), text=broadcast_text, parse_mode=ParseMode.HTML)
            success_count += 1
            await asyncio.sleep(0.1)
        except (Forbidden, BadRequest) as e:
            logger.warning(f"Failed to send broadcast to chat {chat_id}: {e}")
            fail_count += 1
        except Exception as e:
            logger.error(f"Error broadcasting to chat {chat_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(f"Broadcast complete!\n✅ Successfully sent to {success_count} chats.\n❌ Failed for {fail_count} chats.")
    context.user_data.clear()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

if name == 'main':
    try:
        app = ApplicationBuilder().token(BOT_TOKEN).build()
        app.add_error_handler(error_handler)

# Command handlers
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('commands', commands_handler))
        app.add_handler(CommandHandler('admin', admin_panel))
        app.add_handler(CommandHandler('num', handle_num_command))
        app.add_handler(CommandHandler('vehicle', handle_vehicle_command))
        app.add_handler(CommandHandler('adhar', handle_adhar_command))

        # Callback handlers
        app.add_handler(CallbackQueryHandler(check_joined, pattern='^check_join$'))
        app.add_handler(CallbackQueryHandler(handle_admin_callback, pattern='^(broadcast_options|broadcast_users|broadcast_groups|broadcast_all|get_stats)$'))
        
        # Message handler for broadcast text
        app.add_handler(MessageHandler(filters.TEXT & filters.REPLY & filters.User(ADMIN_IDS), handle_broadcast_message))
        
        logger.info("🚀 Bot with updated functionalities started successfully!")
        app.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Application failed... {e}")
