import os
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

client = MongoClient(MONGO_URL)
db = client["telegram_bot"]
users_col = db["users"]
withdraw_col = db["withdraw_history"]

CHANNELS = ["https://t.me/joinmoney_earning"]

user_step = {}

def get_user(user_id):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        users_col.insert_one({"user_id": user_id, "balance": 0})
        user = {"user_id": user_id, "balance": 0}
    return user

def update_balance(user_id, amount):
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": amount}})

async def check_join(user_id):
    for ch in CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

async def auto_message():
    msgs = [
        "🔥 Someone withdrew ₹290",
        "💰 Payment done ₹590",
        "🎉 User got ₹999"
    ]
    while True:
        for user in users_col.find():
            try:
                await bot.send_message(user["user_id"], random.choice(msgs))
            except:
                pass
        await asyncio.sleep(300)

@dp.message_handler(commands=['start'])
async def start(msg: types.Message):
    get_user(msg.from_user.id)
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Join Main", url="https://t.me/joinmoney_earning"),
        InlineKeyboardButton("Join Backup", url="https://t.me/joinmoney_earning"),
        InlineKeyboardButton("Verify", callback_data="verify")
    )
    await msg.answer("Join both channels first", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data == "verify")
async def verify(call: types.CallbackQuery):
    if await check_join(call.from_user.id):
        kb = ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("💰 Earn")
        kb.add("💳 Wallet", "💸 Withdraw")
        kb.add("📜 History")
        await call.message.answer("Verified!", reply_markup=kb)
    else:
        await call.answer("Join channels first", show_alert=True)

@dp.message_handler(lambda m: m.text == "💰 Earn")
async def earn(msg: types.Message):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🥇 Slice ₹250")
    kb.add("🥈 Upstox ₹120")
    kb.add("🥉 TaskBucks ₹70")
    kb.add("⏳ Offer Coming Soon")
    await msg.answer("Select offer:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥇 Slice ₹250")
async def slice(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹250", url="https://t.sliceit.com/s?c=irYwC_h&ic=DSNOX46416"))
    await msg.answer("Install → Signup → UPI Payment\nReward ₹250", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥈 Upstox ₹120")
async def upstox(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹120", url="https://upstox.onelink.me/0H1s/5GCLUE"))
    await msg.answer("Open account → KYC\nReward ₹120", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🥉 TaskBucks ₹70")
async def taskbucks(msg: types.Message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Get ₹70", url="http://tbk.bz/jf3gjkc9"))
    await msg.answer("Install → Complete tasks\nReward ₹70", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "⏳ Offer Coming Soon")
async def coming(msg: types.Message):
    await msg.answer("Complete all offers. New offers coming soon!")

@dp.message_handler(lambda m: m.text == "💳 Wallet")
async def wallet(msg: types.Message):
    user = get_user(msg.from_user.id)
    await msg.answer(f"Balance: ₹{user['balance']}")

@dp.message_handler(lambda m: m.text == "💸 Withdraw")
async def withdraw(msg: types.Message):
    user = get_user(msg.from_user.id)
    if user["balance"] < 290:
        await msg.answer("Minimum ₹290 required")
        return
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("₹290", "₹590", "₹999")
    user_step[msg.from_user.id] = "plan"
    await msg.answer("Select plan:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "📜 History")
async def history(msg: types.Message):
    records = withdraw_col.find({"user_id": msg.from_user.id}).sort("_id", -1).limit(5)
    text = "📜 Last Withdrawals:\n"
    for r in records:
        text += f"₹{r['amount']} - {r['upi']}\n"
    await msg.answer(text)

@dp.message_handler()
async def handle(msg: types.Message):
    user_id = msg.from_user.id
    if user_id not in user_step:
        return
    step = user_step[user_id]

    if step == "plan":
        if msg.text not in ["₹290","₹590","₹999"]:
            await msg.answer("Invalid plan")
            return
        amount = int(msg.text.replace("₹",""))
        user = get_user(user_id)
        if user["balance"] < amount:
            await msg.answer("Not enough balance")
            return
        user_step[user_id] = {"amount": amount}
        await msg.answer("Enter UPI ID:")

    elif isinstance(step, dict):
        amount = step["amount"]
        update_balance(user_id, -amount)

        withdraw_col.insert_one({
            "user_id": user_id,
            "amount": amount,
            "upi": msg.text
        })

        await bot.send_message(
            ADMIN_ID,
            f"Withdrawal Request\nUser: {user_id}\nAmount: ₹{amount}\nUPI: {msg.text}"
        )

        await msg.answer("Request sent. Amount deducted.")
        del user_step[user_id]

@dp.message_handler(commands=['admin'])
async def admin(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer(f"Users: {users_col.count_documents({})}\nBalance: ₹4000")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(auto_message())
    executor.start_polling(dp)
    
