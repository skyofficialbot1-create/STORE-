#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — v5.0 (Auto-Delivery VPN Stock & Premium UI)
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
    
    # Admin System
    ADMIN_USER_ID = 7689218221  # আপনার রিয়েল টেলিগ্রাম আইডি
    SUPPORT_USERNAME = "@FBSKYSUPPORT"  # সাপোর্টের ইউজারনেম (শুধু @ ছাড়া নামটা দিন)

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
        
        # Users
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                email TEXT,
                password TEXT,
                name TEXT DEFAULT 'User',
                balance REAL DEFAULT 0.0,
                reward_points INTEGER DEFAULT 0,
                rank TEXT DEFAULT '🥈 Silver',
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Products (Added is_auto column for auto-delivery)
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                is_auto INTEGER DEFAULT 0,
                icon TEXT DEFAULT '📦',
                description TEXT,
                options TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Add is_auto column safely if updating from older DB
        try:
            c.execute("ALTER TABLE products ADD COLUMN is_auto INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass

        # Stocks for VPN/Accounts
        c.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                package_idx INTEGER NOT NULL,
                account_data TEXT NOT NULL,
                is_sold INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Deposits
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

        # Settings
        c.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")
        
        # Seed default products if empty
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
                ("Free Fire Diamonds", "game", 0, "💎", "ফ্রি ফায়ার ডায়মন্ড টপ-আপ (UID)",
                 json.dumps([
                     {"amount": "💎 ১০০ ডায়মন্ড", "price": 100},
                     {"amount": "💎 ৩১০ ডায়মন্ড", "price": 300},
                 ])),
                ("Premium VPN (Auto)", "vpn", 1, "🛡️", "প্রিমিয়াম ভিপিএন (সাথে সাথে ডেলিভারি)",
                 json.dumps([
                     {"amount": "🛡️ ১ মাস সাবস্ক্রিপশন", "price": 150},
                     {"amount": "🛡️ ৩ মাস সাবস্ক্রিপশন", "price": 400},
                 ]))
            ]
            c.executemany(
                "INSERT INTO products (name, category, is_auto, icon, description, options) VALUES (?, ?, ?, ?, ?, ?)",
                default_products,
            )
    
    logger.info("📦 Database initialized with Stock System.")

def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)).fetchone()

def is_admin(user_row) -> bool:
    if not user_row: return False
    return int(user_row["telegram_id"]) == Config.ADMIN_USER_ID or user_row["is_admin"] == 1


# ──────────────────────────────────────────────────────────────────────────
# 🎨 UI BUILDER
# ──────────────────────────────────────────────────────────────────────────

class UIBuilder:
    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [
                InlineKeyboardButton("🛒 শপ (Shop)", callback_data="shop"),
                InlineKeyboardButton("💳 অ্যাড মানি", callback_data="recharge")
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
            keyboard.append([InlineKeyboardButton("👑 অ্যাডমিন প্যানেল 👑", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data=callback_data)]])


async def edit_or_reply(update: Update, text: str, reply_markup=None):
    kwargs = {"text": text, "parse_mode": ParseMode.HTML, "reply_markup": reply_markup}
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(**kwargs)
            return
        except Exception:
            pass
    if update.message:
        await update.message.reply_text(**kwargs)


