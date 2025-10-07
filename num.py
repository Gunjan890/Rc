import requests
import re
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ----------------------
# CONFIGURATION
# ----------------------

BOT_TOKEN = "8332092829:AAFzACD-PGrEx0t7oS8NxUXUwvLdAa5i3qg"  # Replace with your actual bot token

# AUTHORIZED GROUP IDs (Add your group IDs here)
AUTHORIZED_GROUPS = [
    -1003007170092,  # Example group ID, replace with your own
]

# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Header and Footer
HEADER = "Gunjan"
FOOTER = "\n- Gunjan"

# ----------------------
# AUTHORIZATION FUNCTION
# ----------------------

async def is_authorized(update: Update) -> bool:
    if update.effective_chat:
        return update.effective_chat.id in AUTHORIZED_GROUPS
    return False

# ----------------------
# COMMANDS
# ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return

    msg = (
        f"{HEADER}\n"
        "**WELCOME TO R4MODS OSINT BOT!**\n\n"
        "Use /num <10-digit-number> to search info.\n"
        "Example: `/num 6200303551`\n\n"
        f"{FOOTER}"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

# You can add /num command logic here as needed
# Example stub:
async def num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a 10-digit number. Usage: /num 6200303551")
        return

    number = context.args[0]
    # Validate number
    if not re.fullmatch(r'\d{10}', number):
        await update.message.reply_text("Invalid number format. Please enter a 10-digit number.")
        return

    # Placeholder for actual lookup logic
    await update.message.reply_text(f"Looking up data for: {number}")
    # You can call your API or scraping logic here

# ----------------------
# MAIN FUNCTION
# ----------------------

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("num", num))

    logger.info("Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
