import os
import re
import requests
import random
import json
import logging
from threading import Thread
import secrets
import uuid
from colorama import Fore, Style
from time import sleep
from datetime import datetime
from secrets import token_hex
from uuid import uuid4
import telebot
from telebot import types
from flask import Flask, request
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ================= FORCE JOIN CONFIG =================
FORCE_JOIN_CHANNELS = [
    {
        "id": "@anogenic",
        "link": "https://t.me/anogenic",
        "name": "#𝐐ᴜʀɪᴄᴇ 𝐂ᴏᴍᴇʙᴀᴄᴋ",
        "type": "public_channel"
    },
    {
        "id": -1002724715863,
        "link": "https://t.me/+BtnHDIwukOgzYzhl",
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
        "link": "https://t.me/+TZhXQn08a5tmYTQ9",
        "name": "#𝐌ᴀʀᴋᴇᴛ 𝐇ᴜʙ",
        "type": "private_group"
    },
    {
        "id": -1002535054786,
        "link": "https://t.me/+lwHNj7yb0c00NTA1",
        "name": "𝗥𝗔𝗭𝗔 𝗣𝗬 - 𝗧𝗢𝗢𝗟𝗦",
        "type": "private_channel"
    }
]


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
app = Flask(__name__)


# ================= GLOBALS =================
reports_in_progress = {}
user_sessions = {}
registered_users = set()

# Colors (emoji based)
G = "🟢"
R = "🔴"
Y = "🟡"
B = "🔵"
W = "⚪"
# ================= HELPERS =================
def check_force_join(user_id):
    """
    Check if user is a member of ALL required channels/groups.
    If not, return (False, [missing_channels])
    """
    missing = []
    try:
        for ch in FORCE_JOIN_CHANNELS:
            try:
                member = bot.get_chat_member(ch["id"], user_id)
                if member.status in ["left", "kicked", "banned"]:
                    missing.append(ch)
            except Exception as e:
                print(f"⚠️ Error checking {ch['name']}: {e}")
                missing.append(ch)
        return (len(missing) == 0, missing)
    except Exception as e:
        print(f"❌ Force join check error: {e}")
        return False, FORCE_JOIN_CHANNELS


def force_join_keyboard(channels, with_verify=True):
    """
    Build Inline Keyboard with missing channel links + Verify button
    """
    markup = types.InlineKeyboardMarkup()
    for ch in channels:
        markup.add(types.InlineKeyboardButton(f"Join {ch['name']}", url=ch["link"]))
    if with_verify:
        markup.add(types.InlineKeyboardButton("✅ Verify", callback_data="verify_join"))
    return markup