# ──────────────────────────────────────────────────────────────────────────
# 🚀 CORE COMMANDS
# ──────────────────────────────────────────────────────────────────────────

ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_STOCK_PROD, ADMIN_STOCK_PKG, ADMIN_STOCK_DATA = range(40, 43)

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = str(user.id)
    user_row = get_user(telegram_id)
    
    with db() as conn:
        m_mode = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"]
    
    if m_mode == "ON" and not (user_row and is_admin(user_row)):
        await update.message.reply_text("⚠️ <b>সিস্টেম আপডেটের কাজ চলছে!</b>\nশীঘ্রই ফিরে আসবো।", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    welcome_prefix = ""
    if not user_row:
        name = user.first_name or "গ্রাহক"
        with db() as conn:
            conn.execute(
                "INSERT INTO users (telegram_id, name, balance) VALUES (?, ?, 0.0)",
                (telegram_id, name)
            )
        user_row = get_user(telegram_id)
        welcome_prefix = "🎉 <b>অভিনন্দন! আপনার অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে।</b>\n\n"
    else:
        with db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (telegram_id,))

    welcome = (
        f"{welcome_prefix}"
        f"🌟 <b>SKY TOPUP — PREMIUM SERVICE</b> 🌟\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👋 স্বাগতম, <b>{user_row['name']}</b>!\n\n"
        f"💰 <b>বর্তমান ব্যালেন্স:</b> ৳ {user_row['balance']:,.2f}\n"
        f"🏅 <b>অ্যাকাউন্ট র‍্যাংক:</b> {user_row['rank']}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✨ <i>যেকোনো সার্ভিস অর্ডার করতে নিচের মেন্যু ব্যবহার করুন:</i>"
    )
    context.user_data.clear()
    await edit_or_reply(update, welcome, UIBuilder.main_menu(user_row))
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ <b>প্রক্রিয়া বাতিল করা হয়েছে।</b>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ──────────────────────────────────────────────────────────────────────────
# 🛒 SHOPPING & AUTO-DELIVERY
# ──────────────────────────────────────────────────────────────────────────

async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🛡️ ভিপিএন ও অ্যাকাউন্টস", callback_data="category_vpn")],
        [InlineKeyboardButton("🍿 ওটিটি সাবস্ক্রিপশন", callback_data="category_subscribe")],
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
    await edit_or_reply(update, "🛍️ <b>প্রোডাক্ট লিস্ট</b>\n━━━━━━━━━━━━━━━━━━━━\n\nপ্রোডাক্ট সিলেক্ট করুন:", InlineKeyboardMarkup(keyboard))

