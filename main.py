#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v4.0 (Instant Registration & Premium UI)
───────────────────────────────────────────────────────────────────────────
"""

import logging
import os
import json
import sqlite3
import secrets
import shutil
from datetime import datetime
from contextlib import contextmanager
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ──────────────────────────────────────────────────────────────────────────
# 🎛️ CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    
    # Payment merchant numbers
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    
    MIN_DEPOSIT = 50.0  # সর্বনিম্ন ডিপোজিট
    
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    
    # Admin System (Primary Admin ID)
    ADMIN_USER_ID = 5904838487  # আপনার রিয়েল টেলিগ্রাম আইডি

# ──────────────────────────────────────────────────────────────────────────
# 📝 LOGGING
# ──────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkyTopUp")

# ──────────────────────────────────────────────────────────────────────────
# 🗄️ DATABASE LAYER
# ──────────────────────────────────────────────────────────────────────────

@contextmanager
def db():
    conn = sqlite3.connect(Config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    db_dir = os.path.dirname(Config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    with db() as conn:
        c = conn.cursor()
        
        # Users table (Kept email/password for backwards compatibility with your old DB)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                email TEXT,
                password TEXT,
                name TEXT DEFAULT 'User',
                balance REAL DEFAULT 0.0,
                reward_points INTEGER DEFAULT 0,
                rank TEXT DEFAULT '🥈 Silver Member',
                is_admin INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Orders
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                telegram_id TEXT NOT NULL,
                product_name TEXT NOT NULL,
                package TEXT NOT NULL,
                price REAL NOT NULL,
                user_details TEXT,
                status TEXT DEFAULT '⏳ Pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        
        # Products
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                icon TEXT DEFAULT '📦',
                description TEXT,
                options TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add Money Requests Table
        c.execute("""
            CREATE TABLE IF NOT EXISTS deposit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                telegram_id TEXT NOT NULL,
                method TEXT NOT NULL,
                amount REAL NOT NULL,
                trx_id TEXT NOT NULL,
                status TEXT DEFAULT '⏳ Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Settings Table for Maintenance Mode
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")
        
        # Seed default products
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
                ("Free Fire Diamonds", "game", "💎", "ফ্রি ফায়ার ডায়মন্ড টপ-আপ (UID)",
                 json.dumps([
                     {"amount": "💎 ১০০ ডায়মন্ড", "price": 100},
                     {"amount": "💎 ৩১০ ডায়মন্ড", "price": 300},
                     {"amount": "💎 ৫২০ ডায়মন্ড", "price": 500},
                 ])),
                ("Netflix Premium", "subscribe", "🎬", "নেটফ্লিক্স প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎬 ১ মাস স্ক্রিন", "price": 200},
                     {"amount": "🎬 ৩ মাস প্রিমিয়াম", "price": 500},
                 ]))
            ]
            c.executemany(
                "INSERT INTO products (name, category, icon, description, options) VALUES (?, ?, ?, ?, ?)",
                default_products,
            )
    
    logger.info("📦 Database initialized.")


def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)).fetchone()

def is_maintenance() -> bool:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()
        return row and row["value"] == "ON"

def is_admin(user_row) -> bool:
    if not user_row:
        return False
    return int(user_row["telegram_id"]) == Config.ADMIN_USER_ID or user_row["is_admin"] == 1


# ──────────────────────────────────────────────────────────────────────────
# 🎨 PREMIUM UI BUILDER
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("🛒 শপ (Shop)", callback_data="shop"),
                InlineKeyboardButton("➕ অ্যাড মানি", callback_data="recharge")
            ],
            [
                InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile"),
                InlineKeyboardButton("📦 আমার অর্ডার", callback_data="orders")
            ],
            [
                InlineKeyboardButton("💬 লাইভ সাপোর্ট", callback_data="help")
            ]
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("👑 অ্যাডমিন ড্যাশবোর্ড 👑", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data=callback_data)]])


async def smart_reply(update: Update, text: str, reply_markup=None):
    kwargs = {"text": text, "parse_mode": ParseMode.HTML, "reply_markup": reply_markup}
    if update.callback_query:
        await update.callback_query.message.reply_text(**kwargs)
    elif update.message:
        await update.message.reply_text(**kwargs)

