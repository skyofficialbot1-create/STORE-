#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v3.5 (Optimized OTP & Admin DB Backup/Restore System)
───────────────────────────────────────────────────────────────────────────
"""

import logging
import os
import json
import random
import string
import smtplib
import sqlite3
import hashlib
import re
import secrets
import asyncio
import shutil
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
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
    """Centralized configuration management with hardcoded defaults."""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    
    # SMTP / Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "mehedihasan706261@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "qgpp laff mkgo iktz")
    
    # Payment merchant numbers
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    
    MIN_DEPOSIT = 50.0  # সর্বনিম্ন ডিপোজিট
    
    # OTP & Security
    OTP_VALID_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 6
    
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    
    EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)
    DEV_MODE = not EMAIL_SENDING_ENABLED
    
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
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
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
        
        # OTP codes
        c.execute("""
            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT NOT NULL,
                otp_code TEXT NOT NULL,
                attempt_count INTEGER DEFAULT 0,
                is_used INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
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
        
        # Default Settings
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")
        
        # Seed default products
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
                ("Free Fire Diamonds", "game", "💎", "ফ্রি ফায়ার ডায়মন্ড টপ-আপ",
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

def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def update_balance(telegram_id: str, amount: float) -> None:
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, str(telegram_id)))

def is_maintenance() -> bool:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()
        return row and row["value"] == "ON"

def is_admin(user_row) -> bool:
    if not user_row:
        return False
    return int(user_row["telegram_id"]) == Config.ADMIN_USER_ID or user_row["is_admin"] == 1


# ──────────────────────────────────────────────────────────────────────────
# 🔐 SECURITY & EMAIL HELPERS (OPTIMIZED & ASYNC-READY)
# ──────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = "SKY_TOPUP_2024_v2"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def _sync_send_otp_email(to_email: str, otp: str) -> bool:
    """Synchronous email sender intended to run inside a separate worker thread."""
    if Config.DEV_MODE:
        logger.info("🔧 DEV MODE — OTP for %s: %s", to_email, otp)
        return True
    
    if not Config.EMAIL_SENDING_ENABLED:
        return False
    
    msg = MIMEMultipart("alternative")
    msg["From"] = f"SKY TopUp <{Config.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "🔐 SKY TopUp — OTP Verification Code"
    
    text_body = f"আপনার SKY TopUp OTP কোড: {otp}\n\n⏰ মেয়াদ: {Config.OTP_VALID_MINUTES} মিনিট।"
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    
    try:
        # Added optimized timeout to prevent indefinite blocking
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=8) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error("❌ Failed to send OTP via SMTP: %s", e)
        return False

async def send_otp_email_async(to_email: str, otp: str) -> bool:
    """Non-blocking wrapper that runs the SMTP request in a background thread."""
    return await asyncio.to_thread(_sync_send_otp_email, to_email, otp)


# ──────────────────────────────────────────────────────────────────────────
# 🎨 UI BUILDER
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("🛒 প্রোডাক্ট কিনুন", callback_data="shop"),
                InlineKeyboardButton("💳 ব্যালেন্স চেক", callback_data="balance")
            ],
            [
                InlineKeyboardButton("📦 অর্ডার ট্র্যাক", callback_data="orders"),
                InlineKeyboardButton("➕ ইনস্ট্যান্ট রিচার্জ", callback_data="recharge")
            ],
            [
                InlineKeyboardButton("👤 আমার প্রোফাইল", callback_data="profile"),
                InlineKeyboardButton("⚙️ সেটিংস", callback_data="settings")
            ],
            [
                InlineKeyboardButton("💬 হেল্প ও সাপোর্ট", callback_data="help")
            ],
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("🛠️ অ্যাডমিন প্যানেল 🛠️", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data=callback_data)]])


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
# 👤 REGISTRATION & START FLOW
# ──────────────────────────────────────────────────────────────────────────

