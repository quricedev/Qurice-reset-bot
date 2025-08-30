
import os
import datetime
from io import BytesIO
from PIL import Image
import qrcode
import telebot
from telebot import types
from pymongo import MongoClient
from dotenv import load_dotenv
from flask import Flask
import threading

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
OWNER_ID = int(os.getenv("OWNER_ID"))  

bot = telebot.TeleBot(BOT_TOKEN)
client = MongoClient(MONGO_URI)
db = client['upi_qr_bot']

users_col = db['users']
logs_col = db['qr_logs']
settings_col = db['settings']

DAILY_LIMIT_FREE = 5
COOLDOWN_FREE = 5 * 60  

FORCE_JOIN_CHANNELS = [
    {
        "id": "@anogenic",
        "link": "https://t.me/anogenic",
        "name": "#𝐐ᴜʀɪᴄᴇ 𝐂ᴏᴍᴇʙᴀᴄᴋ",
        "type": "public_channel"
    },
    {
        "id": -1002724715863,
        "link": "https://t.me/+Mfw9JFPR6yxjYmFl",
        "name": "backup",
        "type": "private_channel"
    },
    {
        "id": "@nudipy",
        "link": "https://t.me/nudipy",
        "name": "#𝐐ᴜʀɪᴄᴇ 𝐓ᴏᴏʟꜱ",
        "type": "public_channel"
    },
    {
        "id": -1002894035030,
        "link": "https://t.me/+xWHvKPQfwsU5OGRl",
        "name": "#𝐌ᴀʀᴋᴇᴛ 𝐇ᴜʙ",
        "type": "private_group"
    },
    {
    "id": -1002545843201,
    "link": "https://t.me/+1ZjsfDbP3Dc5NDc9",
    "name": "QR NOTIFYER",
    "type": "private_channel"
    }
    
]

NOTIFICATION_CHANNEL = [
    {
    "id": -1002545843201,
    "link": "https://t.me/+1ZjsfDbP3Dc5NDc9",
    "name": "QR NOTIFYER",
    "type": "private_channel"
    }
]

app = Flask(__name__)

@app.route("/")
def index():
    return "UPI QR Bot is running!"

def is_admin(user_id):
    return user_id == OWNER_ID

def get_global_bg():
    bg_doc = settings_col.find_one({"key": "global_bg"})
    return bg_doc["value"] if bg_doc else None

def check_force_join(user_id):
    markup = types.InlineKeyboardMarkup()
    all_ok = True
    buttons = []

    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = bot.get_chat_member(ch["id"], user_id)
            if member.status in ['left', 'kicked']:
                all_ok = False
                btn = types.InlineKeyboardButton(text=f"Join {ch['name']}", url=ch['link'])
                buttons.append(btn)
        except Exception:
            all_ok = False
            btn = types.InlineKeyboardButton(text=f"Join {ch['name']}", url=ch['link'])
            buttons.append(btn)
    for i in range(0, len(buttons), 2):
        markup.row(*buttons[i:i+2])

    if not all_ok:
        verify_btn = types.InlineKeyboardButton("✅ Verify", callback_data="verify_forcejoin")
        markup.add(verify_btn)

    return all_ok, markup
def is_premium(user):
    if user.get("premium_until"):
        return datetime.datetime.utcnow() < user["premium_until"]
    return False

def check_cooldown(user):
    if is_premium(user):
        return False  
    last_qr = user.get("last_qr_time")
    if not last_qr:
        return False
    elapsed = (datetime.datetime.utcnow() - last_qr).total_seconds()
    return elapsed < COOLDOWN_FREE

def check_daily_limit(user):
    if is_premium(user):
        return False
    today = datetime.datetime.utcnow().date()
    last_reset = user.get("last_reset")
    if not last_reset or last_reset.date() != today:
        users_col.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"daily_count": 0, "last_reset": datetime.datetime.utcnow()}}
        )
        user["daily_count"] = 0

    return user.get("daily_count", 0) >= DAILY_LIMIT_FREE

