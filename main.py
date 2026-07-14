#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v2.0 (Enhanced)
─────────────────────────────────────────
A production-ready Telegram bot for:
  • User registration with email OTP verification
  • Product catalog & ordering
  • Balance & reward point management
  • Admin panel

Author: HackerAI Enhanced Edition
License: MIT
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
from typing import Optional, Dict, List, Any

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
    
    # Database
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    
    # Feature flags
    EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)
    DEV_MODE = not EMAIL_SENDING_ENABLED
    
    # Admin: first registered user gets admin privileges
    ADMIN_USER_ID = 1  # SQLite row ID

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
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
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
    """Initialize all database tables with proper indexes."""
    with db() as conn:
        c = conn.cursor()
        
        # ── Users table ──
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_telegram ON users(telegram_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        
        # ── OTP codes table ──
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_otp_telegram ON otp_codes(telegram_id)")
        
        # ── Orders table ──
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_telegram ON orders(telegram_id)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)")
        
        # ── Products table ──
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
        
        # ── Seed default products if empty ──
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


# ── Database access helpers ──

def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    """Get user by Telegram ID."""
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    """Get user by email address."""
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def update_balance(telegram_id: str, amount: float) -> None:
    """Update user balance (positive for credit, negative for debit)."""
    with db() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )


def update_last_login(telegram_id: str) -> None:
    """Update user's last login timestamp."""
    with db() as conn:
        conn.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?",
            (telegram_id,),
        )


# ──────────────────────────────────────────────────────────────────────────
# 🔐 SECURITY HELPERS
# ──────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    """
    Hash password using SHA-256 with a salt prefix.
    
    ⚠️ NOTE: For production, use bcrypt or argon2 via passlib library.
    This SHA-256 approach is used to avoid extra dependencies.
    
    To upgrade: `pip install passlib[bcrypt]` and replace this function.
    """
    salt = "SKY_TOPUP_2024_v2"  # Pepper — keep this secret in production!
    return hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(plain_password) == hashed_password


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))


def is_admin(user_row) -> bool:
    """Check if user is admin (first registered user or is_admin flag)."""
    return user_row and (user_row["id"] == Config.ADMIN_USER_ID or user_row["is_admin"] == 1)


# ──────────────────────────────────────────────────────────────────────────
# 📧 EMAIL SERVICE
# ──────────────────────────────────────────────────────────────────────────

def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Send OTP verification email via SMTP.
    
    Returns:
        True if email sent successfully, False otherwise.
    
    In DEV_MODE, returns True but logs the OTP instead of sending.
    """
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
    
    # Plain text version
    text_body = (
        f"আপনার SKY TopUp OTP কোড: {otp}\n\n"
        f"⏰ এই কোডটি {Config.OTP_VALID_MINUTES} মিনিটের জন্য বৈধ।\n"
        f"🔒 নিরাপত্তার জন্য কারো সাথে শেয়ার করবেন না।\n\n"
        f"— SKY TopUp টিম"
    )
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    
    # HTML version (nicer for email clients)
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5;">
        <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <div style="text-align: center;">
                <h1 style="color: #1a73e8;">🌤️ SKY TopUp</h1>
                <h2 style="color: #333;">ইমেইল ভেরিফিকেশন</h2>
            </div>
            <div style="background: #f0f7ff; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                <p style="font-size: 14px; color: #666;">আপনার OTP কোড:</p>
                <p style="font-size: 36px; font-weight: bold; letter-spacing: 8px; color: #1a73e8;">{otp}</p>
                <p style="font-size: 12px; color: #999;">এই কোড {Config.OTP_VALID_MINUTES} মিনিটের জন্য বৈধ</p>
            </div>
            <p style="color: #666; font-size: 13px;">
                ⚠️ <strong>নিরাপত্তা সতর্কতা:</strong> এই কোড কারো সাথে শেয়ার করবেন না। 
                SKY TopUp কখনোই আপনার OTP চেয়ে ইমেইল বা ফোন করবে না।
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="color: #999; font-size: 12px; text-align: center;">
                © 2024 SKY TopUp — সকল অধিকার সংরক্ষিত
            </p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, to_email, msg.as_string())
        logger.info("✅ OTP email sent to %s", to_email)
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("❌ SMTP Authentication failed — check SMTP_EMAIL/SMTP_PASSWORD")
        return False
    except smtplib.SMTPException as e:
        logger.error("❌ SMTP error for %s: %s", to_email, e)
        return False
    except Exception as e:
        logger.error("❌ Failed to send OTP email to %s: %s", to_email, e)
        return False