REG_EMAIL, REG_OTP, REG_PASSWORD, REG_CONFIRM_PASSWORD = range(4)
ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_RESTORE_DB_STATE = 40  # রিস্টোর ডাটাবেজ স্টেট


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check Maintenance Mode (Except Admins)
    user_row = get_user(str(user.id))
    if is_maintenance() and not (user_row and is_admin(user_row)):
        await update.message.reply_text(
            "⚠️ <b>সিস্টেম রক্ষণাবেক্ষণ (Maintenance Mode) চলছে!</b>\n\n"
            "বটের কাজ দ্রুত সচল করার চেষ্টা চলছে। সাময়িক অসুবিধার জন্য আমরা আন্তরিকভাবে দুঃখিত।",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    if user_row:
        with db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (str(user.id),))
        welcome = (
            f"⚡ <b>SKY TOPUP — PREMIUM BOT</b> ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 স্বাগতম, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
            f"💵 <b>ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
            f"🏅 <b>র‍্যাংক:</b> {user_row['rank']}\n"
            f"🎁 <b>পয়েন্ট:</b> {user_row['reward_points']} pts\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ দ্রুত ও বিশ্বস্ত সার্ভিসের জন্য নিচের মেন্যু ব্যবহার করুন:"
        )
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))
        return ConversationHandler.END
    
    welcome = (
        f"⚡ <b>SKY TOPUP — PREMIUM BOT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"হ্যালো, <b>{UIBuilder.safe_text(user.first_name or 'গ্রাহক')}</b>! 👋\n\n"
        f"আমাদের হাই-স্পিড টপ-আপ সার্ভিস ব্যবহার করতে হলে প্রথমে মাত্র ১ মিনিটে ইমেল ভেরিফিকেশন সম্পন্ন করুন।\n\n"
        f"👉 <b>শুরু করতে আপনার জিমেইল এড্রেসটি এখানে লিখুন:</b>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    return REG_EMAIL


async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    if not is_valid_email(email):
        await update.message.reply_text("❌ <b>ভুল ইমেইল!</b> সঠিক জিমেইল দিন:")
        return REG_EMAIL
    
    if get_user_by_email(email):
        await update.message.reply_text("⚠️ ইমেলটি ইতিমধ্যে ব্যবহৃত হয়েছে। অন্য মেইল দিন:")
        return REG_EMAIL
    
    otp = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=Config.OTP_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    
    with db() as conn:
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (str(update.effective_user.id),))
        conn.execute("INSERT INTO otp_codes (telegram_id, otp_code, expires_at) VALUES (?, ?, ?)",
                     (str(update.effective_user.id), otp, expires_at))
    
    context.user_data["reg_email"] = email
    
    # Send processing status first so that user is not left waiting
    status_msg = await update.message.reply_text("⏳ <i>আপনার মেইলে ওটিপি (OTP) পাঠানো হচ্ছে... অনুগ্রহ করে একটু অপেক্ষা করুন।</i>", parse_mode=ParseMode.HTML)
    
    # Async calling to send SMTP in the background
    success = await send_otp_email_async(email, otp)
    
    if success:
        await status_msg.edit_text(
            f"📬 <b>OTP পাঠানো হয়েছে!</b>\n\n"
            f"আপনার জিমেইলে পাঠানো ৬ ডিজিটের ওটিপিটি নিচে লিখুন:",
            parse_mode=ParseMode.HTML
        )
        return REG_OTP
    else:
        await status_msg.edit_text(
            "❌ <b>ওটিপি পাঠাতে ব্যর্থ হয়েছে!</b>\n"
            "অনুগ্রহ করে ইমেইল এড্রেসটি চেক করুন অথবা এডমিনের সাথে যোগাযোগ করুন। আবার চেষ্টা করুন:",
            parse_mode=ParseMode.HTML
        )
        return REG_EMAIL


