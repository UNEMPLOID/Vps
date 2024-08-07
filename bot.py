import telebot
from telebot import types
import logging
import time
from pymongo import MongoClient
from threading import Timer

# Enable logging
logging.basicConfig(level=logging.INFO)

# Bot token and log group ID
TOKEN = '7464984710:AAH7Fv1eT63NLgb8eiwyqBRpTpfLkSY6Euc'
LOG_GROUP_ID = -1002155266073

# Channels and group
REQUIRED_CHANNELS = ["@Found_Us", "@Falcon_security", "@Pbail_Squad"]
REQUIRED_GROUP = "@indian_hacker_group"
OWNER_ID = 5460343986  # Use the owner ID directly

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Initialize MongoDB with a direct connection string
MONGO_URI = "mongodb://sr6mv1ru66:AaxQBg50TtxVpX3P@cluster0-shard-00-00.t809eiz.mongodb.net:27017,cluster0-shard-00-01.t809eiz.mongodb.net:27017,cluster0-shard-00-02.t809eiz.mongodb.net:27017/?ssl=true&replicaSet=atlas-12u3ng-shard-0&authSource=admin&retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.bot_database
users_collection = db.users
logs_collection = db.logs

def log_action(user_id, username, action):
    log_entry = {
        'user_id': user_id,
        'username': username,
        'action': action,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    logs_collection.insert_one(log_entry)

@bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.username or f"User_{user_id}"

    # Insert user data into the database
    users_collection.update_one(
        {'user_id': user_id},
        {'$set': {'username': user_name}},
        upsert=True
    )

    # Log user start action
    log_action(user_id, user_name, 'start')

    # Inline buttons
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton("Found Us", url="https://t.me/Found_Us"),
        types.InlineKeyboardButton("Falcon Security", url="https://t.me/Falcon_security")
    )
    keyboard.add(
        types.InlineKeyboardButton("Indian Hacker Group", url="https://t.me/indian_hacker_group"),
        types.InlineKeyboardButton("PBAIL COMM", url="https://t.me/Pbail_Squad")
    )
    keyboard.add(
        types.InlineKeyboardButton("Verify", callback_data='verify')
    )
    keyboard.add(
        types.InlineKeyboardButton("Owner", url="https://t.me/Moon_God_Khonsu")
    )

    # Welcome message
    welcome_message = "Welcome! Please join all the required channels and group to use the bot."
    try:
        bot.send_photo(message.chat.id, "https://i.ibb.co/Jcf4gyy/20240126-165040-0000.png", caption=welcome_message, reply_markup=keyboard)
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send welcome message to user {user_id}: {e}")
        bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=f"Failed to send welcome message to user {user_id}: {e}"
        )

    # Logging new user start
    try:
        bot.send_message(
            chat_id=LOG_GROUP_ID,
            text=f"➕ New User Notification ➕\n\n👤 User: @{user_name}\n🆔 User ID: {user_id}\n🌝 Total Users Count: {users_collection.count_documents({})}"
        )
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to log new user start for user {user_id}: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'verify')
def process_callback_verify(call: telebot.types.CallbackQuery):
    user_id = call.from_user.id
    user_name = call.from_user.username or f"User_{user_id}"

    # Verification check
    try:
        is_verified = all([bot.get_chat_member(channel, user_id).status in ['member', 'administrator', 'creator'] for channel in REQUIRED_CHANNELS])
        is_verified &= bot.get_chat_member(REQUIRED_GROUP, user_id).status in ['member', 'administrator', 'creator']
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Verification check failed for user {user_id}: {e}")
        bot.send_message(
            chat_id=user_id,
            text="Error during verification. Please try again later."
        )
        return
    
    if is_verified:
        # If user is verified
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("Free RDP", web_app=types.WebAppInfo(url="https://app.apponfly.com/trial"))
        )
        try:
            bot.send_message(
                chat_id=user_id,
                text="Thank you for using our service. Press the Free RDP button to use RDP.",
                reply_markup=keyboard
            )
            log_action(user_id, user_name, 'verified')

            # Schedule deletion of the mini app button after 10 seconds
            Timer(10, delete_mini_app_button, [user_id]).start()

        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send Free RDP message to user {user_id}: {e}")
    else:
        # If user is not verified
        try:
            bot.send_message(
                chat_id=user_id,
                text="Please join all the required channels and group first to use the bot."
            )
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send verification failure message to user {user_id}: {e}")

def delete_mini_app_button(user_id):
    try:
        bot.send_message(user_id, "The Free RDP button has expired. Please start the bot again.")
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send expiration message to user {user_id}: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'commands')
def send_commands(call: telebot.types.CallbackQuery):
    commands = (
        "/start - Start the bot\n"
        "/broadcast <message> - Broadcast a message to all users\n"
        "/stats - Get statistics about the bot\n"
    )
    try:
        bot.send_message(call.message.chat.id, "Here are the bot commands:\n" + commands)
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send commands to user {call.from_user.id}: {e}")

@bot.message_handler(commands=['broadcast'])
def broadcast(message: telebot.types.Message):
    # Check if the user is the bot owner by user ID
    if message.from_user.id == OWNER_ID:
        message_text = ' '.join(message.text.split()[1:])
        sent_count = 0
        for user in users_collection.find({}):
            user_id = user['user_id']
            try:
                bot.send_message(chat_id=user_id, text=message_text)
                sent_count += 1
            except telebot.apihelper.ApiTelegramException as e:
                logging.warning(f"Could not send message to {user_id}: {e}")
        try:
            bot.send_message(message.chat.id, f"Broadcast sent to {sent_count} users.")
            log_action(message.from_user.id, message.from_user.username, 'broadcast')
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send broadcast confirmation to owner: {e}")
    else:
        try:
            bot.send_message(message.chat.id, "You are not authorized to use this command.")
        except telebot.apihelper.ApiTelegramException as e:
            logging.error(f"Failed to send unauthorized message to user {message.from_user.id}: {e}")

@bot.message_handler(commands=['stats'])
def stats(message: telebot.types.Message):
    user_count = users_collection.count_documents({})
    try:
        bot.send_message(message.chat.id, f"Total users who started the bot: {user_count}")
    except telebot.apihelper.ApiTelegramException as e:
        logging.error(f"Failed to send stats to user {message.from_user.id}: {e}")

def main():
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            logging.error(f"Bot polling failed: {e}")
            time.sleep(10)  # Wait before restarting the polling loop

if __name__ == "__main__":
    main()
