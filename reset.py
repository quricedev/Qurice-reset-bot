import os
import sqlite3
import time
import random
import requests
from uuid import uuid4
from datetime import datetime
from telebot import TeleBot, types

# ================= CONFIG =================
TOKEN = "7288924933:AAFeIz94cL2M8LkN_ddX6nO73qmL6kiRj8I"
OWNER_ID = 5781973054
BOT_USERNAME = "IGrstlinkBOT"
RESET_DELAY_MIN = 5  # Min delay before reset
RESET_DELAY_MAX = 12  # Max delay before reset
CHANNEL_LINK = "t.me/Fingercorn"
GROUP_LINK = "https://t.me/+pR7zdn3FXn9lZGY9"
# ================ INIT BOT =================
bot = TeleBot(TOKEN, parse_mode="Markdown")
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

# ================ DB SETUP =================
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, joined TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS forcejoin (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS buttons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, url TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS toggles (chat_id INTEGER PRIMARY KEY, enabled INTEGER)")
db.commit()

# ================ HELPERS =================
def is_banned(uid):
    return cur.execute("SELECT 1 FROM banned WHERE user_id=?", (uid,)).fetchone() is not None

def is_owner(uid):
    return uid == OWNER_ID

def add_user(uid):
    if not cur.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone():
        cur.execute("INSERT INTO users (user_id, joined) VALUES (?,?)", (uid, datetime.now().isoformat()))
        db.commit()
        # Notify owner about new user
        bot.send_message(OWNER_ID, f"👤 New user joined!\n[Open Chat](tg://user?id={uid})", parse_mode="Markdown")

def get_forcejoin():
    return [row[0] for row in cur.execute("SELECT link FROM forcejoin").fetchall()]

def get_buttons():
    return [(row[0], row[1]) for row in cur.execute("SELECT name, url FROM buttons").fetchall()]

def set_toggle(chat_id, state):
    cur.execute("INSERT OR REPLACE INTO toggles (chat_id, enabled) VALUES (?,?)", (chat_id, state))
    db.commit()

def is_enabled(chat_id):
    row = cur.execute("SELECT enabled FROM toggles WHERE chat_id=?", (chat_id,)).fetchone()
    return row and row[0] == 1

def is_in_channel(user_id, channel):
    try:
        member = bot.get_chat_member(channel, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False
        
def check_all_forcejoins(user_id):
    links = get_forcejoin()
    for link in links:
        try:
            if "t.me/" in link:
                channel = link.split("t.me/")[1].replace("+", "").replace("/", "")
                member = bot.get_chat_member(channel, user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
        except:
            return False
    return True
    
# ================ START HANDLER 
from datetime import datetime

@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = msg.from_user.id
    chat_id = msg.chat.id
    name = msg.from_user.first_name
    username = f"@{msg.from_user.username}" if msg.from_user.username else "❌ No Username"
    time_now = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    add_user(uid)

    # ✅ If in group, ask to start in DM
    if msg.chat.type != "private":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Start in DM", url=f"https://t.me/{BOT_USERNAME}?start=start"))
        bot.reply_to(msg, "➡️ Please start the bot in DM to use it.", reply_markup=kb)
        return

    # ✅ Check ban
    if is_banned(uid):
        bot.send_message(chat_id, "🚫 You are banned from using this bot.")
        return

    # ✅ Force Join Check
    if not check_all_forcejoins(uid):
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📌 Join Channel", url="https://t.me/Fingercorn"))
        kb.add(types.InlineKeyboardButton("💬 Group Chat", url="https://t.me/+pR7zdn3FXn9lZGY9"))
        kb.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_join"))
        bot.send_message(chat_id, "📢 *Please join the required channel to continue:*", reply_markup=kb, parse_mode="Markdown")
        return

    # ✅ Main Welcome Menu
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
    kb.add(types.InlineKeyboardButton("💬 Group Chat", url="https://t.me/+pR7zdn3FXn9lZGY9"))

    welcome_text = (
        "✅ *Welcome to IG Reset Link Sender Bot!* ✅\n\n"
        "Send Instagram password reset links easily and securely!\n\n"
        "Use /help to know your commands.\n\n"
        "⚠️ *Note:* Use responsibly. Spamming may lead to restrictions."
    )

    bot.send_message(chat_id, welcome_text, reply_markup=kb, parse_mode="Markdown")

    # ✅ Notify Owner
    notify_text = (
        f"👤 *New User Joined!*\n\n"
        f"📛 Name: {name}\n"
        f"🔗 Username: {username}\n"
        f"🆔 ID: `{uid}`\n"
        f"⏰ Time: {time_now}"
    )
    notify_kb = types.InlineKeyboardMarkup()
    notify_kb.add(types.InlineKeyboardButton("🔍 OPEN CHAT", url=f"tg://openmessage?user_id={uid}"))
    bot.send_message(OWNER_ID, notify_text, reply_markup=notify_kb, parse_mode="Markdown")


# ✅ Callback for "I Joined" Button
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def joined_btn(call):
    if not check_all_forcejoins(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ You haven't joined the channel yet!")
    else:
        bot.answer_callback_query(call.id, "✅ Verified!")
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
        kb.add(types.InlineKeyboardButton("💬 Group Chat", url="https://t.me/+pR7zdn3FXn9lZGY9"))
        bot.edit_message_text(
            "✅ Verified! You can now use the bot.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
    )
                                  
# ================ WAMPHIRE TOGGLE =================
@bot.message_handler(func=lambda m: m.text and m.text.lower() in ["wamphire chudai on", "wamphire chudai off"])
def wamphire_toggle(msg):
    if not is_owner(msg.from_user.id):
        return

    if msg.text.lower() == "wamphire chudai on":
        set_toggle(msg.chat.id, 1)
        bot.reply_to(msg, "✅ Wamphire chudai **enabled** in this group!")
    elif msg.text.lower() == "wamphire chudai off":
        set_toggle(msg.chat.id, 0)
        bot.reply_to(msg, "🚫 Wamphire chudai **disabled** in this group!")

# ================ RESET FEATURE =================
def send_reset(target):
    headers = {"User-Agent": "Instagram 150.0.0.0 Android"}
    data = {
        "user_email" if "@" in target else "username": target,
        "device_id": str(uuid4()),
        "guid": str(uuid4())
    }
    t1 = time.time()
    try:
        res = requests.post("https://i.instagram.com/api/v1/accounts/send_password_reset/", headers=headers, data=data, timeout=10)
    except requests.exceptions.RequestException:
        return "❌ Failed to connect to Instagram.", None, 0
    t2 = time.time()

    try:
        json_data = res.json()
    except:
        return "❌ Instagram returned an invalid response.", None, 0

    masked_email = json_data.get("obfuscated_email") or json_data.get("obfuscated_phone_number")
    if masked_email:
        return None, masked_email, round(t2 - t1, 2)
    else:
        return "❌ Reset failed. Invalid username or rate limit.", None, 0

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("wamphire ki mkb"))
def single_reset(msg):
    if is_banned(msg.from_user.id):
        bot.reply_to(msg, "🚫 You are banned from using this bot.")
        return

    if msg.chat.type != "private" and not is_enabled(msg.chat.id):
        return

    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        bot.reply_to(msg, "❗ Format:\n`wamphire ki mkb username_or_email`")
        return

    target = parts[3].strip()
    sent = bot.reply_to(msg, f"🔹 *Target:* `{target}`\n⏳ Sending reset request...")
    
    # ✅ Random delay for anti-spam
    delay = random.randint(RESET_DELAY_MIN, RESET_DELAY_MAX)
    time.sleep(delay)

    err, masked, t = send_reset(target)
    if err:
        bot.edit_message_text(err, sent.chat.id, sent.message_id)
    else:
        funny_msg = (
            f"✅ *Reset Sent!*\n"
            f"📨 *Email:* `{masked}`\n"
            f"🕒 *Time:* `{t}s`\n\n"
            f"🔥 Wamphire ki maa ka reset bhi ho gaya! ⚡\n"
            f"_Server whisper:_ \"Bhai, kya speed hai!\" 🚀💦"
        )

        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
        kb.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/TalkToQuriceBot"))

        bot.edit_message_text(funny_msg, sent.chat.id, sent.message_id, reply_markup=kb)

# ================ HELP =================
@bot.message_handler(commands=['help'])
def help_handler(msg):
    text = (
        "*📘 User Commands*\n\n"
        "🔹 `wamphire ki mkb <username/email>` – Send Instagram reset link\n\n"
        "⚠️ Make sure you have joined our channel before using the bot."
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
    kb.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/TalkToQuriceBot"))

    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=kb)

# ================ ADMIN COMMANDS =================
@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if not is_owner(msg.from_user.id): return
    try:
        uid = int(msg.text.split()[1])
        cur.execute("INSERT INTO banned VALUES (?)", (uid,))
        db.commit()
        bot.reply_to(msg, f"✅ Banned {uid}")
    except:
        bot.reply_to(msg, "❗ Usage: /ban <user_id>")

@bot.message_handler(commands=['unban'])
def unban_user(msg):
    if not is_owner(msg.from_user.id): return
    try:
        uid = int(msg.text.split()[1])
        cur.execute("DELETE FROM banned WHERE user_id=?", (uid,))
        db.commit()
        bot.reply_to(msg, f"✅ Unbanned {uid}")
    except:
        bot.reply_to(msg, "❗ Usage: /unban <user_id>")

@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if not is_owner(msg.from_user.id): return
    text = msg.text.split(maxsplit=1)[1]
    for uid in cur.execute("SELECT user_id FROM users").fetchall():
        try: bot.send_message(uid[0], text)
        except: pass
    bot.reply_to(msg, "✅ Broadcast sent.")

@bot.message_handler(commands=['stat'])
def stats(msg):
    if not is_owner(msg.from_user.id): return
    users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned = cur.execute("SELECT COUNT(*) FROM banned").fetchone()[0]
    fj = cur.execute("SELECT COUNT(*) FROM forcejoin").fetchone()[0]
    btns = cur.execute("SELECT COUNT(*) FROM buttons").fetchone()[0]
    bot.reply_to(msg, f"📊 Stats:\nUsers: {users}\nBanned: {banned}\nForce Join: {fj}\nButtons: {btns}")

@bot.message_handler(commands=['cmds'])
def show_cmds(msg):
    if not is_owner(msg.from_user.id):
        return

    text = (
        "*📘 Bot Commands*\n\n"
        "🔹 **User Commands**\n"
        "`/start` – Start the bot\n"
        "`/help` – Show help menu\n"
        "`wamphire ki mkb <username/email>` – Send Instagram reset link\n\n"
        "🔹 **Admin Commands**\n"
        "`/ban <user_id>` – Ban a user\n"
        "`/unban <user_id>` – Unban a user\n"
        "`/broadcast <text>` – Send message to all users\n"
        "`/addforcejoin <link>` – Add channel/group to Force Join\n"
        "`/removeforcejoin <link>` – Remove Force Join\n"
        "`/addbutton <name> <url>` – Add custom button\n"
        "`/removebutton <name>` – Remove custom button\n"
        "`/stat` – View bot statistics\n"
        "`/cmds` – Show this command list\n"
        "`wamphire chudai on/off` – Enable/Disable group reset"
    )

    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
    kb.add(types.InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/TalkToQuriceBot"))

    bot.send_message(msg.chat.id, text, parse_mode="Markdown", reply_markup=kb)
# ================= KEEP ALIVE =================
from threading import Thread
from flask import Flask
import os

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is alive!"

def run_http_server():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_http_server)
    t.start()

# Call this before starting the bot
if __name__ == "__main__":
    keep_alive()  # Starts Flask web server
    print("✅ Bot is running...")
    bot.infinity_polling()