# ================= CLASS =================
class InstagramReporter:
    def __init__(self):
        self.a = 0
        self.b = 0
        self.c = 0
        self.d = 0
        self.e = 0
        self.f = 0
        self.g = 0
        self.h = 0
        self.z = 0
        self.r = requests.Session()
        self.uid = uuid.uuid4()
        self.cookie = secrets.token_hex(8)*2

    def login(self, username, password):
        url = 'https://i.instagram.com/api/v1/accounts/login/'
        headers = {
            'User-Agent': 'Instagram 113.0.0.39.122 Android (24/5.0; 515dpi; 1440x2416; huawei/google; Nexus 6P; angler; angler; en_US)',
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US",
            "X-IG-Capabilities": "3brTvw==",
            "X-IG-Connection-Type": "WIFI",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            'Host': 'i.instagram.com',
            'Connection': 'keep-alive'
        }
        
        data = {
            'uuid': self.uid,
            'password': password,
            'username': username,
            'device_id': self.uid,
            'from_reg': 'false',
            '_csrftoken': 'missing',
            'login_attempt_countn': '0'
        }

        response = self.r.post(url, headers=headers, data=data)
        cookies = response.cookies
        cookie_jar = cookies.get_dict()
        
        try:
            csrf_token = cookie_jar['csrftoken']
        except:
            csrf_token = self.cookie
            
        if 'logged_in_user' in response.text:
            self.r.headers.update({'X-CSRFToken': csrf_token})
            return True, "Login successful"
        elif 'challenge_required' in response.text:
            return False, "Account is secure - challenge required"
        elif 'two_factor_required' in response.text:
            return False, "Two factor authentication required"
        else:
            return False, "Login failed - check credentials"

    def report_account(self, target_username, report_type, count, sleep_time):
        try:
            url_id = f'https://www.instagram.com/{target_username}/?__a=1'
            req = self.r.get(url_id).json()
            idd = str(req['logging_page_id'])
            target_id = idd.split('_')[1]
            
            url_report = f'https://www.instagram.com/users/{target_id}/report/'
            
            reason_ids = {
                'spam': '1',
                'harassment': '7',
                'sale_drugs': '3',
                'violence': '5',
                'nudity': '4',
                'hate': '6',
                'self_injury': '2',
                'me': '8'
            }
            
            data = {
                'source_name': '',
                'reason_id': reason_ids[report_type],
                'frx_context': ''
            }
            
            for _ in range(count):
                report = self.r.post(url_report, data=data)
                if report.status_code == 200:
                    if report_type == 'spam': self.a += 1
                    elif report_type == 'harassment': self.b += 1
                    elif report_type == 'sale_drugs': self.c += 1
                    elif report_type == 'violence': self.d += 1
                    elif report_type == 'nudity': self.e += 1
                    elif report_type == 'hate': self.f += 1
                    elif report_type == 'self_injury': self.g += 1
                    elif report_type == 'me': self.h += 1
                else:
                    self.z += 1
                sleep(sleep_time)
            
            return True, "Reports completed"
        except Exception as e:
            return False, f"Error during reporting: {str(e)}"
# ================= HANDLERS =================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id

    # ✅ Force Join Check
    is_joined, missing = check_force_join(user_id)
    if not is_joined:
        bot.send_message(
            user_id,
            f"{R} You must join all required channels/groups to use this bot!",
            reply_markup=force_join_keyboard(missing)
        )
        return

    registered_users.add(user_id)

    welcome_msg = f"""{G} Instagram Report Bot {G}

{Y} This bot helps you report Instagram accounts for various violations.

{B} Available commands:
/start - Show this message
/report - Start a new report
"""
    bot.reply_to(message, welcome_msg)


@bot.message_handler(commands=['report'])
def start_report(message):
    chat_id = message.chat.id

    # ✅ Force Join Check
    is_joined, missing = check_force_join(chat_id)
    if not is_joined:
        bot.send_message(
            chat_id,
            f"{R} You must join all required channels/groups to use this command!",
            reply_markup=force_join_keyboard(missing)
        )
        return

    user_sessions[chat_id] = {'state': 'awaiting_option'}

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add('Single Account', 'Multiple Accounts')

    bot.send_message(chat_id, f"{Y}Choose report mode:", reply_markup=markup)
    user_sessions[chat_id]['state'] = 'awaiting_mode'


# ================= VERIFY CALLBACK =================
@bot.callback_query_handler(func=lambda call: call.data == "verify_join")
def verify_callback(call):
    user_id = call.from_user.id
    is_joined, missing = check_force_join(user_id)

    if is_joined:
        registered_users.add(user_id)
        bot.answer_callback_query(call.id, "✅ Verified! You can now use the bot.")
        bot.send_message(user_id, f"{G} Welcome back! You are now verified.\n\nUse /report to start.")
    else:
        bot.answer_callback_query(call.id, "❌ Still missing channels!")
        bot.send_message(
            user_id,
            f"{R} You still need to join all required channels/groups!",
            reply_markup=force_join_keyboard(missing)
        )



