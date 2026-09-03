import os
import asyncio
import logging
import sqlite3
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Configuration
BOT_TOKEN = "8998611945:AAEr55Zq_4jyrOzmc4k2yw6PAM28Iin0md8"
ADMIN_ID = 8122859840
ADMIN_USERNAME = "@SHURJO_0"
NAGAD_NUMBER = "01672630670"

# Updated Product Prices Setup (in BDT)
PRODUCTS = {
    "kos_engine": {
        "name": "Kos Engine",
        "prices": {
            "1": 180,
            "7": 460,
            "15": 770,
            "30": 1240
        }
    },
    "aim_ai": {
        "name": "Aim Ai",
        "prices": {
            "1": 130,
            "3": 220,
            "7": 350,
            "15": 580,
            "30": 1050,
            "90": 2500
        }
    }
}

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            duration TEXT NOT NULL,
            key_code TEXT UNIQUE NOT NULL,
            is_used INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trxid TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# --- Keep-Alive Web Server for Render ---
async def handle_ping(request):
    return web.Response(text="Bot is Live and running 24/7!")

async def start_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/ping", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

# --- Aiogram Setup ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class PurchaseStates(StatesGroup):
    selecting_duration = State()
    awaiting_trxid = State()

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Buy Kos Engine"), KeyboardButton(text="🎯 Buy Aim Ai")],
            [KeyboardButton(text="📞 Support / Admin")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("স্বাগতম! আপনার প্রয়োজনীয় সার্ভিস টি সিলেক্ট করুন:", reply_markup=main_keyboard())

@dp.message(F.text == "📞 Support / Admin")
async def support_cmd(message: types.Message):
    await message.answer(f"যেকোনো প্রয়োজনে যোগাযোগ করুন: {ADMIN_USERNAME}")

@dp.message(F.text.in_(["🟢 Buy Kos Engine", "🎯 Buy Aim Ai"]))
async def select_product(message: types.Message, state: FSMContext):
    product_key = "kos_engine" if "Kos Engine" in message.text else "aim_ai"
    product_data = PRODUCTS[product_key]
    
    await state.update_data(product=product_key)
    
    buttons = []
    for duration, price in product_data["prices"].items():
        buttons.append([InlineKeyboardButton(text=f"{duration} Day(s) - {price} BDT", callback_data=f"dur_{duration}")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(f"**{product_data['name']}** এর মেয়াদ নির্বাচন করুন:", reply_markup=markup, parse_mode="Markdown")
    await state.set_state(PurchaseStates.selecting_duration)

@dp.callback_query(PurchaseStates.selecting_duration, F.data.startswith("dur_"))
async def select_duration(callback: types.CallbackQuery, state: FSMContext):
    duration = callback.data.split("_")[1]
    data = await state.get_data()
    product_key = data["product"]
    product_data = PRODUCTS[product_key]
    price = product_data["prices"][duration]
    
    await state.update_data(days=duration, price=price)
    
    msg = (
        f"**পেমেন্ট বিবরণী:**\n\n"
        f"পণ্য: {product_data['name']}\n"
        f"মেয়াদ: {duration} দিন\n"
        f"মূল্য: {price} টাকা\n\n"
        f"আমাদের **Nagad (Personal)** নম্বর: `{NAGAD_NUMBER}`\n\n"
        f"উপরে দেওয়া নম্বরে {price} টাকা Send Money করার পর নিচে **TrxID** টি টেক্সট করে পাঠান:"
    )
    
    await callback.message.edit_text(msg, parse_mode="Markdown")
    await state.set_state(PurchaseStates.awaiting_trxid)

@dp.message(PurchaseStates.awaiting_trxid)
async def process_trxid(message: types.Message, state: FSMContext):
    trxid = message.text.strip()
    data = await state.get_data()
    product = data["product"]
    
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM transactions WHERE trxid = ?", (trxid,))
    if cursor.fetchone():
        conn.close()
        await message.answer("❌ এই TrxID টি আগে ব্যবহার করা হয়েছে!")
        return
        
    cursor.execute("SELECT id, key_code FROM keys WHERE product = ? AND duration = ? AND is_used = 0 LIMIT 1", (product, data["days"]))
    key_row = cursor.fetchone()
    
    if not key_row:
        conn.close()
        await message.answer("⚠️ দুখেত, এই প্যাকেজের পর্যাপ্ত কি (Key) স্টক নেই। এডমিনের সাথে যোগাযোগ করুন।")
        return
        
    key_id, key_code = key_row
    cursor.execute("UPDATE keys SET is_used = 1 WHERE id = ?", (key_id,))
    cursor.execute("INSERT INTO transactions (trxid, user_id) VALUES (?, ?)", (trxid, message.from_user.id))
    conn.commit()
    conn.close()
    
    await message.answer(f"✅ পেমেন্ট সফল হয়েছে!\n\nআপনার কি (Key):\n`{key_code}`", parse_mode="Markdown")
    
    # Notify Admin
    admin_msg = (
        f"🔔 **New Purchase Alert!**\n\n"
        f"User: @{message.from_user.username or message.from_user.id}\n"
        f"Product: {product.upper()}\n"
        f"Duration: {data['days']} Day(s)\n"
        f"Amount: {data['price']} BDT\n"
        f"TrxID: `{trxid}`"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
    await state.clear()

# --- Main Runner ---
async def main():
    # Render Keep-Alive Port Bind
    await start_server()
    
    # Bot Start Polling
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
