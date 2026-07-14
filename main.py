#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v2.0 (Railway Ready)
─────────────────────────────────────────
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

# ── .env ফাইল থেকে ভেরিয়েবল লোড করার জন্য ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv না থাকলে .env ছাড়াই চলবে
# ─────────────────────────────────────────

# ──────────────────────────────────────────────────────────────────────────
# 🎛️ CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────

class Config:
    """Centralized configuration management."""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # SMTP / Email
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    
    # Payment merchant numbers
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01XXXXXXXXX")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01XXXXXXXXX")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01XXXXXXXXX")
    
    # OTP & Security
    OTP_VALID_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 6
    
    # Database — Railway persistent path
    DB_PATH = os.getenv("DB_PATH", "/data/skytopup.db")
    # /data Railway-এ persistent storage
    
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
    # নিশ্চিত করুন যে /data ডিরেক্টরি আছে
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
                rank TEXT DEFAULT '🥉 Bronze',
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
                     {"amount": "💎 100 Diamonds", "price": 100},
                     {"amount": "💎 310 Diamonds", "price": 300},
                     {"amount": "💎 520 Diamonds", "price": 500},
                     {"amount": "💎 1060 Diamonds", "price": 1000},
                 ])),
                ("PUBG Mobile UC", "game", "🔫", "PUBG মোবাইল UC টপ-আপ",
                 json.dumps([
                     {"amount": "🔫 60 UC", "price": 120},
                     {"amount": "🔫 325 UC", "price": 600},
                     {"amount": "🔫 660 UC", "price": 1150},
                 ])),
                ("Netflix Premium", "subscribe", "🎬", "নেটফ্লিক্স প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎬 1 Month", "price": 200},
                     {"amount": "🎬 3 Months", "price": 500},
                     {"amount": "🎬 12 Months", "price": 1800},
                 ])),
                ("YouTube Premium", "subscribe", "▶️", "ইউটিউব প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "▶️ 1 Month", "price": 120},
                     {"amount": "▶️ 12 Months", "price": 1200},
                 ])),
                ("Spotify Premium", "subscribe", "🎵", "স্পটিফাই প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎵 1 Month", "price": 130},
                     {"amount": "🎵 3 Months", "price": 350},
                 ])),
                ("Crunchyroll Premium", "subscribe", "🎌", "ক্রাঞ্চিরোল প্রিমিয়াম সাবস্ক্রিপশন",
                 json.dumps([
                     {"amount": "🎌 1 Month", "price": 150},
                     {"amount": "🎌 3 Months", "price": 400},
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
    msg["Subject"] = "🔐 SKY TopUp — আপনার OTP ভেরিফিকেশন কোড"
    
    text_body = (
        f"আপনার SKY TopUp OTP কোড: {otp}\n\n"
        f"⏰ এই কোডটি {Config.OTP_VALID_MINUTES} মিনিটের জন্য বৈধ।\n"
        f"🔒 নিরাপত্তার জন্য কারো সাথে শেয়ার করবেন না।\n\n"
        f"— SKY TopUp টিম"
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
# 🎨 UI HELPERS
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🛒 প্রোডাক্ট কিনুন", callback_data="shop"),
             InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance")],
            [InlineKeyboardButton("📦 অর্ডার ট্র্যাক", callback_data="orders"),
             InlineKeyboardButton("➕ রিচার্জ", callback_data="recharge")],
            [InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile"),
             InlineKeyboardButton("⚙️ সেটিংস", callback_data="settings")],
            [InlineKeyboardButton("❓ হেল্প & সাপোর্ট", callback_data="help")],
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("🔧 এডমিন প্যানেল", callback_data="admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ ফিরে যান", callback_data=callback_data)]
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
            f"🌤️━━━ ✦ <b>SKY TopUp</b> ✦ ━━━🌤️\n\n"
            f"👋 <b>স্বাগতম, {UIBuilder.safe_text(user_row['name'])}!</b>\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"💳 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
            f"🏆 <b>র‍্যাংক:</b> {user_row['rank']}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"নিচের মেনু থেকে আপনার পছন্দের অপশন সিলেক্ট করুন 👇"
        )
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))
        return ConversationHandler.END
    
    welcome = (
        f"🌤️━━━ ✦ <b>SKY TopUp</b> ✦ ━━━🌤️\n\n"
        f"হ্যালো <b>{UIBuilder.safe_text(user.first_name or 'ভাই')}</b>! 👋\n\n"
        f"আমাদের প্রিমিয়াম সার্ভিস ব্যবহার করতে প্রথমে রেজিস্ট্রেশন করুন।\n\n"
        f"📌 <b>যা যা লাগবে:</b>\n"
        f"  ✅ একটি Gmail ইমেইল\n"
        f"  ✅ ইমেইল ভেরিফিকেশন\n"
        f"  ✅ একটি নিরাপদ পাসওয়ার্ড\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📧 <b>দয়া করে আপনার Gmail ইমেইল দিন:</b>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    return REG_EMAIL


async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    
    if not is_valid_email(email):
        await update.message.reply_text(
            "❌ <b>ভুল ইমেইল ফরম্যাট!</b>\n\n"
            "দয়া করে সঠিক Gmail ইমেইল দিন:\n"
            "উদাহরণ: <code>yourname@gmail.com</code>\n\n"
            "অথবা /cancel দিয়ে বাতিল করুন।",
            parse_mode=ParseMode.HTML,
        )
        return REG_EMAIL
    
    if get_user_by_email(email):
        await update.message.reply_text(
            "ℹ️ <b>ইমেইলটি ইতিমধ্যে রেজিস্টার করা আছে!</b>\n\n"
            "• /start দিয়ে আবার চেষ্টা করুন\n"
            "• অথবা সাপোর্ট টিমের সাথে যোগাযোগ করুন",
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
            f"📬━━━ ✦ <b>OTP পাঠানো হয়েছে</b> ✦ ━━━📬\n\n"
            f"✅ <code>{email}</code> এই ইমেইলে একটি ৬-সংখ্যার ভেরিফিকেশন কোড পাঠানো হয়েছে।\n\n"
            f"⏰ <b>মেয়াদ:</b> {Config.OTP_VALID_MINUTES} মিনিট\n"
            f"🔒 কোডটি কারো সাথে শেয়ার করবেন না!\n\n"
            f"কোডটি নিচে লিখুন 👇",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"⚠️ <b>ডেভেলপমেন্ট মোড</b>\n\n"
            f"📧 <b>ইমেইল:</b> <code>{email}</code>\n"
            f"🔑 <b>OTP কোড:</b> <code>{otp}</code>\n\n"
            f"⏰ এই কোড {Config.OTP_VALID_MINUTES} মিনিটের জন্য বৈধ।\n\n"
            f"⚠️ <b>প্রোডাকশন ওয়ার্নিং:</b>\n"
            f"SMTP_EMAIL এবং SMTP_PASSWORD সেট না থাকায় "
            f"যেকেউ যেকোনো ইমেইল দিয়ে রেজিস্টার করতে পারে!\n"
            f"প্রোডাকশনে দেওয়ার আগে অবশ্যই ইমেইল কনফিগার করুন।\n\n"
            f"কোডটি নিচে লিখুন 👇",
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
            "❌ <b>OTP পাওয়া যায়নি!</b>\n\nদয়া করে /start দিয়ে আবার শুরু করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    if row["expires_at"]:
        expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() > expires:
            await update.message.reply_text(
                "⌛ <b>OTP-এর মেয়াদ শেষ!</b>\n\n/start দিয়ে আবার চেষ্টা করুন।",
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
            "❌ <b>অনেকবার ভুল OTP!</b>\n\nনিরাপত্তার জন্য কোডটি ব্লক করা হয়েছে।\n/start দিয়ে আবার চেষ্টা করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    if entered_otp != row["otp_code"]:
        remaining = Config.MAX_OTP_ATTEMPTS - attempts
        await update.message.reply_text(
            f"❌ <b>ভুল OTP!</b>\n\nআর {remaining} বার চেষ্টা করতে পারবেন।\nআবার চেষ্টা করুন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_OTP
    
    with db() as conn:
        conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
    
    await update.message.reply_text(
        "✅━━━ ✦ <b>OTP সফলভাবে যাচাই!</b> ✦ ━━━✅\n\n"
        "এখন একটি <b>নিরাপদ পাসওয়ার্ড</b> সেট করুন:\n\n"
        f"🔐 <b>শর্ত:</b> ন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষর\n\n"
        "পাসওয়ার্ড লিখুন 👇",
        parse_mode=ParseMode.HTML,
    )
    return REG_PASSWORD


async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text(
            f"❌ <b>পাসওয়ার্ড খুব ছোট!</b>\n\nন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষর হতে হবে।\nআবার পাসওয়ার্ড দিন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_PASSWORD
    
    try:
        await update.message.delete()
    except Exception:
        pass
    
    context.user_data["reg_password"] = password
    await update.message.reply_text(
        "🔐 <b>পাসওয়ার্ড কনফার্মেশন</b>\n\nপাসওয়ার্ডটি আবার লিখুন 👇",
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
            "❌ <b>পাসওয়ার্ড মিলছে না!</b>\n\nআবার পাসওয়ার্ড দিন:",
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
            "❌ রেজিস্ট্রেশন ব্যর্থ! /start দিয়ে আবার চেষ্টা করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    context.user_data.clear()
    update_balance(telegram_id, 10.0)  # Welcome bonus
    
    await smart_reply(
        update,
        f"🎉━━━ ✦ <b>রেজিস্ট্রেশন সফল!</b> ✦ ━━━🎉\n\n"
        f"আপনার অ্যাকাউন্ট তৈরি হয়েছে!\n\n"
        f"👤 নাম: {UIBuilder.safe_text(name)}\n"
        f"📧 ইমেইল: <code>{email}</code>\n"
        f"💰 ওয়েলকাম বোনাস: ৳১০ 🎁\n\n"
        f"নিচের মেনু থেকে শুরু করুন 👇",
    )
    await show_main_menu_ui(update, context)
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await smart_reply(update, "❌ <b>প্রক্রিয়া বাতিল করা হয়েছে।</b>\n\n/start লিখুন।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🏠 MAIN MENU
# ──────────────────────────────────────────────────────────────────────────

async def show_main_menu_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await smart_reply(update, "⚠️ /start দিয়ে রেজিস্টার করুন।")
        return
    
    welcome = (
        f"🌤️━━━ ✦ <b>SKY TopUp</b> ✦ ━━━🌤️\n\n"
        f"👋 <b>স্বাগতম, {UIBuilder.safe_text(user_row['name'])}!</b>\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
        f"🏆 <b>র‍্যাংক:</b> {user_row['rank']}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"নিচের মেনু থেকে নির্বাচন করুন 👇"
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
        [InlineKeyboardButton("🎬 সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
    ]
    await edit_or_reply(
        update,
        "📂━━━ ✦ <b>প্রোডাক্ট ক্যাটাগরি</b> ✦ ━━━📂\n\nনিচ থেকে নির্বাচন করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute(
            "SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)
        ).fetchall()
    
    if not products:
        await edit_or_reply(update, "😕 <b>কোনো প্রোডাক্ট নেই!</b>", UIBuilder.back_button("back_shop"))
        return
    
    keyboard = [
        [InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")]
        for p in products
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])
    
    category_names = {"game": "🎮 গেম টপ-আপ", "subscribe": "🎬 সাবস্ক্রিপশন"}
    await edit_or_reply(
        update,
        f"📦━━━ ✦ <b>{category_names.get(category, category)}</b> ✦ ━━━📦\n\nপ্রোডাক্ট সিলেক্ট করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        await edit_or_reply(update, "❌ <b>প্রোডাক্ট পাওয়া যায়নি!</b>", UIBuilder.back_button("back_shop"))
        return
    
    options = json.loads(product["options"])
    keyboard = [
        [InlineKeyboardButton(f"{opt['amount']} — ৳{opt['price']:,}", callback_data=f"package_{product_id}_{idx}")]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])
    
    await edit_or_reply(
        update,
        f"📦━━━ ✦ <b>{product['name']}</b> ✦ ━━━📦\n\nপ্যাকেজ সিলেক্ট করুন 👇",
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
        await query.message.reply_text("❌ ভুল তথ্য!")
        return ConversationHandler.END
    
    _, product_id_str, package_idx_str = parts
    product_id, package_idx = int(product_id_str), int(package_idx_str)
    
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        await query.message.reply_text("❌ <b>প্রোডাক্ট পাওয়া যায়নি!</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    options = json.loads(product["options"])
    selected_package = options[package_idx]
    user_row = get_user(str(update.effective_user.id))
    
    if not user_row:
        await query.message.reply_text("⚠️ /start দিয়ে রেজিস্টার করুন।", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    price = selected_package["price"]
    if user_row["balance"] < price:
        await query.message.reply_text(
            f"❌ <b>পর্যাপ্ত ব্যালেন্স নেই!</b>\n\n"
            f"💰 আপনার ব্যালেন্স: ৳{user_row['balance']:,.2f}\n"
            f"💸 প্রয়োজন: ৳{price:,.2f}\n\n"
            f"➕ রিচার্জ করতে মেনু থেকে 'রিচার্জ' সিলেক্ট করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    
    await query.message.reply_text(
        f"🛒━━━ ✦ <b>অর্ডার কনফার্মেশন</b> ✦ ━━━🛒\n\n"
        f"📦 <b>প্রোডাক্ট:</b> {product['name']}\n"
        f"📎 <b>প্যাকেজ:</b> {selected_package['amount']}\n"
        f"💰 <b>মূল্য:</b> ৳{price:,.2f}\n\n"
        f"আপনার {product['name'].split()[0]} ID/ইউজারনেম/ইমেইল দিন\n"
        f"(অথবা /cancel দিয়ে বাতিল করুন):",
        parse_mode=ParseMode.HTML,
    )
    return ORDER_DETAILS_STATE


async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "order_product_name" not in context.user_data:
        await update.message.reply_text("❌ সেশন শেষ! /start দিয়ে শুরু করুন।")
        return ConversationHandler.END
    
    user_details = update.message.text.strip()
    if not user_details or len(user_details) < 3:
        await update.message.reply_text("❌ <b>ভালো করে লিখুন!</b>\n\nআবার দিন:", parse_mode=ParseMode.HTML)
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
        await update.message.reply_text("❌ অর্ডার ব্যর্থ! আবার চেষ্টা করুন।")
        return ConversationHandler.END
    
    context.user_data.clear()
    
    await update.message.reply_text(
        f"✅━━━ ✦ <b>অর্ডার সফল!</b> ✦ ━━━✅\n\n"
        f"🆔 <b>অর্ডার ID:</b> <code>{order_id}</code>\n"
        f"📦 <b>প্রোডাক্ট:</b> {product_name}\n"
        f"📎 <b>প্যাকেজ:</b> {package['amount']}\n"
        f"💰 <b>মূল্য:</b> ৳{price:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড:</b> +{reward} পয়েন্ট\n\n"
        f"⏳ আপনার অর্ডার প্রসেসিং হচ্ছে। ধন্যবাদ! 🎉",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["order_product_name", "order_package"]:
        context.user_data.pop(key, None)
    await update.message.reply_text("❌ অর্ডার বাতিল করা হয়েছে।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 💰 ACCOUNT SCREENS
# ──────────────────────────────────────────────────────────────────────────

async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ /start দিন।")
        return
    
    msg = (
        f"💰━━━ ✦ <b>আমার ব্যালেন্স</b> ✦ ━━━💰\n\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"💵 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']:,}\n"
        f"🏆 <b>র‍্যাংক:</b> {user_row['rank']}\n\n"
        f"➕ ব্যালেন্স যোগ করতে 'রিচার্জ' এ ক্লিক করুন 👇"
    )
    keyboard = [
        [InlineKeyboardButton("➕ রিচার্জ করুন", callback_data="recharge")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
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
            "📭 <b>কোনো অর্ডার নেই!</b>\n\n🛒 শপে গিয়ে অর্ডার করুন 👇",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 শপে যান", callback_data="shop")],
                [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
            ]),
        )
        return
    
    lines = ["📦━━━ ✦ <b>সর্বশেষ ১০টি অর্ডার</b> ✦ ━━━📦\n"]
    for o in orders:
        lines.append(
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 <code>{o['order_id']}</code>\n"
            f"  📦 {o['product_name']} - {o['package']}\n"
            f"  💰 ৳{o['price']:,.2f} | {o['status']}\n"
            f"  📅 {o['created_at']}"
        )
    await edit_or_reply(update, "\n".join(lines), UIBuilder.back_button("back_main"))


async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="recharge_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
    ]
    await edit_or_reply(
        update,
        "💰━━━ ✦ <b>ব্যালেন্স রিচার্জ</b> ✦ ━━━💰\n\nপেমেন্ট মেথড সিলেক্ট করুন 👇",
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
        f"💳━━━ ✦ <b>{method.title()} পেমেন্ট</b> ✦ ━━━💳\n\n"
        f"📌 নিচের নম্বরে টাকা পাঠান:\n"
        f"<code>{number}</code>\n\n"
        f"পেমেন্ট করার পর TrxID ও স্ক্রিনশট সাপোর্টে পাঠান।\n\n"
        f"👨‍💻 সাপোর্ট: @SkyTopUpSupport",
        UIBuilder.back_button("recharge"),
    )


async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ /start দিন।")
        return
    
    await edit_or_reply(
        update,
        f"👤━━━ ✦ <b>প্রোফাইল</b> ✦ ━━━👤\n\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 <b>ইমেইল:</b> <code>{user_row['email']}</code>\n"
        f"🏆 <b>র‍্যাংক:</b> {user_row['rank']}\n"
        f"💰 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
        f"📅 <b>যোগদান:</b> {user_row['created_at']}",
        UIBuilder.back_button("back_main"),
    )


async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(
        update,
        "⚙️━━━ ✦ <b>সেটিংস</b> ✦ ━━━⚙️\n\nশীঘ্রই আসছে:\n🔐 পাসওয়ার্ড পরিবর্তন\n🔔 নোটিফিকেশন\n🌐 ভাষা",
        UIBuilder.back_button("back_main"),
    )


async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(
        update,
        "❓━━━ ✦ <b>সাহায্য</b> ✦ ━━━❓\n\n"
        "📌 <b>কমান্ড:</b>\n  /start - মেনু\n  /cancel - বাতিল\n\n"
        "📌 যেকোনো সমস্যায় সাপোর্টে যোগাযোগ করুন:\n"
        "👨‍💻 @SkyTopUpSupport",
        UIBuilder.back_button("back_main"),
    )


async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not user_row or not is_admin(user_row):
        await edit_or_reply(update, "⛔ <b>অ্যাক্সেস নিষিদ্ধ!</b>", UIBuilder.back_button("back_main"))
        return
    
    with db() as conn:
        total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        pending_orders = conn.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = '⏳ Pending'").fetchone()["cnt"]
        total_revenue = conn.execute("SELECT COALESCE(SUM(price), 0) as total FROM orders").fetchone()["total"]
    
    await edit_or_reply(
        update,
        f"🔧━━━ ✦ <b>এডমিন প্যানেল</b> ✦ ━━━🔧\n\n"
        f"👥 মোট ইউজার: {total_users:,}\n"
        f"⏳ পেন্ডিং অর্ডার: {pending_orders:,}\n"
        f"💰 মোট আয়: ৳{total_revenue:,.2f}",
        UIBuilder.back_button("back_main"),
    )


# ──────────────────────────────────────────────────────────────────────────
# 🚀 MAIN
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
    
    logger.info("🌟 Sky TopUp Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