async def reg_receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_otp = update.message.text.strip()
    telegram_id = str(update.effective_user.id)
    
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM otp_codes WHERE telegram_id = ? AND is_used = 0 ORDER BY created_at DESC LIMIT 1",
            (telegram_id,)
        ).fetchone()
    
    if not row or entered_otp != row["otp_code"]:
        await update.message.reply_text("❌ <b>ভুল ওটিপি!</b> আবার চেষ্টা করুন:")
        return REG_OTP
    
    with db() as conn:
        conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
    
    await update.message.reply_text("✅ ভেরিফাইড! এবার আপনার অ্যাকাউন্টের জন্য একটি নতুন পাসওয়ার্ড দিন (Min 6 letters):")
    return REG_PASSWORD


async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text("❌ পাসওয়ার্ড অত্যন্ত ছোট! আবার দিন:")
        return REG_PASSWORD
    
    context.user_data["reg_password"] = password
    await update.message.reply_text("🔐 পাসওয়ার্ডটি নিশ্চিত করতে পুনরায় টাইপ করুন:")
    return REG_CONFIRM_PASSWORD


async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirm_pass = update.message.text.strip()
    password = context.user_data.get("reg_password")
    
    if confirm_pass != password:
        await update.message.reply_text("❌ পাসওয়ার্ড মেলেনি! পুনরায় পাসওয়ার্ড দিন:")
        return REG_PASSWORD
    
    email = context.user_data.get("reg_email")
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.first_name or "User"
    
    with db() as conn:
        conn.execute(
            "INSERT INTO users (telegram_id, email, password, name, balance) VALUES (?, ?, ?, ?, 10.0)",
            (telegram_id, email, hash_password(password), name)
        )
    
    context.user_data.clear()
    await update.message.reply_text("🎉 <b>রেজিস্ট্রেশন সফল!</b> আপনি ১০ টাকা স্বাগতম বোনাস পেয়েছেন।")
    
    user_row = get_user(telegram_id)
    await update.message.reply_text(
        "✨ নিচের মেন্যু ব্যবহার করে বটের সুযোগ সুবিধা নিন:",
        reply_markup=UIBuilder.main_menu(user_row)
    )
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ চলমান প্রক্রিয়া বাতিল করা হয়েছে।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOPPING & PRODUCTS
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🍿 ওটিটি ও সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data="back_main")],
    ]
    await edit_or_reply(update, "📂 <b>প্রোডাক্ট ক্যাটাগরি</b>\n\nপছন্দের ক্যাটাগরি বেছে নিন:", InlineKeyboardMarkup(keyboard))


