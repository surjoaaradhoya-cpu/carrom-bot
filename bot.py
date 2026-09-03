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

# Product Prices Setup (in BDT)
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
    # ইউজার টেবিল (যারা বট স্টার্ট করবে)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    # অর্ডারের টেবিল
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            duration TEXT NOT NULL,
            trxid TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING'
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

class AdminStates(StatesGroup):
    awaiting_key_input = State()

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Buy Kos Engine"), KeyboardButton(text="🎯 Buy Aim Ai")],
            [KeyboardButton(text="📞 Support / Admin")]
        ],
        resize_keyboard=True
    )

async def clear_previous_messages(message: types.Message, state: FSMContext):
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    data = await state.get_data()
    if "last_msg_id" in data:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=data["last_msg_id"])
        except TelegramBadRequest:
            pass

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    # ইউজার স্টার্ট করলেই ডাটাবেজে সেভ করে রাখবে
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
    conn.commit()
    conn.close()

    await clear_previous_messages(message, state)
    await state.clear()
    sent_msg = await message.answer("স্বাগতম! আপনার প্রয়োজনীয় সার্ভিস টি সিলেক্ট করুন:", reply_markup=main_keyboard())
    await state.update_data(last_msg_id=sent_msg.message_id)

@dp.message(F.text == "📞 Support / Admin")
async def support_cmd(message: types.Message, state: FSMContext):
    await clear_previous_messages(message, state)
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="nav_main")]
    ])
    
    sent_msg = await message.answer(
        f"যেকোনো প্রয়োজনে যোগাযোগ করুন: {ADMIN_USERNAME}",
        reply_markup=markup
    )
    await state.update_data(last_msg_id=sent_msg.message_id)

@dp.message(F.text.in_(["🟢 Buy Kos Engine", "🎯 Buy Aim Ai"]))
async def select_product(message: types.Message, state: FSMContext):
    await clear_previous_messages(message, state)

    product_key = "kos_engine" if "Kos Engine" in message.text else "aim_ai"
    product_data = PRODUCTS[product_key]
    
    await state.update_data(product=product_key)
    
    buttons = []
    for duration, price in product_data["prices"].items():
        buttons.append([InlineKeyboardButton(text=f"{duration} Day(s) - {price} BDT", callback_data=f"dur_{duration}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="nav_main")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    sent_msg = await message.answer(f"**{product_data['name']}** এর মেয়াদ নির্বাচন করুন:", reply_markup=markup, parse_mode="Markdown")
    
    await state.update_data(last_msg_id=sent_msg.message_id)
    await state.set_state(PurchaseStates.selecting_duration)

@dp.callback_query(F.data == "nav_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    sent_msg = await callback.message.answer("স্বাগতম! আপনার প্রয়োজনীয় সার্ভিস টি সিলেক্ট করুন:", reply_markup=main_keyboard())
    await state.update_data(last_msg_id=sent_msg.message_id)

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
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="nav_back_duration")]
    ])
    
    await callback.message.edit_text(msg, reply_markup=markup, parse_mode="Markdown")
    await state.set_state(PurchaseStates.awaiting_trxid)