# ──────────────────────────────────────────────────────────────────────────
# 🎨 UI HELPERS
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    """Build beautiful Telegram UI components."""
    
    @staticmethod
    def safe_text(text: str) -> str:
        """Escape HTML entities for Telegram."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        """Build the main navigation menu."""
        keyboard = [
            [
                InlineKeyboardButton("🛒 প্রোডাক্ট কিনুন", callback_data="shop"),
                InlineKeyboardButton("💰 ব্যালেন্স", callback_data="balance"),
            ],
            [
                InlineKeyboardButton("📦 অর্ডার ট্র্যাক", callback_data="orders"),
                InlineKeyboardButton("➕ রিচার্জ", callback_data="recharge"),
            ],
            [
                InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile"),
                InlineKeyboardButton("⚙️ সেটিংস", callback_data="settings"),
            ],
            [InlineKeyboardButton("❓ হেল্প & সাপোর্ট", callback_data="help")],
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("🔧 এডমিন প্যানেল", callback_data="admin")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        """Standard back button."""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ ফিরে যান", callback_data=callback_data)]
        ])
    
    @staticmethod
    def welcome_message(user_name: str, balance: float, rank: str) -> str:
        """Generate a beautiful welcome/home message."""
        return (
            f"🌤️━━━ ✦ <b>SKY TopUp</b> ✦ ━━━🌤️\n\n"
            f"👋 <b>স্বাগতম, {UIBuilder.safe_text(user_name)}!</b>\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"💳 <b>ব্যালেন্স:</b> ৳{balance:,.2f}\n"
            f"🏆 <b>র‍্যাংক:</b> {rank}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"নিচের মেনু থেকে আপনার পছন্দের অপশন সিলেক্ট করুন 👇"
        )
    
    @staticmethod
    def order_status_emoji(status: str) -> str:
        """Get emoji for order status."""
        emojis = {
            "⏳ Pending": "⏳",
            "🔄 Processing": "🔄",
            "✅ Completed": "✅",
            "❌ Cancelled": "❌",
            "⚠️ Failed": "⚠️",
        }
        return emojis.get(status, "📋")


# ──────────────────────────────────────────────────────────────────────────
# 📨 MESSAGING HELPERS
# ──────────────────────────────────────────────────────────────────────────

async def smart_reply(update: Update, text: str, reply_markup=None):
    """
    Send a reply that works with both normal messages and callback queries.
    
    This is the universal message sender — use it everywhere.
    """
    kwargs = {
        "text": text,
        "parse_mode": ParseMode.HTML,
        "reply_markup": reply_markup,
    }
    
    if update.callback_query:
        await update.callback_query.message.reply_text(**kwargs)
    elif update.message:
        await update.message.reply_text(**kwargs)
    else:
        logger.warning("⚠️ smart_reply: no message or callback_query found")


async def edit_or_reply(update: Update, text: str, reply_markup=None):
    """
    Edit existing message if it's a callback, otherwise send new message.
    This keeps the chat clean without duplicate messages.
    """
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
            # If edit fails (e.g., message too old), send new message
            pass
    
    await smart_reply(update, text, reply_markup)


# ──────────────────────────────────────────────────────────────────────────
# 👤 REGISTRATION FLOW
# ──────────────────────────────────────────────────────────────────────────

# Conversation states
(
    REG_EMAIL,
    REG_OTP,
    REG_PASSWORD,
    REG_CONFIRM_PASSWORD,
) = range(4)

ORDER_DETAILS_STATE = 100


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command — either show menu or start registration."""
    user = update.effective_user
    existing = get_user(str(user.id))
    
    if existing:
        update_last_login(str(user.id))
        await show_main_menu_ui(update, context)
        return ConversationHandler.END
    
    # Registration welcome
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
    """Receive and validate email address."""
    email = update.message.text.strip().lower()
    
    # Validation
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
            "আপনি কি আগেই রেজিস্ট্রেশন করেছিলেন?\n"
            "• /start দিয়ে আবার চেষ্টা করুন\n"
            "• অথবা সাপোর্ট টিমের সাথে যোগাযোগ করুন",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Generate and store OTP
    otp = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=Config.OTP_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    
    with db() as conn:
        # Clear any stale OTPs
        conn.execute(
            "DELETE FROM otp_codes WHERE telegram_id = ?",
            (str(update.effective_user.id),),
        )
        conn.execute(
            "INSERT INTO otp_codes (telegram_id, otp_code, expires_at) VALUES (?, ?, ?)",
            (str(update.effective_user.id), otp, expires_at),
        )
    
    context.user_data["reg_email"] = email
    
    # Send OTP
    sent = send_otp_email(email, otp)
    
    if sent and not Config.DEV_MODE:
        await update.message.reply_text(
            f"📬━━━ ✦ <b>OTP পাঠানো হয়েছে</b> ✦ ━━━📬\n\n"
            f"✅ <code>{email}</code> এই ইমেইলে একটি ৬-সংখ্যার ভেরিফিকেশন কোড পাঠানো হয়েছে।\n\n"
            f"⏰ <b>মেয়াদ:</b> {Config.OTP_VALID_MINUTES} মিনিট\n"
            f"🔒 কোডটি কারো সাথে শেয়ার করবেন না!\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"কোডটি নিচে লিখুন 👇",
            parse_mode=ParseMode.HTML,
        )
    else:
        # DEV MODE — show OTP directly
        await update.message.reply_text(
            f"⚠️━━━ ✦ <b>ডেভেলপমেন্ট মোড</b> ✦ ━━━⚠️\n\n"
            f"📧 <b>ইমেইল:</b> <code>{email}</code>\n"
            f"🔑 <b>OTP কোড:</b> <code>{otp}</code>\n\n"
            f"⏰ এই কোড {Config.OTP_VALID_MINUTES} মিনিটের জন্য বৈধ।\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"⚠️ <b>প্রোডাকশন ওয়ার্নিং:</b>\n"
            f"SMTP_EMAIL এবং SMTP_PASSWORD সেট না থাকায় "
            f"যেকেউ যেকোনো ইমেইল দিয়ে রেজিস্টার করতে পারে!\n"
            f"প্রোডাকশনে দেওয়ার আগে অবশ্যই ইমেইল কনফিগার করুন।\n\n"
            f"কোডটি নিচে লিখুন 👇",
            parse_mode=ParseMode.HTML,
        )
    
    return REG_OTP