@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "🚫 You are not authorized to use this command.")
        return

    text = message.text.split(" ", 1)
    if len(text) < 2:
        bot.reply_to(message, "⚠️ Usage: /broadcast Your message here")
        return

    broadcast_msg = text[1]
    count = 0
    for user in list(registered_users):
        try:
            bot.send_message(user, f"📢 Broadcast:\n\n{broadcast_msg}")
            count += 1
        except Exception as e:
            print(f"❌ Failed to send broadcast to {user}: {e}")

    bot.reply_to(message, f"✅ Broadcast sent to {count} users.")

    
@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_mode')
def handle_mode(message):
    chat_id = message.chat.id
    mode = message.text
    
    if mode not in ['Single Account', 'Multiple Accounts']:
        bot.send_message(chat_id, f"{R}Invalid option. Please choose 'Single Account' or 'Multiple Accounts'")
        return
    
    user_sessions[chat_id]['mode'] = mode
    user_sessions[chat_id]['state'] = 'awaiting_credentials'
    
    if mode == 'Single Account':
        bot.send_message(chat_id, f"{Y}Please send your Instagram credentials in the format:\nusername:password")
    else:
        bot.send_message(chat_id, f"{Y}Please send multiple Instagram credentials separated by new lines in the format:\nusername1:password1\nusername2:password2")

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_credentials')
def handle_credentials(message):
    chat_id = message.chat.id
    credentials = message.text.split('\n')
    
    # Validate credentials format
    valid_creds = []
    for cred in credentials:
        if ':' not in cred or len(cred.split(':')) != 2:
            bot.send_message(chat_id, f"{R}Invalid format. Please use username:password")
            return
        valid_creds.append(cred)
    
    user_sessions[chat_id]['credentials'] = valid_creds
    user_sessions[chat_id]['state'] = 'awaiting_target'
    bot.send_message(chat_id, f"{Y}Now send the target Instagram username you want to report:")

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_target')
def handle_target(message):
    chat_id = message.chat.id
    target = message.text.strip()
    user_sessions[chat_id]['target'] = target
    user_sessions[chat_id]['state'] = 'awaiting_report_types'
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, row_width=2)
    markup.add('Spam', 'Harassment', 'Sale Drugs', 'Violence', 
               'Nudity', 'Hate', 'Self Injury', 'Pretending to be me')
    
    bot.send_message(chat_id, f"{Y}Select the report types (you'll set counts next):", reply_markup=markup)

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_report_types')
def handle_report_types(message):
    chat_id = message.chat.id
    report_type = message.text.strip()
    
    # Map to internal report types
    type_mapping = {
        'Spam': 'spam',
        'Harassment': 'harassment',
        'Sale Drugs': 'sale_drugs',
        'Violence': 'violence',
        'Nudity': 'nudity',
        'Hate': 'hate',
        'Self Injury': 'self_injury',
        'Pretending to be me': 'me'
    }
    
    if report_type not in type_mapping:
        bot.send_message(chat_id, f"{R}Invalid report type. Please select from the options.")
        return
    
    if 'report_types' not in user_sessions[chat_id]:
        user_sessions[chat_id]['report_types'] = []
    
    user_sessions[chat_id]['report_types'].append(type_mapping[report_type])
    user_sessions[chat_id]['state'] = 'awaiting_report_count'
    
    bot.send_message(chat_id, f"{Y}How many '{report_type}' reports do you want to send?")

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_report_count')
def handle_report_count(message):
    chat_id = message.chat.id
    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except ValueError:
        bot.send_message(chat_id, f"{R}Please enter a valid positive number")
        return
    
    if 'report_counts' not in user_sessions[chat_id]:
        user_sessions[chat_id]['report_counts'] = []
    
    user_sessions[chat_id]['report_counts'].append(count)
    
    # Check if we have counts for all selected types
    if len(user_sessions[chat_id]['report_counts']) < len(user_sessions[chat_id]['report_types']):
        remaining_types = [
            t for t in user_sessions[chat_id]['report_types'] 
            if t not in user_sessions[chat_id]['report_counts']
        ]
        bot.send_message(chat_id, f"{Y}Enter count for '{remaining_types[0]}' reports:")
    else:
        user_sessions[chat_id]['state'] = 'awaiting_sleep_time'
        bot.send_message(chat_id, f"{Y}Enter sleep time (in seconds) between reports:")

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'awaiting_sleep_time')
def handle_sleep_time(message):
    chat_id = message.chat.id
    try:
        sleep_time = float(message.text)
        if sleep_time < 0:
            raise ValueError
    except ValueError:
        bot.send_message(chat_id, f"{R}Please enter a valid positive number")
        return
    
    user_sessions[chat_id]['sleep_time'] = sleep_time
    user_sessions[chat_id]['state'] = 'ready_to_start'
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add('Start Reporting', 'Cancel')
    
    # Show summary
    summary = f"{G}Report Summary{G}\n\n"
    summary += f"{B}Target: {W}{user_sessions[chat_id]['target']}\n"
    summary += f"{B}Mode: {W}{user_sessions[chat_id]['mode']}\n"
    summary += f"{B}Accounts: {W}{len(user_sessions[chat_id]['credentials'])}\n"
    
    for i, (rtype, rcount) in enumerate(zip(
        user_sessions[chat_id]['report_types'],
        user_sessions[chat_id]['report_counts']
    )):
        summary += f"{B}{rtype.capitalize()}: {W}{rcount}\n"
    
    summary += f"{B}Sleep time: {W}{sleep_time} seconds\n\n"
    summary += f"{Y}Confirm to start reporting?"
    
    bot.send_message(chat_id, summary, reply_markup=markup)