async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
    
    if not products:
        await edit_or_reply(update, "⚠️ বর্তমানে এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই।", UIBuilder.back_button("shop"))
        return
    
    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("⬅️ পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(update, "📦 <b>প্রোডাক্ট লিস্ট</b>\n\nআপনার কাঙ্ক্ষিত প্রোডাক্টটি সিলেক্ট করুন:", InlineKeyboardMarkup(keyboard))


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
    keyboard.append([InlineKeyboardButton("⬅️ পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n\n"
        f"📌 <b>বিবরণ:</b> {product['description']}\n\n"
        f"নিচ থেকে প্যাকেজ নির্বাচন করুন:",
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
            f"❌ <b>অর্ডার ব্যর্থ! পর্যাপ্ত ব্যালেন্স নেই।</b>\n\n"
            f"আপনার ব্যালেন্স: ৳{user_row['balance']:.2f}\n"
            f"প্রয়োজনীয় ব্যালেন্স: ৳{price:.2f}\n\n"
            f"অনুগ্রহ করে আগে রিচার্জ করে নিন।"
        )
        return ConversationHandler.END
    
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    
    await query.message.reply_text(
        f"🛒 <b>চেকআউট নিশ্চিত করুন</b>\n\n"
        f"📦 প্রোডাক্ট: {product['name']}\n"
        f"📎 প্যাকেজ: {selected_package['amount']}\n"
        f"💰 মূল্য: ৳{price}\n\n"
        f"👉 টপ-আপ ডেলিভারির জন্য আপনার <b>ID / UID / Details</b> দিন (Min 3 letters):"
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
        f"🎉 <b>আপনার অর্ডারটি পেন্ডিং হিসেবে গ্রহণ করা হয়েছে!</b>\n\n"
        f"🆔 অর্ডার আইডি: <code>{order_id}</code>\n"
        f"💰 কর্তনকৃত ব্যালেন্স: ৳{price}\n"
        f"⚡ ৫-১৫ মিনিটের মধ্যে এডমিন অর্ডারটি কমপ্লিট করে দিবে।"
    )
    
    # Send Notification to Admin
    try:
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>নতুন অর্ডার নোটিফিকেশন!</b>\n\n"
                 f"👤 ইউজার আইডি: {telegram_id}\n"
                 f"🆔 অর্ডার আইডি: <code>{order_id}</code>\n"
                 f"📦 প্রোডাক্ট: {product_name}\n"
                 f"📎 প্যাকেজ: {package['amount']}\n"
                 f"ℹ️ ইউজার ডিটেইলস: <code>{user_details}</code>",
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
        [InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data="back_main")]
    ]
    await edit_or_reply(
        update,
        f"💳 <b>ইনস্ট্যান্ট ওয়ালেট রিচার্জ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ <b>সতর্কতা:</b> সর্বনিম্ন রিচার্জের পরিমাণ <b>৳{Config.MIN_DEPOSIT:.2f}</b> টাকা।\n\n"
        f"নিচে থেকে আপনার পেমেন্ট মেথডটি নির্বাচন করুন 👇",
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
        f"💳 <b>{method.upper()} পেমেন্ট গেটওয়ে</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👉 আমাদের {method.title()} পার্সোনাল নম্বর: <code>{number}</code> (ক্লিক করলেই কপি হবে)\n\n"
        f"📌 <b>নিয়মাবলী:</b>\n"
        f"১. প্রথমে ওপরে দেওয়া নম্বরে <b>Send Money</b> করুন।\n"
        f"২. ন্যূনতম রিচার্জ পরিমাণ: ৳{Config.MIN_DEPOSIT}\n"
        f"৩. সফল পেমেন্ট শেষে ট্রানজেকশন আইডি (TrxID) কপি করুন।\n\n"
        f"💵 <b>আপনি কত টাকা পাঠিয়েছেন? শুধু টাকার অংকটি নিচে টাইপ করে পাঠান:</b>"
    )
    return ADD_MONEY_AMOUNT


async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ ভুল ইনপুট! শুধু সংখ্যা দিন (যেমন: ১০০):")
        return ADD_MONEY_AMOUNT
    
    if amount < Config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ দুঃখিত, সর্বনিম্ন ডিপোজিট লিমিট ৳{Config.MIN_DEPOSIT}। আবার ট্রাই করুন:")
        return ADD_MONEY_AMOUNT
    
    context.user_data["recharge_amount"] = amount
    await update.message.reply_text(
        "🔑 এবার আপনার পেমেন্টের <b>Transaction ID (TrxID)</b> টি টাইপ করে এখানে পাঠান:"
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
    
    # Save Request in DB
    with db() as conn:
        conn.execute(
            "INSERT INTO deposit_requests (request_id, telegram_id, method, amount, trx_id) VALUES (?, ?, ?, ?, ?)",
            (req_id, telegram_id, method, amount, trx_id)
        )
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"✅ <b>আপনার পেমেন্ট রিকোয়েস্ট জমা হয়েছে!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ট্র্যাকিং আইডি: <code>{req_id}</code>\n"
        f"💳 মাধ্যম: {method.upper()}\n"
        f"💰 পরিমাণ: ৳{amount:.2f}\n"
        f"🔑 TrxID: <code>{trx_id}</code>\n\n"
        f"⚡ আমাদের টিম ২-৫ মিনিটের মধ্যে এটি ভেরিফাই করে ব্যালেন্স যুক্ত করে দেবে।"
    )
    
    # Notify Admin
    try:
        admin_keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")
            ]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>নতুন ডিপোজিট রিকোয়েস্ট!</b>\n\n"
                 f"👤 ইউজার আইডি: {telegram_id}\n"
                 f"💳 মেথড: {method.upper()}\n"
                 f"💰 এমাউন্ট: ৳{amount:.2f}\n"
                 f"🔑 TrxID: <code>{trx_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        logger.error(f"Deposit notification failure: {e}")
        
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🛠️ ENTERPRISE ADMIN PANEL & CONTROLS (WITH DB BACKUP / RESTORE)
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
    
    m_btn_text = "🟢 Turn Maintenance ON" if m_mode == "OFF" else "🔴 Turn Maintenance OFF"
    
    keyboard = [
        [
            InlineKeyboardButton("📊 অর্ডারসমূহ", callback_data="adm_view_orders"),
            InlineKeyboardButton("💰 অ্যাড-মানি লিস্ট", callback_data="adm_view_deposits")
        ],
        [
            InlineKeyboardButton("👤 ব্যালেন্স এডিট করুন", callback_data="adm_balance_set"),
            InlineKeyboardButton("📦 নতুন প্রোডাক্ট যোগ করুন", callback_data="adm_product_add")
        ],
        [
            InlineKeyboardButton("📤 Backup Database", callback_data="adm_backup_db"),
            InlineKeyboardButton("📥 Restore Database", callback_data="adm_restore_db")
        ],
        [
            InlineKeyboardButton(m_btn_text, callback_data="adm_toggle_maintenance")
        ],
        [InlineKeyboardButton("⬅️ প্রধান মেন্যু", callback_data="back_main")]
    ]
    
    await edit_or_reply(
        update,
        f"🛠️ <b>অ্যাডমিন অপারেশন ড্যাশবোর্ড</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 মোট ইউজার: {users_count} জন\n"
        f"⏳ পেন্ডিং অর্ডার: {pending_orders} টি\n"
        f"💵 পেন্ডিং ডিপোজিট: {pending_deposits} টি\n"
        f"⚙️ মেইনটেনেন্স মোড: <b>{m_mode}</b>\n"
        f"💾 ব্যাকআপ অ্যান্ড রিস্টোর ডাটাবেজ সিস্টেম সচল আছে।",
        InlineKeyboardMarkup(keyboard)
    )


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
            # Safely clone SQLite database using backup api
            src = sqlite3.connect(Config.DB_PATH)
            dst = sqlite3.connect(backup_file)
            with dst:
                src.backup(dst)
            src.close()
            dst.close()
            
            # Send file to admin
            with open(backup_file, "rb") as doc:
                await context.bot.send_document(
                    chat_id=Config.ADMIN_USER_ID,
                    document=doc,
                    filename=os.path.basename(Config.DB_PATH),
                    caption=f"📂 <b>SKY TOPUP DATABASE BACKUP</b>\n\n"
                            f"📅 জেনারেট টাইম: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"⚠️ এই ফাইলটি সুরক্ষিত রাখুন। যেকোনো প্রয়োজনে ডাটাবেজ রিস্টোর করতে এটি ব্যবহার করা যাবে।",
                    parse_mode=ParseMode.HTML
                )
            # Remove temp file
            os.remove(backup_file)
            await query.message.reply_text("✅ ডাটাবেজ ব্যাকআপ সফল হয়েছে এবং আপনার ইনবক্সে ফাইলটি পাঠানো হয়েছে।")
        except Exception as e:
            logger.error(f"DB Backup failed: {e}")
            await query.message.reply_text(f"❌ ব্যাকআপ করতে ত্রুটি হয়েছে: {str(e)}")

    elif data == "adm_restore_db":
        await query.message.reply_text(
            "📥 <b>ডাটাবেজ রিস্টোর সিস্টেম</b>\n\n"
            "আপনার ব্যাকআপ করা ডাটাবেজ ফাইলটি (<code>.db</code>) এখানে আপলোড / সেন্ড করুন।\n"
            "⚠️ <i>সতর্কতা: এটি করলে বর্তমানের সব ডাটা মুছে পূর্বের ব্যাকআপ ডাটা যুক্ত হবে!</i>\n\n"
            "প্রক্রিয়া বাতিল করতে /cancel টাইপ করুন।"
        )
        # We start the conversation inside the admin_restore conversation handler.
        # So we return the state for the admin restore handler.
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
                f"🆔 অর্ডার আইডি: <code>{o['order_id']}</code>\n"
                f"👤 ইউজার: {o['telegram_id']}\n"
                f"📦 প্রোডাক্ট: {o['product_name']} ({o['package']})\n"
                f"ℹ️ ডিটেইলস: <code>{o['user_details']}</code>",
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
                f"🆔 রিকোয়েস্ট আইডি: <code>{d['request_id']}</code>\n"
                f"👤 ইউজার: {d['telegram_id']}\n"
                f"💳 মাধ্যম: {d['method'].upper()}\n"
                f"💰 পরিমাণ: ৳{d['amount']}\n"
                f"🔑 TrxID: <code>{d['trx_id']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Approve/Reject Order
    elif data.startswith("adm_ord_approve_"):
        ord_id = data.replace("adm_ord_approve_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '✅ Completed' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, product_name, package FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
        
        await query.message.edit_text(f"✅ অর্ডার {ord_id} সফলভাবে সম্পন্ন হয়েছে!")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"🎉 <b>আপনার অর্ডারটি সফল হয়েছে!</b>\n\n"
                     f"🆔 অর্ডার আইডি: <code>{ord_id}</code>\n"
                     f"📦 প্রোডাক্ট: {order['product_name']} ({order['package']})\n\n"
                     f"টপ-আপ আপনার অ্যাকাউন্টে যোগ করা হয়েছে। ধন্যবাদ!"
            )
        except Exception:
            pass

    elif data.startswith("adm_ord_reject_"):
        ord_id = data.replace("adm_ord_reject_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '❌ Rejected' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, price FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
            # Refund balance
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (order["price"], order["telegram_id"]))
            
        await query.message.edit_text(f"❌ অর্ডার {ord_id} বাতিল করা হয়েছে (টাকা রিফান্ড করা হয়েছে)!")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"❌ <b>আপনার অর্ডারটি বাতিল করা হয়েছে!</b>\n\n"
                     f"🆔 অর্ডার আইডি: <code>{ord_id}</code>\n"
                     f"💰 আপনার ৳{order['price']} ব্যাক দেওয়া হয়েছে।"
            )
        except Exception:
            pass

    # Approve/Reject Deposit (Add Money)
    elif data.startswith("adm_dep_approve_"):
        req_id = data.replace("adm_dep_approve_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = '⏳ Pending'", (req_id,)).fetchone()
            if dep:
                conn.execute("UPDATE deposit_requests SET status = '✅ Approved' WHERE request_id = ?", (req_id,))
                conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
                
                await query.message.edit_text(f"✅ ডিপোজিট {req_id} সফলভাবে এপ্রুভ হয়েছে!")
                try:
                    await context.bot.send_message(
                        chat_id=dep["telegram_id"],
                        text=f"🎉 <b>আপনার ওয়ালেট রিচার্জ সফল হয়েছে!</b>\n\n"
                             f"💰 যোগকৃত ব্যালেন্স: ৳{dep['amount']:.2f}\n"
                             f"💳 মেথড: {dep['method'].upper()}\n\n"
                             f"ধন্যবাদ আমাদের সাথে থাকার জন্য!"
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
                     f"কারন: আপনার প্রদত্ত TrxID অথবা টাকার অংকটি সঠিক নয়। প্রয়োজনে সাপোর্টে কথা বলুন।"
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
        await update.message.reply_text("❌ এই আইডি দিয়ে কোনো ইউজার পাওয়া যায়নি। পুনরায় আইডি দিন:")
        return ADMIN_SET_BAL_ID
    
    context.user_data["tgt_bal_id"] = tgt_id
    await update.message.reply_text(
        f"👤 ইউজার: {user_row['name']}\n"
        f"💵 বর্তমান ব্যালেন্স: ৳{user_row['balance']:.2f}\n\n"
        f"👉 <b>নতুন ব্যালেন্স কত টাকা বসাতে চান? সেটি টাইপ করে পাঠান:</b>"
    )
    return ADMIN_SET_BAL_AMT

async def bal_amt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_bal = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ অংকটি সঠিক নয়। সঠিক সংখ্যা লিখুন:")
        return ADMIN_SET_BAL_AMT
    
    tgt_id = context.user_data.get("tgt_bal_id")
    with db() as conn:
        conn.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (new_bal, tgt_id))
    
    context.user_data.clear()
    await update.message.reply_text(f"✅ সফলভাবে ইউজারের নতুন ব্যালেন্স ৳{new_bal:.2f} সেট করা হয়েছে!")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 📥 ADMIN RESTORE DATABASE PROCESS
