#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — Elite Experience v5.0
──────────────────────────────────────────────
No email. No OTP. Pure click‑powered elegance.
"""

import logging, os, json, random, string, sqlite3, hashlib, re, secrets, asyncio, shutil
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

# ─────────────────────────────────────────────────────────────────
# 🎛️ PREMIUM CONFIGURATION
# ─────────────────────────────────────────────────────────────────
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    MIN_DEPOSIT = 50.0
    MIN_PASSWORD_LENGTH = 6
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    ADMIN_USER_ID = 7689218221

# ─────────────────────────────────────────────────────────────────
# 📝 LOGGING
# ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkyTopUp")

# ─────────────────────────────────────────────────────────────────
# 🗄️ DATABASE
# ─────────────────────────────────────────────────────────────────
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
        logger.error(f"DB error: {e}")
        raise
    finally:
        conn.close()

def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH) or ".", exist_ok=True)
    with db() as conn:
        c = conn.cursor()
        # users (no email)
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
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
        # orders
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
        # products
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
        # deposit requests
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
        # settings
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")

        # seed products
        c.execute("SELECT COUNT(*) FROM products")
        if c.fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO products (name, category, icon, description, options) VALUES (?,?,?,?,?)",
                [
                    ("Free Fire Diamonds", "game", "💎",
                     "ফ্রি ফায়ার ডায়মন্ড টপ-আপ",
                     json.dumps([
                         {"amount": "💎 100 Diamonds", "price": 100},
                         {"amount": "💎 310 Diamonds", "price": 300},
                         {"amount": "💎 520 Diamonds", "price": 500},
                     ])),
                    ("Netflix Premium", "subscribe", "🎬",
                     "নেটফ্লিক্স প্রিমিয়াম সাবস্ক্রিপশন",
                     json.dumps([
                         {"amount": "🎬 1 Month Screen", "price": 200},
                         {"amount": "🎬 3 Months Premium", "price": 500},
                     ]))
                ]
            )
    logger.info("🌟 Database ready.")

def get_user(telegram_id: str) -> Optional[sqlite3.Row]:
    with db() as conn:
        return conn.execute("SELECT * FROM users WHERE telegram_id = ?", (str(telegram_id),)).fetchone()

def update_balance(telegram_id: str, amount: float):
    with db() as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, str(telegram_id)))

def is_maintenance() -> bool:
    with db() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()
        return row and row["value"] == "ON"

def is_admin(user_row) -> bool:
    return user_row and (int(user_row["telegram_id"]) == Config.ADMIN_USER_ID or user_row["is_admin"] == 1)

def hash_password(password: str) -> str:
    return hashlib.sha256(("SKY_TOPUP_2024_v2" + password).encode()).hexdigest()

# ─────────────────────────────────────────────────────────────────
# 🎨 PREMIUM UI BUILDER
# ─────────────────────────────────────────────────────────────────
class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🛒 Buy Products", callback_data="shop"),
             InlineKeyboardButton("💳 My Balance", callback_data="balance")],
            [InlineKeyboardButton("📦 Order Track", callback_data="orders"),
             InlineKeyboardButton("➕ Instant Recharge", callback_data="recharge")],
            [InlineKeyboardButton("👤 My Profile", callback_data="profile"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("💬 Help & Support", callback_data="help")],
        ]
        if user_row and is_admin(user_row):
            keyboard.append([InlineKeyboardButton("🛠️ Admin Panel", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def back_button(callback_data: str = "back_main") -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Main Menu", callback_data=callback_data)]])

async def smart_reply(update: Update, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    kwargs = {"text": text, "parse_mode": parse_mode, "reply_markup": reply_markup}
    if update.callback_query:
        await update.callback_query.message.reply_text(**kwargs)
    elif update.message:
        await update.message.reply_text(**kwargs)

async def edit_or_reply(update: Update, text: str, reply_markup=None, parse_mode=ParseMode.HTML):
    kwargs = {"text": text, "parse_mode": parse_mode, "reply_markup": reply_markup}
    if update.callback_query:
        try:
            await update.callback_query.edit_message_text(**kwargs)
            return
        except Exception:
            pass
    await smart_reply(update, text, reply_markup, parse_mode)

# ─────────────────────────────────────────────────────────────────
# 🔹 CONVERSATION STATES
# ─────────────────────────────────────────────────────────────────
REG_PASSWORD, REG_CONFIRM_PASSWORD = range(2)
ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_RESTORE_DB_STATE = 40
ADMIN_BROADCAST_MSG = 50
ADMIN_SEARCH_USER = 60

# ─────────────────────────────────────────────────────────────────
# 👋 START & REGISTRATION (No email/OTP)
# ─────────────────────────────────────────────────────────────────
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_row = get_user(str(user.id))

    if is_maintenance() and not (user_row and is_admin(user_row)):
        await update.message.reply_text("⚠️ <b>System Maintenance</b>\n\nWe'll be back shortly.", parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    if user_row:
        with db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (str(user.id),))
        welcome = (
            "✨ <b>SKY TOPUP · PREMIUM</b> ✨\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 Welcome back, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
            f"💵 Balance: <b>৳{user_row['balance']:,.2f}</b>\n"
            f"🏅 Rank: {user_row['rank']}\n"
            f"🎁 Points: {user_row['reward_points']} pts\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "🚀 Use the menu below:"
        )
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))
        return ConversationHandler.END

    # new user
    welcome = (
        "✨ <b>SKY TOPUP · PREMIUM</b> ✨\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Hello, <b>{UIBuilder.safe_text(user.first_name or 'User')}</b>! 👋\n\n"
        "To secure your account, create a password 🔐\n"
        "<i>(minimum 6 characters)</i>\n\n"
        "👉 <b>Type your password now:</b>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    return REG_PASSWORD

async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text("❌ Too short! Please enter at least 6 characters:")
        return REG_PASSWORD
    context.user_data["reg_password"] = password
    await update.message.reply_text("🔁 Confirm your password:")
    return REG_CONFIRM_PASSWORD

async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() != context.user_data.get("reg_password"):
        await update.message.reply_text("❌ Passwords don't match! Start again:")
        return REG_PASSWORD
    user = update.effective_user
    tid = str(user.id)
    name = user.first_name or "User"
    with db() as conn:
        conn.execute(
            "INSERT INTO users (telegram_id, password, name, balance) VALUES (?, ?, ?, 10.0)",
            (tid, hash_password(context.user_data["reg_password"]), name)
        )
    context.user_data.clear()
    await update.message.reply_text("🎉 <b>Registration complete!</b> You got ৳10 as a welcome gift.")
    user_row = get_user(tid)
    await update.message.reply_text("✨ Use the menu:", reply_markup=UIBuilder.main_menu(user_row))
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 🛒 SHOP
# ─────────────────────────────────────────────────────────────────
async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Game Top‑Up", callback_data="category_game")],
        [InlineKeyboardButton("🍿 OTT & Subs", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")],
    ]
    await edit_or_reply(update, "📂 <b>Product Categories</b>", InlineKeyboardMarkup(keyboard))

async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
    if not products:
        await edit_or_reply(update, "⚠️ No products found.", UIBuilder.back_button("shop"))
        return
    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="shop")])
    await edit_or_reply(update, "📦 <b>Select a product</b>", InlineKeyboardMarkup(keyboard))

async def select_package_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        await edit_or_reply(update, "❌ Product not found!", UIBuilder.back_button("shop"))
        return
    options = json.loads(product["options"])
    keyboard = [
        [InlineKeyboardButton(f"{opt['amount']} ➔ ৳{opt['price']}", callback_data=f"package_{product_id}_{idx}")]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="shop")])
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {product['description']}\n\n"
        f"Choose a package:",
        InlineKeyboardMarkup(keyboard)
    )

# ─────────────────────────────────────────────────────────────────
# 📋 ORDER
# ─────────────────────────────────────────────────────────────────
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
            f"❌ <b>Insufficient balance</b>\n"
            f"Your balance: ৳{user_row['balance']:.2f}\n"
            f"Needed: ৳{price:.2f}\n\n"
            f"➕ Recharge your wallet first."
        )
        return ConversationHandler.END
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    await query.message.reply_text(
        f"🛒 <b>Confirm Checkout</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 {product['name']}\n"
        f"📎 {selected_package['amount']}\n"
        f"💰 Price: ৳{price}\n\n"
        f"👉 Enter your <b>Game ID / UID / Details</b> (min 3 chars):"
    )
    return ORDER_DETAILS_STATE

async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    if len(details) < 3:
        await update.message.reply_text("❌ Too short! Provide a valid ID:")
        return ORDER_DETAILS_STATE
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    tid = str(update.effective_user.id)
    order_id = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"
    with db() as conn:
        conn.execute(
            "INSERT INTO orders (order_id, telegram_id, product_name, package, price, user_details) VALUES (?,?,?,?,?,?)",
            (order_id, tid, product_name, package["amount"], price, details)
        )
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, tid))
    context.user_data.clear()
    await update.message.reply_text(
        f"🎉 <b>Order Placed!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{order_id}</code>\n"
        f"💰 Deducted: ৳{price}\n"
        f"⚡ Admin will process within 5–15 mins."
    )
    # notify admin
    try:
        await context.bot.send_message(
            Config.ADMIN_USER_ID,
            f"🔔 <b>New Order</b>\n"
            f"👤 {tid}\n"
            f"🆔 <code>{order_id}</code>\n"
            f"📦 {product_name} ({package['amount']})\n"
            f"ℹ️ <code>{details}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin notify: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 💰 DEPOSIT (Clickable Amounts)
# ─────────────────────────────────────────────────────────────────
DEPOSIT_AMOUNTS = [50, 100, 200, 500, 1000]

def deposit_amount_keyboard() -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(f"৳{a}", callback_data=f"depamt_{a}") for a in DEPOSIT_AMOUNTS]
    # split into rows of 2
    kb = [buttons[i:i+2] for i in range(0, len(buttons), 2)]
    kb.append([InlineKeyboardButton("✏️ Custom Amount", callback_data="depamt_custom")])
    kb.append([InlineKeyboardButton("⬅️ Cancel", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)

async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="recharge_bkash"),
         InlineKeyboardButton("📱 Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(update, "💳 <b>Instant Recharge</b>\n━━━━━━━━━━━━━━━\nChoose your method:", InlineKeyboardMarkup(keyboard))

async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {"bkash": Config.BKASH_NUMBER, "nagad": Config.NAGAD_NUMBER, "rocket": Config.ROCKET_NUMBER}
    number = numbers[method]
    context.user_data["recharge_method"] = method
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Send money to: <code>{number}</code>\n"
        f"Then select the amount you sent:",
        deposit_amount_keyboard()
    )
    return ADD_MONEY_AMOUNT

async def deposit_amount_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("depamt_"):
        amt_str = data.split("_")[1]
        if amt_str == "custom":
            await query.message.reply_text("💬 Type the exact amount you sent (৳):")
            return ADD_MONEY_AMOUNT
        amount = float(amt_str)
        context.user_data["recharge_amount"] = amount
        await query.message.reply_text("🔑 Now send the <b>Transaction ID (TrxID)</b>:")
        return ADD_MONEY_TRX
    return ADD_MONEY_AMOUNT

async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Numbers only! Try again or choose a preset.")
        return ADD_MONEY_AMOUNT
    if amount < Config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ Minimum ৳{Config.MIN_DEPOSIT}. Try again:")
        return ADD_MONEY_AMOUNT
    context.user_data["recharge_amount"] = amount
    await update.message.reply_text("🔑 Now send the <b>Transaction ID (TrxID)</b>:")
    return ADD_MONEY_TRX

async def add_money_trx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = update.message.text.strip()
    if len(trx) < 5:
        await update.message.reply_text("❌ Invalid TrxID! Minimum 5 characters:")
        return ADD_MONEY_TRX
    method = context.user_data.get("recharge_method")
    amount = context.user_data.get("recharge_amount")
    tid = str(update.effective_user.id)
    req_id = f"DEP-{int(datetime.now().timestamp())}"
    with db() as conn:
        conn.execute(
            "INSERT INTO deposit_requests (request_id, telegram_id, method, amount, trx_id) VALUES (?,?,?,?,?)",
            (req_id, tid, method, amount, trx)
        )
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ <b>Deposit request submitted!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{req_id}</code>\n"
        f"💳 {method.upper()}\n"
        f"💰 ৳{amount:.2f}\n"
        f"🔑 <code>{trx}</code>\n\n"
        f"⚡ Verification in 2–5 minutes."
    )
    try:
        await context.bot.send_message(
            Config.ADMIN_USER_ID,
            f"🔔 <b>New Deposit</b>\n"
            f"👤 {tid}\n"
            f"💳 {method.upper()}  |  ৳{amount:.2f}\n"
            f"🔑 <code>{trx}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin notify: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 🛡️ ADMIN PANEL
# ─────────────────────────────────────────────────────────────────
async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        await edit_or_reply(update, "❌ Access denied.")
        return
    with db() as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pend_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status='⏳ Pending'").fetchone()[0]
        pend_deps = conn.execute("SELECT COUNT(*) FROM deposit_requests WHERE status='⏳ Pending'").fetchone()[0]
        mmode = conn.execute("SELECT value FROM settings WHERE key='maintenance_mode'").fetchone()["value"]
    mm_btn = "🟢 Turn ON Maintenance" if mmode == "OFF" else "🔴 Turn OFF Maintenance"
    keyboard = [
        [InlineKeyboardButton("📊 Orders", callback_data="adm_view_orders"),
         InlineKeyboardButton("💰 Deposits", callback_data="adm_view_deposits")],
        [InlineKeyboardButton("👤 Edit Balance", callback_data="adm_balance_set"),
         InlineKeyboardButton("📦 Add Product", callback_data="adm_product_add")],
        [InlineKeyboardButton("📤 Backup DB", callback_data="adm_backup_db"),
         InlineKeyboardButton("📥 Restore DB", callback_data="adm_restore_db")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast"),
         InlineKeyboardButton("🔍 Search User", callback_data="adm_search_user")],
        [InlineKeyboardButton(mm_btn, callback_data="adm_toggle_maintenance")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(
        update,
        f"🛠️ <b>Admin Dashboard</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Users: {users_count}\n"
        f"⏳ Orders: {pend_orders}\n"
        f"💵 Pending: {pend_deps}\n"
        f"⚙️ Maintenance: <b>{mmode}</b>",
        InlineKeyboardMarkup(keyboard)
    )

# admin callbacks (approve/reject, etc.)
async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not is_admin(get_user(str(update.effective_user.id))):
        await query.answer("❌ Unauthorized.", show_alert=True)
        return
    await query.answer()

    if data == "adm_toggle_maintenance":
        new = "OFF" if is_maintenance() else "ON"
        with db() as conn:
            conn.execute("UPDATE settings SET value = ? WHERE key = 'maintenance_mode'", (new,))
        await show_admin_panel_ui(update, context)

    elif data == "adm_backup_db":
        file = f"backup_{int(datetime.now().timestamp())}.db"
        try:
            src = sqlite3.connect(Config.DB_PATH)
            dst = sqlite3.connect(file)
            with dst:
                src.backup(dst)
            src.close(); dst.close()
            with open(file, "rb") as f:
                await context.bot.send_document(Config.ADMIN_USER_ID, f,
                    filename="skytopup_backup.db",
                    caption="📂 <b>Database Backup</b>")
            os.remove(file)
            await query.message.reply_text("✅ Backup sent to your DM.")
        except Exception as e:
            await query.message.reply_text(f"❌ Backup failed: {e}")

    elif data == "adm_view_orders":
        with db() as conn:
            orders = conn.execute("SELECT * FROM orders WHERE status='⏳ Pending' LIMIT 10").fetchall()
        if not orders:
            await query.message.reply_text("🟢 No pending orders.")
            return
        for o in orders:
            await query.message.reply_text(
                f"🆔 <code>{o['order_id']}</code>\n"
                f"👤 {o['telegram_id']}  |  📦 {o['product_name']} ({o['package']})\n"
                f"ℹ️ <code>{o['user_details']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{o['order_id']}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{o['order_id']}")]
                ])
            )
    elif data == "adm_view_deposits":
        with db() as conn:
            deps = conn.execute("SELECT * FROM deposit_requests WHERE status='⏳ Pending' LIMIT 10").fetchall()
        if not deps:
            await query.message.reply_text("🟢 No pending deposits.")
            return
        for d in deps:
            await query.message.reply_text(
                f"🆔 <code>{d['request_id']}</code>\n"
                f"👤 {d['telegram_id']}  |  💳 {d['method']}  |  ৳{d['amount']}\n"
                f"🔑 <code>{d['trx_id']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{d['request_id']}"),
                     InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{d['request_id']}")]
                ])
            )

    # approve/reject order
    elif data.startswith("adm_ord_approve_"):
        oid = data.replace("adm_ord_approve_", "")
        with db() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_id=? AND status='⏳ Pending'", (oid,)).fetchone()
            if not order:
                await query.message.edit_text("⚠️ Already processed.")
                return
            conn.execute("UPDATE orders SET status='✅ Completed' WHERE order_id=?", (oid,))
        await query.message.edit_text(f"✅ Order {oid} completed.")
        try:
            await context.bot.send_message(order["telegram_id"], f"🎉 Your order <code>{oid}</code> is complete!")
        except: pass

    elif data.startswith("adm_ord_reject_"):
        oid = data.replace("adm_ord_reject_", "")
        with db() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_id=? AND status='⏳ Pending'", (oid,)).fetchone()
            if not order:
                await query.message.edit_text("⚠️ Already processed.")
                return
            conn.execute("UPDATE orders SET status='❌ Rejected' WHERE order_id=?", (oid,))
            conn.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (order["price"], order["telegram_id"]))
        await query.message.edit_text(f"❌ Order {oid} rejected (refunded).")
        try:
            await context.bot.send_message(order["telegram_id"], f"❌ Order <code>{oid}</code> rejected. ৳{order['price']} refunded.")
        except: pass

    # approve/reject deposit
    elif data.startswith("adm_dep_approve_"):
        rid = data.replace("adm_dep_approve_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id=? AND status='⏳ Pending'", (rid,)).fetchone()
            if not dep:
                await query.message.edit_text("⚠️ Already processed.")
                return
            conn.execute("UPDATE deposit_requests SET status='✅ Approved' WHERE request_id=?", (rid,))
            conn.execute("UPDATE users SET balance=balance+? WHERE telegram_id=?", (dep["amount"], dep["telegram_id"]))
        await query.message.edit_text(f"✅ Deposit {rid} approved.")
        try:
            await context.bot.send_message(dep["telegram_id"], f"💰 ৳{dep['amount']} added to your wallet.")
        except: pass

    elif data.startswith("adm_dep_reject_"):
        rid = data.replace("adm_dep_reject_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id=? AND status='⏳ Pending'", (rid,)).fetchone()
            if not dep:
                await query.message.edit_text("⚠️ Already processed.")
                return
            conn.execute("UPDATE deposit_requests SET status='❌ Rejected' WHERE request_id=?", (rid,))
        await query.message.edit_text(f"❌ Deposit {rid} rejected.")
        try:
            await context.bot.send_message(dep["telegram_id"], "❌ Your recharge was rejected. Contact support.")
        except: pass

    elif data == "adm_broadcast":
        await query.message.reply_text("📢 Type the message to broadcast:")
        return ADMIN_BROADCAST_MSG
    elif data == "adm_search_user":
        await query.message.reply_text("🔍 Enter Telegram ID of the user:")
        return ADMIN_SEARCH_USER

# broadcast / search handlers
async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))): return ConversationHandler.END
    text = update.message.text
    with db() as conn:
        users = conn.execute("SELECT telegram_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u["telegram_id"], text)
            sent += 1
        except: pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent}/{len(users)} users.")
    return ConversationHandler.END

async def search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))): return ConversationHandler.END
    q = update.message.text.strip()
    user = get_user(q)  # search by telegram_id
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    info = (
        f"👤 <b>User Info</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{user['telegram_id']}</code>\n"
        f"👤 {user['name']}\n"
        f"💵 ৳{user['balance']:.2f}\n"
        f"🏅 {user['rank']}\n"
        f"🎁 {user['reward_points']} pts\n"
        f"📅 Joined: {user['created_at']}"
    )
    await update.message.reply_text(info, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# ⚖️ ADMIN BALANCE EDIT
# ─────────────────────────────────────────────────────────────────
async def start_balance_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("👤 Enter the Telegram ID:")
    return ADMIN_SET_BAL_ID

async def bal_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tid = update.message.text.strip()
    user = get_user(tid)
    if not user:
        await update.message.reply_text("❌ Not found. Try again:")
        return ADMIN_SET_BAL_ID
    context.user_data["tgt_bal_id"] = tid
    await update.message.reply_text(
        f"👤 {user['name']}\n💵 Current: ৳{user['balance']:.2f}\n\n👉 New balance:"
    )
    return ADMIN_SET_BAL_AMT

async def bal_amt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amt = float(update.message.text.strip())
    except:
        await update.message.reply_text("❌ Invalid amount. Try again:")
        return ADMIN_SET_BAL_AMT
    tid = context.user_data.get("tgt_bal_id")
    with db() as conn:
        conn.execute("UPDATE users SET balance=? WHERE telegram_id=?", (amt, tid))
    context.user_data.clear()
    await update.message.reply_text(f"✅ Balance updated to ৳{amt:.2f}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# ➕ ADD PRODUCT CONVERSATION
# ─────────────────────────────────────────────────────────────────
async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    kb = [[InlineKeyboardButton("Game", callback_data="cat_sel_game"),
           InlineKeyboardButton("Subscribe", callback_data="cat_sel_subscribe")]]
    await update.callback_query.message.reply_text("📂 Select category:", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["new_prod_cat"] = "game" if "game" in update.callback_query.data else "subscribe"
    await update.callback_query.message.reply_text("📦 Product name:")
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text("📝 Description:")
    return ADMIN_ADD_PROD_DESC

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_desc"] = update.message.text.strip()
    await update.message.reply_text("💎 JSON options:\n<code>[{\"amount\":\"...\",\"price\":...}]</code>")
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    try:
        json.loads(raw)
    except:
        await update.message.reply_text("❌ Invalid JSON. Try again:")
        return ADMIN_ADD_PROD_OPTS
    cat = context.user_data["new_prod_cat"]
    name = context.user_data["new_prod_name"]
    desc = context.user_data["new_prod_desc"]
    with db() as conn:
        conn.execute("INSERT INTO products (name, category, description, options) VALUES (?,?,?,?)",
                     (name, cat, desc, raw))
    context.user_data.clear()
    await update.message.reply_text("✅ Product added!")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 💾 ADMIN DB RESTORE
# ─────────────────────────────────────────────────────────────────
async def start_db_restore_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📥 Send your backup <code>.db</code> file.\n⚠️ This will replace current data.")
    return ADMIN_RESTORE_DB_STATE

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))): return ConversationHandler.END
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ Only .db files accepted.")
        return ADMIN_RESTORE_DB_STATE
    msg = await update.message.reply_text("⏳ Restoring...")
    try:
        file = await context.bot.get_file(doc.file_id)
        temp = "temp_restore.db"
        await file.download_to_drive(temp)
        # validate
        test = sqlite3.connect(temp)
        test.execute("SELECT name FROM sqlite_master WHERE type='table'")
        test.close()
        shutil.copyfile(temp, Config.DB_PATH)
        os.remove(temp)
        await msg.edit_text("✅ Database restored successfully!")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 👤 PROFILE & MISC
# ─────────────────────────────────────────────────────────────────
async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"💳 <b>My Wallet</b>\n━━━━━━━━━━━━━\n"
        f"👤 {UIBuilder.safe_text(u['name'])}\n"
        f"💰 ৳{u['balance']:,.2f}\n"
        f"🎁 {u['reward_points']} pts\n\n"
        f"➕ Recharge instantly 👇",
        InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Instant Recharge", callback_data="recharge")],
            [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
        ])
    )

async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"👤 <b>My Profile</b>\n━━━━━━━━━━━━━\n"
        f"🆔 <code>{u['telegram_id']}</code>\n"
        f"👤 {UIBuilder.safe_text(u['name'])}\n"
        f"🏅 {u['rank']}\n"
        f"💵 ৳{u['balance']:.2f}\n"
        f"📅 Joined: {u['created_at']}",
        UIBuilder.back_button()
    )

async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "⚙️ <b>Settings</b>\n\nMore options coming soon.", UIBuilder.back_button())

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "💬 <b>24/7 Support</b>\n\nContact @SkyTopUpSupport", UIBuilder.back_button())

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE telegram_id=? ORDER BY created_at DESC LIMIT 5",
            (str(update.effective_user.id),)
        ).fetchall()
    if not orders:
        await edit_or_reply(update, "📭 No orders yet.", UIBuilder.back_button())
        return
    lines = ["📦 <b>Last Orders</b>\n"]
    for o in orders:
        lines.append(f"🆔 <code>{o['order_id']}</code> | {o['product_name']} | ৳{o['price']} | {o['status']}")
    await edit_or_reply(update, "\n".join(lines), UIBuilder.back_button())

# ─────────────────────────────────────────────────────────────────
# 🔄 MAIN CALLBACK ROUTER
# ─────────────────────────────────────────────────────────────────
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
    elif data.startswith("depamt_"):
        await deposit_amount_button(update, context)

# ─────────────────────────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(Config.BOT_TOKEN).build()

    # Registration (password only)
    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
            REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_receive_password)],
            REG_CONFIRM_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, reg_confirm_password)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Order
    order_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={
            ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Deposit (with amount buttons)
    deposit_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_recharge_instructions_ui, pattern=r"^recharge_(bkash|nagad|rocket)$")],
        states={
            ADD_MONEY_AMOUNT: [
                CallbackQueryHandler(deposit_amount_button, pattern=r"^depamt_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_amount_handler)
            ],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_trx_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin balance
    admin_bal_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_balance_set, pattern="^adm_balance_set$")],
        states={
            ADMIN_SET_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_id_received)],
            ADMIN_SET_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_amt_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin product add
    admin_prod_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_product_add, pattern="^adm_product_add$")],
        states={
            ADMIN_ADD_PROD_CAT: [CallbackQueryHandler(prod_cat_received, pattern="^cat_sel_")],
            ADMIN_ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_name_received)],
            ADMIN_ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_desc_received)],
            ADMIN_ADD_PROD_OPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_opts_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin restore
    admin_restore_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_db_restore_process, pattern="^adm_restore_db$")],
        states={
            ADMIN_RESTORE_DB_STATE: [MessageHandler(filters.Document.ALL, db_file_restore_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin broadcast
    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u,c: ADMIN_BROADCAST_MSG, pattern="^adm_broadcast$")],
        states={
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin search
    search_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u,c: ADMIN_SEARCH_USER, pattern="^adm_search_user$")],
        states={
            ADMIN_SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_user_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(deposit_handler)
    app.add_handler(admin_bal_handler)
    app.add_handler(admin_prod_handler)
    app.add_handler(admin_restore_handler)
    app.add_handler(broadcast_handler)
    app.add_handler(search_handler)

    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)(?!depamt_)"))

    logger.info("💫 SKY TopUp Elite launched...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
