#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v2.5 (Fully Integrated & Premium UI)
───────────────────────────────────────────────────────────
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
# 🎛️ CONFIGURATION (Integrated from .env)
# ──────────────────────────────────────────────────────────────────────────

class Config:
    """Centralized configuration management with hardcoded defaults."""
    
    # Telegram Bot Token
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
    
    # OTP & Security
    OTP_VALID_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 6
    
    # Database path
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    
    # Feature flags
    EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)
    DEV_MODE = not EMAIL_SENDING_ENABLED
    
    # Admin
    ADMIN_USER_ID = 1

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
    """Context-managed SQLite connection with row factory."""
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
    """Initialize all database tables."""
    db_dir = os.path.dirname(Config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Created directory: {db_dir}")
    
    with db() as conn:
        c = conn.cursor()
        
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
        
        # Seed default products
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
                ("Free Fire Diamonds", "game", "💎", "ফ্রি ফায়ার ডায়মন্ড টপ-আপ",
                 json.dumps([
                     {"amount": "💎 ১০০ ডায়মন্ড", "price": 100},
                     {"amount": "💎 ৩১০ ডায়মন্ড", "price": 300},
                     {"amount": "💎 ৫২০ ডায়মন্ড", "price": 500},
                     {"amount": "💎 ১০৬০ ডায়মন্ড", "price": 1000},
                 ])),
                ("PUBG Mobile UC", "game", "🔫", "PUBG মোবাইল UC টপ-আপ",
                 json.dumps([
                     {"amount": "🔫 ৬০ UC", "price": 120},
                     {"amount": "🔫 ৩২৫ UC", "price": 600},
                     {"amount": "🔫 ৬৬০ UC", "price": 1150},
                 ])),
                ("Netflix Premium", "subscribe", "🎬", "নেটফ্লিক্স প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎬 ১ মাস স্ক্রিন", "price": 200},
                     {"amount": "🎬 ৩ মাস প্রিমিয়াম", "price": 500},
                     {"amount": "🎬 ১২ মাস প্রিমিয়াম", "price": 1800},
                 ])),
                ("YouTube Premium", "subscribe", "▶️", "ইউটিউব প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "▶️ ১ মাস প্রিমিয়াম", "price": 120},
                     {"amount": "▶️ ১২ মাস প্রিমিয়াম", "price": 1200},
                 ])),
                ("Spotify Premium", "subscribe", "🎵", "স্পটিফাই প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎵 ১ মাস প্রিমিয়াম", "price": 130},
                     {"amount": "🎵 ৩ মাস প্রিমিয়াম", "price": 350},
                 ])),
                ("Crunchyroll Premium", "subscribe", "🎌", "ক্রাঞ্চিরোল প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎌 ১ মাস মেম্বারশিপ", "price": 150},
                     {"amount": "🎌 ৩ মাস মেম্বারশিপ", "price": 400},
                 ])),
            ]
            c.executemany(
                "INSERT INTO products (name, category, icon, description, options) VALUES (?, ?, ?, ?, ?)",
                default_products,
            )
            logger.info("✅ Seeded %d default products", len(default_products))
    
    logger.info("📦 Database initialized at %s", Config.DB_PATH)


def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def update_balance(telegram_id: str, amount: float) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )


def update_last_login(telegram_id: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?",
            (telegram_id,),
        )


# ──────────────────────────────────────────────────────────────────────────
# 🔐 SECURITY HELPERS
# ──────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = "SKY_TOPUP_2024_v2"
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)


def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def is_admin(user_row) -> bool:
    return user_row and (user_row["id"] == Config.ADMIN_USER_ID or user_row["is_admin"] == 1)