async def edit_or_reply(update: Update, text: str, reply_markup=None):
    kwargs = {"text": text, "parse_mode": ParseMode.HTML, "reply_markup": reply_markup}
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(**kwargs)
            return
        except Exception:
            pass
    await smart_reply(update, text, reply_markup)


# ──────────────────────────────────────────────────────────────────────────
# 🚀 INSTANT START & REGISTRATION
# ──────────────────────────────────────────────────────────────────────────

ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_RESTORE_DB_STATE = 40


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    
    user_row = get_user(telegram_id)
    
    # Check Maintenance
    if is_maintenance() and not (user_row and is_admin(user_row)):
        await update.message.reply_text(
            "⚠️ <b>সিস্টেম আপডেটের কাজ চলছে!</b>\n\n"
            "খুব শীঘ্রই বটটি আবার সচল হবে। সাময়িক অসুবিধার জন্য আমরা আন্তরিকভাবে দুঃখিত।",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    welcome_prefix = ""
    
    # Instant Background Registration
    if not user_row:
        name = user.first_name or "গ্রাহক"
        dummy_email = f"{telegram_id}@skytopup.user"
        with db() as conn:
            conn.execute(
                "INSERT INTO users (telegram_id, email, password, name, balance) VALUES (?, ?, 'NO_PASS', ?, 10.0)",
                (telegram_id, dummy_email, name)
            )
        user_row = get_user(telegram_id)
        welcome_prefix = (
            f"🎉 <b>অভিনন্দন! আপনার অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে।</b>\n"
            f"🎁 <i>স্বাগতম বোনাস হিসেবে আপনি পেয়েছেন ৳10.00</i>\n\n"
        )
    else:
        with db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))

    welcome = (
        f"{welcome_prefix}"
        f"🌟 <b>SKY TOPUP — PREMIUM SERVICE</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 স্বাগতম, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
        f"🔹 <b>কারেন্ট ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
        f"🔹 <b>অ্যাকাউন্ট র‍্যাংক:</b> {user_row['rank']}\n"
        f"🔹 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']} pts\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <i>যেকোনো সার্ভিস অর্ডার করতে নিচের মেন্যু ব্যবহার করুন:</i>"
    )
    
    # Clean previous context if any
    context.user_data.clear()
    
    await edit_or_reply(update, welcome, UIBuilder.main_menu(user_row))
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ <b>চলমান প্রক্রিয়া বাতিল করা হয়েছে।</b>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOPPING & PRODUCTS
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🍿 ওটিটি ও সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")],
    ]
    await edit_or_reply(update, "📂 <b>প্রোডাক্ট ক্যাটাগরি</b>\n━━━━━━━━━━━━━━━━━━━━\n\nআপনার পছন্দের ক্যাটাগরি বেছে নিন:", InlineKeyboardMarkup(keyboard))


