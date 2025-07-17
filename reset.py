import os
import sqlite3
import time
import random
import requests
from uuid import uuid4
from datetime import datetime
from telebot import TeleBot, types
from threading import Thread
from flask import Flask

# ================= CONFIG =================
TOKEN = "YOUR_BOT_TOKEN"  # Replace with your bot token
OWNER_ID = 5781973054
BOT_USERNAME = "IGrstlinkBOT"
RESET_DELAY_MIN = 5
RESET_DELAY_MAX = 12

# ================= INIT BOT =================
bot = TeleBot(TOKEN, parse_mode="Markdown")
db = sqlite3.connect("bot.db", check_same_thread=False)
cur = db.cursor()

# ================= DB SETUP =================
cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, joined TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS banned (user_id INTEGER)")
cur.execute("CREATE TABLE IF NOT EXISTS forcejoin (id INTEGER PRIMARY KEY AUTOINCREMENT, link TEXT)")
cur.execute("CREATE TABLE IF NOT EXISTS buttons (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, url TEXT)")
db.commit()

# ================= HELPERS =================
cooldowns = {}

def is_banned(uid):
    return cur.execute("SELECT 1 FROM banned WHERE user_id=?", (uid,)).fetchone() is not None

def add_user(uid, name, username):
    if not cur.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone():
        cur.execute("INSERT INTO users (user_id, joined) VALUES (?,?)", (uid, datetime.now().isoformat()))
        db.commit()
        uname = f"@{username}" if username else "None"
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("OPEN CHAT", url=f"tg://openmessage?user_id={uid}"))
        bot.send_message(OWNER_ID,
            f"👤 *New User Joined*\n"
            f"Name: {name}\n"
            f"Username: {uname}\n"
            f"ID: `{uid}`\n"
            f"Time: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
            reply_markup=kb)

def get_forcejoin():
    return [row[0] for row in cur.execute("SELECT link FROM forcejoin").fetchall()]

def get_buttons():
    return [(row[0], row[1]) for row in cur.execute("SELECT name, url FROM buttons").fetchall()]

def check_all_forcejoins(uid):
    for link in get_forcejoin():
        channel = link.replace("https://t.me/", "@")
        try:
            member = bot.get_chat_member(channel, uid)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ================= START =================
@bot.message_handler(commands=['start'])
def start_handler(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name
    username = msg.from_user.username
    chat_id = msg.chat.id
    add_user(uid, name, username)

    if msg.chat.type != "private":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("Start in DM", url=f"https://t.me/{BOT_USERNAME}?start=start"))
        return bot.reply_to(msg, "➡️ Please start the bot in DM.", reply_markup=kb)

    if is_banned(uid):
        return bot.send_message(chat_id, "🚫 You are banned from using this bot.")

    if not check_all_forcejoins(uid):
        kb = types.InlineKeyboardMarkup()
        for link in get_forcejoin():
            kb.add(types.InlineKeyboardButton("📌 Join", url=link))
        kb.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_join"))
        return bot.send_message(chat_id, "📢 Please join all required channels to continue:", reply_markup=kb)

    kb = types.InlineKeyboardMarkup()
    for name, url in get_buttons():
        kb.add(types.InlineKeyboardButton(name, url=url))
    kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
    kb.add(types.InlineKeyboardButton("💬 Group", url="https://t.me/+pR7zdn3FXn9lZGY9"))
    bot.send_message(chat_id, "✅ Welcome to IG Reset Link Sender Bot ✅\nSend Instagram password reset links easily!\n\nUse /help to know commands.\n\n⚠️ Note: Use responsibly!", reply_markup=kb)

# ================= "I Joined" Button =================
@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def joined_btn(call):
    if not check_all_forcejoins(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels yet!")
    else:
        bot.answer_callback_query(call.id, "✅ Verified!")
        kb = types.InlineKeyboardMarkup()
        for name, url in get_buttons():
            kb.add(types.InlineKeyboardButton(name, url=url))
        kb.add(types.InlineKeyboardButton("📌 Channel", url="https://t.me/Fingercorn"))
        kb.add(types.InlineKeyboardButton("💬 Group", url="https://t.me/+pR7zdn3FXn9lZGY9"))
        bot.edit_message_text("✅ Verified! You can now use the bot.", call.message.chat.id, call.message.message_id, reply_markup=kb)

# ================= HELP =================
@bot.message_handler(commands=['help'])
def help_cmd(msg):
    text = (
        "✅ *Commands List*\n\n"
        "/start - Start the bot\n"
        "/help - Show commands\n"
        "`wamphire ki mkb username_or_email` - Send Instagram reset\n\n"
        "⚠️ Use responsibly!"
    )
    bot.send_message(msg.chat.id, text)

# ================= RESET FEATURE =================
def send_reset(target):
    headers = {"User-Agent": "Instagram 150.0.0.0 Android"}
    data = {"user_email" if "@" in target else "username": target, "device_id": str(uuid4()), "guid": str(uuid4())}
    t1 = time.time()
    try:
        res = requests.post("https://i.instagram.com/api/v1/accounts/send_password_reset/", headers=headers, data=data, timeout=10)
    except:
        return "❌ Failed to connect to Instagram.", None, 0
    t2 = time.time()
    json_data = res.json()
    masked = json_data.get("obfuscated_email") or json_data.get("obfuscated_phone_number")
    if masked:
        return None, masked, round(t2 - t1, 2)
    return "❌ Reset failed. Invalid username or rate limit.", None, 0

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("wamphire ki mkb"))
def reset_cmd(msg):
    uid = msg.from_user.id

    if is_banned(uid):
        return bot.reply_to(msg, "🚫 You are banned from using this bot.")

    # ✅ Force Join Check
    if not check_all_forcejoins(uid):
        kb = types.InlineKeyboardMarkup()
        for link in get_forcejoin():
            kb.add(types.InlineKeyboardButton("📌 Join", url=link))
        kb.add(types.InlineKeyboardButton("✅ I Joined", callback_data="check_join"))
        return bot.send_message(uid, "📢 Please join all required channels first:", reply_markup=kb)

    # ✅ Cooldown check
    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < 10:
        return bot.reply_to(msg, "⏳ Please wait 10 seconds before sending another reset.")
    cooldowns[uid] = now

    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        return bot.reply_to(msg, "❗ Format:\n`wamphire ki mkb username_or_email`")

    target = parts[3].strip()
    sent = bot.reply_to(msg, f"🔹 *Target:* `{target}`\n⏳ Sending reset request...")
    time.sleep(random.randint(RESET_DELAY_MIN, RESET_DELAY_MAX))
    err, masked, t = send_reset(target)
    if err:
        return bot.edit_message_text(err, sent.chat.id, sent.message_id)

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

