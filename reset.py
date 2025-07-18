import os
import time
import sqlite3
import requests
from uuid import uuid4
from flask import Flask, request
import telebot
from telebot import types

# ================= SESSION & CONFIG =================
session = requests.Session()
session.headers.update({"User-Agent": "Instagram 150.0.0.0 Android"})

TOKEN = "7288924933:AAFeIz94cL2M8LkN_ddX6nO73qmL6kiRj8I"  # Replace with your bot token
OWNER_ID = 5781973054     # Replace with your Telegram ID
BOT_USERNAME = "IGrstlinkBOT"  # Without @
RESET_DELAY = 2  # User wait simulation
COOLDOWN = 10  # Prevent spam
START_TIME = time.time()

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ================= DATABASE =================
db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS banned_users (user_id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS buttons (name TEXT, url TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS forcejoin (link TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER)")
cursor.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_reset', 0)")
db.commit()

cooldowns = {}
active_resets = 0

# ================= HELPERS =================
def is_admin(uid):
    return uid == OWNER_ID

def add_stat(key, amount=1):
    cursor.execute("UPDATE stats SET value = value + ? WHERE key = ?", (amount, key))
    db.commit()

def get_stat(key):
    cursor.execute("SELECT value FROM stats WHERE key=?", (key,))
    val = cursor.fetchone()
    return val[0] if val else 0

def get_buttons():
    cursor.execute("SELECT name, url FROM buttons")
    return cursor.fetchall()

def get_forcejoin():
    cursor.execute("SELECT link FROM forcejoin")
    return [x[0] for x in cursor.fetchall()]

def check_forcejoin(user_id):
    links = get_forcejoin()
    if not links:
        return True
    for link in links:
        try:
            channel = link.split("/")[-1]
            status = bot.get_chat_member(channel, user_id)
            if status.status in ["member", "administrator", "creator"]:
                continue
            return False
        except:
            return False
    return True

def format_time(seconds):
    return time.strftime("%H:%M:%S", time.gmtime(seconds))

# ================= RESET FEATURE =================
def send_reset(target):
    data = {
        "user_email" if "@" in target else "username": target,
        "device_id": str(uuid4()),
        "guid": str(uuid4())
    }
    t1 = time.time()
    try:
        res = session.post("https://i.instagram.com/api/v1/accounts/send_password_reset/", data=data, timeout=5)
    except:
        return "❌ Failed to connect to Instagram.", None, 0
    t2 = time.time()
    json_data = res.json()
    masked = json_data.get("obfuscated_email") or json_data.get("obfuscated_phone_number")
    if masked:
        return None, masked, round(t2 - t1, 2)
    return "❌ Invalid username or email!", None, 0

# ================= USER COMMANDS =================
@bot.message_handler(commands=['start'])
def start_cmd(msg):
    uid = msg.from_user.id
    name = msg.from_user.first_name

    if msg.chat.type != "private":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🤖 Start in DM", url=f"https://t.me/{BOT_USERNAME}?start=start"))
        return bot.reply_to(msg, "📩 Use me in DM for full features:", reply_markup=kb)

    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)", (uid, name))
    db.commit()

    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(types.InlineKeyboardButton("📢 Channel", url="https://t.me/fingercorn"),
           types.InlineKeyboardButton("💬 Group", url="https://t.me/+pR7zdn3FXn9lZGY9"))
    kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="check_join"))
    for btn_name, url in get_buttons():
        kb.add(types.InlineKeyboardButton(btn_name, url=url))

    if not check_forcejoin(uid):
        return bot.send_message(uid, "⚠ Please join required channels to use the bot:", reply_markup=kb)

    welcome_text = (
        "**WELCOME TO @IGrstlinkBot**\n"
        "✨ Powered by **Qurice**\n\n"
        "**💌 Send Instagram Reset Links Easily!**\n"
        "__**💦 Wamphire mom gonna go down! 💦**__\n\n"
        "✅ **Use /help to see all commands**\n"
        "**📌 Join all required channels to use the bot!**"
    )
    bot.send_message(uid, welcome_text, parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def check_join(call):
    if check_forcejoin(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Verified!")
        bot.send_message(call.message.chat.id, "✅ You are verified! Use /help for commands.")
    else:
        bot.answer_callback_query(call.id, "❌ Still missing some joins!")

@bot.message_handler(commands=['help'])
def help_cmd(msg):
    text = (
        "📜 *User Commands:*\n\n"
        "`/start` - Start bot\n"
        "`/help` - Show this menu\n"
        "`wamphire ka mkb <username/email>` - Send Instagram reset link\n"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("wamphire ka mkb"))
def reset_cmd(msg):
    global active_resets
    uid = msg.from_user.id
    name = msg.from_user.first_name

    cursor.execute("SELECT 1 FROM banned_users WHERE user_id=?", (uid,))
    if cursor.fetchone():
        return bot.reply_to(msg, "🚫 You are banned from using this bot.")

    if not check_forcejoin(uid):
        kb = types.InlineKeyboardMarkup()
        for link in get_forcejoin():
            kb.add(types.InlineKeyboardButton("📌 Join", url=link))
        kb.add(types.InlineKeyboardButton("✅ Verify", callback_data="check_join"))
        return bot.send_message(uid, "📢 Please join all required channels first:", reply_markup=kb)

    now = time.time()
    if uid in cooldowns and now - cooldowns[uid] < COOLDOWN:
        remaining = COOLDOWN - int(now - cooldowns[uid])
        return bot.reply_to(msg, f"Wamphire ki maa ko {remaining}s ka rest karne de {name}!! 😂")
    cooldowns[uid] = now

    parts = msg.text.split(maxsplit=3)
    if len(parts) < 4:
        return bot.reply_to(msg, "❗ Format:\n`wamphire ka mkb username_or_email`", parse_mode="Markdown")

    target = parts[3].strip()
    sent = bot.reply_to(msg, f"🔹 *Target:* `{target}`\n⏳ Sending reset request...", parse_mode="Markdown")

    active_resets += 1
    start_time = time.time()
    err, masked, t = send_reset(target)
    elapsed = time.time() - start_time
    remaining = RESET_DELAY - elapsed
    if remaining > 0:
        time.sleep(remaining)
    active_resets -= 1

    if err:
        funny_error = f"Dear {name},\nYe mail invalid hai! Username try karo Wamphire ki maa chodne!! 😂" if "@" in target else f"Dear {name},\nYe username galat hai! Mail try karo Wamphire ki maa chodne!! 😂"
        return bot.edit_message_text(funny_error, sent.chat.id, sent.message_id)

    add_stat('total_reset')
    funny_msg = (
        f"✅ *Reset Sent!*\n"
        f"📨 *Email:* `{masked}`\n"
        f"🕒 *Time:* `{t}s`\n\n"
        f"🔥 Wamphire ki maa ka reset bhi ho gaya! ⚡"
    )
    bot.edit_message_text(funny_msg, sent.chat.id, sent.message_id, parse_mode="Markdown")

# ================= ADMIN COMMANDS =================
@bot.message_handler(commands=['cmds'])
def cmds_cmd(msg):
    if not is_admin(msg.from_user.id):
        return
    text = (
        "👑 *Admin Commands:*\n"
        "`/ban <id>`\n"
        "`/unban <id>`\n"
        "`/broadcast <msg>`\n"
        "`/addbutton <name> <url>`\n"
        "`/removebutton <name>`\n"
        "`/addforcejoin <link>`\n"
        "`/removeforcejoin <link>`\n"
        "`wamphire chudai on/off`\n"
        "`/stat`\n"
        "`/ping`"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def ban_user(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /ban <user_id>")
    uid = int(parts[1])
    cursor.execute("INSERT OR IGNORE INTO banned_users VALUES (?)", (uid,))
    db.commit()
    bot.reply_to(msg, f"✅ User {uid} banned!")

@bot.message_handler(commands=['unban'])
def unban_user(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /unban <user_id>")
    uid = int(parts[1])
    cursor.execute("DELETE FROM banned_users WHERE user_id=?", (uid,))
    db.commit()
    bot.reply_to(msg, f"✅ User {uid} unbanned!")

@bot.message_handler(commands=['broadcast'])
def broadcast(msg):
    if not is_admin(msg.from_user.id):
        return
    text = msg.text.replace("/broadcast", "").strip()
    if not text:
        return bot.reply_to(msg, "Usage: /broadcast <message>")
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for u in users:
        try:
            bot.send_message(u[0], text)
        except:
            pass
    bot.reply_to(msg, "✅ Broadcast sent!")

@bot.message_handler(commands=['addbutton'])
def addbutton(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(msg, "Usage: /addbutton <name> <url>")
    name, url = parts[1], parts[2]
    cursor.execute("INSERT INTO buttons VALUES (?,?)", (name, url))
    db.commit()
    bot.reply_to(msg, f"✅ Button '{name}' added!")

@bot.message_handler(commands=['removebutton'])
def removebutton(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /removebutton <name>")
    cursor.execute("DELETE FROM buttons WHERE name=?", (parts[1],))
    db.commit()
    bot.reply_to(msg, f"✅ Button '{parts[1]}' removed!")

@bot.message_handler(commands=['addforcejoin'])
def addfj(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /addforcejoin <link>")
    cursor.execute("INSERT INTO forcejoin VALUES (?)", (parts[1],))
    db.commit()
    bot.reply_to(msg, f"✅ Force join link added!")

@bot.message_handler(commands=['removeforcejoin'])
def removefj(msg):
    if not is_admin(msg.from_user.id):
        return
    parts = msg.text.split()
    if len(parts) < 2:
        return bot.reply_to(msg, "Usage: /removeforcejoin <link>")
    cursor.execute("DELETE FROM forcejoin WHERE link=?", (parts[1],))
    db.commit()
    bot.reply_to(msg, f"✅ Force join link removed!")

@bot.message_handler(commands=['stat'])
def stat(msg):
    if not is_admin(msg.from_user.id):
        return
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM banned_users")
    banned_users = cursor.fetchone()[0]
    uptime = format_time(time.time() - START_TIME)
    text = (
        f"📊 *Bot Stats:*\n\n"
        f"👤 Total Users: {total_users}\n"
        f"🚫 Banned: {banned_users}\n"
        f"✅ Active Resets: {active_resets}\n"
        f"📤 Total Reset: {get_stat('total_reset')}\n"
        f"🕒 Uptime: {uptime}"
    )
    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

@bot.message_handler(commands=['ping'])
def ping(msg):
    start = time.time()
    pong = bot.send_message(msg.chat.id, "🏓 Pinging...")
    latency = round((time.time() - start) * 1000)
    bot.edit_message_text(f"📶 Ping: {latency} ms", msg.chat.id, pong.message_id)

# ================= FLASK SERVER =================
@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = request.get_data().decode("utf-8")
    bot.process_new_updates([telebot.types.Update.de_json(update)])
    return "OK", 200

@app.route('/')
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))