async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
    
    if not products:
        await edit_or_reply(update, "⚠️ <i>বর্তমানে এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই।</i>", UIBuilder.back_button("shop"))
        return
    
    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("🔙 পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(update, "🛍️ <b>প্রোডাক্ট লিস্ট</b>\n━━━━━━━━━━━━━━━━━━━━\n\nনিচ থেকে প্রোডাক্ট সিলেক্ট করুন:", InlineKeyboardMarkup(keyboard))


async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        await edit_or_reply(update, "❌ প্রোডাক্ট পাওয়া যায়নি!", UIBuilder.back_button("shop"))
        return
    
    options = json.loads(product["options"])
    keyboard = [
        [InlineKeyboardButton(f"{opt['amount']} ➔ ৳{opt['price']}", callback_data=f"package_{product_id}_{idx}")]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("🔙 পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>বিবরণ:</b> {product['description']}\n\n"
        f"👇 <i>আপনার কাঙ্ক্ষিত প্যাকেজটি নির্বাচন করুন:</i>",
        InlineKeyboardMarkup(keyboard)
    )


# ──────────────────────────────────────────────────────────────────────────
# 📋 ORDER FLOW
# ──────────────────────────────────────────────────────────────────────────

async def package_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    product_id, package_idx = int(parts[1]), int(parts[2])
    
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    options = json.loads(product["options"])
    selected_package = options[package_idx]
    user_row = get_user(str(update.effective_user.id))
    
    price = selected_package["price"]
    if user_row["balance"] < price:
        await query.message.reply_text(
            f"❌ <b>অর্ডার ব্যর্থ!</b>\n\n"
            f"আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই।\n"
            f"🔹 <b>বর্তমান ব্যালেন্স:</b> ৳{user_row['balance']:.2f}\n"
            f"🔹 <b>প্রয়োজনীয় ব্যালেন্স:</b> ৳{price:.2f}\n\n"
            f"<i>অনুগ্রহ করে আগে অ্যাকাউন্টে টাকা অ্যাড করুন।</i>"
        )
        return ConversationHandler.END
    
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    
    await query.message.reply_text(
        f"🛒 <b>চেকআউট নিশ্চিতকরণ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>প্রোডাক্ট:</b> {product['name']}\n"
        f"📎 <b>প্যাকেজ:</b> {selected_package['amount']}\n"
        f"💰 <b>মূল্য:</b> ৳{price}\n\n"
        f"👉 <i>টপ-আপ ডেলিভারির জন্য আপনার <b>ID / UID / Details</b> লিখে সেন্ড করুন (কমপক্ষে ৩ অক্ষর):</i>"
    )
    return ORDER_DETAILS_STATE


async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_details = update.message.text.strip()
    if len(user_details) < 3:
        await update.message.reply_text("❌ ভুল আইডি! পুনরায় সঠিক ও সম্পূর্ণ আইডি দিন:")
        return ORDER_DETAILS_STATE
    
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    telegram_id = str(update.effective_user.id)
    
    order_id = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"
    
    with db() as conn:
        conn.execute(
            "INSERT INTO orders (order_id, telegram_id, product_name, package, price, user_details) VALUES (?, ?, ?, ?, ?, ?)",
            (order_id, telegram_id, product_name, package["amount"], price, user_details)
        )
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, telegram_id))
    
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ <b>আপনার অর্ডারটি সফলভাবে গ্রহণ করা হয়েছে!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>অর্ডার আইডি:</b> <code>{order_id}</code>\n"
        f"💰 <b>কর্তনকৃত ব্যালেন্স:</b> ৳{price}\n\n"
        f"⚡ <i>আমাদের টিম ৫-১৫ মিনিটের মধ্যে আপনার অর্ডারটি সম্পন্ন করে দিবে।</i>"
    )
    
    # Notify Admin
    try:
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>New Order Received!</b>\n\n"
                 f"👤 <b>User:</b> <code>{telegram_id}</code>\n"
                 f"🆔 <b>Order ID:</b> <code>{order_id}</code>\n"
                 f"📦 <b>Product:</b> {product_name}\n"
                 f"📎 <b>Package:</b> {package['amount']}\n"
                 f"ℹ️ <b>Details:</b> <code>{user_details}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")
        
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# ➕ AUTOMATED ADD MONEY SYSTEM
# ──────────────────────────────────────────────────────────────────────────

async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📱 বিকাশ (bKash)", callback_data="recharge_bkash"),
            InlineKeyboardButton("📱 নগদ (Nagad)", callback_data="recharge_nagad")
        ],
        [
            InlineKeyboardButton("📱 রকেট (Rocket)", callback_data="recharge_rocket")
        ],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")]
    ]
    await edit_or_reply(
        update,
        f"💳 <b>অ্যাড মানি / ব্যালেন্স রিচার্জ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ <b>সতর্কতা:</b> আমাদের বটে সর্বনিম্ন রিচার্জ লিমিট <b>৳{Config.MIN_DEPOSIT:.2f}</b> টাকা।\n\n"
        f"<i>নিচে থেকে আপনি কোন মাধ্যমে টাকা পাঠাতে চান তা সিলেক্ট করুন:</i> 👇",
        InlineKeyboardMarkup(keyboard)
    )


