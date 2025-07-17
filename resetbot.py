import os
import uuid
import string
import random
import logging
import requests
import sqlite3
from threading import Thread
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import apihelper

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
CHANNEL_LINK = "https://t.me/Aniredirect"
BACKUP_CHANNEL_LINK = "https://t.me/ScammerFuk"
ADMIN_IDS = [6302016869]  # Replace with your admin user ID(s)
DATABASE_NAME = "bot_users.db"

# Initialize bot
bot = telebot.TeleBot(os.getenv("BOT_TOKEN") or "7558578299:AAHFs0hw01sBov9Q9B-kJoKUB7q2CN3CoJU")

# Initialize database
def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            date_added TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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

# Store new user in database
def store_user(user):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, date_added)
        VALUES (?, ?, ?, ?, datetime('now'))
    ''', (user.id, user.username, user.first_name, user.last_name))
    conn.commit()
    conn.close()

# Get total user count
def get_user_count():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Start Command
@bot.message_handler(commands=['start'])
def start(message):
    store_user(message.from_user)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(InlineKeyboardButton("📢 Main Channel", url=CHANNEL_LINK))
    keyboard.row(InlineKeyboardButton("🔄 Backup Channel", url=BACKUP_CHANNEL_LINK))
    keyboard.row(InlineKeyboardButton("✅ I've Joined", callback_data='joined'))
    
    text = (
        f"👋 Welcome *{message.from_user.first_name}*!\n\n"
        "🔹 Join our main or backup channel.\n"
        "🔹 Then click *I've Joined*."
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=keyboard)

# Button Handler
@bot.callback_query_handler(func=lambda call: True)
def button_handler(call):
    if call.data == "joined":
        bot.edit_message_text(
            "🎉 Thanks for joining! Use /help for commands.",
            call.message.chat.id,
            call.message.message_id
        )

# Help Command
@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message,
        "🔹 *Available Commands* 🔹\n\n"
        "/start - Start bot\n/reset - Reset one account\n/bulk - Reset multiple accounts",
        parse_mode="Markdown"
    )

# Reset Command
@bot.message_handler(commands=['reset'])
def reset_command(message):
    msg = bot.reply_to(message, "Send Instagram username or email")
    bot.register_next_step_handler(msg, process_reset_step)

def process_reset_step(message):
    target = message.text
    if target.startswith('@'):
        bot.reply_to(message, "❌ Username without '@'")
        return
    
    result = PasswordReset(target).send_password_reset()
    if "obfuscated_email" in result:
        bot.reply_to(message, "✅ Reset link sent!")
    else:
        bot.reply_to(message, "❌ Failed to send link")

# Bulk Command
@bot.message_handler(commands=['bulk'])
def bulk_command(message):
    msg = bot.reply_to(message, "Send multiple usernames/emails (one per line)")
    bot.register_next_step_handler(msg, process_bulk_step)

def process_bulk_step(message):
    targets = [t.strip() for t in message.text.split("\n") if t.strip()]
    bot.reply_to(message, f"⏳ Processing {len(targets)} accounts...")
    
    for t in targets:
        if not t.startswith('@'):
            PasswordReset(t).send_password_reset()
    
    bot.reply_to(message, "✅ Bulk processing completed")

# Admin: Broadcast Command
@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied")
        return
    
    msg = bot.reply_to(message, "Send the message you want to broadcast to all users")
    bot.register_next_step_handler(msg, process_broadcast_step)

def process_broadcast_step(message):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    total = len(users)
    success = 0
    failed = 0
    
    bot.reply_to(message, f"📢 Broadcasting to {total} users...")
    
    for user in users:
        try:
            bot.copy_message(user[0], message.chat.id, message.message_id)
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {user[0]}: {e}")
            failed += 1
    
    bot.reply_to(message, f"📢 Broadcast completed!\nSuccess: {success}\nFailed: {failed}")

# Admin: Stats Command
@bot.message_handler(commands=['stats'])
def stats_command(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ Access denied")
        return
    
    count = get_user_count()
    bot.reply_to(message, f"📊 Total users: {count}")

# Handle other messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, "Use /help for commands")

# Flask App for keep-alive
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is running!"

def run_flask():
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    # Start Flask in a separate thread
    Thread(target=run_flask).start()
    
    # Start the bot
    logger.info("Starting bot...")
    bot.infinity_polling()