@bot.message_handler(func=lambda message: user_sessions.get(message.chat.id, {}).get('state') == 'ready_to_start' and message.text == 'Start Reporting')
def start_reporting_process(message):
    chat_id = message.chat.id
    session = user_sessions[chat_id]
    
    # Initialize reporter
    reporter = InstagramReporter()
    
    # Process each account
    for cred in session['credentials']:
        username, password = cred.split(':')
        success, msg = reporter.login(username, password)
        
        if not success:
            bot.send_message(chat_id, f"{R}Login failed for {username}: {msg}")
            continue
        
        bot.send_message(chat_id, f"{G}Logged in successfully with {username}")
        
        # Process each report type
        for rtype, rcount in zip(session['report_types'], session['report_counts']):
            bot.send_message(chat_id, f"{Y}Sending {rcount} '{rtype}' reports...")
            success, msg = reporter.report_account(
                session['target'],
                rtype,
                rcount,
                session['sleep_time']
            )
            
            if success:
                bot.send_message(chat_id, f"{G}Completed {rcount} '{rtype}' reports")
            else:
                bot.send_message(chat_id, f"{R}Error during '{rtype}' reports: {msg}")
    
    # Send final stats
    stats = f"{G}Final Report Statistics{G}\n\n"
    stats += f"Spam: {reporter.a}\n"
    stats += f"Harassment: {reporter.b}\n"
    stats += f"Sale Drugs: {reporter.c}\n"
    stats += f"Violence: {reporter.d}\n"
    stats += f"Nudity: {reporter.e}\n"
    stats += f"Hate: {reporter.f}\n"
    stats += f"Self Injury: {reporter.g}\n"
    stats += f"Pretending to be me: {reporter.h}\n"
    stats += f"Errors: {reporter.z}\n"
    
    bot.send_message(chat_id, stats)
    user_sessions[chat_id] = {}  # Reset session

@bot.message_handler(commands=['stats'])
def show_stats(message):
    # This would show statistics if we were storing them
    bot.reply_to(message, f"{Y}Statistics feature coming soon!")

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
    print("Starting bot...")
    bot.infinity_polling()
