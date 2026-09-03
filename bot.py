import asyncio
import logging
import sqlite3
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

# Configuration (Updated New Bot Token)
BOT_TOKEN = "8998611945:AAEr55Zq_4jyrOzmc4k2yw6PAM28Iin0md8"
ADMIN_ID = 8122859840
ADMIN_USERNAME = "@SHURJO_0"
NAGAD_NUMBER = "01672630670"

# Product Prices Setup (in BDT)
PRICES = {
    "kos": {"1": 100, "7": 500, "15": 900, "30": 1500},
    "aim": {"1": 80, "7": 400, "15": 750, "30": 1200},
}

# Key Stock Setup
KEY_STOCK = {
    "kos": "CARROM-AUTO-KEY-8823-PRO",
    "aim": "AIM-KEY-1102-M33B-LITE",
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_active_menu = {}


class BotStates(StatesGroup):
    waiting_for_trxid = State()


def init_db():
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            plan TEXT DEFAULT 'Bronze'
        )
    """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            duration TEXT,
            price REAL,
            license_key TEXT,
            status TEXT DEFAULT 'Completed'
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


def get_user_balance(user_id):
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?", (int(user_id),)
    )
    res = cursor.fetchone()
    if not res:
        cursor.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, 0)", (int(user_id),)
        )
        conn.commit()
        balance = 0.0
    else:
        balance = res[0]
    conn.close()
    return float(balance)


def update_user_balance(user_id, amount):
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    get_user_balance(user_id)
    cursor.execute(
        "UPDATE users SET balance = balance + ? WHERE user_id = ?",
        (float(amount), int(user_id)),
    )
    conn.commit()
    conn.close()


def record_order(user_id, item_name, duration, price, key):
    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, item_name, duration, price, license_key) VALUES (?, ?, ?, ?, ?)",
        (int(user_id), item_name, duration, float(price), key),
    )
    conn.commit()
    conn.close()


def get_main_inline_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Buy 1 Day", callback_data="buy_1"
                ),
                InlineKeyboardButton(
                    text="🛒 Buy 7 Days", callback_data="buy_7"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Buy 15 Days", callback_data="buy_15"
                ),
                InlineKeyboardButton(
                    text="🛒 Buy 30 Days", callback_data="buy_30"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="➕ Add Funds", callback_data="add_funds"
                ),
                InlineKeyboardButton(
                    text="💰 Balance", callback_data="my_balance"
                ),
            ],
            [
                InlineKeyboardButton(text="📦 Stock", callback_data="stock"),
                InlineKeyboardButton(
                    text="📜 My Purchases", callback_data="my_purchases"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🤖 AI Support", callback_data="ai_support"
                ),
                InlineKeyboardButton(
                    text="👤 Admin Support", callback_data="admin_support"
                ),
            ],
        ]
    )


def get_back_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 Back to Main Menu", callback_data="main_menu"
                )
            ]
        ]
    )


async def update_user_menu(
    chat_id: int, user_id: int, text: str, reply_markup=None, parse_mode="HTML"
):
    msg_id = user_active_menu.get(user_id)
    if msg_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=msg_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                disable_web_page_preview=False,
            )
            return
        except TelegramBadRequest:
            pass

    sent_msg = await bot.send_message(
        chat_id,
        text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=False,
    )
    user_active_menu[user_id] = sent_msg.message_id


@dp.message(Command("start"))
@dp.message(F.text == "⚡ Main Menu")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    get_user_balance(user_id)

    try:
        await message.delete()
    except Exception:
        pass

    text = (
        f"👋 <b>Welcome to Carrom Auto Play Purchase Bot!</b>\n\n"
        f"👤 <b>Your User ID:</b> <code>{user_id}</code>\n"
        f"🏅 <b>Plan:</b> Bronze\n\n"
        f"⚡ Select an option below to buy keys or manage funds:"
    )

    await update_user_menu(
        message.chat.id, user_id, text, get_main_inline_keyboard()
    )


@dp.callback_query(F.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user_id = callback.from_user.id
    text = (
        f"👋 <b>Welcome to Carrom Auto Play Purchase Bot!</b>\n\n"
        f"👤 <b>Your User ID:</b> <code>{user_id}</code>\n"
        f"🏅 <b>Plan:</b> Bronze\n\n"
        f"⚡ Select an option below to buy keys or manage funds:"
    )
    await update_user_menu(
        callback.message.chat.id, user_id, text, get_main_inline_keyboard()
    )


@dp.callback_query(F.data == "my_balance")
async def process_balance(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    bal = get_user_balance(user_id)
    text = (
        f"💼 <b>MY WALLET</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Balance:</b> ৳{bal:.2f}\n"
        f"🏅 <b>Plan:</b> Bronze\n\n"
        f"🚀 Top up via Add Funds to buy keys instantly!"
    )
    await update_user_menu(
        callback.message.chat.id, user_id, text, get_back_keyboard()
    )


@dp.callback_query(F.data == "admin_support")
async def admin_supp(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    admin_clean_username = ADMIN_USERNAME.replace("@", "")

    text = (
        f"🎧 <b>ADMIN SUPPORT</b>\n\n"
        f"Need human assistance or want manual top up?\n"
        f"👤 <b>Admin Username:</b> {ADMIN_USERNAME}\n"
        f"🆔 <b>Your User ID:</b> <code>{user_id}</code>\n\n"
        f"👉 <a href='https://t.me/{admin_clean_username}'>Click Here to Message Admin</a>"
    )
    await update_user_menu(
        callback.message.chat.id, user_id, text, get_back_keyboard()
    )


@dp.callback_query(F.data.startswith("buy_"))
async def process_buy_duration(callback: types.CallbackQuery):
    await callback.answer()
    days = callback.data.split("_")[1]

    kos_price = PRICES["kos"].get(days, 0)
    aim_price = PRICES["aim"].get(days, 0)

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🎯 Carrom Auto Play - ৳{kos_price}",
                    callback_data=f"confirm_kos_{days}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🎯 Aim Line AI - ৳{aim_price}",
                    callback_data=f"confirm_aim_{days}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Back to Main Menu", callback_data="main_menu"
                )
            ],
        ]
    )
    await update_user_menu(
        callback.message.chat.id,
        callback.from_user.id,
        f"🎯 <b>Select Hack/Tool for {days} Day(s):</b>",
        kb,
    )


@dp.callback_query(F.data.startswith("confirm_"))
async def process_purchase_confirm(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    item_code = parts[1]
    days = parts[2]

    user_id = callback.from_user.id
    bal = get_user_balance(user_id)
    price = PRICES[item_code][days]
    item_name = "Carrom Auto Play" if item_code == "kos" else "Aim Line AI"

    if bal < price:
        text = (
            f"❌ <b>INSUFFICIENT BALANCE!</b>\n\n"
            f"🛍️ <b>Item:</b> {item_name} ({days} Day)\n"
            f"💵 <b>Price:</b> ৳{price}\n"
            f"💰 <b>Your Current Balance:</b> ৳{bal:.2f}\n\n"
            f"⚠️ Please add funds to your account to buy this key."
        )
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ Add Funds", callback_data="add_funds"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 Back to Main Menu", callback_data="main_menu"
                    )
                ],
            ]
        )
        await update_user_menu(callback.message.chat.id, user_id, text, kb)
        return

    update_user_balance(user_id, -price)
    license_key = KEY_STOCK[item_code]
    record_order(user_id, item_name, f"{days} Day(s)", price, license_key)

    text = (
        f"🎉 <b>PURCHASE SUCCESSFUL!</b>\n\n"
        f"📦 <b>Product:</b> {item_name}\n"
        f"⏱️ <b>Duration:</b> {days} Day(s)\n"
        f"💵 <b>Paid:</b> ৳{price}\n"
        f"🔑 <b>Your Key:</b> <code>{license_key}</code>\n\n"
        f"Thank you for using Carrom Auto Play Bot!"
    )
    await update_user_menu(
        callback.message.chat.id, user_id, text, get_back_keyboard()
    )


@dp.callback_query(F.data == "stock")
async def process_stock(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "📦 <b>AVAILABLE STOCK</b>\n\n"
        "🎯 <b>Carrom Auto Play:</b> Available ✅\n"
        "🎯 <b>Aim Line AI:</b> Available ✅\n\n"
        "⚡ Select any Buy option to order!"
    )
    await update_user_menu(
        callback.message.chat.id,
        callback.from_user.id,
        text,
        get_back_keyboard(),
    )


@dp.callback_query(F.data == "my_purchases")
async def process_purchases(callback: types.CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id

    conn = sqlite3.connect("shop_database.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT item_name, duration, price, license_key FROM orders WHERE user_id = ?",
        (int(user_id),),
    )
    orders = cursor.fetchall()
    conn.close()

    if not orders:
        text = "📜 <b>MY PURCHASES</b>\n\nYou have no purchase history yet."
    else:
        text = "📜 <b>MY PURCHASES</b>\n\n"
        for idx, item in enumerate(orders, 1):
            text += f"{idx}. <b>{item[0]}</b> ({item[1]}) - ৳{item[2]}\n🔑 Key: <code>{item[3]}</code>\n\n"

    await update_user_menu(
        callback.message.chat.id, user_id, text, get_back_keyboard()
    )


@dp.callback_query(F.data == "add_funds")
async def add_funds_cmd(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(BotStates.waiting_for_trxid)
    text = (
        "💳 <b>ADD FUNDS (Nagad Personal Only)</b>\n\n"
        f"1️⃣ Send money to Nagad Personal: <code>{NAGAD_NUMBER}</code>\n"
        "2️⃣ Minimum Deposit: ৳100\n"
        "3️⃣ Enter your <b>Transaction ID (TrxID)</b> in the chat below:"
    )
    await update_user_menu(
        callback.message.chat.id,
        callback.from_user.id,
        text,
        get_back_keyboard(),
    )


@dp.message(BotStates.waiting_for_trxid)
async def process_trx(message: types.Message, state: FSMContext):
    trx_id = message.text
    user_id = message.from_user.id
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

    admin_msg = (
        f"🔔 <b>NEW TOP-UP REQUEST!</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🧾 <b>TrxID:</b> <code>{trx_id}</code>\n\n"
        f"To approve balance, click to copy below command:\n"
        f"<code>/addbalance {user_id} 100</code>"
    )
    await bot.send_message(ADMIN_ID, admin_msg, parse_mode="HTML")

    text = "✅ Your TrxID has been sent to Admin for verification!"
    await update_user_menu(
        message.chat.id, user_id, text, get_back_keyboard()
    )


@dp.callback_query(F.data == "ai_support")
async def ai_supp(callback: types.CallbackQuery):
    await callback.answer()
    text = (
        "🤖 <b>AI ASSISTANT</b>\n\n"
        "AI Support is currently under maintenance.\n"
        "Please click 'Admin Support' to chat with Admin!"
    )
    await update_user_menu(
        callback.message.chat.id,
        callback.from_user.id,
        text,
        get_back_keyboard(),
    )


@dp.message(Command("addbalance"))
async def admin_add_balance(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "⚠️ Usage: <code>/addbalance USER_ID AMOUNT</code>", parse_mode="HTML"
        )
        return

    try:
        target_id = int(args[1])
        amount = float(args[2])

        update_user_balance(target_id, amount)
        new_bal = get_user_balance(target_id)

        await message.answer(
            f"✅ Added ৳{amount} to User <code>{target_id}</code>.\n💰 New Balance: ৳{new_bal:.2f}",
            parse_mode="HTML",
        )
        try:
            await bot.send_message(
                target_id,
                f"🎉 <b>Deposit Approved!</b>\n💰 ৳{amount} has been added to your wallet.",
                parse_mode="HTML",
            )
        except Exception:
            pass
    except ValueError:
        await message.answer("⚠️ Invalid User ID or Amount!")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())