import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from fpdf import FPDF
from flask import Flask
import re
import threading

# ================================
# CONFIG
# ================================
BOT_TOKEN = "7644742257:AAGzE5_fVD9xPb_KUWlrI7cAYh7Bxcd4utY"
OWNER_ID = 5781973054
CHANNEL_ID = -1002546105906
GROUP_ID = -1002586710325

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)

admins = [OWNER_ID]
user_steps = {}
pending_send = {}

# ================================
# HELPERS
# ================================
def is_admin(uid): return uid in admins
def is_owner(uid): return uid == OWNER_ID
def bold(t): return f"<b>{t}</b>"
def italic(t): return f"<i>{t}</i>"
def code(t): return f"<code>{t}</code>"

def admin_only(message):
    bot.reply_to(message, "❌ <b>This bot is only allowed for admins.</b>\nYou are not authorized to use it.")

# ================================
# /START
# ================================
@bot.message_handler(commands=['start'])
def start_command(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return
    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👋 <b>Welcome, Admin!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ You have access to the <b>Format Maker Bot</b>.\n"
        "This bot helps you create professional formats and reports effortlessly.\n\n"
        "📌 To get started, use:\n"
        f"{bold('/help')} – View all available commands.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, text)

# ================================
# /HELP
# ================================
@bot.message_handler(commands=['help'])
def help_command(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return

    text = (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>Format Maker Bot - Help</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👮 <b>Admins Only:</b>\n"
        "🔹 /help – Show this help menu\n"
        "🔹 NUMBER – (Reply) Extract info & format in 'User Information' style\n"
        "🔹 Details – Step-by-step scam report creation\n"
        "🔹 PDF – (Reply) Convert format into PDF\n"
        "🔹 /send – Post message to Channel or Group\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <b>Owner Only:</b>\n"
        "🔹 /admin <user_id> – Promote user to admin\n"
        "🔹 /demote <user_id> – Remove user from admin list\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    bot.reply_to(message, text)

# ================================
# OWNER COMMANDS
# ================================
@bot.message_handler(commands=['admin'])
def add_admin(message: Message):
    if not is_owner(message.from_user.id):
        admin_only(message)
        return
    try:
        uid = int(message.text.split()[1])
        if uid not in admins:
            admins.append(uid)
            bot.reply_to(message, f"✅ User {uid} promoted to admin.")
        else:
            bot.reply_to(message, "⚠️ Already an admin.")
    except:
        bot.reply_to(message, "❌ Usage: /admin <user_id>")

@bot.message_handler(commands=['demote'])
def remove_admin(message: Message):
    if not is_owner(message.from_user.id):
        admin_only(message)
        return
    try:
        uid = int(message.text.split()[1])
        if uid == OWNER_ID:
            bot.reply_to(message, "⚠️ You cannot demote yourself.")
            return
        if uid in admins:
            admins.remove(uid)
            bot.reply_to(message, f"✅ User {uid} removed from admin list.")
        else:
            bot.reply_to(message, "⚠️ Not an admin.")
    except:
        bot.reply_to(message, "❌ Usage: /demote <user_id>")

# ================================
# /SEND COMMAND
# ================================
@bot.message_handler(commands=['send'])
def send_menu(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📢 Channel", callback_data="send_channel"),
        InlineKeyboardButton("👥 Group", callback_data="send_group")
    )
    bot.reply_to(message, "Where do you want to send the message?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("send_"))
def choose_send(call):
    uid = call.from_user.id
    if not is_admin(uid):
        bot.answer_callback_query(call.id, "❌ Access Denied.")
        return

    if call.data == "send_channel":
        pending_send[uid] = "channel"
        bot.send_message(call.message.chat.id, "✅ Send me the message to post in the channel.")
    elif call.data == "send_group":
        pending_send[uid] = "group"
        bot.send_message(call.message.chat.id, "✅ Send me the message to post in the group.")

@bot.message_handler(func=lambda msg: msg.from_user.id in pending_send)
def handle_send_content(message: Message):
    target = pending_send.pop(message.from_user.id)
    if target == "channel":
        bot.send_message(CHANNEL_ID, message.text, parse_mode="HTML")
        bot.reply_to(message, "✅ Sent to Channel.")
    elif target == "group":
        bot.send_message(GROUP_ID, message.text, parse_mode="HTML")
        bot.reply_to(message, "✅ Sent to Group.")

# ================================
# NUMBER COMMAND
# ================================
@bot.message_handler(func=lambda m: m.text.strip().lower() == "number")
def handle_number(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return

    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to a message containing the data.")
        return

    text = message.reply_to_message.text
    user_id = re.search(r'ID[:\s]+(\d+)', text)
    phone = re.search(r'(\+?\d{10,15})', text)
    usernames = re.findall(r'@[\w\d_]+', text)
    date_match = re.search(r'as of (\d{1,2} \w+ \d{4})', text)

    user_id = user_id.group(1) if user_id else "N/A"
    phone = phone.group(1) if phone else "N/A"
    date = date_match.group(1) if date_match else "Unknown Date"

    formatted = (
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>User Information</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 {bold('Telegram User ID:')} {code(user_id)}\n"
        f"📞 {bold('Phone Number:')} {code(phone)}\n\n"
        f"📜 {bold('Username History')} (as of {italic(date)}):\n"
    )
    if usernames:
        formatted += "\n".join([f"- {bold(usernames[0])}"] + [f"- {code(u)}" for u in usernames[1:]])
    else:
        formatted += "- N/A"
    formatted += "\n━━━━━━━━━━━━━━━━━━━━━━━━"

    bot.reply_to(message, formatted)

# ================================
# DETAILS COMMAND
# ================================
DETAILS_FIELDS = ["Victim Username", "Scammer Username", "Telegram ID", "Scammed Amount", "UPI ID Used", "Phone Number", "Location", "Aadhar", "Real Name"]

@bot.message_handler(func=lambda m: m.text.strip().lower() == "details")
def start_details(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return

    user_steps[message.from_user.id] = {"step": 0, "data": {}}
    bot.reply_to(message, f"Enter {DETAILS_FIELDS[0]}:")

@bot.message_handler(func=lambda m: m.from_user.id in user_steps)
def handle_details(message: Message):
    step_info = user_steps[message.from_user.id]
    step = step_info["step"]
    value = message.text if message.text.lower() != "no" else "N/A"
    step_info["data"][DETAILS_FIELDS[step]] = value

    if step + 1 < len(DETAILS_FIELDS):
        step_info["step"] += 1
        bot.reply_to(message, f"Enter {DETAILS_FIELDS[step+1]}:")
    else:
        report = "━━━━━━━━━━━━━━━━━━━━━━━━\n🔴 <b>Scammer Report</b>\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
        emojis = ["🙍‍♂️","👤","🆔","💰","🏦","📞","📍","🪪","🧾"]
        for i, field in enumerate(DETAILS_FIELDS):
            report += f"{emojis[i]} {bold(field+':')} {code(step_info['data'][field])}\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━"
        bot.send_message(message.chat.id, report)
        del user_steps[message.from_user.id]

# ================================
# PDF COMMAND
# ================================
class PDF(FPDF):
    def header(self): pass

@bot.message_handler(func=lambda m: m.text.strip().lower() == "pdf")
def generate_pdf(message: Message):
    if not is_admin(message.from_user.id):
        admin_only(message)
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Reply to the message you want to convert to PDF.")
        return

    content = message.reply_to_message.text
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for line in content.split("\n"):
        if ":" in line:
            parts = line.split(":", 1)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, parts[0].strip(), ln=0)
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, ": "+parts[1].strip(), ln=1)
        else:
            pdf.cell(0, 10, line, ln=1)

    file_path = "report.pdf"
    pdf.output(file_path)
    with open(file_path, "rb") as f:
        bot.send_document(message.chat.id, f)

# ================================
# FLASK STATUS PAGE
# ================================
@app.route('/')
def home():
    return "✅ Bot is running with polling."

# ================================
# RUN BOT + FLASK
# ================================
def run_bot():
    print("✅ Bot started with polling...")
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    app.run(host="0.0.0.0", port=5000)