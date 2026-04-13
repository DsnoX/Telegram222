import os
import time
import random
import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from pymongo import MongoClient
from threading import Thread

load_dotenv()

# ===== ENV =====
API_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URI")

if not API_TOKEN:
    raise Exception("BOT_TOKEN missing")
if not MONGO_URL:
    raise Exception("MONGO_URI missing")

bot = telebot.TeleBot(API_TOKEN)

# ===== DATABASE =====
client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]
withdraw_col = db["withdraw_history"]

CHANNELS = ["@joinmoney_earning"]

user_step = {}

# ===== USER =====
def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0})
        user = {"user_id": user_id, "balance": 0}
    return user

def update_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

def check_join(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ===== AUTO MESSAGE =====
def auto_message():
    msgs = [
        "🔥 Someone withdrew ₹290",
        "💰 Payment done ₹590",
        "🎉 User got ₹999"
    ]
    while True:
        for user in users_col.find():
            try:
                bot.send_message(user["user_id"], random.choice(msgs))
            except:
                pass
        time.sleep(300)

# ===== START =====
@bot.message_handler(commands=['start'])
def start(msg):
    get_user(msg.from_user.id)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Join Main", url="https://t.me/joinmoney_earning"),
        InlineKeyboardButton("Join Backup", url="https://t.me/joinmoney_earning")
    )
    kb.add(InlineKeyboardButton("Verify", callback_data="verify"))

    bot.send_message(msg.chat.id, "Join both channels first", reply_markup=kb)

# ===== VERIFY =====
@bot.callback_query_handler(func=lambda call: call.data == "verify")
def verify(call):
    if check_join(call.from_user.id):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💰 Earn")
        kb.add("💳 Wallet", "💸 Withdraw")
        kb.add("📜 History")
        bot.send_message(call.message.chat.id, "Verified!", reply_markup=kb)
    else:
        bot.answer_callback_query(call.id, "Join channels first", show_alert=True)

# ===== EARN =====
@bot.message_handler(func=lambda m: m.text == "💰 Earn")
def earn(msg):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥇 Slice ₹250")
    kb.add("🥈 Upstox ₹120")
    kb.add("🥉 TaskBucks ₹70")
    kb.add("⏳ Offer Coming Soon")
    bot.send_message(msg.chat.id, "Select offer:", reply_markup=kb)

# ===== OFFERS =====
@bot.message_handler(func=lambda m: m.text == "🥇 Slice ₹250")
def slice_offer(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹250", url="https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"))
    bot.send_message(msg.chat.id, "Install → Signup → UPI Payment\nReward ₹250", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🥈 Upstox ₹120")
def upstox(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹120", url="https://upstox.onelink.me/0H1s/5GCLUE"))
    bot.send_message(msg.chat.id, "Open account → KYC\nReward ₹120", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🥉 TaskBucks ₹70")
def taskbucks(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹70", url="http://tbk.bz/jf3gjkc9"))
    bot.send_message(msg.chat.id, "Install → Complete tasks\nReward ₹70", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "⏳ Offer Coming Soon")
def coming(msg):
    bot.send_message(msg.chat.id, "Complete all offers. New offers coming soon!")

# ===== WALLET (BALANCE BUTTON) =====
@bot.message_handler(func=lambda m: m.text == "💳 Wallet")
def wallet(msg):
    user = get_user(msg.from_user.id)
    bot.send_message(msg.chat.id, f"Balance: ₹{user['balance']}")

# ===== WITHDRAW =====
@bot.message_handler(func=lambda m: m.text == "💸 Withdraw")
def withdraw(msg):
    user = get_user(msg.from_user.id)
    if user["balance"] < 290:
        bot.send_message(msg.chat.id, "Minimum ₹290 required")
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("₹290", "₹590", "₹999")
    user_step[msg.from_user.id] = "plan"
    bot.send_message(msg.chat.id, "Select plan:", reply_markup=kb)

# ===== HISTORY =====
@bot.message_handler(func=lambda m: m.text == "📜 History")
def history(msg):
    records = withdraw_col.find({"user_id": msg.from_user.id}).sort("_id", -1).limit(5)
    text = "📜 Last Withdrawals:\n"
    for r in records:
        text += f"₹{r['amount']} - {r['upi']}\n"
    bot.send_message(msg.chat.id, text)

# ===== HANDLE =====
@bot.message_handler(func=lambda msg: True)
def handle(msg):
    user_id = msg.from_user.id

    if user_id not in user_step:
        return

    step = user_step[user_id]

    if step == "plan":
        if msg.text not in ["₹290","₹590","₹999"]:
            bot.send_message(msg.chat.id, "Invalid plan")
            return

        amount = int(msg.text.replace("₹",""))
        user = get_user(user_id)

        if user["balance"] < amount:
            bot.send_message(msg.chat.id, "Not enough balance")
            return

        user_step[user_id] = {"amount": amount}
        bot.send_message(msg.chat.id, "Enter UPI ID:")

    elif isinstance(step, dict):
        amount = step["amount"]
        update_balance(user_id, -amount)

        withdraw_col.insert_one({
            "user_id": user_id,
            "amount": amount,
            "upi": msg.text
        })

        bot.send_message(
            ADMIN_ID,
            f"Withdrawal Request\nUser: {user_id}\nAmount: ₹{amount}\nUPI: {msg.text}"
        )

        bot.send_message(msg.chat.id, "Request sent. Amount deducted.")
        del user_step[user_id]

# ===== ADMIN =====
@bot.message_handler(commands=['admin'])
def admin(msg):
    if msg.from_user.id == ADMIN_ID:
        bot.send_message(msg.chat.id, f"Users: {users_col.count_documents({})}\nBalance: ₹4000")

# ===== RUN =====
if __name__ == "__main__":
    Thread(target=auto_message, daemon=True).start()
    bot.infinity_polling()