# ──────────────────────────────────────────────────────────────────────────
# 📧 EMAIL SERVICE
# ──────────────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, otp: str) -> bool:
    if Config.DEV_MODE:
        logger.info("🔧 DEV MODE — OTP for %s: %s", to_email, otp)
        return True
    
    if not Config.EMAIL_SENDING_ENABLED:
        logger.warning("⚠️ SMTP not configured — cannot send email.")
        return False
    
    msg = MIMEMultipart("alternative")
    msg["From"] = f"SKY TopUp <{Config.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "🔐 SKY TopUp — OTP Verification Code"
    
    text_body = (
        f"আপনার SKY TopUp OTP কোড: {otp}\n\n"
        f"⏰ এই কোডটি {Config.OTP_VALID_MINUTES} মিনিটের জন্য কার্যকর থাকবে।\n"
        f"🔒 নিরাপত্তার জন্য দয়া করে এটি কারো সাথে শেয়ার করবেন না।\n\n"
        f"ধন্যবাদ,\nSKY TopUp টিম"
    )
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    
    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, to_email, msg.as_string())
        logger.info("✅ OTP email sent to %s", to_email)
        return True
    except Exception as e:
        logger.error("❌ Failed to send OTP email to %s: %s", to_email, e)
        return False


# ──────────────────────────────────────────────────────────────────────────
# 🎨 UI HELPERS (Polished and Made Premium)
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
            keyboard.append([InlineKeyboardButton("🛠️ অ্যাডমিন প্যানেল 🛠️", callback_data="admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data=callback_data)]
        ])

# ──────────────────────────────────────────────────────────────────────────
# 📨 MESSAGING HELPERS
# ──────────────────────────────────────────────────────────────────────────

async def smart_reply(update: Update, text: str, reply_markup=None):
    kwargs = {
        "text": text,
        "parse_mode": ParseMode.HTML,
        "reply_markup": reply_markup,
    }
    if update.callback_query:
        await update.callback_query.message.reply_text(**kwargs)
    elif update.message:
        await update.message.reply_text(**kwargs)


async def edit_or_reply(update: Update, text: str, reply_markup=None):
    kwargs = {
        "text": text,
        "parse_mode": ParseMode.HTML,
        "reply_markup": reply_markup,
    }
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(**kwargs)
            return
        except Exception:
            pass
    await smart_reply(update, text, reply_markup)


# ──────────────────────────────────────────────────────────────────────────
# 👤 REGISTRATION FLOW
# ──────────────────────────────────────────────────────────────────────────

REG_EMAIL, REG_OTP, REG_PASSWORD, REG_CONFIRM_PASSWORD = range(4)
ORDER_DETAILS_STATE = 100


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(str(user.id))
    
    if existing:
        update_last_login(str(user.id))
        user_row = get_user(str(user.id))
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
        f"📌 <b>ভেরিফিকেশনের জন্য প্রয়োজন:</b>\n"
        f" └ 📧 সচল জিমেইল আইডি (Gmail)\n"
        f" └ 🔑 ওটিপি ভেরিফিকেশন (OTP Code)\n"
        f" └ 🔐 নিজের পছন্দমতো স্ট্রং পাসওয়ার্ড\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>শুরু করতে আপনার জিমেইল এড্রেসটি এখানে লিখুন:</b>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    return REG_EMAIL


async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    
    if not is_valid_email(email):
        await update.message.reply_text(
            "❌ <b>ভুল বা অবৈধ ইমেইল ফরম্যাট!</b>\n\n"
            "অনুগ্রহ করে সঠিক ফরম্যাটে জিমেইল দিন।\n"
            "যেমন: <code>username@gmail.com</code>\n\n"
            "<i>(বাতিল করতে /cancel টাইপ করুন)</i>",
            parse_mode=ParseMode.HTML,
        )
        return REG_EMAIL
    
    if get_user_by_email(email):
        await update.message.reply_text(
            "⚠️ <b>দুঃখিত! এই ইমেইলটি ইতিমধ্যে ব্যবহৃত হয়েছে।</b>\n\n"
            "• নতুন কোনো ইমেইল ব্যবহার করুন।\n"
            "• অথবা যেকোনো প্রয়োজনে এডমিন সাপোর্টে যোগাযোগ করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    otp = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=Config.OTP_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    
    with db() as conn:
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (str(update.effective_user.id),))
        conn.execute(
            "INSERT INTO otp_codes (telegram_id, otp_code, expires_at) VALUES (?, ?, ?)",
            (str(update.effective_user.id), otp, expires_at),
        )
    
    context.user_data["reg_email"] = email
    sent = send_otp_email(email, otp)
    
    if sent and not Config.DEV_MODE:
        await update.message.reply_text(
            f"📬 <b>OTP পাঠানো হয়েছে!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ আপনার ইমেইল: <code>{email}</code>\n"
            f"একটি ৬-সংখ্যার ওটিপি কোড পাঠানো হয়েছে।\n\n"
            f"⏳ <b>মেয়াদ:</b> {Config.OTP_VALID_MINUTES} মিনিট।\n"
            f"🔒 নিরাপত্তার স্বার্থে ওটিপি কাউকে শেয়ার করবেন না।\n\n"
            f"👇 <b>কোডটি নিচে টাইপ করুন:</b>",
            parse_mode=ParseMode.HTML,
        )
    else:
        # SMTP কনফিগার না থাকলে ডেভেলপারদের সুবিধার্থে OTP মেসেজে দেখাবে
        await update.message.reply_text(
            f"⚙️ <b>টেস্টিং / ডেভেলপার মোড</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📧 <b>ইমেইল:</b> <code>{email}</code>\n"
            f"🔑 <b>সিস্টেম OTP কোড:</b> <code>{otp}</code>\n\n"
            f"⏳ <b>মেয়াদ:</b> {Config.OTP_VALID_MINUTES} মিনিট।\n\n"
            f"⚠️ <i>বিকাশকারী সতর্কতা: জিমেইল এবং অ্যাপ পাসওয়ার্ড পুরোপুরি সচল করা রয়েছে। প্রোডাকশন টেস্ট হিসেবে ওটিপি সাবমিট করুন।</i>\n\n"
            f"👇 <b>কোডটি নিচে টাইপ করুন:</b>",
            parse_mode=ParseMode.HTML,
        )
    
    return REG_OTP


async def reg_receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered_otp = update.message.text.strip()
    telegram_id = str(update.effective_user.id)
    
    with db() as conn:
        row = conn.execute(
            """SELECT otp_code, expires_at, attempt_count, id
               FROM otp_codes 
               WHERE telegram_id = ? AND is_used = 0
               ORDER BY created_at DESC LIMIT 1""",
            (telegram_id,),
        ).fetchone()
    
    if not row:
        await update.message.reply_text(
            "❌ <b>ওটিপি পাওয়া যায়নি!</b>\n\nদয়া করে /start চাপুন এবং নতুন করে চেষ্টা করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    if row["expires_at"]:
        expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() > expires:
            await update.message.reply_text(
                "⌛ <b>ওটিপি কোডের মেয়াদ শেষ হয়ে গেছে!</b>\n\nআবার নতুন করে শুরু করতে /start দিন।",
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    
    attempts = row["attempt_count"] + 1
    with db() as conn:
        conn.execute("UPDATE otp_codes SET attempt_count = ? WHERE id = ?", (attempts, row["id"]))
    
    if attempts > Config.MAX_OTP_ATTEMPTS:
        with db() as conn:
            conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
        await update.message.reply_text(
            "❌ <b>অতিরিক্ত ভুলের কারণে ওটিপি বাতিল করা হয়েছে!</b>\n\nনিরাপত্তাজনিত কারণে আবার শুরু করতে /start দিন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    if entered_otp != row["otp_code"]:
        remaining = Config.MAX_OTP_ATTEMPTS - attempts
        await update.message.reply_text(
            f"❌ <b>ভুল ওটিপি কোড!</b>\n\n"
            f"আপনার আর মাত্র {remaining} বার সুযোগ রয়েছে।\n"
            f"সঠিক ওটিপি কোডটি পুনরায় টাইপ করুন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_OTP
    
    with db() as conn:
        conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
    
    await update.message.reply_text(
        "✅ <b>ইমেইল সফলভাবে ভেরিফাইড হয়েছে!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔐 <b>একটি নিরাপদ পাসওয়ার্ড সেট করুন:</b>\n"
        f"└ ন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষরের হতে হবে।\n\n"
        "👇 <b>পাসওয়ার্ডটি নিচে লিখুন:</b>",
        parse_mode=ParseMode.HTML,
    )
    return REG_PASSWORD


async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text(
            f"❌ <b>পাসওয়ার্ডটি অত্যন্ত ছোট!</b>\n\n"
            f"নিরাপত্তার স্বার্থে ন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষরের পাসওয়ার্ড দিন:\n"
            f"আবার পাসওয়ার্ড লিখুন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_PASSWORD
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    context.user_data["reg_password"] = password
    await update.message.reply_text(
        "🔐 <b>পাসওয়ার্ড নিশ্চিত করুন:</b>\n\n"
        "পাসওয়ার্ডটি পুনরায় নিচে টাইপ করুন 👇",
        parse_mode=ParseMode.HTML,
    )
    return REG_CONFIRM_PASSWORD


async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirm_pass = update.message.text.strip()
    password = context.user_data.get("reg_password")
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    if confirm_pass != password:
        await update.message.reply_text(
            "❌ <b>দুঃখিত, পাসওয়ার্ড দুইটি মেলেনি!</b>\n\n"
            "অনুগ্রহ করে নতুন করে পাসওয়ার্ডটি দিন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_PASSWORD
    
    email = context.user_data.get("reg_email", "")
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.first_name or update.effective_user.username or "User"
    
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO users (telegram_id, email, password, name) VALUES (?, ?, ?, ?)",
                (telegram_id, email, hash_password(password), name),
            )
        logger.info("✅ New user registered: %s (%s)", telegram_id, email)
    except sqlite3.IntegrityError:
        await update.message.reply_text(
            "❌ রেজিস্ট্রেশন ব্যর্থ হয়েছে। আবার শুরু করতে /start দিন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    context.user_data.clear()
    update_balance(telegram_id, 10.0)  # ওয়েলকাম বোনাস
    
    await smart_reply(
        update,
        f"🎉 <b>অভিনন্দন! রেজিস্ট্রেশন সফল হয়েছে!</b> 🎉\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(name)}\n"
        f"📧 <b>ইমেইল:</b> <code>{email}</code>\n"
        f"🎁 <b>ওয়েলকাম বোনাস:</b> ৳ ১০.০০ (আপনার ব্যালেন্সে যোগ করা হয়েছে!)\n\n"
        f"সবচেয়ে কম মূল্যে টপ-আপের আনন্দ উপভোগ করুন! 👇",
    )
    await show_main_menu_ui(update, context)
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await smart_reply(update, "❌ <b>চলমান প্রক্রিয়াটি বাতিল করা হয়েছে।</b>\n\nপ্রধান মেন্যুতে যেতে /start লিখুন।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🏠 MAIN MENU
# ──────────────────────────────────────────────────────────────────────────

async def show_main_menu_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await smart_reply(update, "⚠️ সিস্টেম ত্রুটি। সেশন চালু করতে অনুগ্রহ করে /start দিন।")
        return
    
    welcome = (
        f"⚡ <b>SKY TOPUP — PREMIUM BOT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 স্বাগতম, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
        f"💳 <b>ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
        f"🏅 <b>র‍্যাংক:</b> {user_row['rank']}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']} pts\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ নিচের ইন্টারেক্টিভ মেন্যু থেকে অপশন নির্বাচন করুন:"
    )
    await edit_or_reply(update, welcome, UIBuilder.main_menu(user_row))


# ──────────────────────────────────────────────────────────────────────────
# 🔄 CALLBACK ROUTER
# ──────────────────────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    routes = {
        "back_main": show_main_menu_ui,
        "shop": show_categories_ui,
        "back_shop": show_categories_ui,
        "balance": show_balance_ui,
        "orders": show_orders_ui,
        "recharge": show_recharge_ui,
        "profile": show_profile_ui,
        "settings": show_settings_ui,
        "help": show_help_ui,
        "admin": show_admin_panel_ui,
    }
    
    if data in routes:
        await routes[data](update, context)
    elif data.startswith("category_"):
        await show_products_ui(update, context, data.replace("category_", ""))
    elif data.startswith("product_"):
        await select_package_ui(update, context, int(data.replace("product_", "")))
    elif data.startswith("recharge_"):
        await show_recharge_instructions_ui(update, context, data.replace("recharge_", ""))


# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOP
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🍿 ওটিটি ও সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data="back_main")],
    ]
    await edit_or_reply(
        update,
        "📂 <b>প্রোডাক্ট ক্যাটাগরি</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "নিচে থেকে আপনার পছন্দের প্রোডাক্টের ধরণ নির্বাচন করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute(
            "SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)
        ).fetchall()
    
    if not products:
        await edit_or_reply(update, "⚠️ <b>দুঃখিত! এই ক্যাটাগরিতে বর্তমানে কোনো প্রোডাক্ট স্টক নেই।</b>", UIBuilder.back_button("back_shop"))
        return
    
    keyboard = [
        [InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")]
        for p in products
    ]
    keyboard.append([InlineKeyboardButton("⬅️ পিছনে যান", callback_data="back_shop")])
    
    category_names = {"game": "🎮 গেম টপ-আপ স্টোর", "subscribe": "🎬 সাবস্ক্রিপশন প্ল্যানসমূহ"}
    await edit_or_reply(
        update,
        f"📦 <b>{category_names.get(category, category)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"আপনার কাঙ্ক্ষিত প্রোডাক্ট নির্বাচন করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        await edit_or_reply(update, "❌ <b>প্রোডাক্টটি খুঁজে পাওয়া যায়নি!</b>", UIBuilder.back_button("back_shop"))
        return
    
    options = json.loads(product["options"])
    keyboard = [
        [InlineKeyboardButton(f"{opt['amount']} ➔ ৳{opt['price']:,}", callback_data=f"package_{product_id}_{idx}")]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ পিছনে যান", callback_data="back_shop")])
    
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>বিবরণ:</b> {product['description'] or 'সেরা মূল্যে ও দ্রুত ডেলিভারি।'}\n\n"
        f"ডেলিভারি নিতে যেকোনো একটি প্যাকেজ বেছে নিন 👇",
        InlineKeyboardMarkup(keyboard),
    )


# ──────────────────────────────────────────────────────────────────────────
# 📋 ORDER FLOW
# ──────────────────────────────────────────────────────────────────────────

async def package_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    if len(parts) != 3:
        await query.message.reply_text("❌ সিস্টেমে ভুল তথ্য প্রবেশ করানো হয়েছে!")
        return ConversationHandler.END
    
    _, product_id_str, package_idx_str = parts
    product_id, package_idx = int(product_id_str), int(package_idx_str)
    
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        await query.message.reply_text("❌ <b>প্রোডাক্ট পাওয়া যায়নি!</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    options = json.loads(product["options"])
    selected_package = options[package_idx]
    user_row = get_user(str(update.effective_user.id))
    
    if not user_row:
        await query.message.reply_text("⚠️ সেশন চালু করতে অনুগ্রহ করে /start দিন।", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    price = selected_package["price"]
    if user_row["balance"] < price:
        await query.message.reply_text(
            f"⚠️ <b>দুঃখিত, পর্যাপ্ত ব্যালেন্স নেই!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 <b>আপনার ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
            f"💸 <b>প্যাকেজ মূল্য:</b> ৳ {price:,.2f}\n"
            f"🔄 <b>ঘাটতি ব্যালেন্স:</b> ৳ {price - user_row['balance']:,.2f}\n\n"
            f"👉 অনুগ্রহ করে মেইন মেন্যু থেকে <b>'➕ ইনস্ট্যান্ট রিচার্জ'</b> করে আবার ট্রাই করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    
    await query.message.reply_text(
        f"🛒 <b>অর্ডার চেকআউট / কনফার্মেশন</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 <b>প্রোডাক্ট:</b> {product['name']}\n"
        f"📎 <b>প্যাকেজ:</b> {selected_package['amount']}\n"
        f"💰 <b>মোট মূল্য:</b> ৳ {price:,.2f}\n\n"
        f"👉 টপ-আপের জন্য আপনার <b>ID / UID / Username / Gmail</b> প্রদান করুন:\n"
        f"<i>(ভুল আইডি দিলে ডেলিভারি ব্যাহত হবে। বাতিল করতে /cancel লিখুন)</i>",
        parse_mode=ParseMode.HTML,
    )
    return ORDER_DETAILS_STATE


async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "order_product_name" not in context.user_data:
        await update.message.reply_text("❌ সেশনের সময় শেষ! দয়া করে /start দিয়ে নতুনভাবে শুরু করুন।")
        return ConversationHandler.END
    
    user_details = update.message.text.strip()
    if not user_details or len(user_details) < 3:
        await update.message.reply_text(
            "❌ <b>ইনপুট অসম্পূর্ণ বা অত্যন্ত ছোট!</b>\n\n"
            "অনুগ্রহ করে সঠিক ও স্পষ্ট আইডি তথ্য লিখুন:", 
            parse_mode=ParseMode.HTML
        )
        return ORDER_DETAILS_STATE
    
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    telegram_id = str(update.effective_user.id)
    
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    order_id = f"SKY-{timestamp}-{secrets.token_hex(2).upper()}"
    reward = int(price) // 10
    
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO orders (order_id, telegram_id, product_name, package, price, user_details) VALUES (?, ?, ?, ?, ?, ?)",
                (order_id, telegram_id, product_name, package["amount"], price, user_details),
            )
            conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, telegram_id))
            conn.execute("UPDATE users SET reward_points = reward_points + ? WHERE telegram_id = ?", (reward, telegram_id))
    except sqlite3.Error as e:
        logger.error("Order failed: %s", e)
        await update.message.reply_text("❌ ডাটাবেজ ত্রুটির কারণে অর্ডার ব্যর্থ হয়েছে। আবার ট্রাই করুন।")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"🎉 <b>আপনার অর্ডারটি সফল হয়েছে!</b> 🎉\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>অর্ডার আইডি:</b> <code>{order_id}</code>\n"
        f"📦 <b>প্রোডাক্ট:</b> {product_name}\n"
        f"📎 <b>প্যাকেজ:</b> {package['amount']}\n"
        f"💰 <b>পরিশোধিত:</b> ৳ {price:,.2f} <i>(ব্যালেন্স থেকে কর্তিত)</i>\n"
        f"🎁 <b>অর্জিত পয়েন্ট:</b> +{reward} pts\n"
        f"👤 <b>আইডি তথ্য:</b> <code>{user_details}</code>\n\n"
        f"⚡ আমাদের টিম সর্বোচ্চ ৫-১৫ মিনিটের মধ্যে আপনার অর্ডারটি ডেলিভারি করে দিবে। ধন্যবাদ!",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["order_product_name", "order_package"]:
        context.user_data.pop(key, None)
    await update.message.reply_text("❌ আপনার অর্ডার প্রক্রিয়াটি বাতিল করা হয়েছে।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 💰 ACCOUNT SCREENS
# ──────────────────────────────────────────────────────────────────────────

async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ সেশন আউট। /start দিন।")
        return
    
    msg = (
        f"💰 <b>আমার ওয়ালেট ও ব্যালেন্স</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"💳 <b>কারেন্ট ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']:,} pts\n"
        f"🏅 <b>ইউজার র‍্যাংক:</b> {user_row['rank']}\n\n"
        f"⚡ ব্যালেন্স রিচার্জ করতে নিচের <b>'➕ রিচার্জ করুন'</b> বাটনে ক্লিক করুন 👇"
    )
    keyboard = [
        [InlineKeyboardButton("➕ রিচার্জ করুন", callback_data="recharge")],
        [InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data="back_main")],
    ]
    await edit_or_reply(update, msg, InlineKeyboardMarkup(keyboard))


async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 10",
            (str(update.effective_user.id),),
        ).fetchall()
    
    if not orders:
        await edit_or_reply(
            update,
            "📭 <b>আপনি এখনও কোনো অর্ডার করেননি!</b>\n\nশপ ক্যাটাগরি থেকে আপনার প্রথম অর্ডারটি করুন 👇",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 প্রোডাক্ট শপ", callback_data="shop")],
                [InlineKeyboardButton("⬅️ প্রধান মেন্যু", callback_data="back_main")],
            ]),
        )
        return
    
    lines = ["📦 <b>আপনার শেষ ১০টি অর্ডারের ইতিহাস</b>\n"
             "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"]
    for o in orders:
        lines.append(
            f"🆔 <code>{o['order_id']}</code>\n"
            f" └ 📦 {o['product_name']} ({o['package']})\n"
            f" └ 💰 ৳{o['price']:,.2f} | {o['status']}\n"
            f" └ 📅 {o['created_at']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    await edit_or_reply(update, "\n".join(lines), UIBuilder.back_button("back_main"))


async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📱 বিকাশ (bKash)", callback_data="recharge_bkash"),
            InlineKeyboardButton("📱 নগদ (Nagad)", callback_data="recharge_nagad")
        ],
        [
            InlineKeyboardButton("📱 রকেট (Rocket)", callback_data="recharge_rocket")
        ],
        [
            InlineKeyboardButton("⬅️ প্রধান মেন্যুতে ফিরুন", callback_data="back_main")
        ],
    ]
    await edit_or_reply(
        update,
        "💳 <b>ইনস্ট্যান্ট ওয়ালেট রিচার্জ</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "আমাদের স্বয়ংক্রিয় গেটওয়ে পেমেন্ট সচল রয়েছে। নিচে থেকে আপনার পেমেন্ট মাধ্যমটি সিলেক্ট করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {
        "bkash": Config.BKASH_NUMBER,
        "nagad": Config.NAGAD_NUMBER,
        "rocket": Config.ROCKET_NUMBER,
    }
    number = numbers.get(method, "01XXXXXXXXX")
    
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()} পেমেন্ট মেথড</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>সেন্ড মানি করার নির্দেশনা:</b>\n"
        f" └ আমাদের {method.title()} পার্সোনাল নম্বর:\n"
        f"   👉 <code>{number}</code> <i>(নম্বরটি কপি করতে ক্লিক করুন)</i>\n\n"
        f"📥 <b>টাকা পাঠানোর পর করণীয়:</b>\n"
        f"১. সফল লেনদেনের TrxID এবং পেমেন্ট স্ক্রিনশটটি সংরক্ষণ করুন।\n"
        f"২. আমাদের অফিশিয়াল সাপোর্ট অ্যাকাউন্টে সেন্ড করুন।\n"
        f"৩. ৫ মিনিটের মধ্যে আপনার অ্যাকাউন্টে টাকা ক্রেডিট হয়ে যাবে।\n\n"
        f"👨‍💻 <b>সরাসরি পেমেন্ট সাপোর্ট:</b> @SkyTopUpSupport",
        UIBuilder.back_button("recharge"),
    )


async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ অ্যাকাউন্ট খুঁজে পাওয়া যায়নি। /start দিন।")
        return
    
    await edit_or_reply(
        update,
        f"👤 <b>ব্যবহারকারীর প্রোফাইল</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>গ্রাহকের নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 <b>নিবন্ধিত ইমেইল:</b> <code>{user_row['email']}</code>\n"
        f"🏅 <b>মেম্বারশিপ র‍্যাংক:</b> {user_row['rank']}\n"
        f"💳 <b>ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']:,} pts\n"
        f"📅 <b>অ্যাকাউন্ট তৈরি:</b> {user_row['created_at']}",
        UIBuilder.back_button("back_main"),
    )


async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(
        update,
        "⚙️ <b>সিস্টেম ও সেটিংস</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⏳ <b>নিচের ফিচারগুলো পরবর্তী আপডেটে আসছে:</b>\n"
        " ├ 🔐 পাসওয়ার্ড পরিবর্তন (Change Password)\n"
        " ├ 🔔 নোটিফিকেশন অ্যালার্ট (Notification settings)\n"
        " └ 🌐 ইন্টারফেস ভাষা পরিবর্তন (Language options)",
        UIBuilder.back_button("back_main"),
    )


async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(
        update,
        "❓ <b>হেল্প সেন্টার ও সাপোর্ট</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🤖 <b>বটের প্রধান কমান্ডসমূহ:</b>\n"
        " ├ /start - প্রধান ড্যাশবোর্ড ও মেন্যু ওপেন করুন\n"
        " └ /cancel - যেকোনো চলমান প্রক্রিয়া বাতিল করুন\n\n"
        "📌 <b>২৪/৭ কাস্টমার কেয়ার:</b>\n"
        "টপ-আপ রিফান্ড, পেমেন্ট অ্যাড অথবা যেকোনো টেকনিক্যাল ইস্যুতে সরাসরি আমাদের সাপোর্ট টিমের সাথে কথা বলুন।\n\n"
        "👉 <b>কাস্টমার সাপোর্ট আইডি:</b> @SkyTopUpSupport",
        UIBuilder.back_button("back_main"),
    )


async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row or not is_admin(user_row):
        await edit_or_reply(update, "⛔ <b>অ্যাক্সেস ডিনাইড! এই প্যানেলটি শুধুমাত্র অ্যাডমিনদের জন্য সংরক্ষিত।</b>", UIBuilder.back_button("back_main"))
        return
    
    with db() as conn:
        total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        pending_orders = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = '⏳ Pending'").fetchone()["cnt"]
        total_revenue = conn.execute("SELECT COALESCE(SUM(price), 0) as total FROM orders").fetchone()["total"]
    
    await edit_or_reply(
        update,
        f"🛠️ <b>অ্যাডমিন কন্ট্রোল ড্যাশবোর্ড</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 <b>মোট রেজিস্টার্ড ইউজার:</b> {total_users:,} জন\n"
        f"⏳ <b>পেন্ডিং অর্ডারসমূহ:</b> {pending_orders:,} টি\n"
        f"💰 <b>মোট অর্জিত রেভিনিউ:</b> ৳ {total_revenue:,.2f}",
        UIBuilder.back_button("back_main"),
    )


# ──────────────────────────────────────────────────────────────────────────
# 🚀 MAIN RUNNER
# ──────────────────────────────────────────────────────────────────────────

def main():
    if not Config.BOT_TOKEN:
        raise SystemExit(
            "❌ BOT_TOKEN environment variable is not set!\n\n"
            "Railway Dashboard → Variables → Add:\n"
            "  BOT_TOKEN = your_bot_token\n\n"
            "Then redeploy."
        )
    
    if Config.DEV_MODE:
        logger.warning("⚠️ DEV MODE ACTIVE — SMTP not configured. OTP shown in chat.")
    else:
        logger.info("✅ Email sending ENABLED")
    
    init_db()
    
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
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
    
    order_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={
            ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order_handler)],
    )
    
    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)"))
    
    logger.info("🌟 Sky TopUp Bot is now running on high performance...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
