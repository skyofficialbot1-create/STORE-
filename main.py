#!/usr/bin/env python3
"""
🌟 SKY TopUp Telegram Bot — v3.5 (Pro Max Edition)
───────────────────────────────────────────────────────────────────────────
✅ Optimized OTP System | ✅ Admin DB Backup/Restore | ✅ Ultra Pro Max UI
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
# ⚙️ CONFIGURATION (কনফিগারেশন)
# ──────────────────────────────────────────────────────────────────────────

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    
    # 📧 SMTP / Email Configuration
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "mehedihasan706261@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "qgpp laff mkgo iktz")
    
    # 💳 Payment merchant numbers
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    
    MIN_DEPOSIT = 50.0  # 💵 সর্বনিম্ন ডিপোজিট
    
    # 🔐 OTP & Security
    OTP_VALID_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 6
    
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    
    EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)
    DEV_MODE = not EMAIL_SENDING_ENABLED
    
    # 👑 Admin System (Primary Admin ID)
    ADMIN_USER_ID =7689218221 # আপনার রিয়েল টেলিগ্রাম আইডি

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
# 🗄️ DATABASE LAYER (ডাটাবেজ)
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
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, name TEXT DEFAULT 'User', balance REAL DEFAULT 0.0,
            reward_points INTEGER DEFAULT 0, rank TEXT DEFAULT '🥈 Silver Member', is_admin INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1, last_login TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT NOT NULL, otp_code TEXT NOT NULL,
            attempt_count INTEGER DEFAULT 0, is_used INTEGER DEFAULT 0, expires_at TIMESTAMP, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT UNIQUE NOT NULL, telegram_id TEXT NOT NULL,
            product_name TEXT NOT NULL, package TEXT NOT NULL, price REAL NOT NULL, user_details TEXT,
            status TEXT DEFAULT '⏳ Pending', admin_note TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP)""")
        
        c.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL, icon TEXT DEFAULT '📦',
            description TEXT, options TEXT, is_active INTEGER DEFAULT 1, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        c.execute("""CREATE TABLE IF NOT EXISTS deposit_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT UNIQUE NOT NULL, telegram_id TEXT NOT NULL,
            method TEXT NOT NULL, amount REAL NOT NULL, trx_id TEXT NOT NULL, status TEXT DEFAULT '⏳ Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")

        c.execute("""CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)""")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")
        
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
                ("Free Fire Diamonds", "game", "💎", "🔥 অফিশিয়াল ফ্রি ফায়ার ডায়মন্ড টপ-আপ", json.dumps([{"amount": "💎 ১০০ ডায়মন্ড", "price": 100}, {"amount": "💎 ৩১০ ডায়মন্ড", "price": 300}, {"amount": "💎 ৫২০ ডায়মন্ড", "price": 500}])),
                ("Netflix Premium", "subscribe", "🎬", "🍿 নেটফ্লিক্স ৪কে আল্ট্রা এইচডি প্রিমিয়াম", json.dumps([{"amount": "🎬 ১ মাস স্ক্রিন", "price": 200}, {"amount": "🎬 ৩ মাস প্রিমিয়াম", "price": 500}]))
            ]
            c.executemany("INSERT INTO products (name, category, icon, description, options) VALUES (?, ?, ?, ?, ?)", default_products)
    logger.info("📦 Database initialized perfectly.")

def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    with db() as conn: return conn.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)).fetchone()

def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    with db() as conn: return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

def is_maintenance() -> bool:
    with db() as conn: return conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"] == "ON"

def is_admin(user_row) -> bool:
    return False if not user_row else int(user_row["telegram_id"]) == Config.ADMIN_USER_ID or user_row["is_admin"] == 1

# ──────────────────────────────────────────────────────────────────────────
# 🔐 SECURITY & EMAIL HELPERS
# ──────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return hashlib.sha256(("SKY_TOPUP_2024_v2" + password).encode()).hexdigest()

def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)

def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email.strip()))

def _sync_send_otp_email(to_email: str, otp: str) -> bool:
    if Config.DEV_MODE: return True
    msg = MIMEMultipart("alternative")
    msg["From"] = f"SKY TopUp <{Config.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "🔐 SKY TopUp — OTP Verification Code"
    msg.attach(MIMEText(f"আপনার SKY TopUp OTP কোড: {otp}\n\n⏰ মেয়াদ: {Config.OTP_VALID_MINUTES} মিনিট।", "plain", "utf-8"))
    try:
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=8) as server:
            server.ehlo(); server.starttls(); server.ehlo(); server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
            server.sendmail(Config.SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as e:
        logger.error(f"❌ OTP Error: {e}")
        return False

async def send_otp_email_async(to_email: str, otp: str) -> bool:
    return await asyncio.to_thread(_sync_send_otp_email, to_email, otp)

# ──────────────────────────────────────────────────────────────────────────
# 🎨 UI BUILDER (PRO MAX EMOJI EDITION)
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🛒 প্রো-শপ (Shop)", callback_data="shop"), InlineKeyboardButton("💰 আমার ওয়ালেট", callback_data="balance")],
            [InlineKeyboardButton("📦 অর্ডার হিস্ট্রি", callback_data="orders"), InlineKeyboardButton("⚡ ফাস্ট রিচার্জ", callback_data="recharge")],
            [InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile"), InlineKeyboardButton("⚙️ সেটিংস", callback_data="settings")],
            [InlineKeyboardButton("💬 লাইভ হেল্প ও সাপোর্ট 💬", callback_data="help")]
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("👑 অ্যাডমিন কন্ট্রোল প্যানেল 👑", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 প্রধান মেন্যুতে ফিরুন", callback_data=callback_data)]])
    
    @staticmethod
    def cancel_btn() -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল করুন (Cancel)", callback_data="cancel")]])

async def edit_or_reply(update: Update, text: str, reply_markup=None):
    kwargs = {"text": text, "parse_mode": ParseMode.HTML, "reply_markup": reply_markup}
    if update.callback_query:
        try: await update.callback_query.edit_message_text(**kwargs); return
        except Exception: pass
    if update.message: await update.message.reply_text(**kwargs)

# ──────────────────────────────────────────────────────────────────────────
# 🚀 REGISTRATION & START FLOW
# ──────────────────────────────────────────────────────────────────────────
REG_EMAIL, REG_OTP, REG_PASSWORD, REG_CONFIRM_PASSWORD = range(4)
ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_RESTORE_DB_STATE = 40

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_row = get_user(str(user.id))
    
    if is_maintenance() and not (user_row and is_admin(user_row)):
        await update.message.reply_text("⚠️ <b>সিস্টেম আপডেট চলছে!</b>\n\nসার্ভার রক্ষণাবেক্ষণের কারণে বট সাময়িকভাবে বন্ধ আছে। একটু পর আবার চেষ্টা করুন।", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    if user_row:
        with db() as conn: conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (str(user.id),))
        welcome = (f"✨ <b>SKY TOPUP — PREMIUM HUB</b> ✨\n"
                   f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                   f"👋 ওয়েলকাম ব্যাক, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
                   f"💵 <b>বর্তমান ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
                   f"🏅 <b>আপনার র‍্যাংক:</b> {user_row['rank']}\n"
                   f"🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {user_row['reward_points']} pts\n\n"
                   f"👇 <i>নিচের প্রিমিয়াম মেন্যু থেকে আপনার পছন্দের সার্ভিসটি বেছে নিন:</i>")
        if update.callback_query: await update.callback_query.edit_message_text(welcome, parse_mode=ParseMode.HTML, reply_markup=UIBuilder.main_menu(user_row))
        else: await update.message.reply_text(welcome, parse_mode=ParseMode.HTML, reply_markup=UIBuilder.main_menu(user_row))
        return ConversationHandler.END
    
    welcome = (f"🚀 <b>SKY TOPUP — PREMIUM BOT</b> 🚀\n"
               f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"হ্যালো, <b>{UIBuilder.safe_text(user.first_name or 'গ্রাহক')}</b>! 👋\n\n"
               f"🛡️ <i>আমাদের সুপারফাস্ট টপ-আপ সার্ভিসে যুক্ত হতে মাত্র ১ মিনিটে ইমেইল ভেরিফিকেশনটি সম্পন্ন করুন।</i>\n\n"
               f"📧 <b>দয়া করে আপনার সঠিক Gmail এড্রেসটি নিচে টাইপ করুন:</b>")
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return REG_EMAIL

async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    if not is_valid_email(email):
        await update.message.reply_text("❌ <b>ভুল ইমেইল!</b> দয়া করে সঠিক একটি জিমেইল এড্রেস দিন:", reply_markup=UIBuilder.cancel_btn())
        return REG_EMAIL
    if get_user_by_email(email):
        await update.message.reply_text("⚠️ <b>এই ইমেইলটি ইতিমধ্যে ব্যবহৃত!</b> অন্য কোনো ইমেইল দিন:", reply_markup=UIBuilder.cancel_btn())
        return REG_EMAIL
    
    otp = generate_otp()
    exp = (datetime.utcnow() + timedelta(minutes=Config.OTP_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    with db() as conn:
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (str(update.effective_user.id),))
        conn.execute("INSERT INTO otp_codes (telegram_id, otp_code, expires_at) VALUES (?, ?, ?)", (str(update.effective_user.id), otp, exp))
    
    context.user_data["reg_email"] = email
    status_msg = await update.message.reply_text("⏳ <i>আপনার জিমেইলে সিকিউর OTP পাঠানো হচ্ছে... দয়া করে অপেক্ষা করুন।</i>", parse_mode=ParseMode.HTML)
    
    if await send_otp_email_async(email, otp):
        await status_msg.edit_text(f"📬 <b>OTP সফলভাবে পাঠানো হয়েছে!</b>\n\nআপনার ইনবক্স (বা স্প্যাম ফোল্ডার) চেক করুন এবং <b>৬-ডিজিটের</b> কোডটি এখানে লিখুন:", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
        return REG_OTP
    else:
        await status_msg.edit_text("❌ <b>ওটিপি সেন্ড ফেইল্ড!</b>\nমেইল এড্রেসটি চেক করুন এবং আবার চেষ্টা করুন:", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
        return REG_EMAIL

async def reg_receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    with db() as conn:
        row = conn.execute("SELECT * FROM otp_codes WHERE telegram_id = ? AND is_used = 0 ORDER BY created_at DESC LIMIT 1", (str(update.effective_user.id),)).fetchone()
    if not row or otp != row["otp_code"]:
        await update.message.reply_text("❌ <b>ভুল ওটিপি!</b> দয়া করে সঠিক কোডটি দিন:", reply_markup=UIBuilder.cancel_btn())
        return REG_OTP
    
    with db() as conn: conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
    await update.message.reply_text("✅ <b>ভেরিফিকেশন সাকসেস!</b>\n\nএবার অ্যাকাউন্টের সুরক্ষার জন্য একটি নতুন পাসওয়ার্ড দিন (সর্বনিম্ন ৬ অক্ষরের):", reply_markup=UIBuilder.cancel_btn())
    return REG_PASSWORD

async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pwd = update.message.text.strip()
    if len(pwd) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text("❌ <b>পাসওয়ার্ড অত্যন্ত ছোট!</b> আবার দিন (কমপক্ষে ৬ অক্ষর):", reply_markup=UIBuilder.cancel_btn())
        return REG_PASSWORD
    context.user_data["reg_password"] = pwd
    await update.message.reply_text("🔐 <b>নিশ্চিত করুন:</b> পাসওয়ার্ডটি পুনরায় টাইপ করুন:", reply_markup=UIBuilder.cancel_btn())
    return REG_CONFIRM_PASSWORD

async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() != context.user_data.get("reg_password"):
        await update.message.reply_text("❌ <b>পাসওয়ার্ড মেলেনি!</b> দয়া করে প্রথম থেকে পাসওয়ার্ডটি আবার দিন:", reply_markup=UIBuilder.cancel_btn())
        return REG_PASSWORD
    
    tid = str(update.effective_user.id)
    with db() as conn:
        conn.execute("INSERT INTO users (telegram_id, email, password, name, balance) VALUES (?, ?, ?, ?, 10.0)",
                     (tid, context.user_data.get("reg_email"), hash_password(update.message.text.strip()), update.effective_user.first_name or "User"))
    
    context.user_data.clear()
    await update.message.reply_text("🎉 <b>রেজিস্ট্রেশন সম্পূর্ণ সফল!</b>\n🎁 আপনি ৳১০ স্বাগতম বোনাস পেয়েছেন!", parse_mode=ParseMode.HTML)
    await cmd_start(update, context)
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    msg = "❌ <b>প্রক্রিয়া বাতিল করা হয়েছে।</b>"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode=ParseMode.HTML, reply_markup=UIBuilder.back_button("back_main"))
    else:
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=UIBuilder.back_button("back_main"))
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOPPING & ORDER SYSTEM (প্রোডাক্ট শপ)
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
          [InlineKeyboardButton("🍿 ওটিটি ও সাবস্ক্রিপশন", callback_data="category_subscribe")],
          [InlineKeyboardButton("🔙 প্রধান মেন্যুতে ফিরুন", callback_data="back_main")]]
    await edit_or_reply(update, "📂 <b>প্রিমিয়াম ক্যাটাগরি</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👇 <i>আপনার পছন্দের ক্যাটাগরিটি নির্বাচন করুন:</i>", InlineKeyboardMarkup(kb))

async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, cat: str):
    with db() as conn: prods = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (cat,)).fetchall()
    if not prods:
        await edit_or_reply(update, "⚠️ <i>বর্তমানে এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই।</i>", UIBuilder.back_button("shop"))
        return
    kb = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in prods]
    kb.append([InlineKeyboardButton("🔙 পিছনে যান", callback_data="shop")])
    await edit_or_reply(update, "🛍️ <b>অফিশিয়াল প্রোডাক্ট লিস্ট</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👇 <i>কাঙ্ক্ষিত প্রোডাক্টটি সিলেক্ট করুন:</i>", InlineKeyboardMarkup(kb))

async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, pid: int):
    with db() as conn: p = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    if not p: return await edit_or_reply(update, "❌ প্রোডাক্ট পাওয়া যায়নি!", UIBuilder.back_button("shop"))
    
    opts = json.loads(p["options"])
    kb = [[InlineKeyboardButton(f"👉 {opt['amount']}  ━━  ৳{opt['price']}", callback_data=f"package_{pid}_{idx}")] for idx, opt in enumerate(opts)]
    kb.append([InlineKeyboardButton("🔙 পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(update, f"⚡ <b>{p['icon']} {p['name']}</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📌 <b>বিবরণ:</b> <i>{p['description']}</i>\n\n👇 <b>প্যাকেজ নির্বাচন করুন:</b>", InlineKeyboardMarkup(kb))

async def package_selected_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid, pidx = int(query.data.split("_")[1]), int(query.data.split("_")[2])
    
    with db() as conn:
        p = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    pkg = json.loads(p["options"])[pidx]
    u = get_user(str(update.effective_user.id))
    
    if u["balance"] < pkg["price"]:
        await query.message.reply_text(f"❌ <b>অর্ডার ব্যর্থ! অপর্যাপ্ত ব্যালেন্স।</b>\n\n💰 আপনার ব্যালেন্স: ৳{u['balance']:.2f}\n💳 প্রয়োজন: ৳{pkg['price']:.2f}\n\n<i>দয়া করে আগে ওয়ালেট রিচার্জ করুন।</i>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.back_button("back_main"))
        return ConversationHandler.END
    
    context.user_data.update({"order_product_name": p["name"], "order_package": pkg})
    await query.message.reply_text(f"🛒 <b>চেকআউট পেজ</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📦 <b>প্রোডাক্ট:</b> {p['name']}\n📎 <b>প্যাকেজ:</b> {pkg['amount']}\n💵 <b>মূল্য:</b> ৳{pkg['price']}\n\n👉 <i>টপ-আপ ডেলিভারির জন্য আপনার <b>Player ID / Username</b> নিচে টাইপ করে পাঠান:</i>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ORDER_DETAILS_STATE

async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    if len(details) < 3:
        await update.message.reply_text("❌ <b>ভুল ইনপুট!</b> দয়া করে সঠিক ও সম্পূর্ণ আইডি দিন:", reply_markup=UIBuilder.cancel_btn())
        return ORDER_DETAILS_STATE
    
    pname, pkg = context.user_data["order_product_name"], context.user_data["order_package"]
    tid = str(update.effective_user.id)
    oid = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"
    
    with db() as conn:
        conn.execute("INSERT INTO orders (order_id, telegram_id, product_name, package, price, user_details) VALUES (?, ?, ?, ?, ?, ?)", (oid, tid, pname, pkg["amount"], pkg["price"], details))
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (pkg["price"], tid))
    
    context.user_data.clear()
    await update.message.reply_text(f"🎉 <b>আপনার অর্ডারটি সফলভাবে গ্রহণ করা হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🆔 <b>অর্ডার আইডি:</b> <code>{oid}</code>\n💵 <b>কর্তনকৃত ব্যালেন্স:</b> ৳{pkg['price']}\n⏳ <i>আমাদের এক্সিকিউটিভ ৫-১৫ মিনিটের মধ্যে ডেলিভারি সম্পন্ন করবেন।</i>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.back_button("back_main"))
    
    try:
        akb = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{oid}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{oid}")]]
        await context.bot.send_message(Config.ADMIN_USER_ID, f"🔔 <b>New Order Alert!</b>\n\n👤 <b>User:</b> <code>{tid}</code>\n🆔 <b>Order ID:</b> <code>{oid}</code>\n📦 <b>Product:</b> {pname}\n📎 <b>Package:</b> {pkg['amount']}\n📝 <b>Details:</b> <code>{details}</code>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(akb))
    except: pass
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# ➕ AUTOMATED ADD MONEY (ফাস্ট রিচার্জ)
# ──────────────────────────────────────────────────────────────────────────

async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [[InlineKeyboardButton("📱 বিকাশ (bKash)", callback_data="recharge_bkash"), InlineKeyboardButton("📱 নগদ (Nagad)", callback_data="recharge_nagad")],
          [InlineKeyboardButton("📱 রকেট (Rocket)", callback_data="recharge_rocket")],
          [InlineKeyboardButton("🔙 প্রধান মেন্যুতে ফিরুন", callback_data="back_main")]]
    await edit_or_reply(update, f"💳 <b>ইনস্ট্যান্ট ওয়ালেট রিচার্জ</b>\n━━━━━━━━━━━━━━━━━━━━\n\n⚠️ <i>সর্বনিম্ন রিচার্জ লিমিট: <b>৳{Config.MIN_DEPOSIT:.2f}</b></i>\n\n👇 <b>যেকোনো একটি পেমেন্ট গেটওয়ে নির্বাচন করুন:</b>", InlineKeyboardMarkup(kb))

async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    nums = {"bkash": Config.BKASH_NUMBER, "nagad": Config.NAGAD_NUMBER, "rocket": Config.ROCKET_NUMBER}
    context.user_data["recharge_method"] = method
    
    msg = (f"💳 <b>{method.upper()} পেমেন্ট গেটওয়ে</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
           f"📞 আমাদের <b>{method.title()} Personal</b> নম্বর:\n👉 <code>{nums[method]}</code> (ক্লিক করলেই কপি হবে)\n\n"
           f"📌 <b>নির্দেশনা:</b>\n"
           f"১. নম্বরটিতে <b>Send Money</b> করুন।\n"
           f"২. সর্বনিম্ন পরিমাণ: ৳{Config.MIN_DEPOSIT}\n\n"
           f"💵 <b>আপনি কত টাকা পাঠিয়েছেন? শুধু টাকার অংকটি নিচে ইংরেজিতে টাইপ করুন:</b>")
    await edit_or_reply(update, msg, UIBuilder.cancel_btn())
    return ADD_MONEY_AMOUNT

async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: amt = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ <b>ভুল ইনপুট!</b> শুধু সংখ্যা দিন (যেমন: 100):", reply_markup=UIBuilder.cancel_btn())
        return ADD_MONEY_AMOUNT
    
    if amt < Config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ <b>লিমিট এরর!</b> সর্বনিম্ন ডিপোজিট ৳{Config.MIN_DEPOSIT}। আবার দিন:", reply_markup=UIBuilder.cancel_btn())
        return ADD_MONEY_AMOUNT
    
    context.user_data["recharge_amount"] = amt
    await update.message.reply_text("🔑 <b>পারফেক্ট!</b> এবার আপনার পেমেন্টের <b>Transaction ID (TrxID)</b> টি হুবহু কপি করে এখানে পেস্ট করুন:", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADD_MONEY_TRX

async def add_money_trx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text.strip()
    if len(trx) < 5:
        await update.message.reply_text("❌ <b>ভুল TrxID!</b> সঠিক Transaction ID দিন:", reply_markup=UIBuilder.cancel_btn())
        return ADD_MONEY_TRX
    
    method, amt = context.user_data["recharge_method"], context.user_data["recharge_amount"]
    tid = str(update.effective_user.id)
    req_id = f"DEP-{int(datetime.now().timestamp())}"
    
    with db() as conn: conn.execute("INSERT INTO deposit_requests (request_id, telegram_id, method, amount, trx_id) VALUES (?, ?, ?, ?, ?)", (req_id, tid, method, amt, trx))
    context.user_data.clear()
    
    await update.message.reply_text(f"✅ <b>অ্যাড মানি রিকোয়েস্ট সাকসেস!</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🆔 <b>ট্র্যাকিং আইডি:</b> <code>{req_id}</code>\n💳 <b>মাধ্যম:</b> {method.upper()}\n💰 <b>পরিমাণ:</b> ৳{amt:.2f}\n🔑 <b>TrxID:</b> <code>{trx}</code>\n\n⚡ <i>আমাদের টিম ২-৫ মিনিটের মধ্যে যাচাই করে আপনার ব্যালেন্স যুক্ত করে দেবে।</i>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.back_button("back_main"))
    
    try:
        akb = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")]]
        await context.bot.send_message(Config.ADMIN_USER_ID, f"🔔 <b>New Deposit Request!</b>\n\n👤 <b>User:</b> <code>{tid}</code>\n💳 <b>Method:</b> {method.upper()}\n💰 <b>Amount:</b> ৳{amt:.2f}\n🔑 <b>TrxID:</b> <code>{trx}</code>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(akb))
    except: pass
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# 👑 ENTERPRISE ADMIN PANEL (প্রো-ম্যাক্স ড্যাশবোর্ড)
# ──────────────────────────────────────────────────────────────────────────

async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(str(update.effective_user.id))
    if not is_admin(u): return await edit_or_reply(update, "❌ <b>অ্যাক্সেস ডিনাইড!</b>")
    
    with db() as conn:
        uc = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        po = conn.execute("SELECT COUNT(*) FROM orders WHERE status = '⏳ Pending'").fetchone()[0]
        pd = conn.execute("SELECT COUNT(*) FROM deposit_requests WHERE status = '⏳ Pending'").fetchone()[0]
        mm = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"]
    
    kb = [
        [InlineKeyboardButton("📊 পেন্ডিং অর্ডার", callback_data="adm_view_orders"), InlineKeyboardButton("💰 পেন্ডিং ডিপোজিট", callback_data="adm_view_deposits")],
        [InlineKeyboardButton("👤 ব্যালেন্স এডিট", callback_data="adm_balance_set"), InlineKeyboardButton("📦 প্রোডাক্ট যোগ", callback_data="adm_product_add")],
        [InlineKeyboardButton("📤 Backup Database", callback_data="adm_backup_db"), InlineKeyboardButton("📥 Restore Database", callback_data="adm_restore_db_init")],
        [InlineKeyboardButton(f"{'🟢 Turn Maintenance ON' if mm == 'OFF' else '🔴 Turn Maintenance OFF'}", callback_data="adm_toggle_maintenance")],
        [InlineKeyboardButton("🔙 প্রধান মেন্যু", callback_data="back_main")]
    ]
    await edit_or_reply(update, f"👑 <b>সুপার অ্যাডমিন ড্যাশবোর্ড</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👥 <b>মোট ইউজার:</b> {uc} জন\n⏳ <b>পেন্ডিং অর্ডার:</b> {po} টি\n💵 <b>পেন্ডিং ডিপোজিট:</b> {pd} টি\n⚙️ <b>মেইনটেনেন্স মোড:</b> <b>{mm}</b>\n\n<i>নিচের কন্ট্রোল প্যানেল থেকে সিস্টেম ম্যানেজ করুন:</i>", InlineKeyboardMarkup(kb))

async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    d = query.data
    if not is_admin(get_user(str(update.effective_user.id))): return await query.answer("❌ আপনি অ্যাডমিন নন।", show_alert=True)
    await query.answer()
    
    if d == "adm_toggle_maintenance":
        with db() as conn:
            curr = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"]
            conn.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", ("ON" if curr == "OFF" else "OFF",))
        await show_admin_panel_ui(update, context)
        
    elif d == "adm_backup_db":
        b_file = f"backup_{int(datetime.now().timestamp())}.db"
        try:
            s, d_conn = sqlite3.connect(Config.DB_PATH), sqlite3.connect(b_file)
            with d_conn: s.backup(d_conn)
            s.close(); d_conn.close()
            with open(b_file, "rb") as doc:
                await context.bot.send_document(Config.ADMIN_USER_ID, document=doc, filename="SkyTopUp_Backup.db", caption=f"📂 <b>DATABASE SECURE BACKUP</b>\n📅 <b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", parse_mode=ParseMode.HTML)
            os.remove(b_file)
            await query.message.reply_text("✅ <b>ডাটাবেজ ব্যাকআপ সফল!</b> ফাইলটি আপনার ইনবক্সে পাঠানো হয়েছে।", parse_mode=ParseMode.HTML)
        except Exception as e: await query.message.reply_text(f"❌ <b>ব্যাকআপ এরর:</b> {str(e)}", parse_mode=ParseMode.HTML)

    elif d == "adm_view_orders":
        with db() as conn: ords = conn.execute("SELECT * FROM orders WHERE status = '⏳ Pending' LIMIT 5").fetchall()
        if not ords: return await query.message.reply_text("🟢 কোনো পেন্ডিং অর্ডার নেই!")
        for o in ords:
            kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{o['order_id']}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{o['order_id']} कैमरे")]]
            await query.message.reply_text(f"🆔 <code>{o['order_id']}</code>\n👤 User: <code>{o['telegram_id']}</code>\n📦 {o['product_name']} ({o['package']})\n📝 <code>{o['user_details']}</code>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
            
    elif d == "adm_view_deposits":
        with db() as conn: deps = conn.execute("SELECT * FROM deposit_requests WHERE status = '⏳ Pending' LIMIT 5").fetchall()
        if not deps: return await query.message.reply_text("🟢 কোনো পেন্ডিং ডিপোজিট নেই!")
        for d in deps:
            kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{d['request_id']}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{d['request_id']}")] ]
            await query.message.reply_text(f"🆔 <code>{d['request_id']}</code>\n👤 User: <code>{d['telegram_id']}</code>\n💳 {d['method'].upper()} - ৳{d['amount']}\n🔑 <code>{d['trx_id']}</code>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("adm_ord_approve_"):
        oid = d.split("adm_ord_approve_")[1]
        with db() as conn:
            conn.execute("UPDATE orders SET status = '✅ Completed' WHERE order_id = ?", (oid,))
            o = conn.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone()
        await query.message.edit_text(f"✅ Order {oid} Approved!")
        try: await context.bot.send_message(o["telegram_id"], f"🎉 <b>অর্ডার কমপ্লিট!</b>\nআপনার <b>{o['product_name']}</b> ডেলিভারি করা হয়েছে।", parse_mode=ParseMode.HTML)
        except: pass

    elif d.startswith("adm_ord_reject_"):
        oid = d.split("adm_ord_reject_")[1]
        with db() as conn:
            o = conn.execute("SELECT * FROM orders WHERE order_id = ?", (oid,)).fetchone()
            conn.execute("UPDATE orders SET status = '❌ Rejected' WHERE order_id = ?", (oid,))
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (o["price"], o["telegram_id"]))
        await query.message.edit_text(f"❌ Order {oid} Rejected & Refunded!")
        try: await context.bot.send_message(o["telegram_id"], f"❌ <b>অর্ডার বাতিল!</b>\nআপনার ৳{o['price']} ব্যালেন্সে রিফান্ড করা হয়েছে।", parse_mode=ParseMode.HTML)
        except: pass

    elif d.startswith("adm_dep_approve_"):
        rid = d.split("adm_dep_approve_")[1]
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = '⏳ Pending'", (rid,)).fetchone()
            if dep:
                conn.execute("UPDATE deposit_requests SET status = '✅ Approved' WHERE request_id = ?", (rid,))
                conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
                await query.message.edit_text(f"✅ Deposit {rid} Approved!")
                try: await context.bot.send_message(dep["telegram_id"], f"🎉 <b>রিচার্জ সফল!</b>\nআপনার অ্যাকাউন্টে ৳{dep['amount']} যুক্ত হয়েছে।", parse_mode=ParseMode.HTML)
                except: pass

    elif d.startswith("adm_dep_reject_"):
        rid = d.split("adm_dep_reject_")[1]
        with db() as conn: conn.execute("UPDATE deposit_requests SET status = '❌ Rejected' WHERE request_id = ?", (rid,))
        await query.message.edit_text(f"❌ Deposit {rid} Rejected!")

# --- DB Restore Entry Point ---
async def adm_restore_db_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(get_user(str(update.effective_user.id))): return ConversationHandler.END
    await q.message.reply_text("📥 <b>ডাটাবেজ রিস্টোর সিস্টেম</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📂 <i>আপনার ব্যাকআপ ফাইলটি (.db) এখানে আপলোড করুন।</i>\n⚠️ <b>সতর্কতা:</b> বর্তমান সব ডাটা মুছে পূর্বের ডাটা যুক্ত হবে!", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_RESTORE_DB_STATE

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))): return ConversationHandler.END
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ <b>অকার্যকর ফাইল!</b> দয়া করে .db এক্সটেনশনের ফাইল দিন:", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
        return ADMIN_RESTORE_DB_STATE
    
    msg = await update.message.reply_text("⏳ <i>ফাইল প্রসেস করা হচ্ছে...</i>", parse_mode=ParseMode.HTML)
    try:
        f = await context.bot.get_file(doc.file_id)
        await f.download_to_drive("temp.db")
        try:
            t = sqlite3.connect("temp.db"); t.execute("SELECT name FROM sqlite_master WHERE type='table'"); t.close()
        except:
            os.remove("temp.db"); await msg.edit_text("❌ <b>ফাইলটি সঠিক SQLite ডাটাবেজ নয়!</b>", parse_mode=ParseMode.HTML); return ConversationHandler.END
        
        shutil.copyfile("temp.db", Config.DB_PATH)
        os.remove("temp.db")
        await msg.edit_text("✅ <b>ডাটাবেজ রিস্টোর সাকসেসফুল!</b> সিস্টেম রিস্টার্ট হয়েছে।", parse_mode=ParseMode.HTML)
    except Exception as e: await msg.edit_text(f"❌ <b>Error:</b> {str(e)}", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# 🛠️ BALANCE & PRODUCT ADD SYSTEM
# ──────────────────────────────────────────────────────────────────────────

async def start_balance_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👤 <b>ইউজারের Telegram ID দিন:</b>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_SET_BAL_ID

async def bal_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.message.text.strip()
    u = get_user(tid)
    if not u: return await update.message.reply_text("❌ ইউজার ডাটাবেজে নেই। আবার দিন:", reply_markup=UIBuilder.cancel_btn()) or ADMIN_SET_BAL_ID
    context.user_data["tgt_bal_id"] = tid
    await update.message.reply_text(f"👤 <b>নাম:</b> {u['name']}\n💵 <b>বর্তমান ব্যালেন্স:</b> ৳{u['balance']}\n\n👉 <b>নতুন ব্যালেন্স কত বসাতে চান?</b>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_SET_BAL_AMT

async def bal_amt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: amt = float(update.message.text.strip())
    except: return await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন:", reply_markup=UIBuilder.cancel_btn()) or ADMIN_SET_BAL_AMT
    with db() as conn: conn.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (amt, context.user_data["tgt_bal_id"]))
    context.user_data.clear()
    await update.message.reply_text(f"✅ <b>ব্যালেন্স সাকসেসফুলি ৳{amt} এ সেট করা হয়েছে!</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 প্যানেল", callback_data="admin_panel")]]))
    return ConversationHandler.END

async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = [[InlineKeyboardButton("🎮 Game", callback_data="cat_sel_game"), InlineKeyboardButton("🍿 Subscribe", callback_data="cat_sel_subscribe")]]
    await update.callback_query.message.reply_text("📂 <b>প্রোডাক্টের ক্যাটাগরি বেছে নিন:</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["new_prod_cat"] = "game" if "game" in update.callback_query.data else "subscribe"
    await update.callback_query.message.reply_text("📦 <b>প্রোডাক্টের নাম লিখুন:</b> (যেমন: Free Fire VIP)", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text("📝 <b>ছোট বিবরণ দিন:</b>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_ADD_PROD_DESC

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_desc"] = update.message.text.strip()
    await update.message.reply_text("💎 <b>প্যাকেজগুলো JSON ফরম্যাটে দিন।</b>\nযেমন:\n<code>[{\"amount\": \"১০০ ডায়মন্ড\", \"price\": 100}]</code>", parse_mode=ParseMode.HTML, reply_markup=UIBuilder.cancel_btn())
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opts = update.message.text.strip()
    try: json.loads(opts)
    except: return await update.message.reply_text("❌ সঠিক JSON দিন:", reply_markup=UIBuilder.cancel_btn()) or ADMIN_ADD_PROD_OPTS
    with db() as conn: conn.execute("INSERT INTO products (name, category, description, options) VALUES (?, ?, ?, ?)", (context.user_data["new_prod_name"], context.user_data["new_prod_cat"], context.user_data["new_prod_desc"], opts))
    context.user_data.clear()
    await update.message.reply_text("✅ <b>প্রোডাক্ট সফলভাবে যুক্ত হয়েছে!</b>", parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 প্যানেল", callback_data="admin_panel")]]))
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# 👤 PROFILE & GENERAL VIEWS
# ──────────────────────────────────────────────────────────────────────────

async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(str(update.effective_user.id))
    msg = (f"💰 <b>আমার স্পেশাল ওয়ালেট</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👤 <b>ব্যবহারকারী:</b> {UIBuilder.safe_text(u['name'])}\n💳 <b>কারেন্ট ব্যালেন্স:</b> ৳{u['balance']:,.2f}\n🎁 <b>রিওয়ার্ড পয়েন্ট:</b> {u['reward_points']:,} pts\n\n👇 <i>ওয়ালেট রিচার্জ করতে নিচের বাটনে ক্লিক করুন:</i>")
    await edit_or_reply(update, msg, InlineKeyboardMarkup([[InlineKeyboardButton("⚡ ফাস্ট রিচার্জ", callback_data="recharge")], [InlineKeyboardButton("🔙 প্রধান মেন্যু", callback_data="back_main")]]))

async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(str(update.effective_user.id))
    msg = (f"👤 <b>ইউজার প্রোফাইল</b>\n━━━━━━━━━━━━━━━━━━━━\n\n📛 <b>নাম:</b> {UIBuilder.safe_text(u['name'])}\n📧 <b>ইমেইল:</b> <code>{u['email']}</code>\n🏅 <b>র‍্যাংক:</b> {u['rank']}\n💵 <b>ব্যালেন্স:</b> ৳{u['balance']:.2f}\n📅 <b>জয়েনিং ডেট:</b> {u['created_at']}")
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))

async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "⚙️ <b>সেটিংস ও প্রাইভেসি</b>\n━━━━━━━━━━━━━━━━━━━━\n\n🔒 <i>আপনার অ্যাকাউন্ট ১০০% সুরক্ষিত। পরবর্তী আপডেটে কাস্টম ফিচার আসবে!</i>", UIBuilder.back_button("back_main"))

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "💬 <b>২৪/৭ লাইভ সাপোর্ট</b>\n━━━━━━━━━━━━━━━━━━━━\n\n👨‍💻 <i>যেকোনো প্রয়োজনে আমাদের অফিশিয়াল এডমিনের সাথে কথা বলুন:</i> <b>@SkyTopUpSupport</b>", UIBuilder.back_button("back_main"))

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn: ords = conn.execute("SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 5", (str(update.effective_user.id),)).fetchall()
    if not ords: return await edit_or_reply(update, "📭 <i>আপনার কোনো পূর্ববর্তী অর্ডার পাওয়া যায়নি।</i>", UIBuilder.back_button("back_main"))
    msg = "📦 <b>আপনার শেষ ৫টি অর্ডারের ইতিহাস:</b>\n━━━━━━━━━━━━━━━━━━━━\n\n"
    for o in ords: msg += f"▪️ 🆔 <code>{o['order_id']}</code>\n   └ 📦 {o['product_name']} ━━ ৳{o['price']} ━━ {o['status']}\n\n"
    await edit_or_reply(update, msg, UIBuilder.back_button("back_main"))

# ──────────────────────────────────────────────────────────────────────────
# 🔄 MAIN ROUTER & APP RUNNER
# ──────────────────────────────────────────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; d = q.data; await q.answer()
    routes = {"back_main": cmd_start, "shop": show_categories_ui, "balance": show_balance_ui, "orders": show_orders_ui, "recharge": show_recharge_ui, "profile": show_profile_ui, "settings": show_settings_ui, "help": show_help_ui, "admin_panel": show_admin_panel_ui}
    if d in routes: await routes[d](update, context)
    elif d.startswith("category_"): await show_products_ui(update, context, d.split("_")[1])
    elif d.startswith("product_"): await select_package_ui(update, context, int(d.split("_")[1]))

def main():
    init_db()
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={REG_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_email)], REG_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_otp)], REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_password)], REG_CONFIRM_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm_password)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(show_recharge_instructions_ui, pattern=r"^recharge_(bkash|nagad|rocket)$")],
        states={ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_amount_handler)], ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_trx_handler)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_balance_set, pattern="^adm_balance_set$")],
        states={ADMIN_SET_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_id_received)], ADMIN_SET_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_amt_received)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_product_add, pattern="^adm_product_add$")],
        states={ADMIN_ADD_PROD_CAT: [CallbackQueryHandler(prod_cat_received, pattern="^cat_sel_")], ADMIN_ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_name_received)], ADMIN_ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_desc_received)], ADMIN_ADD_PROD_OPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_opts_received)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(adm_restore_db_start, pattern="^adm_restore_db_init$")],
        states={ADMIN_RESTORE_DB_STATE: [MessageHandler(filters.Document.ALL, db_file_restore_received)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel), CallbackQueryHandler(cmd_cancel, pattern="^cancel$")]
    ))
    
    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)"))
    
    logger.info("🌟 Sky TopUp Pro Max Edition Started Successfully...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