@dp.callback_query(PurchaseStates.awaiting_trxid, F.data == "nav_back_duration")
async def back_to_duration(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    product_key = data.get("product", "kos_engine")
    product_data = PRODUCTS[product_key]
    
    buttons = []
    for duration, price in product_data["prices"].items():
        buttons.append([InlineKeyboardButton(text=f"{duration} Day(s) - {price} BDT", callback_data=f"dur_{duration}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="nav_main")])
        
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"**{product_data['name']}** এর মেয়াদ নির্বাচন করুন:", reply_markup=markup, parse_mode="Markdown")
    await state.set_state(PurchaseStates.selecting_duration)

@dp.message(PurchaseStates.awaiting_trxid)
async def process_trxid(message: types.Message, state: FSMContext):
    trxid = message.text.strip()
    data = await state.get_data()
    product = data["product"]
    days = data["days"]
    price = data["price"]
    
    await clear_previous_messages(message, state)
    
    # Save order to DB
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pending_orders (user_id, product, duration, trxid) VALUES (?, ?, ?, ?)",
        (message.from_user.id, product, days, trxid)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Inform customer
    wait_msg = (
        f"⏳ **পেমেন্ট ভেরিফিকেশন চলছে...**\n\n"
        f"আপনার TrxID: `{trxid}` গ্রহণ করা হয়েছে।\n"
        f"এডমিন আপনার পেমেন্ট ভেরিফাই করে কিছুক্ষণের মধ্যেই **Key** পাঠিয়ে দিচ্ছে। অনুগ্রহ করে একটু অপেক্ষা করুন।"
    )
    sent_msg = await message.answer(wait_msg, parse_mode="Markdown")
    await state.update_data(last_msg_id=sent_msg.message_id)
    await state.clear()
    
    # Notify Admin with Action Button
    admin_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔑 Send Key Now", callback_data=f"sendkey_{order_id}")]
    ])
    admin_msg = (
        f"🔔 **New Order Received!**\n\n"
        f"Order ID: #{order_id}\n"
        f"User: @{message.from_user.username or message.from_user.id} (ID: `{message.from_user.id}`)\n"
        f"Product: {PRODUCTS[product]['name']}\n"
        f"Duration: {days} Day(s)\n"
        f"Amount: {price} BDT\n"
        f"TrxID: `{trxid}`\n\n"
        f"ক্লিক করে কাস্টমারকে Key পাঠান 👇"
    )
    await bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=admin_markup, parse_mode="Markdown")

# --- Admin Key Delivery Logic ---
@dp.callback_query(F.data.startswith("sendkey_"))
async def admin_prompt_key(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
        
    order_id = callback.data.split("_")[1]
    await state.update_data(delivering_order_id=order_id)
    await state.set_state(AdminStates.awaiting_key_input)
    
    await callback.message.reply(f"🔑 Order #{order_id} এর জন্য **Key** টি টেক্সট করে পাঠান:")

@dp.message(AdminStates.awaiting_key_input)
async def admin_process_key(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
        
    key_code = message.text.strip()
    data = await state.get_data()
    order_id = data.get("delivering_order_id")
    
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, product, duration FROM pending_orders WHERE id = ?", (order_id,))
    order = cursor.fetchone()
    
    if order:
        user_id, product, duration = order
        cursor.execute("UPDATE pending_orders SET status = 'COMPLETED' WHERE id = ?", (order_id,))
        conn.commit()
        conn.close()
        
        # Deliver Key to Customer via Bot
        customer_delivery_msg = (
            f"✅ **আপনার পেমেন্ট সফলভাবে ভেরিফাই করা হয়েছে!**\n\n"
            f"পণ্য: {PRODUCTS[product]['name']} ({duration} Days)\n\n"
            f"আপনার অ্যাক্টিভেশন কি (Key):\n`{key_code}`\n\n"
            f"ধন্যবাদ আমাদের সাথে থাকার জন্য! 😇"
        )
        try:
            await bot.send_message(chat_id=user_id, text=customer_delivery_msg, parse_mode="Markdown")
            await message.reply(f"✅ Order #{order_id} এর কাস্টমারকে সফলভাবে Key ডেলিভারি করা হয়েছে!")
        except Exception as e:
            await message.reply(f"❌ কাস্টমারকে মেসেজ পাঠাতে সমস্যা হয়েছে: {e}")
    else:
        conn.close()
        await message.reply("❌ অর্ডারটি পাওয়া যায়নি।")
        
    await state.clear()

# --- Broadcast Feature for Admin (Updated to use 'users' table) ---
@dp.message(Command("broadcast"))
async def broadcast_msg(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
        
    text_to_send = message.text.replace("/broadcast", "").strip()
    if not text_to_send:
        await message.reply("⚠️ মেসেজ লিখুন! উদাহরণ:\n`/broadcast আজ রাতে বিশেষ ছাড় চলছে!`", parse_mode="Markdown")
        return

    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()

    count = 0
    for user in users:
        try:
            await bot.send_message(chat_id=user[0], text=text_to_send, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.reply(f"📢 মোট {count} জন ইউজারের কাছে নোটিশ পাঠানো হয়েছে!")

# --- Main Runner ---
async def main():
    await start_server()
    logging.basicConfig(level=logging.INFO)
    logging.info("Starting Telegram Bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