# ================= ADMIN COMMANDS =================

# ✅ Ban a user
@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        uid = int(msg.text.split()[1])
        cur.execute("INSERT INTO banned VALUES (?)", (uid,))
        db.commit()
        bot.reply_to(msg, f"✅ Banned user: `{uid}`")
    except:
        bot.reply_to(msg, "❗ Usage: /ban <user_id>")

# ✅ Unban a user
@bot.message_handler(commands=['unban'])
def unban_user(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        uid = int(msg.text.split()[1])
        cur.execute("DELETE FROM banned WHERE user_id=?", (uid,))
        db.commit()
        bot.reply_to(msg, f"✅ Unbanned user: `{uid}`")
    except:
        bot.reply_to(msg, "❗ Usage: /unban <user_id>")

# ✅ Broadcast message to all users
@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        text = msg.text.split(maxsplit=1)[1]
    except:
        bot.reply_to(msg, "❗ Usage: /broadcast <message>")
        return
    users = cur.execute("SELECT user_id FROM users").fetchall()
    sent, failed = 0, 0
    for uid in users:
        try:
            bot.send_message(uid[0], text)
            sent += 1
        except:
            failed += 1
    bot.reply_to(msg, f"✅ Broadcast done.\nSent: {sent}\nFailed: {failed}")

# ✅ Add Force Join channel
@bot.message_handler(commands=['addforcejoin'])
def add_forcejoin(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        link = msg.text.split()[1]
        cur.execute("INSERT INTO forcejoin (link) VALUES (?)", (link,))
        db.commit()
        bot.reply_to(msg, f"✅ Added Force Join link:\n{link}")
    except:
        bot.reply_to(msg, "❗ Usage: /addforcejoin <channel_link>")

# ✅ Remove Force Join channel
@bot.message_handler(commands=['removeforcejoin'])
def remove_forcejoin(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        link = msg.text.split()[1]
        cur.execute("DELETE FROM forcejoin WHERE link=?", (link,))
        db.commit()
        bot.reply_to(msg, f"✅ Removed Force Join link:\n{link}")
    except:
        bot.reply_to(msg, "❗ Usage: /removeforcejoin <channel_link>")

# ✅ Add custom button
@bot.message_handler(commands=['addbutton'])
def add_button(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        parts = msg.text.split(maxsplit=2)
        name = parts[1]
        url = parts[2]
        cur.execute("INSERT INTO buttons (name, url) VALUES (?,?)", (name, url))
        db.commit()
        bot.reply_to(msg, f"✅ Button added:\nName: {name}\nURL: {url}")
    except:
        bot.reply_to(msg, "❗ Usage: /addbutton <name> <url>")

# ✅ Remove custom button
@bot.message_handler(commands=['removebutton'])
def remove_button(msg):
    if not is_owner(msg.from_user.id):
        return
    try:
        name = msg.text.split()[1]
        cur.execute("DELETE FROM buttons WHERE name=?", (name,))
        db.commit()
        bot.reply_to(msg, f"✅ Button removed: {name}")
    except:
        bot.reply_to(msg, "❗ Usage: /removebutton <name>")

# ✅ Show stats
@bot.message_handler(commands=['stat'])
def show_stats(msg):
    if not is_owner(msg.from_user.id):
        return
    users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    banned = cur.execute("SELECT COUNT(*) FROM banned").fetchone()[0]
    fj = cur.execute("SELECT COUNT(*) FROM forcejoin").fetchone()[0]
    btns = cur.execute("SELECT COUNT(*) FROM buttons").fetchone()[0]
    bot.reply_to(msg, f"📊 *Bot Stats:*\n\nUsers: {users}\nBanned: {banned}\nForce Join: {fj}\nButtons: {btns}", parse_mode="Markdown")

# ✅ Show admin commands
@bot.message_handler(commands=['cmds'])
def show_cmds(msg):
    if not is_owner(msg.from_user.id):
        return
    text = (
        "*📘 Admin Commands:*\n\n"
        "`/ban <user_id>` – Ban user\n"
        "`/unban <user_id>` – Unban user\n"
        "`/broadcast <text>` – Send message to all users\n"
        "`/addforcejoin <link>` – Add Force Join channel\n"
        "`/removeforcejoin <link>` – Remove Force Join\n"
        "`/addbutton <name> <url>` – Add custom button\n"
        "`/removebutton <name>` – Remove custom button\n"
        "`/stat` – Show bot stats\n"
        "`/cmds` – Show this list"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")


# ================= FLASK SERVER =================
app = Flask('')
@app.route('/')
def home(): return "✅ Bot is alive!"
def run_http_server(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run_http_server)
    t.start()

keep_alive()
print("✅ Bot is running...")
bot.infinity_polling()