def generate_qr(upi_id, amount, bg_file_id=None):
    uri = f"upi://pay?pa={upi_id}&am={amount}&cu=INR"
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    if bg_file_id:
        try:
            file_info = bot.get_file(bg_file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            bg_img = Image.open(BytesIO(downloaded_file)).convert("RGBA")
            bg_img = bg_img.resize(img.size)
            img = Image.alpha_composite(bg_img, img)
        except Exception as e:
            print(f"❌ Failed to apply background: {e}")

    output = BytesIO()
    img.save(output, "PNG")
    output.seek(0)
    return output

def notify_qr_owner(user, amount):
    text = (
        f"💳 New QR Generated\n"
        f"👤 User: {user.get('first_name')} (@{user.get('username')})\n"
        f"🆔 ID: {user.get('user_id')}\n"
        f"💰 Amount: ₹{amount}"
    )
    try:
        bot.send_message(OWNER_ID, text)
        print("✅ Owner notified")
    except Exception as e:
        print(f"❌ Failed to notify owner: {e}")
        
def notify_admin_new_user(user):
    text = (
        f"🆕 New User!\n"
        f"📊 Total Users: {users_col.count_documents({})}\n"
        f"👤 Name: {user.get('first_name')}\n"
        f"🔗 Username: @{user.get('username')}\n"
        f"🆔 ID: {user.get('user_id')}"
    )
    try:
        bot.send_message(OWNER_ID, text)
    except:
        pass

@bot.message_handler(commands=['start'])
def start_handler(message):
    user = users_col.find_one({"user_id": message.from_user.id})
    if not user:
        new_user = {
            "user_id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "upi_id": None,
            "bg_file_id": None,
            "daily_count": 0,
            "last_reset": datetime.datetime.utcnow(),
            "last_qr_time": None,
            "premium_until": None,
            "banned": False
        }
        users_col.insert_one(new_user)
        notify_admin_new_user(new_user)
        user = new_user

    if user.get("banned"):
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return

    ok, markup = check_force_join(message.from_user.id)
    if not ok:
        bot.send_message(message.chat.id, "⚠️ Please join required channels to use the bot.", reply_markup=markup)
        return

    bot.send_message(message.chat.id, f"Hello {message.from_user.first_name}! Send /help to see commands.")

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = """
📌 Available Commands:

- /start : check if alive 
- /help : to see all command 
- /setupi : Set your UPI ID
- /resetupi : remove your current upi
- /qr {amount} : Generate QR code for amount
"""

    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['setupi'])
def setupi_handler(message):
    msg = bot.send_message(message.chat.id, "Send your UPI ID:")
    bot.register_next_step_handler(msg, save_upi)

def save_upi(message):
    upi = message.text.strip()
    if "@" not in upi:
        bot.reply_to(message, "⚠️ Invalid UPI ID.")
        return
    users_col.update_one({"user_id": message.from_user.id}, {"$set": {"upi_id": upi}})
    bot.reply_to(message, f"✅ Your UPI ID is set to {upi}")
    
@bot.message_handler(commands=['qr'])
def qr_handler(message):
    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        bot.reply_to(message, "⚠️ Usage: /qr {amount}")
        return

    amount = int(args[1])
    user = users_col.find_one({"user_id": message.from_user.id})

    if not user or not user.get("upi_id"):
        bot.reply_to(message, "⚠️ Please set your UPI ID first using /setupi")
        return

    if user.get("banned"):
        bot.reply_to(message, "🚫 You are banned from using this bot.")
        return

    ok, markup = check_force_join(message.from_user.id)
    if not ok:
        bot.send_message(
            message.chat.id,
            "⚠️ Please join required channels to use the bot.",
            reply_markup=markup
        )
        return

    if not is_premium(user):
        if check_cooldown(user):
            last_time = user.get("last_qr_time")
            remaining = int(COOLDOWN_FREE - (datetime.datetime.utcnow() - last_time).total_seconds())
            mins, secs = divmod(remaining, 60)
            bot.reply_to(
                message,
                f"⏳ Cooldown active!\nPlease wait {mins}m {secs}s before generating another QR."
            )
            return

        if check_daily_limit(user):
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("👤 Contact Owner", url="https://t.me/Qutype")
            )
            bot.send_message(
                message.chat.id,
                "⚠️ Daily limit reached.\nContact owner if you need more access.",
                reply_markup=markup
            )
            return

    bg_file = get_global_bg()
    qr_img = generate_qr(user["upi_id"], amount, bg_file)

    bot.send_photo(
        message.chat.id,
        qr_img,
        caption=f"💳 QR for ₹{amount}\n\n📲 Scan in any UPI app to pay"
    )

    users_col.update_one(
        {"user_id": user["user_id"]},
        {"$inc": {"daily_count": 1, "total_qr_count": 1},
         "$set": {"last_qr_time": datetime.datetime.utcnow()}}
    )
    log_qr_generation(user["user_id"], amount)

    notify_qr_owner(user, amount)
    if not is_premium(user):
        remaining = DAILY_LIMIT_FREE - (user.get("daily_count", 0) + 1)
        remaining = max(0, remaining)
        bot.send_message(
            message.chat.id,
            f"📊 You have {remaining} QR generation(s) left for today."
        )
    else:
        bot.send_message(
            message.chat.id,
            "⭐ Premium user: Unlimited QR generation!"
        )