async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    
    options = json.loads(product["options"])
    keyboard = []
    
    # Show stock count if it's auto-delivery
    for idx, opt in enumerate(options):
        stock_text = ""
        if product["is_auto"] == 1:
            with db() as conn:
                stock_cnt = conn.execute("SELECT COUNT(*) FROM stocks WHERE product_id=? AND package_idx=? AND is_sold=0", (product_id, idx)).fetchone()[0]
            stock_text = f" [স্টক: {stock_cnt} টি]" if stock_cnt > 0 else " [স্টক আউট]"
            
        btn_text = f"{opt['amount']} ➔ ৳{opt['price']}{stock_text}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"package_{product_id}_{idx}")])
        
    keyboard.append([InlineKeyboardButton("🔙 পিছনে যান", callback_data="shop")])
    
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>বিবরণ:</b> {product['description']}\n\n"
        f"👇 <i>প্যাকেজ নির্বাচন করুন:</i>",
        InlineKeyboardMarkup(keyboard)
    )

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
    telegram_id = str(user_row["telegram_id"])
    price = selected_package["price"]
    
    # Check Balance
    if user_row["balance"] < price:
        await query.message.reply_text(f"❌ <b>অপর্যাপ্ত ব্যালেন্স!</b>\nপ্রয়োজন: ৳{price:.2f} | আপনার আছে: ৳{user_row['balance']:.2f}")
        return ConversationHandler.END

    # AUTO-DELIVERY FLOW (VPN / Accounts)
    if product["is_auto"] == 1:
        with db() as conn:
            stock = conn.execute("SELECT * FROM stocks WHERE product_id=? AND package_idx=? AND is_sold=0 LIMIT 1", (product_id, package_idx)).fetchone()
            
            if not stock:
                await query.message.reply_text("❌ <b>দুঃখিত! এই প্যাকেজটি বর্তমানে স্টক আউট।</b>\nদয়া করে কিছুক্ষণ পর আবার চেষ্টা করুন।")
                return ConversationHandler.END
            
            order_id = f"AUTO-{int(datetime.now().timestamp())}"
            account_data = stock["account_data"]
            
            # Deduct balance, update stock, insert order
            conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, telegram_id))
            conn.execute("UPDATE stocks SET is_sold = 1 WHERE id = ?", (stock["id"],))
            conn.execute(
                "INSERT INTO orders (order_id, telegram_id, product_name, package, price, status, user_details) VALUES (?, ?, ?, ?, ?, '✅ Completed', 'Auto-Delivered')",
                (order_id, telegram_id, product["name"], selected_package["amount"], price)
            )

        # Parse Account Details for 1-click copy
        formatted_account = ""
        if ":" in account_data:
            u, p = account_data.split(":", 1)
            formatted_account = f"📧 <b>ইমেইল/ইউজার:</b> <code>{u.strip()}</code>\n🔑 <b>পাসওয়ার্ড:</b> <code>{p.strip()}</code>"
        elif "|" in account_data:
            u, p = account_data.split("|", 1)
            formatted_account = f"📧 <b>ইমেইল/ইউজার:</b> <code>{u.strip()}</code>\n🔑 <b>পাসওয়ার্ড:</b> <code>{p.strip()}</code>"
        else:
            formatted_account = f"📦 <b>অ্যাকাউন্ট ডিটেইলস:</b>\n<code>{account_data.strip()}</code>"

        success_msg = (
            f"🎉 <b>পেমেন্ট সফল! আপনার অ্যাকাউন্ট নিচে দেওয়া হলো:</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 <b>প্রোডাক্ট:</b> {product['name']}\n"
            f"📎 <b>প্যাকেজ:</b> {selected_package['amount']}\n\n"
            f"👇 <i>ক্লিক করে কপি করুন:</i> 👇\n\n"
            f"{formatted_account}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <i>আমাদের সাথে থাকার জন্য ধন্যবাদ!</i>"
        )
        await query.message.reply_text(success_msg, parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    # MANUAL DELIVERY FLOW (Games / Others)
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    
    await query.message.reply_text(
        f"🛒 <b>চেকআউট নিশ্চিতকরণ</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 <b>প্রোডাক্ট:</b> {product['name']}\n"
        f"💰 <b>মূল্য:</b> ৳{price}\n\n"
        f"👉 <i>ডেলিভারির জন্য আপনার <b>ID / UID / Details</b> লিখে সেন্ড করুন:</i>"
    )
    return ORDER_DETAILS_STATE

async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_details = update.message.text.strip()
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    telegram_id = str(update.effective_user.id)
    
    order_id = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"
    
    with db() as conn:
        conn.execute("INSERT INTO orders (order_id, telegram_id, product_name, package, price, user_details) VALUES (?, ?, ?, ?, ?, ?)",
                     (order_id, telegram_id, product_name, package["amount"], price, user_details))
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, telegram_id))
    
    context.user_data.clear()
    await update.message.reply_text(f"✅ <b>অর্ডার সফল!</b>\n🆔 আইডি: <code>{order_id}</code>\n⚡ ৫-১৫ মিনিটে ডেলিভারি দেওয়া হবে।")
    
    # Notify Admin
    keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")]]
    try:
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>New Order!</b>\n👤 {telegram_id}\n🆔 <code>{order_id}</code>\n📦 {product_name}\n📎 {package['amount']}\nℹ️ <code>{user_details}</code>",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception: pass
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# ➕ AUTOMATED ADD MONEY (RECHARGE)
# ──────────────────────────────────────────────────────────────────────────

async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 বিকাশ (bKash)", callback_data="recharge_bkash"), InlineKeyboardButton("📱 নগদ (Nagad)", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 রকেট (Rocket)", callback_data="recharge_rocket")],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")]
    ]
    await edit_or_reply(update, f"💳 <b>অ্যাড মানি</b>\n━━━━━━━━━━━━━━━━━━━━\n⚠️ সর্বনিম্ন 리চার্জ <b>৳{Config.MIN_DEPOSIT}</b> টাকা।\nমাধ্যম নির্বাচন করুন:", InlineKeyboardMarkup(keyboard))