async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {
        "bkash": Config.BKASH_NUMBER,
        "nagad": Config.NAGAD_NUMBER,
        "rocket": Config.ROCKET_NUMBER
    }
    number = numbers.get(method, "N/A")
    context.user_data["recharge_method"] = method
    
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()} পেমেন্ট পদ্ধতি</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👉 আমাদের {method.title()} পার্সোনাল নম্বর:\n"
        f"📞 <code>{number}</code> (ক্লিক করলেই কপি হবে)\n\n"
        f"📌 <b>কীভাবে ব্যালেন্স অ্যাড করবেন?</b>\n"
        f"১. প্রথমে উপরের নম্বরে <b>Send Money</b> করুন।\n"
        f"২. সর্বনিম্ন ৳{Config.MIN_DEPOSIT} টাকা পাঠাতে হবে।\n"
        f"৩. টাকা পাঠানোর পর ট্রানজেকশন আইডি (TrxID) টি কপি করে রাখুন।\n\n"
        f"💵 <b>আপনি কত টাকা পাঠিয়েছেন? (শুধুমাত্র টাকার অংকটি ইংরেজিতে লিখে সেন্ড করুন):</b>"
    )
    return ADD_MONEY_AMOUNT


async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ভুল ইনপুট! শুধু সংখ্যা দিন (যেমন: 100):")
        return ADD_MONEY_AMOUNT
    
    if amount < Config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ দুঃখিত, সর্বনিম্ন রিচার্জ লিমিট ৳{Config.MIN_DEPOSIT}। আবার সঠিক অ্যামাউন্ট দিন:")
        return ADD_MONEY_AMOUNT
    
    context.user_data["recharge_amount"] = amount
    await update.message.reply_text(
        "🔑 <b>চমৎকার!</b> এবার আপনার পেমেন্টের <b>Transaction ID (TrxID)</b> টি হুবহু কপি করে এখানে পেস্ট করুন:"
    )
    return ADD_MONEY_TRX


async def add_money_trx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_id = update.message.text.strip()
    if len(trx_id) < 5:
        await update.message.reply_text("❌ ভুল TrxID! দয়া করে সঠিক TrxID দিন:")
        return ADD_MONEY_TRX
    
    method = context.user_data.get("recharge_method")
    amount = context.user_data.get("recharge_amount")
    telegram_id = str(update.effective_user.id)
    req_id = f"DEP-{int(datetime.now().timestamp())}"
    
    with db() as conn:
        conn.execute(
            "INSERT INTO deposit_requests (request_id, telegram_id, method, amount, trx_id) VALUES (?, ?, ?, ?, ?)",
            (req_id, telegram_id, method, amount, trx_id)
        )
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"✅ <b>আপনার অ্যাড মানি রিকোয়েস্ট সফলভাবে জমা হয়েছে!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <b>ট্র্যাকিং আইডি:</b> <code>{req_id}</code>\n"
        f"💳 <b>পেমেন্ট মাধ্যম:</b> {method.upper()}\n"
        f"💰 <b>পরিমাণ:</b> ৳{amount:.2f}\n"
        f"🔑 <b>TrxID:</b> <code>{trx_id}</code>\n\n"
        f"⚡ <i>এডমিন ভেরিফাই করে ২-৫ মিনিটের মধ্যে আপনার অ্যাকাউন্টে ব্যালেন্স যুক্ত করে দেবেন।</i>"
    )
    
    try:
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>New Deposit Request!</b>\n\n"
                 f"👤 <b>User:</b> <code>{telegram_id}</code>\n"
                 f"💳 <b>Method:</b> {method.upper()}\n"
                 f"💰 <b>Amount:</b> ৳{amount:.2f}\n"
                 f"🔑 <b>TrxID:</b> <code>{trx_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        logger.error(f"Deposit notification failure: {e}")
        
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🛠️ ADMIN PANEL (UNCHANGED FUNCTIONALITY, POLISHED UI)
# ──────────────────────────────────────────────────────────────────────────