@bot.message_handler(commands=['resetupi'])
def reset_upi(message):
    user_id = message.from_user.id
    user = users_col.find_one({"user_id": user_id})

    if not user:
        bot.reply_to(message, "⚠️ You are not registered. Please use /start first.")
        return

    users_col.update_one({"user_id": user_id}, {"$unset": {"upi_id": ""}})
    
    bot.reply_to(
        message,
        "🔄 Your UPI ID has been cleared.\n"
        "⚠️ Please set a new one using /setupi {your_upi_id}"
    )


@bot.message_handler(commands=['setbg'])
def setbg_handler(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Send the image to set as global QR background:")
    bot.register_next_step_handler(msg, save_global_bg)

def save_global_bg(message):
    if not message.photo:
        bot.reply_to(message, "⚠️ Please send an image.")
        return
    file_id = message.photo[-1].file_id
    settings_col.update_one({"key": "global_bg"}, {"$set": {"value": file_id}}, upsert=True)
    bot.reply_to(message, "✅ Global QR background set.")

@bot.message_handler(commands=['resetbg'])
def resetbg_handler(message):
    if not is_admin(message.from_user.id):
        return
    settings_col.delete_one({"key": "global_bg"})
    bot.reply_to(message, "✅ Global QR background reset.")

@bot.message_handler(commands=['stat'])
def stats_handler(message):
    if not is_admin(message.from_user.id):
        return

    total_users = users_col.count_documents({})
    premium_users = users_col.count_documents({"premium_until": {"$gt": datetime.datetime.utcnow()}})
    today_qr = users_col.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$daily_count"}}}
    ])
    today_qr_generated = next(today_qr, {}).get("total", 0)
    total_qr = users_col.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$total_qr_count"}}}
    ])
    total_qr_generated = next(total_qr, {}).get("total", 0)

    text = (
        f"📊 Bot Statistics\n\n"
        f"🗓 QR Today: {today_qr_generated}\n"
        f"💳 QR Total: {total_qr_generated}\n"
        f"👥 Users: {total_users}\n"
        f"⭐ Premium: {premium_users}"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['ban'])
def ban_handler(message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Usage: /ban {user_id}")
        return
    user_id = int(args[1])
    users_col.update_one({"user_id": user_id}, {"$set": {"banned": True}})
    bot.reply_to(message, f"✅ User {user_id} banned.")

@bot.message_handler(commands=['premium'])
def premium_handler(message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 3:
        bot.reply_to(message, "Usage: /premium {user_id} {days}")
        return
    user_id = int(args[1])
    days = int(args[2])
    until = datetime.datetime.utcnow() + datetime.timedelta(days=days)
    users_col.update_one({"user_id": user_id}, {"$set": {"premium_until": until}}, upsert=True)
    bot.reply_to(message, f"✅ User {user_id} granted premium until {until} UTC.")

@bot.message_handler(commands=['broadcast'])

def broadcast_handler(message):
    if not is_admin(message.from_user.id):
        return
    msg = bot.send_message(message.chat.id, "Send the broadcast message:")
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    for user in users_col.find({}):
        try:
            bot.send_message(user["user_id"], message.text)
        except:
            continue
    bot.reply_to(message, "✅ Broadcast sent to all users.")

@bot.message_handler(commands=['unban'])

def unban_handler(message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "Usage: /unban {user_id}")
        return
    user_id = int(args[1])
    users_col.update_one({"user_id": user_id}, {"$set": {"banned": False}})
    bot.reply_to(message, f"✅ User {user_id} has been unbanned.")
    
@bot.callback_query_handler(func=lambda call: call.data == "verify_forcejoin")
def callback_verify(call):
    ok, markup = check_force_join(call.from_user.id)
    if ok:
        bot.edit_message_text("✅ You have joined all required channels!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ You still need to join required channels.")

def run_bot():
    bot.infinity_polling()
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))