async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {"bkash": Config.BKASH_NUMBER, "nagad": Config.NAGAD_NUMBER, "rocket": Config.ROCKET_NUMBER}
    context.user_data["recharge_method"] = method
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()} পেমেন্ট</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 <b>Send Money</b> করুন এই নম্বরে:\n📞 <code>{numbers[method]}</code>\n\n"
        f"💵 <b>কত টাকা পাঠিয়েছেন? (ইংরেজিতে লিখুন):</b>"
    )
    return ADD_MONEY_AMOUNT

async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
        if amount < Config.MIN_DEPOSIT: raise ValueError
    except ValueError:
        await update.message.reply_text(f"❌ সঠিক পরিমাণ দিন (সর্বনিম্ন ৳{Config.MIN_DEPOSIT}):")
        return ADD_MONEY_AMOUNT
    
    context.user_data["recharge_amount"] = amount
    await update.message.reply_text("🔑 <b>Transaction ID (TrxID)</b> টি হুবহু কপি করে এখানে দিন:")
    return ADD_MONEY_TRX

async def add_money_trx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_id = update.message.text.strip()
    method = context.user_data.get("recharge_method")
    amount = context.user_data.get("recharge_amount")
    telegram_id = str(update.effective_user.id)
    req_id = f"DEP-{int(datetime.now().timestamp())}"
    
    with db() as conn:
        conn.execute("INSERT INTO deposit_requests (request_id, telegram_id, method, amount, trx_id) VALUES (?, ?, ?, ?, ?)",
                     (req_id, telegram_id, method, amount, trx_id))
    context.user_data.clear()
    await update.message.reply_text(f"✅ <b>রিকোয়েস্ট জমা হয়েছে!</b>\n🆔 ট্র্যাকিং আইডি: <code>{req_id}</code>\n⚡ ২-৫ মিনিটের মধ্যে এডমিন ভেরিফাই করবে।")
    
    try:
        keyboard = [[InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"), InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")]]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID, text=f"🔔 <b>New Deposit!</b>\n👤 {telegram_id}\n💳 {method.upper()} - ৳{amount}\n🔑 <code>{trx_id}</code>",
            parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception: pass
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 🛠️ ADMIN PANEL & STOCK MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────

async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row): return
    
    keyboard = [
        [InlineKeyboardButton("📦 অটো-স্টক অ্যাড (VPN)", callback_data="adm_stock_add")],
        [InlineKeyboardButton("📊 অর্ডার লিস্ট", callback_data="adm_view_orders"), InlineKeyboardButton("💰 অ্যাড-মানি লিস্ট", callback_data="adm_view_deposits")],
        [InlineKeyboardButton("👤 ব্যালেন্স এডিট", callback_data="adm_balance_set"), InlineKeyboardButton("➕ নতুন প্রোডাক্ট", callback_data="adm_product_add")],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")]
    ]
    await edit_or_reply(update, "👑 <b>অ্যাডমিন কন্ট্রোল প্যানেল</b>\n━━━━━━━━━━━━━━━━━━━━", InlineKeyboardMarkup(keyboard))