async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        await edit_or_reply(update, "❌ অ্যাক্সেস ডিনাইড!")
        return
    
    with db() as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = '⏳ Pending'").fetchone()[0]
        pending_deposits = conn.execute("SELECT COUNT(*) FROM deposit_requests WHERE status = '⏳ Pending'").fetchone()[0]
        m_mode = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"]
    
    m_btn_text = "🟢 Maintenance ON" if m_mode == "OFF" else "🔴 Maintenance OFF"
    
    keyboard = [
        [
            InlineKeyboardButton("📊 অর্ডার লিস্ট", callback_data="adm_view_orders"),
            InlineKeyboardButton("💰 অ্যাড-মানি লিস্ট", callback_data="adm_view_deposits")
        ],
        [
            InlineKeyboardButton("👤 ব্যালেন্স এডিট", callback_data="adm_balance_set"),
            InlineKeyboardButton("📦 নতুন প্রোডাক্ট যোগ", callback_data="adm_product_add")
        ],
        [
            InlineKeyboardButton("📤 Backup Database", callback_data="adm_backup_db"),
            InlineKeyboardButton("📥 Restore Database", callback_data="adm_restore_db")
        ],
        [
            InlineKeyboardButton(m_btn_text, callback_data="adm_toggle_maintenance")
        ],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")]
    ]
    
    await edit_or_reply(
        update,
        f"👑 <b>অ্যাডমিন কন্ট্রোল প্যানেল</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>মোট ইউজার:</b> {users_count} জন\n"
        f"⏳ <b>পেন্ডিং অর্ডার:</b> {pending_orders} টি\n"
        f"💵 <b>পেন্ডিং ডিপোজিট:</b> {pending_deposits} টি\n"
        f"⚙️ <b>মেইনটেনেন্স:</b> {m_mode}",
        InlineKeyboardMarkup(keyboard)
    )