# ──────────────────────────────────────────────────────────────────────────

async def start_db_restore_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        await update.message.reply_text("❌ অ্যাক্সেস ডিনাইড!")
        return ConversationHandler.END
        
    await update.message.reply_text("📥 রিস্টোর করতে ব্যাকআপ ফাইলটি (.db) পাঠান:")
    return ADMIN_RESTORE_DB_STATE

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        return ConversationHandler.END
        
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ অকার্যকর ফাইল ফরম্যাট! দয়া করে একটি সঠিক <b>.db</b> ফাইল পাঠান:")
        return ADMIN_RESTORE_DB_STATE
        
    status_msg = await update.message.reply_text("⏳ <i>ডাটাবেজ ফাইলটি ডাউনলোড এবং ভেরিফাই করা হচ্ছে...</i>", parse_mode=ParseMode.HTML)
    
    try:
        # Download file
        file_obj = await context.bot.get_file(doc.file_id)
        temp_path = "temp_restore.db"
        await file_obj.download_to_drive(temp_path)
        
        # Connection check (Verify if the uploaded file is a valid sqlite database)
        try:
            test_conn = sqlite3.connect(temp_path)
            test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            test_conn.close()
        except Exception:
            os.remove(temp_path)
            await status_msg.edit_text("❌ অকার্যকর ডাটাবেজ ফাইল! আপলোড করা ফাইলটি সঠিক SQLite ডাটাবেজ নয়।")
            return ADMIN_RESTORE_DB_STATE
            
        # Stop DB activity, swap file
        shutil.copyfile(temp_path, Config.DB_PATH)
        os.remove(temp_path)
        
        await status_msg.edit_text("✅ <b>ডাটাবেজ সফলভাবে রিস্টোর করা হয়েছে!</b>\n\nইউজারদের ব্যালেন্স, রেকর্ড এবং সেটিংস সফলভাবে রিসেট করা হয়েছে।", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status_msg.edit_text(f"❌ ডাটাবেজ রিস্টোর করতে ব্যর্থ হয়েছে! ভুল: {str(e)}")
        
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# ➕ DYNAMIC PRODUCT ADD CONVERSATION
# ──────────────────────────────────────────────────────────────────────────

async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Game", callback_data="cat_sel_game"), InlineKeyboardButton("Subscribe", callback_data="cat_sel_subscribe")]
    ]
    await update.callback_query.message.reply_text("📂 প্রোডাক্টের ক্যাটাগরি বেছে নিন:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = "game" if "game" in query.data else "subscribe"
    context.user_data["new_prod_cat"] = category
    await query.message.reply_text("📦 প্রোডাক্টের <b>নাম</b> লিখুন (যেমন: Free Fire 500 Diamonds):")
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["new_prod_name"] = name
    await update.message.reply_text("📝 প্রোডাক্টের <b>ছোট বিবরণ বা ডেসক্রিপশন</b> লিখুন:")
    return ADMIN_ADD_PROD_DESC

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["new_prod_desc"] = desc
    await update.message.reply_text(
        "💎 এবার অপশন বা প্যাকেজগুলো JSON ফরম্যাটে দিন।\n"
        "যেমন:\n"
        '<code>[{"amount": "১০০ ডায়মন্ড", "price": 100}, {"amount": "২০০ ডায়মন্ড", "price": 200}]</code>'
    )
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opts_raw = update.message.text.strip()
    try:
        json.loads(opts_raw)  # Validation Check
    except ValueError:
        await update.message.reply_text("❌ ইনপুটটি সঠিক JSON ফরম্যাটে হয়নি! আবার পাঠান:")
        return ADMIN_ADD_PROD_OPTS
    
    category = context.user_data.get("new_prod_cat")
    name = context.user_data.get("new_prod_name")
    desc = context.user_data.get("new_prod_desc")
    
    with db() as conn:
        conn.execute(
            "INSERT INTO products (name, category, description, options) VALUES (?, ?, ?, ?)",
            (name, category, desc, opts_raw)
        )
    
    context.user_data.clear()
    await update.message.reply_text("✅ প্রোডাক্টটি সফলভাবে যুক্ত করা হয়েছে!")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 👤 PROFILE & GENERAL VIEWS
# ──────────────────────────────────────────────────────────────────────────

async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    msg = (
        f"💰 <b>আমার ওয়ালেট ব্যালেন্স</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 ব্যবহারকারী: {UIBuilder.safe_text(user_row['name'])}\n"
        f"💳 কারেন্ট ব্যালেন্স: ৳{user_row['balance']:,.2f}\n"
        f"🎁 রিওয়ার্ড পয়েন্ট: {user_row['reward_points']:,} pts\n\n"
        f"রিচার্জ করতে নিচের বাটনে ক্লিক করুন 👇"
    )
    keyboard = [
        [InlineKeyboardButton("➕ ইনস্ট্যান্ট রিচার্জ", callback_data="recharge")],
        [InlineKeyboardButton("⬅️ প্রধান মেন্যু", callback_data="back_main")]
    ]
    await edit_or_reply(update, msg, InlineKeyboardMarkup(keyboard))


async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"👤 <b>আমার প্রোফাইল</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 নাম: {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 ইমেল: <code>{user_row['email']}</code>\n"
        f"🏅 র‍্যাংক: {user_row['rank']}\n"
        f"💳 ব্যালেন্স: ৳{user_row['balance']:.2f}\n"
        f"📅 তৈরির তারিখ: {user_row['created_at']}",
        UIBuilder.back_button("back_main")
    )