async def reg_receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate OTP code."""
    entered_otp = update.message.text.strip()
    telegram_id = str(update.effective_user.id)
    
    with db() as conn:
        row = conn.execute(
            """SELECT otp_code, expires_at, attempt_count 
               FROM otp_codes 
               WHERE telegram_id = ? AND is_used = 0
               ORDER BY created_at DESC LIMIT 1""",
            (telegram_id,),
        ).fetchone()
    
    if not row:
        await update.message.reply_text(
            "❌ <b>OTP পাওয়া যায়নি!</b>\n\n"
            "দয়া করে /start দিয়ে আবার শুরু করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Check expiry
    if row["expires_at"]:
        expires = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
        if datetime.utcnow() > expires:
            await update.message.reply_text(
                "⌛ <b>OTP-এর মেয়াদ শেষ!</b>\n\n"
                "দয়া করে /start দিয়ে আবার চেষ্টা করুন।",
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END
    
    # Check attempts
    attempts = row["attempt_count"] + 1
    with db() as conn:
        conn.execute(
            "UPDATE otp_codes SET attempt_count = ? WHERE id = ?",
            (attempts, row["id"]),
        )
    
    if attempts > Config.MAX_OTP_ATTEMPTS:
        with db() as conn:
            conn.execute(
                "UPDATE otp_codes SET is_used = 1 WHERE id = ?",
                (row["id"],),
            )
        await update.message.reply_text(
            "❌ <b>অনেকবার ভুল OTP!</b>\n\n"
            "নিরাপত্তার জন্য কোডটি ব্লক করা হয়েছে।\n"
            "/start দিয়ে আবার চেষ্টা করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    if entered_otp != row["otp_code"]:
        remaining = Config.MAX_OTP_ATTEMPTS - attempts
        await update.message.reply_text(
            f"❌ <b>ভুল OTP!</b>\n\n"
            f"আর {remaining} বার চেষ্টা করতে পারবেন।\n"
            f"আবার চেষ্টা করুন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_OTP
    
    # OTP verified successfully
    with db() as conn:
        conn.execute(
            "UPDATE otp_codes SET is_used = 1 WHERE id = ?",
            (row["id"],),
        )
    
    await update.message.reply_text(
        "✅━━━ ✦ <b>OTP সফলভাবে যাচাই!</b> ✦ ━━━✅\n\n"
        "আপনার ইমেইল কনফার্ম করা হয়েছে। 🎉\n\n"
        "এখন একটি <b>নিরাপদ পাসওয়ার্ড</b> সেট করুন:\n\n"
        f"🔐 <b>শর্ত:</b> ন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষর\n"
        "🔐 পাসওয়ার্ডে অক্ষর, সংখ্যা এবং স্পেশাল ক্যারেক্টার ব্যবহার করুন\n\n"
        "পাসওয়ার্ড লিখুন 👇",
        parse_mode=ParseMode.HTML,
    )
    return REG_PASSWORD


async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate password."""
    password = update.message.text.strip()
    
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text(
            f"❌ <b>পাসওয়ার্ড খুব ছোট!</b>\n\n"
            f"ন্যূনতম {Config.MIN_PASSWORD_LENGTH} অক্ষর হতে হবে।\n"
            f"আবার একটি পাসওয়ার্ড দিন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_PASSWORD
    
    # Check password strength
    if not any(c.isupper() for c in password) and len(password) < 8:
        # Warning but don't block
        pass
    
    # Delete the password message for privacy (Telegram keeps it but removes from UI)
    try:
        await update.message.delete()
    except Exception:
        pass  # Gracefully handle if message can't be deleted
    
    context.user_data["reg_password"] = password
    
    await update.message.reply_text(
        "🔐 <b>পাসওয়ার্ড কনফার্মেশন</b>\n\n"
        "নিরাপত্তার জন্য পাসওয়ার্ডটি আবার লিখুন 👇",
        parse_mode=ParseMode.HTML,
    )
    return REG_CONFIRM_PASSWORD


async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm password matches and complete registration."""
    confirm_pass = update.message.text.strip()
    password = context.user_data.get("reg_password")
    
    # Delete password message
    try:
        await update.message.delete()
    except Exception:
        pass
    
    if confirm_pass != password:
        await update.message.reply_text(
            "❌ <b>পাসওয়ার্ড মিলছে না!</b>\n\n"
            "আবার একটি পাসওয়ার্ড দিন:",
            parse_mode=ParseMode.HTML,
        )
        return REG_PASSWORD
    
    # Save user to database
    email = context.user_data.get("reg_email", "")
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.first_name or update.effective_user.username or "User"
    
    try:
        with db() as conn:
            conn.execute(
                """INSERT INTO users 
                   (telegram_id, email, password, name) 
                   VALUES (?, ?, ?, ?)""",
                (telegram_id, email, hash_password(password), name),
            )
        logger.info("✅ New user registered: %s (%s)", telegram_id, email)
    except sqlite3.IntegrityError as e:
        logger.error("❌ Registration failed (duplicate): %s", e)
        await update.message.reply_text(
            "❌ <b>রেজিস্ট্রেশন ব্যর্থ!</b>\n\n"
            "এই অ্যাকাউন্ট বা ইমেইল আগে থেকে রেজিস্টার করা আছে।\n"
            "/start দিয়ে আবার চেষ্টা করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Clean up
    context.user_data.clear()
    
    # Success message
    success_msg = (
        f"🎉━━━ ✦ <b>রেজিস্ট্রেশন সফল!</b> ✦ ━━━🎉\n\n"
        f"আপনার অ্যাকাউন্ট তৈরি হয়েছে!\n\n"
        f"📋 <b>আপনার তথ্য:</b>\n"
        f"  👤 নাম: {UIBuilder.safe_text(name)}\n"
        f"  📧 ইমেইল: <code>{email}</code>\n"
        f"  💰 বোনাস: ৳১০ (নতুন ইউজার welcome bonus 🎁)\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"এখন আপনি আমাদের সকল সার্ভিস ব্যবহার করতে পারবেন!\n"
        f"নিচের মেনু থেকে শুরু করুন 👇"
    )
    
    # Give welcome bonus
    update_balance(telegram_id, 10.0)
    
    await smart_reply(update, success_msg)
    await show_main_menu_ui(update, context)
    return ConversationHandler.END


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any ongoing conversation."""
    context.user_data.clear()
    await smart_reply(
        update,
        "❌ <b>প্রক্রিয়া বাতিল করা হয়েছে।</b>\n\n"
        "আবার শুরু করতে /start লিখুন।",
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🏠 MAIN MENU UI
# ──────────────────────────────────────────────────────────────────────────

async def show_main_menu_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main menu to the user."""
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await smart_reply(update, "⚠️ দয়া করে প্রথমে /start দিয়ে রেজিস্টার করুন।")
        return
    
    welcome = UIBuilder.welcome_message(
        user_row["name"],
        user_row["balance"],
        user_row["rank"],
    )
    
    if update.callback_query:
        await edit_or_reply(update, welcome, UIBuilder.main_menu(user_row))
    else:
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))


# ──────────────────────────────────────────────────────────────────────────
# 🔄 CALLBACK ROUTER
# ──────────────────────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to appropriate handlers."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    # Route map
    routes = {
        "back_main": lambda u, c: show_main_menu_ui(u, c),
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
        category = data.replace("category_", "")
        await show_products_ui(update, context, category)
    elif data.startswith("product_"):
        product_id = int(data.replace("product_", ""))
        await select_package_ui(update, context, product_id)
    elif data.startswith("recharge_"):
        method = data.replace("recharge_", "")
        await show_recharge_instructions_ui(update, context, method)
    else:
        logger.warning("Unknown callback data: %s", data)


# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOP — CATEGORIES & PRODUCTS
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product categories."""
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🎬 সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
    ]
    await edit_or_reply(
        update,
        "📂━━━ ✦ <b>প্রোডাক্ট ক্যাটাগরি</b> ✦ ━━━📂\n\n"
        "নিচ থেকে আপনার পছন্দের ক্যাটাগরি নির্বাচন করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    """Show products for a given category."""
    with db() as conn:
        products = conn.execute(
            "SELECT * FROM products WHERE category = ? AND is_active = 1",
            (category,),
        ).fetchall()
    
    if not products:
        await edit_or_reply(
            update,
            "😕 <b>এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই!</b>\n\n"
            "শীঘ্রই নতুন প্রোডাক্ট যোগ করা হবে। আপডেটের জন্য চোখ রাখুন! 👀",
            UIBuilder.back_button("back_shop"),
        )
        return
    
    keyboard = [
        [InlineKeyboardButton(
            f"{p['icon']} {p['name']}",
            callback_data=f"product_{p['id']}",
        )]
        for p in products
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])
    
    category_names = {"game": "🎮 গেম টপ-আপ", "subscribe": "🎬 সাবস্ক্রিপশন"}
    await edit_or_reply(
        update,
        f"📦━━━ ✦ <b>{category_names.get(category, category)}</b> ✦ ━━━📦\n\n"
        f"নিচ থেকে প্রোডাক্ট সিলেক্ট করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Show available packages for a product."""
    with db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
    
    if not product:
        await edit_or_reply(
            update,
            "❌ <b>প্রোডাক্ট পাওয়া যায়নি!</b>",
            UIBuilder.back_button("back_shop"),
        )
        return
    
    try:
        options = json.loads(product["options"])
    except (json.JSONDecodeError, TypeError) as e:
        logger.error("Invalid product options for %s: %s", product["name"], e)
        await edit_or_reply(
            update,
            "❌ <b>প্রোডাক্ট কনফিগারেশন ত্রুটিপূর্ণ!</b>\n\n"
            "অনুগ্রহ করে অ্যাডমিনকে জানান।",
            UIBuilder.back_button("back_shop"),
        )
        return
    
    keyboard = [
        [InlineKeyboardButton(
            f"{opt['amount']} — ৳{opt['price']:,}",
            callback_data=f"package_{product_id}_{idx}",
        )]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])
    
    product_desc = product.get("description", "")
    desc_section = f"\n📝 <b>বিবরণ:</b> {product_desc}\n" if product_desc else "\n"
    
    await edit_or_reply(
        update,
        f"📦━━━ ✦ <b>{product['name']}</b> ✦ ━━━📦\n{desc_section}\n"
        f"নিচ থেকে প্যাকেজ সিলেক্ট করুন 👇",
        InlineKeyboardMarkup(keyboard),
    )


# ──────────────────────────────────────────────────────────────────────────
# 📋 ORDER FLOW
# ──────────────────────────────────────────────────────────────────────────

async def package_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle package selection and start order flow."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    if len(parts) != 3:
        await query.message.reply_text("❌ ভুল প্যাকেজ তথ্য!")
        return ConversationHandler.END
    
    _, product_id_str, package_idx_str = parts
    product_id = int(product_id_str)
    package_idx = int(package_idx_str)
    
    # Fetch product
    with db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()
    
    if not product:
        await query.message.reply_text("❌ <b>প্রোডাক্ট পাওয়া যায়নি!</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    try:
        options = json.loads(product["options"])
        selected_package = options[package_idx]
    except (IndexError, json.JSONDecodeError, TypeError):
        await query.message.reply_text("❌ <b>প্যাকেজ তথ্য ত্রুটিপূর্ণ!</b>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    
    # Check user and balance
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await query.message.reply_text(
            "দয়া করে প্রথমে /start দিয়ে রেজিস্টার করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    price = selected_package["price"]
    if user_row["balance"] < price:
        await query.message.reply_text(
            f"❌ <b>পর্যাপ্ত ব্যালেন্স নেই!</b>\n\n"
            f"💰 <b>আপনার ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
            f"💸 <b>প্রয়োজন:</b> ৳{price:,.2f}\n"
            f"📉 <b>ঘাটতি:</b> ৳{(price - user_row['balance']):,.2f}\n\n"
            f"➕ ব্যালেন্স যোগ করতে মেনু থেকে 'রিচার্জ' সিলেক্ট করুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Store order info in context
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    context.user_data["order_product_id"] = product_id
    
    await query.message.reply_text(
        f"🛒━━━ ✦ <b>অর্ডার কনফার্মেশন</b> ✦ ━━━🛒\n\n"
        f"📦 <b>প্রোডাক্ট:</b> {product['name']}\n"
        f"📎 <b>প্যাকেজ:</b> {selected_package['amount']}\n"
        f"💰 <b>মূল্য:</b> ৳{price:,.2f}\n"
        f"💳 <b>ব্যালেন্সের পর:</b> ৳{(user_row['balance'] - price):,.2f}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📝 নিচে আপনার {product['name'].split()[0]} ID/ইউজারনেম/ইমেইল দিন:\n\n"
        f"(অথবা /cancel লিখে বাতিল করুন)",
        parse_mode=ParseMode.HTML,
    )
    return ORDER_DETAILS_STATE


async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive user details and complete the order."""
    if "order_product_name" not in context.user_data:
        await update.message.reply_text("❌ অর্ডার সেশন শেষ হয়ে গেছে। /start দিয়ে আবার শুরু করুন।")
        return ConversationHandler.END
    
    user_details = update.message.text.strip()
    if not user_details or len(user_details) < 3:
        await update.message.reply_text(
            "❌ <b>ভালো করে লিখুন!</b>\n\n"
            "আপনার গেমার ID, ইউজারনেম বা ইমেইল দিন:",
            parse_mode=ParseMode.HTML,
        )
        return ORDER_DETAILS_STATE
    
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    
    telegram_id = str(update.effective_user.id)
    
    # Generate order ID
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(2).upper()
    order_id = f"SKY-{timestamp}-{random_suffix}"
    
    try:
        with db() as conn:
            # Create order
            conn.execute(
                """INSERT INTO orders 
                   (order_id, telegram_id, product_name, package, price, user_details, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, telegram_id, product_name, package["amount"], price, user_details, "⏳ Pending"),
            )
            # Deduct balance
            conn.execute(
                "UPDATE users SET balance = balance - ? WHERE telegram_id = ?",
                (price, telegram_id),
            )
            # Add reward points (10% of price)
            reward = int(price) // 10
            conn.execute(
                "UPDATE users SET reward_points = reward_points + ? WHERE telegram_id = ?",
                (reward, telegram_id),
            )
    except sqlite3.Error as e:
        logger.error("❌ Order creation failed: %s", e)
        await update.message.reply_text(
            "❌ <b>অর্ডার তৈরি করতে সমস্যা হয়েছে!</b>\n\n"
            "অনুগ্রহ করে কিছুক্ষণ পর চেষ্টা করুন বা সাপোর্টে জানান।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END
    
    # Clear order session data (keep other context)
    context.user_data.pop("order_product_name", None)
    context.user_data.pop("order_package", None)
    context.user_data.pop("order_product_id", None)
    
    # Success message
    success_msg = (
        f"✅━━━ ✦ <b>অর্ডার সফল!</b> ✦ ━━━✅\n\n"
        f"🆔 <b>অর্ডার ID:</b> <code>{order_id}</code>\n"
        f"📦 <b>প্রোডাক্ট:</b> {product_name}\n"
        f"📎 <b>প্যাকেজ:</b> {package['amount']}\n"
        f"💰 <b>মূল্য:</b> ৳{price:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> +{reward}\n\n"
        f"📌 <b>আপনার দেওয়া তথ্য:</b> {UIBuilder.safe_text(user_details)}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⏳ আপনার অর্ডারটি প্রসেস করা হচ্ছে।\n"
        f"সম্পূর্ণ হলে নোটিফিকেশন পাঠানো হবে। 🎉\n\n"
        f"ধন্যবাদ আমাদের সাথে থাকার জন্য! 🙏"
    )
    
    await update.message.reply_text(success_msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cancel_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel order flow."""
    for key in ["order_product_name", "order_package", "order_product_id"]:
        context.user_data.pop(key, None)
    
    await update.message.reply_text(
        "❌ <b>অর্ডার বাতিল করা হয়েছে।</b>\n\n"
        "প্রধান মেনুতে ফিরে যেতে /start লিখুন।",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 💰 ACCOUNT SCREENS
# ──────────────────────────────────────────────────────────────────────────

async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance and rewards."""
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ দয়া করে /start দিয়ে রেজিস্টার করুন।")
        return
    
    # Calculate rank progress (simplified)
    balance = user_row["balance"]
    if balance >= 5000:
        rank_emoji = "👑 Platinum"
    elif balance >= 2000:
        rank_emoji = "🥈 Gold"
    elif balance >= 500:
        rank_emoji = "🥉 Silver"
    else:
        rank_emoji = "🪙 Bronze"
    
    # Next rank info
    if rank_emoji == "🪙 Bronze":
        next_rank = "🥉 Silver (৳৫০০)"
        next_rank_progress = min(100, int((balance / 500) * 100))
    elif rank_emoji == "🥉 Silver":
        next_rank = "🥈 Gold (৳২,০০০)"
        next_rank_progress = min(100, int(((balance - 500) / 1500) * 100))
    elif rank_emoji == "🥈 Gold":
        next_rank = "👑 Platinum (৳৫,০০০)"
        next_rank_progress = min(100, int(((balance - 2000) / 3000) * 100))
    else:
        next_rank = "🏆 MAX LEVEL"
        next_rank_progress = 100
    
    # Progress bar
    filled = "▓" * (next_rank_progress // 10)
    empty = "░" * (10 - next_rank_progress // 10)
    progress_bar = f"{filled}{empty}"
    
    msg = (
        f"💰━━━ ✦ <b>আমার ব্যালেন্স</b> ✦ ━━━💰\n\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 <b>ইমেইল:</b> <code>{user_row['email']}</code>\n\n"
        f"💵 <b>ব্যালেন্স:</b> ৳{balance:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']:,}\n"
        f"🏆 <b>কর্তৃক র‍্যাংক:</b> {rank_emoji}\n\n"
        f"📊 <b>র‍্যাংক প্রোগ্রেস:</b>\n"
        f"  {progress_bar} {next_rank_progress}%\n"
        f"  পরবর্তী: {next_rank}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"➕ ব্যালেন্স যোগ করতে 'রিচার্জ' এ ক্লিক করুন 👇"
    )
    
    keyboard = [
        [InlineKeyboardButton("➕ রিচার্জ করুন", callback_data="recharge")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
    ]
    
    await edit_or_reply(update, msg, InlineKeyboardMarkup(keyboard))


async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's recent orders."""
    with db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 10",
            (str(update.effective_user.id),),
        ).fetchall()
    
    if not orders:
        await edit_or_reply(
            update,
            "📭━━━ ✦ <b>আমার অর্ডার</b> ✦ ━━━📭\n\n"
            "আপনার কোনো অর্ডার নেই!\n\n"
            "🛒 নতুন অর্ডার করতে 'শপ' এ যান 👇",
            InlineKeyboardMarkup([
                [InlineKeyboardButton("🛒 শপে যান", callback_data="shop")],
                [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
            ]),
        )
        return
    
    lines = ["📦━━━ ✦ <b>আমার সর্বশেষ ১০টি অর্ডার</b> ✦ ━━━📦\n"]
    for o in orders:
        emoji = UIBuilder.order_status_emoji(o["status"])
        lines.append(
            f"━━━━━━━━━━━━━━━━\n"
            f"{emoji} <code>{o['order_id']}</code>\n"
            f"  📦 <b>{o['product_name']}</b>\n"
            f"  📎 {o['package']}\n"
            f"  💰 ৳{o['price']:,.2f}\n"
            f"  📊 স্ট্যাটাস: {o['status']}\n"
            f"  📅 {o['created_at']}"
        )
    lines.append("\n━━━━━━━━━━━━━━━━")
    
    await edit_or_reply(
        update,
        "\n".join(lines),
        UIBuilder.back_button("back_main"),
    )


async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show recharge/payment method selection."""
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="recharge_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ মেইন মেনু", callback_data="back_main")],
    ]
    await edit_or_reply(
        update,
        "💰━━━ ✦ <b>ব্যালেন্স রিচার্জ</b> ✦ ━━━💰\n\n"
        "আপনার পছন্দের পেমেন্ট মেথড সিলেক্ট করুন 👇\n\n"
        "⚡ <i>মিনিমাম রিচার্জ: ৳৫০</i>\n"
        "⚡ <i>পেমেন্ট কনফার্ম হতে ৫-১০ মিনিট সময় লাগতে পারে</i>",
        InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML,
    )


async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    """Show payment instructions for a specific method."""
    numbers = {
        "bkash": Config.BKASH_NUMBER,
        "nagad": Config.NAGAD_NUMBER,
        "rocket": Config.ROCKET_NUMBER,
    }
    
    number = numbers.get(method, "01XXXXXXXXX")
    method_name = method.title()
    
    instructions = (
        f"💳━━━ ✦ <b>{method_name} পেমেন্ট</b> ✦ ━━━💳\n\n"
        f"📌 <b>নির্দেশিকা:</b>\n\n"
        f"1️⃣ নিচের নম্বরে টাকা পাঠান:\n"
        f"   <code>{number}</code>\n\n"
        f"2️⃣ পেমেন্ট করার পর নিচের তথ্য আমাদের সাপোর্টে পাঠান:\n"
        f"   • ট্রানজেকশন ID (TrxID)\n"
        f"   • যে পরিমাণ টাকা পাঠিয়েছেন\n"
        f"   • পেমেন্টের স্ক্রিনশট\n\n"
        f"3️⃣ আমরা ম্যানুয়ালি যাচাই করে ৫-১০ মিনিটের মধ্যে ব্যালেন্স যোগ করে দেব।\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👨‍💻 <b>সাপোর্ট:</b> @SkyTopUpSupport (অথবা মেনু থেকে 'হেল্প' সিলেক্ট করুন)\n\n"
        f"⚠️ <i>প্রতারণা থেকে সাবধান! শুধুমাত্র উপরের অফিসিয়াল নম্বরেই পেমেন্ট করুন।</i>"
    )
    
    keyboard = [
        [InlineKeyboardButton("👨‍💻 সাপোর্টে যোগাযোগ", callback_data="help")],
        [InlineKeyboardButton("⬅️ রিচার্জ মেনু", callback_data="recharge")],
    ]
    
    await edit_or_reply(update, instructions, InlineKeyboardMarkup(keyboard))


async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile."""
    user_row = get_user(str(update.effective_user.id))
    if not user_row:
        await edit_or_reply(update, "⚠️ দয়া করে /start দিয়ে রেজিস্টার করুন।")
        return
    
    msg = (
        f"👤━━━ ✦ <b>আমার প্রোফাইল</b> ✦ ━━━👤\n\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_row['telegram_id']}</code>\n"
        f"👤 <b>নাম:</b> {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 <b>ইমেইল:</b> <code>{user_row['email']}</code>\n"
        f"🏆 <b>র‍্যাংক:</b> {user_row['rank']}\n"
        f"💰 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
        f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']:,}\n"
        f"📅 <b>যোগদান:</b> {user_row['created_at']}\n"
        f"🔐 <b>অ্যাকাউন্ট:</b> {'✅ সক্রিয়' if user_row['is_active'] else '❌ নিষ্ক্রিয়'}"
    )
    
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))


async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    msg = (
        f"⚙️━━━ ✦ <b>সেটিংস</b> ✦ ━━━⚙️\n\n"
        f"শীঘ্রই আসছে:\n"
        f"  🔐 পাসওয়ার্ড পরিবর্তন\n"
        f"  🔔 নোটিফিকেশন সেটিংস\n"
        f"  🌐 ভাষা পরিবর্তন\n"
        f"  🗑️ অ্যাকাউন্ট ডিলিট\n\n"
        f"আপডেটের জন্য চোখ রাখুন! 👀"
    )
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))


async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help and support information."""
    msg = (
        f"❓━━━ ✦ <b>সাহায্য ও সাপোর্ট</b> ✦ ━━━❓\n\n"
        f"📌 <b>কমান্ড লিস্ট:</b>\n"
        f"  /start — বট শুরু করুন / মেনু দেখুন\n"
        f"  /cancel — চলমান প্রক্রিয়া বাতিল করুন\n\n"
        f"📌 <b>সাধারণ জিজ্ঞাসা:</b>\n"
        f"  ❓ অর্ডার করতে → 'শপ' এ যান\n"
        f"  ❓ ব্যালেন্স চেক → 'ব্যালেন্স' এ ক্লিক করুন\n"
        f"  ❓ রিচার্জ → 'রিচার্জ' সিলেক্ট করুন\n"
        f"  ❓ অর্ডার ট্র্যাক → 'অর্ডার' সিলেক্ট করুন\n\n"
        f"📌 <b>যোগাযোগ:</b>\n"
        f"  👨‍💻 সাপোর্ট: @SkyTopUpSupport\n"
        f"  📧 ইমেইল: support@skytopup.com\n\n"
        f"⏰ <b>সাপোর্ট সময়:</b> সকাল ৯টা থেকে রাত ১১টা\n\n"
        f"আপনার যেকোনো সমস্যায় আমরা পাশে আছি! 🤝"
    )
    
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))


async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel (restricted)."""
    user_row = get_user(str(update.effective_user.id))
    if not user_row or not is_admin(user_row):
        await edit_or_reply(
            update,
            "⛔ <b>অ্যাক্সেস নিষিদ্ধ!</b>\n\n"
            "এই মেনু শুধুমাত্র এডমিনদের জন্য সংরক্ষিত।",
            UIBuilder.back_button("back_main"),
        )
        return
    
    # Gather statistics
    with db() as conn:
        total_users = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        active_today = conn.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE last_login >= datetime('now', '-1 day')"
        ).fetchone()["cnt"]
        pending_orders = conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE status = '⏳ Pending'"
        ).fetchone()["cnt"]
        total_revenue = conn.execute(
            "SELECT COALESCE(SUM(price), 0) as total FROM orders WHERE status != '❌ Cancelled'"
        ).fetchone()["total"]
        total_orders = conn.execute("SELECT COUNT(*) as cnt FROM orders").fetchone()["cnt"]
    
    msg = (
        f"🔧━━━ ✦ <b>এডমিন প্যানেল</b> ✦ ━━━🔧\n\n"
        f"📊 <b>স্ট্যাটিস্টিকস:</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"👥 <b>মোট ইউজার:</b> {total_users:,}\n"
        f"🟢 <b>আজ একটিভ:</b> {active_today:,}\n"
        f"📦 <b>মোট অর্ডার:</b> {total_orders:,}\n"
        f"⏳ <b>পেন্ডিং অর্ডার:</b> {pending_orders:,}\n"
        f"💰 <b>মোট আয়:</b> ৳{total_revenue:,.2f}\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"🔜 শীঘ্রই আরও এডমিন ফিচার আসছে:\n"
        f"  • অর্ডার ম্যানেজমেন্ট\n"
        f"  • ইউজার ম্যানেজমেন্ট\n"
        f"  • প্রোডাক্ট এডিটর\n"
        f"  • রিপোর্ট জেনারেটর"
    )
    
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))


# ──────────────────────────────────────────────────────────────────────────
# 🚀 APPLICATION ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────

def main():
    """Initialize and start the bot."""
    # ── Validate configuration ──
    if not Config.BOT_TOKEN:
        raise SystemExit(
            "❌ BOT_TOKEN environment variable is not set!\n\n"
            "1. Go to @BotFather on Telegram\n"
            "2. Create a new bot or get your existing bot token\n"
            "3. Set it as environment variable:\n"
            "   export BOT_TOKEN='your_bot_token_here'\n\n"
            "Then run this script again."
        )
    
    if Config.DEV_MODE:
        logger.warning(
            "⚠️  ===== DEV MODE ACTIVE ====="
        )
        logger.warning(
            "⚠️  SMTP_EMAIL / SMTP_PASSWORD not configured."
        )
        logger.warning(
            "⚠️  OTPs will be shown in Telegram chat instead of email."
        )
        logger.warning(
            "⚠️  Do NOT use this in production!"
        )
        logger.warning(
            "⚠️  ==========================="
        )
    else:
        logger.info("✅ Email sending is ENABLED (SMTP configured)")
    
    # ── Initialize database ──
    init_db()
    
    # ── Build application ──
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    # ── Registration conversation handler ──
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_email)],
            REG_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_otp)],
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_password)],
            REG_CONFIRM_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm_password)
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        name="registration",
        persistent=False,
    )
    
    # ── Order conversation handler ──
    order_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")
        ],
        states={
            ORDER_DETAILS_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_order_handler)],
        name="order_flow",
        persistent=False,
    )
    
    # ── Register handlers ──
    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)"))
    # Note: order_handler catches package_* callbacks first; button_callback catches everything else
    
    # ── Start polling ──
    logger.info("🌟 Sky TopUp Bot v2.0 starting...")
    logger.info("🤖 Bot username: @%s", Config.BOT_TOKEN.split(":")[0])
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user.")
    except Exception as e:
        logger.error("❌ Bot crashed: %s", e)
        raise


if __name__ == "__main__":
    main()