# Admin callbacks routing logic remains exactly the same
async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_row = get_user(str(update.effective_user.id))
    
    if not is_admin(user_row):
        await query.answer("❌ আপনি অ্যাডমিন নন।", show_alert=True)
        return
        
    await query.answer()
    
    if data == "adm_toggle_maintenance":
        current = "OFF" if is_maintenance() else "ON"
        with db() as conn:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", (current,))
        await show_admin_panel_ui(update, context)
        
    elif data == "adm_backup_db":
        backup_file = f"backup_{int(datetime.now().timestamp())}.db"
        try:
            src = sqlite3.connect(Config.DB_PATH)
            dst = sqlite3.connect(backup_file)
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
            
            with open(backup_file, "rb") as doc:
                await context.bot.send_document(
                    chat_id=Config.ADMIN_USER_ID,
                    document=doc,
                    filename=os.path.basename(Config.DB_PATH),
                    caption=f"📂 <b>SKY TOPUP DATABASE BACKUP</b>\n\n"
                            f"📅 টাইম: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    parse_mode=ParseMode.HTML
                )
            os.remove(backup_file)
            await query.message.reply_text("✅ ব্যাকআপ ফাইল পাঠানো হয়েছে।")
        except Exception as e:
            logger.error(f"DB Backup failed: {e}")
            await query.message.reply_text(f"❌ ব্যাকআপ এরর: {str(e)}")

    elif data == "adm_restore_db":
        await query.message.reply_text(
            "📥 <b>ডাটাবেজ রিস্টোর সিস্টেম</b>\n\n"
            "আপনার ব্যাকআপ করা ডাটাবেজ ফাইলটি (<code>.db</code>) এখানে আপলোড করুন।\n"
            "⚠️ <i>সতর্কতা: এটি বর্তমান ডাটা মুছে ফেলবে!</i>\n"
            "প্রক্রিয়া বাতিল করতে /cancel টাইপ করুন।"
        )
        return ADMIN_RESTORE_DB_STATE

    elif data == "adm_view_orders":
        with db() as conn:
            orders = conn.execute("SELECT * FROM orders WHERE status = '⏳ Pending' LIMIT 5").fetchall()
        if not orders:
            await query.message.reply_text("🟢 কোনো পেন্ডিং অর্ডার নেই!")
            return
        
        for o in orders:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{o['order_id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{o['order_id']}")
                ]
            ]
            await query.message.reply_text(
                f"🆔 <b>অর্ডার:</b> <code>{o['order_id']}</code>\n"
                f"👤 <b>ইউজার:</b> {o['telegram_id']}\n"
                f"📦 <b>প্রোডাক্ট:</b> {o['product_name']} ({o['package']})\n"
                f"ℹ️ <b>ডিটেইলস:</b> <code>{o['user_details']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    elif data == "adm_view_deposits":
        with db() as conn:
            deposits = conn.execute("SELECT * FROM deposit_requests WHERE status = '⏳ Pending' LIMIT 5").fetchall()
        if not deposits:
            await query.message.reply_text("🟢 কোনো পেন্ডিং ডিপোজিট নেই!")
            return
        
        for d in deposits:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{d['request_id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{d['request_id']}")
                ]
            ]
            await query.message.reply_text(
                f"🆔 <b>রিকোয়েস্ট:</b> <code>{d['request_id']}</code>\n"
                f"👤 <b>ইউজার:</b> {d['telegram_id']}\n"
                f"💳 <b>মাধ্যম:</b> {d['method'].upper()}\n"
                f"💰 <b>পরিমাণ:</b> ৳{d['amount']}\n"
                f"🔑 <b>TrxID:</b> <code>{d['trx_id']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data.startswith("adm_ord_approve_"):
        ord_id = data.replace("adm_ord_approve_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '✅ Completed' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, product_name, package FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
        
        await query.message.edit_text(f"✅ অর্ডার {ord_id} অ্যাপ্রুভ করা হয়েছে!")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"🎉 <b>আপনার অর্ডারটি সফল হয়েছে!</b>\n\n"
                     f"🆔 <b>অর্ডার আইডি:</b> <code>{ord_id}</code>\n"
                     f"📦 <b>প্রোডাক্ট:</b> {order['product_name']} ({order['package']})\n\n"
                     f"<i>আমাদের সাথে থাকার জন্য ধন্যবাদ!</i>"
            )
        except Exception:
            pass

    elif data.startswith("adm_ord_reject_"):
        ord_id = data.replace("adm_ord_reject_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '❌ Rejected' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, price FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (order["price"], order["telegram_id"]))
            
        await query.message.edit_text(f"❌ অর্ডার {ord_id} বাতিল করা হয়েছে (টাকা রিফান্ডেড)!")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"❌ <b>আপনার অর্ডারটি বাতিল করা হয়েছে!</b>\n\n"
                     f"🆔 <b>অর্ডার আইডি:</b> <code>{ord_id}</code>\n"
                     f"💰 আপনার অ্যাকাউন্টে ৳{order['price']} ব্যাক দেওয়া হয়েছে।"
            )
        except Exception:
            pass

    elif data.startswith("adm_dep_approve_"):
        req_id = data.replace("adm_dep_approve_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = '⏳ Pending'", (req_id,)).fetchone()
            if dep:
                conn.execute("UPDATE deposit_requests SET status = '✅ Approved' WHERE request_id = ?", (req_id,))
                conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
                
                await query.message.edit_text(f"✅ ডিপোজিট {req_id} অ্যাপ্রুভ হয়েছে!")
                try:
                    await context.bot.send_message(
                        chat_id=dep["telegram_id"],
                        text=f"🎉 <b>আপনার ওয়ালেট রিচার্জ সফল হয়েছে!</b>\n\n"
                             f"💰 <b>যোগকৃত ব্যালেন্স:</b> ৳{dep['amount']:.2f}\n"
                             f"💳 <b>মেথড:</b> {dep['method'].upper()}\n\n"
                             f"<i>ধন্যবাদ আমাদের সাথে থাকার জন্য!</i>"
                    )
                except Exception:
                    pass

    elif data.startswith("adm_dep_reject_"):
        req_id = data.replace("adm_dep_reject_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ?", (req_id,)).fetchone()
            conn.execute("UPDATE deposit_requests SET status = '❌ Rejected' WHERE request_id = ?", (req_id,))
            
        await query.message.edit_text(f"❌ ডিপোজিট রিকোয়েস্ট {req_id} রিজেক্ট করা হয়েছে!")
        try:
            await context.bot.send_message(
                chat_id=dep["telegram_id"],
                text=f"❌ <b>আপনার ওয়ালেট রিচার্জ বাতিল করা হয়েছে!</b>\n\n"
                     f"<i>কারন: আপনার প্রদত্ত TrxID অথবা টাকার অংকটি সঠিক নয়। প্রয়োজনে সাপোর্টে কথা বলুন।</i>"
            )
        except Exception:
            pass

# ──────────────────────────────────────────────────────────────────────────
# 🛠️ BALANCE SET CONVERSATION
# ──────────────────────────────────────────────────────────────────────────

async def start_balance_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text("👤 যে ইউজারের ব্যালেন্স পরিবর্তন করতে চান তার <b>Telegram ID</b> দিন:")
    return ADMIN_SET_BAL_ID

async def bal_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tgt_id = update.message.text.strip()
    user_row = get_user(tgt_id)
    if not user_row:
        await update.message.reply_text("❌ আইডি পাওয়া যায়নি। পুনরায় আইডি দিন:")
        return ADMIN_SET_BAL_ID
    
    context.user_data["tgt_bal_id"] = tgt_id
    await update.message.reply_text(
        f"👤 ইউজার: {user_row['name']}\n"
        f"💵 বর্তমান ব্যালেন্স: ৳{user_row['balance']:.2f}\n\n"
        f"👉 <b>নতুন ব্যালেন্স কত টাকা বসাতে চান?</b>"
    )
    return ADMIN_SET_BAL_AMT

async def bal_amt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_bal = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:")
        return ADMIN_SET_BAL_AMT
    
    tgt_id = context.user_data.get("tgt_bal_id")
    with db() as conn:
        conn.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (new_bal, tgt_id))
    
    context.user_data.clear()
    await update.message.reply_text(f"✅ ব্যালেন্স আপডেট করে ৳{new_bal:.2f} করা হয়েছে!")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 📥 ADMIN RESTORE DATABASE PROCESS
# ──────────────────────────────────────────────────────────────────────────

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        return ConversationHandler.END
        
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ অকার্যকর ফাইল! .db ফাইল পাঠান:")
        return ADMIN_RESTORE_DB_STATE
        
    status_msg = await update.message.reply_text("⏳ <i>প্রসেস হচ্ছে...</i>", parse_mode=ParseMode.HTML)
    
    try:
        file_obj = await context.bot.get_file(doc.file_id)
        temp_path = "temp_restore.db"
        await file_obj.download_to_drive(temp_path)
        
        try:
            test_conn = sqlite3.connect(temp_path)
            test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            test_conn.close()
        except Exception:
            os.remove(temp_path)
            await status_msg.edit_text("❌ ফাইলটি সঠিক SQLite ডাটাবেজ নয়।")
            return ADMIN_RESTORE_DB_STATE
            
        shutil.copyfile(temp_path, Config.DB_PATH)
        os.remove(temp_path)
        
        await status_msg.edit_text("✅ <b>ডাটাবেজ সফলভাবে রিস্টোর করা হয়েছে!</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status_msg.edit_text(f"❌ ব্যর্থ হয়েছে: {str(e)}")
        
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# ➕ DYNAMIC PRODUCT ADD CONVERSATION
# ──────────────────────────────────────────────────────────────────────────

async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Game", callback_data="cat_sel_game"), InlineKeyboardButton("Subscribe", callback_data="cat_sel_subscribe")]]
    await update.callback_query.message.reply_text("📂 ক্যাটাগরি বেছে নিন:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = "game" if "game" in query.data else "subscribe"
    context.user_data["new_prod_cat"] = category
    await query.message.reply_text("📦 প্রোডাক্টের <b>নাম</b> লিখুন:")
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["new_prod_name"] = name
    await update.message.reply_text("📝 প্রোডাক্টের <b>বিবরণ</b> লিখুন:")
    return ADMIN_ADD_PROD_DESC

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["new_prod_desc"] = desc
    await update.message.reply_text(
        "💎 অপশনগুলো JSON এ দিন। যেমন:\n"
        '<code>[{"amount": "১০০ ডায়মন্ড", "price": 100}, {"amount": "২০০ ডায়মন্ড", "price": 200}]</code>'
    )
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opts_raw = update.message.text.strip()
    try:
        json.loads(opts_raw)
    except ValueError:
        await update.message.reply_text("❌ সঠিক JSON ফরম্যাট দিন:")
        return ADMIN_ADD_PROD_OPTS
    
    category = context.user_data.get("new_prod_cat")
    name = context.user_data.get("new_prod_name")
    desc = context.user_data.get("new_prod_desc")
    
    with db() as conn:
        conn.execute("INSERT INTO products (name, category, description, options) VALUES (?, ?, ?, ?)", (name, category, desc, opts_raw))
    
    context.user_data.clear()
    await update.message.reply_text("✅ প্রোডাক্ট যুক্ত করা হয়েছে!")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 👤 PROFILE & GENERAL VIEWS
# ──────────────────────────────────────────────────────────────────────────

async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"👤 <b>আমার প্রোফাইল</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"🆔 <b>টেলিগ্রাম আইডি:</b> <code>{user_row['telegram_id']}</code>\n"
        f"🏅 <b>র‍্যাংক:</b> {user_row['rank']}\n"
        f"💰 <b>ব্যালেন্স:</b> ৳{user_row['balance']:.2f}\n"
        f"📅 <b>যোগদানের তারিখ:</b> {user_row['created_at'][:10]}\n",
        UIBuilder.back_button("back_main")
    )

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(
        update, 
        "💬 <b>২৪/৭ লাইভ সাপোর্ট</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "যেকোনো সমস্যা বা প্রশ্নের জন্য আমাদের অফিশিয়াল এডমিনের সাথে যোগাযোগ করুন:\n\n"
        "👉 <b>@SkyTopUpSupport</b>", 
        UIBuilder.back_button("back_main")
    )

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute("SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 5", (str(update.effective_user.id),)).fetchall()
    
    if not orders:
        await edit_or_reply(update, "📭 <i>আপনি এখনও কোনো অর্ডার করেননি।</i>", UIBuilder.back_button("back_main"))
        return
    
    lines = ["📦 <b>আপনার শেষ ৫টি অর্ডারের ইতিহাস:</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for o in orders:
        status_icon = "✅" if "Completed" in o['status'] else ("❌" if "Rejected" in o['status'] else "⏳")
        lines.append(f"{status_icon} <b>{o['product_name']}</b>\n   ├ আইডি: <code>{o['order_id']}</code>\n   └ মূল্য: ৳{o['price']} | স্ট্যাটাস: {o['status']}\n")
    await edit_or_reply(update, "\n".join(lines), UIBuilder.back_button("back_main"))


# ──────────────────────────────────────────────────────────────────────────
# 🔄 MAIN CALLBACK ROUTER
# ──────────────────────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    routes = {
        "back_main": cmd_start,
        "shop": show_categories_ui,
        "orders": show_orders_ui,
        "recharge": show_recharge_ui,
        "profile": show_profile_ui,
        "help": show_help_ui,
        "admin_panel": show_admin_panel_ui,
    }
    
    if data in routes:
        await routes[data](update, context)
    elif data.startswith("category_"):
        await show_products_ui(update, context, data.replace("category_", ""))
    elif data.startswith("product_"):
        await select_package_ui(update, context, int(data.replace("product_", "")))


# ──────────────────────────────────────────────────────────────────────────
# 🚀 MAIN RUNNER
# ──────────────────────────────────────────────────────────────────────────

def main():
    init_db()
    
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    # Registration Conversation has been REMOVED. Directly handling /start
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    
    # Order Details Handler
    order_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={
            ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Deposit/Add Money Handler
    deposit_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_recharge_instructions_ui, pattern=r"^recharge_(bkash|nagad|rocket)$")],
        states={
            ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_amount_handler)],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_trx_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Set Balance Handler
    admin_balance_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_balance_set, pattern="^adm_balance_set$")],
        states={
            ADMIN_SET_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_id_received)],
            ADMIN_SET_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_amt_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)]
    )

    # Admin Add Product Handler
    admin_product_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_product_add, pattern="^adm_product_add$")],
        states={
            ADMIN_ADD_PROD_CAT: [CallbackQueryHandler(prod_cat_received, pattern="^cat_sel_")],
            ADMIN_ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_name_received)],
            ADMIN_ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_desc_received)],
            ADMIN_ADD_PROD_OPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_opts_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)]
    )
    
    # Admin DB Restore Handler
    admin_restore_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_callback_router, pattern="^adm_restore_db$")],
        states={
            ADMIN_RESTORE_DB_STATE: [MessageHandler(filters.Document.ALL, db_file_restore_received)]
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)]
    )
    
    app.add_handler(order_handler)
    app.add_handler(deposit_handler)
    app.add_handler(admin_balance_handler)
    app.add_handler(admin_product_handler)
    app.add_handler(admin_restore_handler)
    
    # Unified Query Handlers
    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)"))
    
    logger.info("🌟 Sky TopUp Bot (Instant Reg Engine) started successfully...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
