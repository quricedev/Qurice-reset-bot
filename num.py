import telebot
from telebot import types
import requests
import os
import re
from flask import Flask, request
from threading import Thread
import logging 
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URL = os.getenv("MONGO_URL")
OWNER_ID = int(os.getenv("OWNER_ID", "123456"))

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

client = MongoClient(MONGO_URL)
db = client['tginfo']
users = db['users']
bans = db['banned']
forces = db['forcejoin']
locked = db['locked']
allowed_groups = db['allowed_groups']

# ================= Utils =================
def format_number(num: str):
    digits = re.sub(r"\D", "", num)
    if digits.startswith("91"):
        return "91" + digits[-10:]
    elif digits.startswith("0"):
        return "91" + digits[-10:]
    elif len(digits) == 10:
        return "91" + digits
    elif digits.startswith("+91"):
        return digits[1:]
    return digits

def is_banned(user_id):
    return bans.find_one({"_id": user_id}) is not None

def is_registered(user_id):
    return users.find_one({"_id": user_id}) is not None

def is_locked(number):
    return locked.find_one({"_id": number}) is not None

def get_forcejoin():
    return list(forces.find())

def check_joined(user_id):
    required = get_forcejoin()
    for ch in required:
        try:
            member = bot.get_chat_member(ch['chat_id'], user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def group_allowed(chat_id):
    return allowed_groups.find_one({"_id": chat_id}) is not None

def save_user(user):
    if not users.find_one({"_id": user.id}):
        users.insert_one({"_id": user.id, "name": user.first_name, "username": user.username})

# ================= Command Handlers =================
@bot.message_handler(commands=['start'])
def start_cmd(message):
    if message.chat.type != "private":
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("⚠️ Start in DM", url=f"https://t.me/{bot.get_me().username}?start=start"))
        bot.reply_to(message, "⚠️ Please start the bot in DM and get registered.", reply_markup=btn)
        return

    user_id = message.from_user.id
    save_user(message.from_user)

    # Force Join
    fjoins = get_forcejoin()
    if fjoins:
        btns = types.InlineKeyboardMarkup()
        for ch in fjoins:
            btns.add(types.InlineKeyboardButton(ch['name'], url=ch['url']))
        btns.add(types.InlineKeyboardButton("✅ I've Joined", callback_data="check_join"))
        bot.send_message(user_id, "⚠️ Please join required channels/groups to use the bot.", reply_markup=btns)
    else:
        bot.send_message(user_id, "✅ You are registered and ready to go!")

@bot.callback_query_handler(func=lambda c: c.data == "check_join")
def check_joined_callback(call):
    if check_joined(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!")
        bot.send_message(call.from_user.id, "✅ You're all set! Send a number to get info.")
    else:
        bot.answer_callback_query(call.id, "❌ You're missing some required joins!")

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.send_message(message.chat.id, f"""`Status     : Online 📡
Up         : 100 MB/s
Down       : 99 MB/s`""", parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        bans.insert_one({"_id": uid})
        bot.reply_to(message, f"✅ User `{uid}` banned.", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Usage: /ban <user_id>")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        uid = int(message.text.split()[1])
        bans.delete_one({"_id": uid})
        bot.reply_to(message, f"✅ User `{uid}` unbanned.", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Usage: /unban <user_id>")

@bot.message_handler(commands=['addforcejoin'])
def add_forcejoin(message):
    if message.from_user.id != OWNER_ID:
        return
    msg = bot.reply_to(message, "🔗 Send public/private channel or group link.")
    bot.register_next_step_handler(msg, collect_forcejoin)

def collect_forcejoin(message):
    url = message.text.strip()
    try:
        info = bot.get_chat(url)
        btn_msg = bot.reply_to(message, "📝 Send name for button (supports font).")
        bot.register_next_step_handler(btn_msg, lambda m: save_force(info, url, m.text))
    except:
        bot.reply_to(message, "❌ Invalid link. Make sure bot is admin.")

def save_force(info, url, name):
    forces.insert_one({
        "chat_id": info.id,
        "url": url,
        "name": name
    })
    bot.send_message(OWNER_ID, f"✅ Forcejoin added:\n- {name}\n- {url}")

@bot.message_handler(commands=['removeforcejoin'])
def remove_fj(message):
    if message.from_user.id != OWNER_ID:
        return
    msg = bot.reply_to(message, "🧹 Send link of forcejoin to remove.")
    bot.register_next_step_handler(msg, lambda m: forces.delete_one({"url": m.text.strip()}))

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        return
    msg = bot.reply_to(message, "📢 Send message to broadcast.")
    bot.register_next_step_handler(msg, broadcast_to_all)

def broadcast_to_all(message):
    total = sent = failed = 0
    for user in users.find():
        total += 1
        try:
            bot.send_message(user['_id'], message.text, parse_mode="Markdown", disable_web_page_preview=True)
            sent += 1
        except:
            failed += 1
    bot.reply_to(message, f"✅ Sent: {sent}\n❌ Failed: {failed}\n👥 Total: {total}")

@bot.message_handler(commands=['lockinfo'])
def lockinfo(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        num = format_number(message.text.split()[1])
        locked.insert_one({"_id": num})
        bot.reply_to(message, f"🔒 Number locked: {num}")
    except:
        bot.reply_to(message, "❌ Usage: /lockinfo <number>")

@bot.message_handler(commands=['infon'])
def infon(message):
    if message.from_user.id == OWNER_ID and message.chat.type != "private":
        allowed_groups.insert_one({"_id": message.chat.id})
        bot.reply_to(message, "✅ Info enabled in this group.")

@bot.message_handler(commands=['infof'])
def infof(message):
    if message.from_user.id == OWNER_ID and message.chat.type != "private":
        allowed_groups.delete_one({"_id": message.chat.id})
        bot.reply_to(message, "🚫 Info disabled in this group.")

@bot.message_handler(func=lambda m: True, content_types=['text'])
def get_info(message):
    if message.text.startswith("/"):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_banned(user_id):
        return bot.send_message(chat_id, "🚫 You are banned. DM owner for access.")

    if not is_registered(user_id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("⚠️ Start in DM", url=f"https://t.me/{bot.get_me().username}?start=start"))
        return bot.reply_to(message, "⚠️ Start the bot in DM and get registered.", reply_markup=btn)

    if not check_joined(user_id):
        btn = types.InlineKeyboardMarkup()
        btn.add(types.InlineKeyboardButton("⚠️ Start in DM", url=f"https://t.me/{bot.get_me().username}?start=start"))
        return bot.reply_to(message, "⚠️ Please join required channels to use the bot.", reply_markup=btn)

    if message.chat.type != "private" and not group_allowed(chat_id):
        return bot.reply_to(message, "🚫 This group is not authorized to use the bot.")

    num = format_number(message.text)
    if not num or len(num) < 10:
        return bot.reply_to(message, "⚠️ Invalid number. Please check and try again.")

    if is_locked(num):
        return bot.reply_to(message, "❌ This number is protected by the owner.")

    try:
        r = requests.get(f"https://glonova.in/Iwowoo3o.php/?num={num}")
        if "error" in r.text.lower() or len(r.text) < 20:
            raise ValueError
        return bot.send_message(chat_id, f"```{r.text.strip()}```", parse_mode="Markdown")
    except:
        return bot.send_message(chat_id, "❌ No data found. This may be a fake or unlisted number.")

# ============= Flask Webhook (Optional) =============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App to keep Render service alive
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "✅ Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Start Flask keep-alive server
    Thread(target=run_flask).start()

    # Start Telegram Bot polling
    logger.info("🚀 Starting bot...")
    bot.infinity_polling()