async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "⚙️ <b>সেটিংস ও নিরাপত্তা</b>\n\nফিচারগুলো পরবর্তী আপডেটে আসবে।", UIBuilder.back_button("back_main"))

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "💬 <b>২৪/৭ কাস্টমার সাপোর্ট</b>\n\nযেকোনো সমস্যায় আমাদের অফিশিয়াল সাপোর্টে নক করুন: @SkyTopUpSupport", UIBuilder.back_button("back_main"))

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute("SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 5", (str(update.effective_user.id),)).fetchall()
    
    if not orders:
        await edit_or_reply(update, "📭 আপনি এখনও কোনো অর্ডার করেননি।", UIBuilder.back_button("back_main"))
        return
    
    lines = ["📦 <b>আপনার শেষ ৫টি অর্ডারের ইতিহাস:</b>\n"]
    for o in orders:
        lines.append(f"🆔 <code>{o['order_id']}</code> | 📦 {o['product_name']} | ৳{o['price']} | {o['status']}")
    await edit_or_reply(update, "\n\n".join(lines), UIBuilder.back_button("back_main"))


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
        "balance": show_balance_ui,
        "orders": show_orders_ui,
        "recharge": show_recharge_ui,
        "profile": show_profile_ui,
        "settings": show_settings_ui,
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
    
    # Registration Handler
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_email)],
            REG_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_otp)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_password)],
            REG_CONFIRM_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm_password)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )
    
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
    
    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(deposit_handler)
    app.add_handler(admin_balance_handler)
    app.add_handler(admin_product_handler)
    app.add_handler(admin_restore_handler)
    
    # Unified Query Handlers
    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)"))
    
    logger.info("🌟 Sky TopUp Bot (Enterprise Engine) started successfully...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
