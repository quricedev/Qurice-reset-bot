import os
import uuid
import string
import random
import logging
import requests
import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='bot.log',
    filemode='a'
)
logger = logging.getLogger(__name__)

# Channel information
CHANNEL_USERNAME = "@Aniredirect"  # Replace with your actual channel username
CHANNEL_LINK = "https://t.me/Aniredirect"  # Replace with your actual channel link
BACKUP_CHANNEL = "@ScammerFuk"  # Optional backup channel

class PasswordReset:
    def __init__(self, target):
        self.target = target.strip()
        if "@" in self.target:
            self.data = {
                "_csrftoken": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
                "user_email": self.target,
                "guid": str(uuid.uuid4()),
                "device_id": str(uuid.uuid4())
            }
        else:
            self.data = {
                "_csrftoken": "".join(random.choices(string.ascii_letters + string.digits, k=32)),
                "username": self.target,
                "guid": str(uuid.uuid4()),
                "device_id": str(uuid.uuid4())
            }

    def send_password_reset(self):
        head = {
            "user-agent": "Instagram 150.0.0.0.000 Android"
        }
        try:
            req = requests.post(
                "https://i.instagram.com/api/v1/accounts/send_password_reset/",
                headers=head,
                data=self.data,
                timeout=10)
            return req.text
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return "error"

def start(update, context):
    """Send welcome message with channel join button."""
    user = update.message.from_user
    logger.info(f"User {user.id} started the bot")
    
    # Create inline keyboard with channel button
    keyboard = [
        [InlineKeyboardButton("📢 Join Our Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ I've Joined", callback_data='joined')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
👋 Welcome *{user.first_name}* to Instagram pass reset Bot!

🔹 *Please join our channel* .
🔹 After joining, click *"I've Joined"* below.
"""
    update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

def button_handler(update, context):
    """Handle button callbacks."""
    query = update.callback_query
    query.answer()
    
    if query.data == 'joined':
        # Check if user actually joined (basic implementation)
        # In production, you should implement proper channel membership check
        query.edit_message_text(
            text="🎉 Thanks for joining! Use /help to see available commands.",
            parse_mode=ParseMode.MARKDOWN
        )

def help_command(update, context):
    """Send help message."""
    help_text = """
🔹 *Available Commands* 🔹

/start - Check if bot is alive
/reset - Reset single account
/bulk - Reset multiple accounts

📢 *Our Channel*: [Join Here]({})
""".format(CHANNEL_LINK)
    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

def reset_command(update, context):
    """Initiate single reset."""
    update.message.reply_text('Send Instagram username or email')
    context.user_data['awaiting_reset'] = True

def bulk_command(update, context):
    """Initiate bulk reset."""
    update.message.reply_text('Send multiple usernames/emails (one per line)')
    context.user_data['awaiting_bulk'] = True

def handle_message(update, context):
    """Handle all messages."""
    try:
        if context.user_data.get('awaiting_reset'):
            target = update.message.text
            if target.startswith('@'):
                update.message.reply_text("❌ Username without '@'")
                return
                
            result = PasswordReset(target).send_password_reset()
            if "obfuscated_email" in result:
                update.message.reply_text("✅ Reset link sent!")
            else:
                update.message.reply_text("❌ Failed to send link")
            context.user_data['awaiting_reset'] = False
            
        elif context.user_data.get('awaiting_bulk'):
            targets = [t.strip() for t in update.message.text.split('\n') if t.strip()]
            update.message.reply_text(f"⏳ Processing {len(targets)} accounts...")
            
            for target in targets:
                try:
                    result = PasswordReset(target).send_password_reset()
                    time.sleep(2)
                except Exception as e:
                    logger.error(f"Error processing {target}: {e}")
            
            update.message.reply_text("✅ Bulk processing completed")
            context.user_data['awaiting_bulk'] = False
            
        else:
            update.message.reply_text("Use /help for commands")
            
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        update.message.reply_text("⚠️ An error occurred")

def error_handler(update, context):
    """Log errors."""
    logger.error(f'Update {update} caused error {context.error}')

def main():
    """Start the bot."""
    try:
        TOKEN = os.getenv('BOT_TOKEN') or "7558578299:AAHFs0hw01sBov9Q9B-kJoKUB7q2CN3CoJU"
        
        updater = Updater(TOKEN, use_context=True)
        dp = updater.dispatcher
        
        # Add handlers
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CommandHandler("reset", reset_command))
        dp.add_handler(CommandHandler("bulk", bulk_command))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dp.add_handler(CallbackQueryHandler(button_handler))
        dp.add_error_handler(error_handler)
        
        logger.info("Starting bot polling...")
        updater.start_polling()
        updater.idle()
        
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
        raise

if __name__ == '__main__':
    main()