import os
import uuid
import string
import random
import logging
import requests
import asyncio
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Channel info
CHANNEL_LINK = "https://t.me/Aniredirect"
BACKUP_CHANNEL_LINK = "https://t.me/ScammerFuk"

# Instagram Password Reset Logic
class PasswordReset:
    def __init__(self, target):
        self.target = target.strip()
        self.data = {
            "_csrftoken": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
            "guid": str(uuid.uuid4()),
            "device_id": str(uuid.uuid4())
        }
        if "@" in self.target:
            self.data["user_email"] = self.target
        else:
            self.data["username"] = self.target

    def send_password_reset(self):
        try:
            r = requests.post(
                "https://i.instagram.com/api/v1/accounts/send_password_reset/",
                headers={"user-agent": "Instagram 150.0.0.0.000 Android"},
                data=self.data,
                timeout=10
            )
            return r.text
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return "error"

# Start Command
async def start(update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Main Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("🔄 Backup Channel", url=BACKUP_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data='joined')]
    ]
    text = (
        f"👋 Welcome *{update.message.from_user.first_name}*!\n\n"
        "🔹 Join our main or backup channel.\n"
        "🔹 Then click *I've Joined*."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))

# Button Handler
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "joined":
        await query.edit_message_text("🎉 Thanks for joining! Use /help for commands.")

# Help Command
async def help_command(update, context):
    await update.message.reply_text(
        f"🔹 *Available Commands* 🔹\n\n"
        f"/start - Start bot\n/reset - Reset one account\n/bulk - Reset multiple accounts",
        parse_mode=ParseMode.MARKDOWN
    )

# Reset Command
async def reset_command(update, context):
    await update.message.reply_text("Send Instagram username or email")
    context.user_data["awaiting_reset"] = True

# Bulk Command
async def bulk_command(update, context):
    await update.message.reply_text("Send multiple usernames/emails (one per line)")
    context.user_data["awaiting_bulk"] = True

# Message Handler
async def handle_message(update, context):
    if context.user_data.get("awaiting_reset"):
        target = update.message.text
        if target.startswith('@'):
            await update.message.reply_text("❌ Username without '@'")
            return
        result = PasswordReset(target).send_password_reset()
        if "obfuscated_email" in result:
            await update.message.reply_text("✅ Reset link sent!")
        else:
            await update.message.reply_text("❌ Failed to send link")
        context.user_data["awaiting_reset"] = False

    elif context.user_data.get("awaiting_bulk"):
        targets = [t.strip() for t in update.message.text.split("\n") if t.strip()]
        await update.message.reply_text(f"⏳ Processing {len(targets)} accounts...")
        for t in targets:
            PasswordReset(t).send_password_reset()
            await asyncio.sleep(2)
        await update.message.reply_text("✅ Bulk processing completed")
        context.user_data["awaiting_bulk"] = False

    else:
        await update.message.reply_text("Use /help for commands")

# Main Bot Runner
async def main():
    token = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset_command))
    app.add_handler(CommandHandler("bulk", bulk_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    await app.run_polling()

# Flask App for keep-alive
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    asyncio.run(main())