async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not is_admin(get_user(str(update.effective_user.id))): return
    await query.answer()

    if data.startswith("adm_ord_approve_"):
        ord_id = data.replace("adm_ord_approve_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '✅ Completed' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, product_name FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
        await query.message.edit_text(f"✅ অর্ডার {ord_id} অ্যাপ্রুভড!")
        try:
            await context.bot.send_message(chat_id=order["telegram_id"], text=f"🎉 <b>আপনার অর্ডারটি সম্পন্ন হয়েছে!</b>\n📦 {order['product_name']}", parse_mode=ParseMode.HTML)
        except Exception: pass

    elif data.startswith("adm_ord_reject_"):
        ord_id = data.replace("adm_ord_reject_", "")
        with db() as conn:
            conn.execute("UPDATE orders SET status = '❌ Rejected' WHERE order_id = ?", (ord_id,))
            order = conn.execute("SELECT telegram_id, price FROM orders WHERE order_id = ?", (ord_id,)).fetchone()
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (order["price"], order["telegram_id"]))
        await query.message.edit_text(f"❌ অর্ডার রিজেক্ট ও ৳{order['price']} রিফান্ড করা হয়েছে!")

    elif data.startswith("adm_dep_approve_"):
        req_id = data.replace("adm_dep_approve_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = '⏳ Pending'", (req_id,)).fetchone()
            if dep:
                conn.execute("UPDATE deposit_requests SET status = '✅ Approved' WHERE request_id = ?", (req_id,))
                conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
        await query.message.edit_text(f"✅ ডিপোজিট অ্যাপ্রুভড!")

    elif data.startswith("adm_dep_reject_"):
        req_id = data.replace("adm_dep_reject_", "")
        with db() as conn:
            conn.execute("UPDATE deposit_requests SET status = '❌ Rejected' WHERE request_id = ?", (req_id,))
        await query.message.edit_text(f"❌ ডিপোজিট রিজেক্ট করা হয়েছে!")

# --- ADMIN STOCK ADD FLOW ---
async def start_stock_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        auto_prods = conn.execute("SELECT * FROM products WHERE is_auto = 1 AND is_active = 1").fetchall()
    
    if not auto_prods:
        await update.callback_query.message.reply_text("❌ কোনো অটো-ডেলিভারি প্রোডাক্ট নেই! আগে প্রোডাক্ট যোগ করুন।")
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"stk_prod_{p['id']}")] for p in auto_prods]
    await update.callback_query.message.reply_text("📦 কোন প্রোডাক্টের স্টক অ্যাড করবেন?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_STOCK_PROD

async def stock_prod_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.replace("stk_prod_", ""))
    context.user_data["stock_prod_id"] = prod_id
    
    with db() as conn:
        product = conn.execute("SELECT options FROM products WHERE id = ?", (prod_id,)).fetchone()
    
    opts = json.loads(product["options"])
    keyboard = [[InlineKeyboardButton(opt["amount"], callback_data=f"stk_pkg_{idx}")] for idx, opt in enumerate(opts)]
    await query.message.reply_text("📎 কোন প্যাকেজের স্টক অ্যাড করবেন?", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_STOCK_PKG

async def stock_pkg_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["stock_pkg_idx"] = int(query.data.replace("stk_pkg_", ""))
    
    await query.message.reply_text(
        "📝 <b>অ্যাকাউন্ট ডিটেইলস দিন:</b>\n\n"
        "আপনি চাইলে মেসেজে লিখতে পারেন অথবা <code>.txt</code> ফাইল আপলোড করতে পারেন।\n"
        "📌 <i>ফরম্যাট: প্রতি লাইনে একটি অ্যাকাউন্ট (যেমন: email@gmail.com:password123)</i>"
    )
    return ADMIN_STOCK_DATA

async def stock_data_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = []
    if update.message.document:
        doc = update.message.document
        if doc.file_name.endswith(".txt"):
            file_obj = await context.bot.get_file(doc.file_id)
            content = await file_obj.download_as_bytearray()
            lines = content.decode('utf-8').splitlines()
        else:
            await update.message.reply_text("❌ শুধুমাত্র .txt ফাইল গ্রহণযোগ্য!")
            return ADMIN_STOCK_DATA
    elif update.message.text:
        lines = update.message.text.strip().splitlines()
        
    valid_lines = [l.strip() for l in lines if l.strip()]
    if not valid_lines:
        await update.message.reply_text("❌ কোনো ভ্যালিড ডাটা পাওয়া যায়নি।")
        return ConversationHandler.END
        
    prod_id = context.user_data["stock_prod_id"]
    pkg_idx = context.user_data["stock_pkg_idx"]
    
    insert_data = [(prod_id, pkg_idx, line) for line in valid_lines]
    with db() as conn:
        conn.executemany("INSERT INTO stocks (product_id, package_idx, account_data) VALUES (?, ?, ?)", insert_data)
        
    context.user_data.clear()
    await update.message.reply_text(f"✅ <b>সফলভাবে {len(valid_lines)} টি স্টক যোগ করা হয়েছে!</b>", parse_mode=ParseMode.HTML)
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# 👤 USER PROFILE & SUPPORT VIEWS
# ──────────────────────────────────────────────────────────────────────────

async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"👤 <b>আমার প্রোফাইল</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📛 <b>নাম:</b> {user_row['name']}\n"
        f"🆔 <b>টেলিগ্রাম আইডি:</b> <code>{user_row['telegram_id']}</code>\n"
        f"🏅 <b>র‍্যাংক:</b> {user_row['rank']}\n"
        f"💰 <b>ব্যালেন্স:</b> ৳{user_row['balance']:.2f}\n\n"
        f"<i>Sky TopUp এর সাথে থাকার জন্য ধন্যবাদ!</i>",
        UIBuilder.back_button("back_main")
    )

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💬 এডমিনকে মেসেজ দিন", url=f"https://t.me/{Config.SUPPORT_USERNAME}")],
        [InlineKeyboardButton("🔙 মেন্যুতে ফিরে যান", callback_data="back_main")]
    ]
    await edit_or_reply(
        update, 
        "🛡️ <b>লাইভ হেল্পলাইন ও সাপোর্ট</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "যেকোনো সমস্যা, পেমেন্ট ইস্যু বা প্রশ্নের জন্য সরাসরি আমাদের সাপোর্ট এডমিনের সাথে যোগাযোগ করুন।\n\n"
        "<i>নিচের বাটনে ক্লিক করলেই সরাসরি আমাদের ইনবক্সে নিয়ে যাবে:</i> 👇", 
        InlineKeyboardMarkup(keyboard)
    )

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute("SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 5", (str(update.effective_user.id),)).fetchall()
    
    if not orders:
        await edit_or_reply(update, "📭 <i>আপনি এখনও কোনো অর্ডার করেননি।</i>", UIBuilder.back_button("back_main"))
        return
    
    lines = ["📦 <b>আপনার শেষ ৫টি অর্ডার:</b>\n━━━━━━━━━━━━━━━━━━━━\n"]
    for o in orders:
        icon = "✅" if "Completed" in o['status'] else ("❌" if "Rejected" in o['status'] else "⏳")
        lines.append(f"{icon} <b>{o['product_name']}</b>\n   ├ আইডি: <code>{o['order_id']}</code>\n   └ মূল্য: ৳{o['price']} | {o['status']}\n")
    await edit_or_reply(update, "\n".join(lines), UIBuilder.back_button("back_main"))

# ──────────────────────────────────────────────────────────────────────────
# 🔄 MAIN ROUTER
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
# 🚀 BOT RUNNER
# ──────────────────────────────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(Config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    
    # Handlers
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)]},
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    ))
    
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(show_recharge_instructions_ui, pattern=r"^recharge_(bkash|nagad|rocket)$")],
        states={
            ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_amount_handler)],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_trx_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    ))

    # Admin Stock Handler
    app.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(start_stock_add, pattern="^adm_stock_add$")],
        states={
            ADMIN_STOCK_PROD: [CallbackQueryHandler(stock_prod_selected, pattern="^stk_prod_")],
            ADMIN_STOCK_PKG: [CallbackQueryHandler(stock_pkg_selected, pattern="^stk_pkg_")],
            ADMIN_STOCK_DATA: [MessageHandler((filters.TEXT | filters.Document.ALL) & ~filters.COMMAND, stock_data_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    ))
    
    # Unified Query Handlers
    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)(?!stk_)"))
    
    logger.info("🌟 Sky TopUp Bot (Auto-Stock Update) started successfully...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
