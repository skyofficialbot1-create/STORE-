#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — Enterprise Premium Edition v4.0
────────────────────────────────────────────────────────
Features:
• Email OTP verification with retry & robust delivery
• Multi‑method wallet recharge (bKash/Nagad/Rocket)
• Product catalogue with dynamic options
• Order & transaction history
• Full admin panel: order/deposit approval, balance edit,
  product management, DB backup/restore, broadcast, user search
• Maintenance mode, referral points system (coming soon)
"""

import logging, os, json, random, string, smtplib, sqlite3, hashlib, re, secrets, asyncio, shutil
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

# ─────────────────────────────────────────────────────────────────
# 🎛️ CONFIGURATION
# ─────────────────────────────────────────────────────────────────
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_EMAIL = os.getenv("SMTP_EMAIL", "mehedihasan706261@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "qgpp laff mkgo iktz")
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    MIN_DEPOSIT = 50.0
    OTP_VALID_MINUTES = 5
    MAX_OTP_ATTEMPTS = 3
    MIN_PASSWORD_LENGTH = 6
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)
    DEV_MODE = not EMAIL_SENDING_ENABLED
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
# 🗄️ DATABASE LAYER
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT DEFAULT 'User',
                balance REAL DEFAULT 0.0,
                reward_points INTEGER DEFAULT 0,
                rank TEXT DEFAULT 'Silver Member',
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
                status TEXT DEFAULT 'Pending',
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS deposit_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT UNIQUE NOT NULL,
                telegram_id TEXT NOT NULL,
                method TEXT NOT NULL,
                amount REAL NOT NULL,
                trx_id TEXT NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('maintenance_mode', 'OFF')")

        # seed default products
        c.execute("SELECT COUNT(*) as cnt FROM products")
        if c.fetchone()["cnt"] == 0:
            default_products = [
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

# ─────────────────────────────────────────────────────────────────
# 🔐 SECURITY & EMAIL HELPERS
# ─────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = "SKY_TOPUP_2024_v2"
    return hashlib.sha256((salt + password).encode()).hexdigest()

def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)

def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def _sync_send_otp_email(to_email: str, otp: str) -> bool:
    """Synchronous email sender – called via asyncio.to_thread."""
    if Config.DEV_MODE:
        logger.info("🔧 DEV MODE — OTP for %s: %s", to_email, otp)
        return True
    if not Config.EMAIL_SENDING_ENABLED:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"SKY TopUp <{Config.SMTP_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "🔐 SKY TopUp — OTP Verification Code"
    text_body = f"Your SKY TopUp OTP is: {otp}\n\nValid for {Config.OTP_VALID_MINUTES} minutes."
    msg.attach(MIMEText(text_body, "plain", "utf-8"))

    # retry logic for robust delivery
    for attempt in range(2):
        try:
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(Config.SMTP_EMAIL, Config.SMTP_PASSWORD)
                server.sendmail(Config.SMTP_EMAIL, to_email, msg.as_string())
            return True
        except Exception as e:
            logger.error(f"SMTP attempt {attempt+1} failed: %s", e)
            if attempt == 0:
                asyncio.sleep(2)   # small wait before retry (this is sync, but acceptable)
    return False

async def send_otp_email_async(to_email: str, otp: str) -> bool:
    """Non‑blocking OTP email dispatch."""
    return await asyncio.to_thread(_sync_send_otp_email, to_email, otp)

# ─────────────────────────────────────────────────────────────────
# 🎨 UI BUILDER
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

# ─────────────────────────────────────────────────────────────────
# 👤 REGISTRATION & START FLOW
# ─────────────────────────────────────────────────────────────────
REG_EMAIL, REG_OTP, REG_PASSWORD, REG_CONFIRM_PASSWORD = range(4)
ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC, ADMIN_ADD_PROD_OPTS = range(30, 34)
ADMIN_RESTORE_DB_STATE = 40
ADMIN_BROADCAST_MSG = 50
ADMIN_SEARCH_USER = 60

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_row = get_user(str(user.id))
    if is_maintenance() and not (user_row and is_admin(user_row)):
        await update.message.reply_text(
            "⚠️ <b>System Maintenance in progress!</b>\n\n"
            "We are working to restore service quickly. Sorry for the inconvenience.",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    if user_row:
        with db() as conn:
            conn.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE telegram_id = ?", (str(user.id),))
        welcome = (
            f"⚡ <b>SKY TOPUP — PREMIUM BOT</b> ⚡\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👋 Welcome back, <b>{UIBuilder.safe_text(user_row['name'])}</b>!\n\n"
            f"💵 <b>Balance:</b> ৳ {user_row['balance']:,.2f}\n"
            f"🏅 <b>Rank:</b> {user_row['rank']}\n"
            f"🎁 <b>Points:</b> {user_row['reward_points']} pts\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"✨ Use the menu below to explore our services:"
        )
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))
        return ConversationHandler.END

    welcome = (
        f"⚡ <b>SKY TOPUP — PREMIUM BOT</b> ⚡\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Hello, <b>{UIBuilder.safe_text(user.first_name or 'User')}</b>! 👋\n\n"
        f"To use our high‑speed top‑up service, please complete the email verification.\n\n"
        f"👉 <b>Enter your Gmail address to begin:</b>"
    )
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    return REG_EMAIL

async def reg_receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()
    if not is_valid_email(email):
        await update.message.reply_text("❌ <b>Invalid email!</b> Please provide a correct Gmail address:")
        return REG_EMAIL
    if get_user_by_email(email):
        await update.message.reply_text("⚠️ This email is already registered. Try another one:")
        return REG_EMAIL

    otp = generate_otp()
    expires_at = (datetime.utcnow() + timedelta(minutes=Config.OTP_VALID_MINUTES)).strftime("%Y-%m-%d %H:%M:%S")
    with db() as conn:
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (str(update.effective_user.id),))
        conn.execute("INSERT INTO otp_codes (telegram_id, otp_code, expires_at) VALUES (?, ?, ?)",
                     (str(update.effective_user.id), otp, expires_at))
    context.user_data["reg_email"] = email

    status_msg = await update.message.reply_text("⏳ <i>Sending OTP to your email... Please wait.</i>", parse_mode=ParseMode.HTML)
    success = await send_otp_email_async(email, otp)
    if success:
        await status_msg.edit_text(
            f"📬 <b>OTP sent successfully!</b>\n\n"
            f"Enter the 6‑digit code you received in your email:",
            parse_mode=ParseMode.HTML
        )
        return REG_OTP
    else:
        await status_msg.edit_text(
            "❌ <b>OTP delivery failed.</b>\n"
            "Please check your email address or try again later.\n\n"
            "Enter a valid email to retry:",
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
        await update.message.reply_text("❌ <b>Wrong OTP!</b> Please try again:")
        return REG_OTP
    with db() as conn:
        conn.execute("UPDATE otp_codes SET is_used = 1 WHERE id = ?", (row["id"],))
    await update.message.reply_text("✅ Verified! Now create a password for your account (minimum 6 characters):")
    return REG_PASSWORD

async def reg_receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if len(password) < Config.MIN_PASSWORD_LENGTH:
        await update.message.reply_text("❌ Password too short! Please enter at least 6 characters:")
        return REG_PASSWORD
    context.user_data["reg_password"] = password
    await update.message.reply_text("🔐 Confirm your password by typing it again:")
    return REG_CONFIRM_PASSWORD

async def reg_confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirm_pass = update.message.text.strip()
    password = context.user_data.get("reg_password")
    if confirm_pass != password:
        await update.message.reply_text("❌ Passwords do not match! Enter your password again:")
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
    await update.message.reply_text("🎉 <b>Registration successful!</b> You received a 10 Taka welcome bonus.")
    user_row = get_user(telegram_id)
    await update.message.reply_text("✨ Use the menu below:", reply_markup=UIBuilder.main_menu(user_row))
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Process cancelled.")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 🛒 SHOPPING & PRODUCTS
# ─────────────────────────────────────────────────────────────────
async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 Game Top-Up", callback_data="category_game")],
        [InlineKeyboardButton("🍿 OTT & Subscriptions", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")],
    ]
    await edit_or_reply(update, "📂 <b>Product Categories</b>\n\nSelect a category:", InlineKeyboardMarkup(keyboard))

async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
    if not products:
        await edit_or_reply(update, "⚠️ No products found in this category.", UIBuilder.back_button("shop"))
        return
    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="shop")])
    await edit_or_reply(update, "📦 <b>Product List</b>\n\nChoose your desired product:", InlineKeyboardMarkup(keyboard))

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
        f"⚡ <b>{product['icon']} {product['name']}</b>\n\n"
        f"📌 <b>Description:</b> {product['description']}\n\n"
        f"Select a package:",
        InlineKeyboardMarkup(keyboard)
    )

# ─────────────────────────────────────────────────────────────────
# 📋 ORDER FLOW
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
            f"❌ <b>Insufficient balance!</b>\n\n"
            f"Your balance: ৳{user_row['balance']:.2f}\n"
            f"Required: ৳{price:.2f}\n\n"
            f"Please recharge your wallet first."
        )
        return ConversationHandler.END
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    await query.message.reply_text(
        f"🛒 <b>Confirm Checkout</b>\n\n"
        f"📦 Product: {product['name']}\n"
        f"📎 Package: {selected_package['amount']}\n"
        f"💰 Price: ৳{price}\n\n"
        f"👉 Enter your <b>Game ID / UID / Details</b> (minimum 3 characters):"
    )
    return ORDER_DETAILS_STATE

async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_details = update.message.text.strip()
    if len(user_details) < 3:
        await update.message.reply_text("❌ Invalid details! Provide a valid ID (min 3 characters):")
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
        f"🎉 <b>Order placed successfully!</b>\n\n"
        f"🆔 Order ID: <code>{order_id}</code>\n"
        f"💰 Deducted: ৳{price}\n"
        f"⚡ The admin will complete your order within 5–15 minutes."
    )
    # notify admin
    try:
        admin_keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>New Order</b>\n\n"
                 f"👤 User: {telegram_id}\n"
                 f"🆔 Order: <code>{order_id}</code>\n"
                 f"📦 {product_name} ({package['amount']})\n"
                 f"ℹ️ Details: <code>{user_details}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        logger.error(f"Admin notify error: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# ➕ AUTOMATED ADD MONEY
# ─────────────────────────────────────────────────────────────────
async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="recharge_bkash"),
         InlineKeyboardButton("📱 Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(
        update,
        f"💳 <b>Instant Wallet Recharge</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚠️ <b>Minimum recharge:</b> ৳{Config.MIN_DEPOSIT:.2f}\n\n"
        f"Select your payment method 👇",
        InlineKeyboardMarkup(keyboard)
    )

async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {"bkash": Config.BKASH_NUMBER, "nagad": Config.NAGAD_NUMBER, "rocket": Config.ROCKET_NUMBER}
    number = numbers.get(method, "N/A")
    context.user_data["recharge_method"] = method
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()} Payment Gateway</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👉 Send money to: <code>{number}</code>\n\n"
        f"📌 <b>Steps:</b>\n"
        f"1. Send the exact amount via {method.title()}.\n"
        f"2. Minimum: ৳{Config.MIN_DEPOSIT}\n"
        f"3. Copy the Transaction ID (TrxID).\n\n"
        f"💵 <b>Enter the amount you sent (numbers only):</b>"
    )
    return ADD_MONEY_AMOUNT

async def add_money_amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid input! Please enter a number (e.g. 100):")
        return ADD_MONEY_AMOUNT
    if amount < Config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ Minimum deposit is ৳{Config.MIN_DEPOSIT}. Try again:")
        return ADD_MONEY_AMOUNT
    context.user_data["recharge_amount"] = amount
    await update.message.reply_text("🔑 Now enter the <b>Transaction ID (TrxID)</b>:")
    return ADD_MONEY_TRX

async def add_money_trx_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx_id = update.message.text.strip()
    if len(trx_id) < 5:
        await update.message.reply_text("❌ Invalid TrxID! It must be at least 5 characters:")
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
        f"✅ <b>Deposit request submitted!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Tracking ID: <code>{req_id}</code>\n"
        f"💳 Method: {method.upper()}\n"
        f"💰 Amount: ৳{amount:.2f}\n"
        f"🔑 TrxID: <code>{trx_id}</code>\n\n"
        f"⚡ Our team will verify and add the balance within 2–5 minutes."
    )
    # notify admin
    try:
        admin_keyboard = [
            [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}"),
             InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")]
        ]
        await context.bot.send_message(
            chat_id=Config.ADMIN_USER_ID,
            text=f"🔔 <b>New Deposit Request</b>\n\n"
                 f"👤 User: {telegram_id}\n"
                 f"💳 Method: {method.upper()}\n"
                 f"💰 Amount: ৳{amount:.2f}\n"
                 f"🔑 TrxID: <code>{trx_id}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(admin_keyboard)
        )
    except Exception as e:
        logger.error(f"Deposit notify error: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 🛠️ ENTERPRISE ADMIN PANEL
# ─────────────────────────────────────────────────────────────────
async def show_admin_panel_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        await edit_or_reply(update, "❌ Access denied!")
        return
    with db() as conn:
        users_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'").fetchone()[0]
        pending_deposits = conn.execute("SELECT COUNT(*) FROM deposit_requests WHERE status = 'Pending'").fetchone()[0]
        m_mode = conn.execute("SELECT value FROM settings WHERE key = 'maintenance_mode'").fetchone()["value"]
    m_btn_text = "🟢 Turn Maintenance ON" if m_mode == "OFF" else "🔴 Turn Maintenance OFF"
    keyboard = [
        [InlineKeyboardButton("📊 View Orders", callback_data="adm_view_orders"),
         InlineKeyboardButton("💰 View Deposits", callback_data="adm_view_deposits")],
        [InlineKeyboardButton("👤 Edit Balance", callback_data="adm_balance_set"),
         InlineKeyboardButton("📦 Add Product", callback_data="adm_product_add")],
        [InlineKeyboardButton("📤 Backup Database", callback_data="adm_backup_db"),
         InlineKeyboardButton("📥 Restore Database", callback_data="adm_restore_db")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔍 Search User", callback_data="adm_search_user")],
        [InlineKeyboardButton(m_btn_text, callback_data="adm_toggle_maintenance")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(
        update,
        f"🛠️ <b>Admin Dashboard</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 Total Users: {users_count}\n"
        f"⏳ Pending Orders: {pending_orders}\n"
        f"💵 Pending Deposits: {pending_deposits}\n"
        f"⚙️ Maintenance Mode: <b>{m_mode}</b>\n\n"
        f"Select an option:",
        InlineKeyboardMarkup(keyboard)
    )

async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_row = get_user(str(update.effective_user.id))
    if not is_admin(user_row):
        await query.answer("❌ You are not an admin.", show_alert=True)
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
                    caption=f"📂 <b>SKY TOPUP DATABASE BACKUP</b>\n"
                            f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            f"⚠️ Keep this file safe.",
                    parse_mode=ParseMode.HTML
                )
            os.remove(backup_file)
            await query.message.reply_text("✅ Database backup sent to your inbox.")
        except Exception as e:
            logger.error(f"Backup error: {e}")
            await query.message.reply_text(f"❌ Backup failed: {str(e)}")

    elif data == "adm_view_orders":
        with db() as conn:
            orders = conn.execute("SELECT * FROM orders WHERE status = 'Pending' LIMIT 10").fetchall()
        if not orders:
            await query.message.reply_text("🟢 No pending orders!")
            return
        for o in orders:
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{o['order_id']}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{o['order_id']}")]
            ]
            await query.message.reply_text(
                f"🆔 Order: <code>{o['order_id']}</code>\n"
                f"👤 User: {o['telegram_id']}\n"
                f"📦 {o['product_name']} ({o['package']})\n"
                f"ℹ️ Details: <code>{o['user_details']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    elif data == "adm_view_deposits":
        with db() as conn:
            deposits = conn.execute("SELECT * FROM deposit_requests WHERE status = 'Pending' LIMIT 10").fetchall()
        if not deposits:
            await query.message.reply_text("🟢 No pending deposits!")
            return
        for d in deposits:
            keyboard = [
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{d['request_id']}"),
                 InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{d['request_id']}")]
            ]
            await query.message.reply_text(
                f"🆔 Request: <code>{d['request_id']}</code>\n"
                f"👤 User: {d['telegram_id']}\n"
                f"💳 {d['method'].upper()} | ৳{d['amount']}\n"
                f"🔑 TrxID: <code>{d['trx_id']}</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    # Approve/Reject order
    elif data.startswith("adm_ord_approve_"):
        ord_id = data.replace("adm_ord_approve_", "")
        with db() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_id = ? AND status = 'Pending'", (ord_id,)).fetchone()
            if not order:
                await query.message.edit_text(f"⚠️ Order {ord_id} already processed.")
                return
            conn.execute("UPDATE orders SET status = 'Completed' WHERE order_id = ?", (ord_id,))
        await query.message.edit_text(f"✅ Order {ord_id} completed.")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"🎉 <b>Order Completed!</b>\n\n"
                     f"🆔 Order ID: <code>{ord_id}</code>\n"
                     f"📦 {order['product_name']} ({order['package']})\n"
                     f"Thank you for using SKY TopUp."
            )
        except: pass

    elif data.startswith("adm_ord_reject_"):
        ord_id = data.replace("adm_ord_reject_", "")
        with db() as conn:
            order = conn.execute("SELECT * FROM orders WHERE order_id = ? AND status = 'Pending'", (ord_id,)).fetchone()
            if not order:
                await query.message.edit_text(f"⚠️ Order {ord_id} already processed.")
                return
            conn.execute("UPDATE orders SET status = 'Rejected' WHERE order_id = ?", (ord_id,))
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (order["price"], order["telegram_id"]))
        await query.message.edit_text(f"❌ Order {ord_id} rejected (refunded).")
        try:
            await context.bot.send_message(
                chat_id=order["telegram_id"],
                text=f"❌ <b>Order Rejected</b>\n\n"
                     f"🆔 Order ID: <code>{ord_id}</code>\n"
                     f"💰 Refunded ৳{order['price']}."
            )
        except: pass

    # Approve/Reject deposit
    elif data.startswith("adm_dep_approve_"):
        req_id = data.replace("adm_dep_approve_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = 'Pending'", (req_id,)).fetchone()
            if not dep:
                await query.message.edit_text(f"⚠️ Request {req_id} already processed.")
                return
            conn.execute("UPDATE deposit_requests SET status = 'Approved' WHERE request_id = ?", (req_id,))
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
        await query.message.edit_text(f"✅ Deposit {req_id} approved.")
        try:
            await context.bot.send_message(
                chat_id=dep["telegram_id"],
                text=f"🎉 <b>Recharge Successful!</b>\n\n"
                     f"💰 Added: ৳{dep['amount']:.2f}\n"
                     f"💳 Method: {dep['method'].upper()}"
            )
        except: pass

    elif data.startswith("adm_dep_reject_"):
        req_id = data.replace("adm_dep_reject_", "")
        with db() as conn:
            dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id = ? AND status = 'Pending'", (req_id,)).fetchone()
            if not dep:
                await query.message.edit_text(f"⚠️ Request {req_id} already processed.")
                return
            conn.execute("UPDATE deposit_requests SET status = 'Rejected' WHERE request_id = ?", (req_id,))
        await query.message.edit_text(f"❌ Deposit {req_id} rejected.")
        try:
            await context.bot.send_message(
                chat_id=dep["telegram_id"],
                text=f"❌ <b>Recharge Rejected</b>\n\n"
                     f"Please contact support for more info."
            )
        except: pass

    elif data == "adm_broadcast":
        await query.message.reply_text("📢 Enter the message you want to broadcast to all users:")
        return ADMIN_BROADCAST_MSG

    elif data == "adm_search_user":
        await query.message.reply_text("🔍 Enter the Telegram ID or email of the user:")
        return ADMIN_SEARCH_USER

async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    text = update.message.text
    with db() as conn:
        users = conn.execute("SELECT telegram_id FROM users").fetchall()
    success = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["telegram_id"], text=text)
            success += 1
        except:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {success}/{len(users)} users.")
    return ConversationHandler.END

async def search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    query = update.message.text.strip()
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE telegram_id = ? OR email = ?", (query, query)).fetchone()
    if not user:
        await update.message.reply_text("❌ User not found.")
        return ConversationHandler.END
    info = (
        f"👤 <b>User Details</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"• Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"• Name: {user['name']}\n"
        f"• Email: {user['email']}\n"
        f"• Balance: ৳{user['balance']:.2f}\n"
        f"• Rank: {user['rank']}\n"
        f"• Points: {user['reward_points']}\n"
        f"• Joined: {user['created_at']}"
    )
    await update.message.reply_text(info, parse_mode=ParseMode.HTML)
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 🛠️ BALANCE SET CONVERSATION
# ─────────────────────────────────────────────────────────────────
async def start_balance_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("👤 Enter the <b>Telegram ID</b> of the user:")
    return ADMIN_SET_BAL_ID

async def bal_id_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tgt_id = update.message.text.strip()
    user_row = get_user(tgt_id)
    if not user_row:
        await update.message.reply_text("❌ User not found. Enter a valid Telegram ID:")
        return ADMIN_SET_BAL_ID
    context.user_data["tgt_bal_id"] = tgt_id
    await update.message.reply_text(
        f"👤 User: {user_row['name']}\n"
        f"💵 Current Balance: ৳{user_row['balance']:.2f}\n\n"
        f"👉 <b>Enter the new balance amount:</b>"
    )
    return ADMIN_SET_BAL_AMT

async def bal_amt_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_bal = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Invalid number. Please enter a valid amount:")
        return ADMIN_SET_BAL_AMT
    tgt_id = context.user_data.get("tgt_bal_id")
    with db() as conn:
        conn.execute("UPDATE users SET balance = ? WHERE telegram_id = ?", (new_bal, tgt_id))
    context.user_data.clear()
    await update.message.reply_text(f"✅ Balance updated to ৳{new_bal:.2f}.")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 📥 ADMIN RESTORE DATABASE PROCESS
# ─────────────────────────────────────────────────────────────────
async def start_db_restore_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    await query.message.reply_text(
        "📥 <b>Database Restore</b>\n\n"
        "Upload your backup <code>.db</code> file.\n"
        "⚠️ <i>This will replace the current database!</i>\n\n"
        "Type /cancel to abort."
    )
    return ADMIN_RESTORE_DB_STATE

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ Invalid file format. Please send a valid <b>.db</b> file:")
        return ADMIN_RESTORE_DB_STATE
    status_msg = await update.message.reply_text("⏳ <i>Downloading and verifying...</i>", parse_mode=ParseMode.HTML)
    try:
        file_obj = await context.bot.get_file(doc.file_id)
        temp_path = "temp_restore.db"
        await file_obj.download_to_drive(temp_path)
        # validate
        test_conn = sqlite3.connect(temp_path)
        test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        test_conn.close()
        shutil.copyfile(temp_path, Config.DB_PATH)
        os.remove(temp_path)
        await status_msg.edit_text("✅ <b>Database restored successfully!</b>", parse_mode=ParseMode.HTML)
    except Exception as e:
        await status_msg.edit_text(f"❌ Restore failed: {str(e)}")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# ➕ DYNAMIC PRODUCT ADD CONVERSATION
# ─────────────────────────────────────────────────────────────────
async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Game", callback_data="cat_sel_game"),
         InlineKeyboardButton("Subscribe", callback_data="cat_sel_subscribe")]
    ]
    await query.message.reply_text("📂 Select product category:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = "game" if "game" in query.data else "subscribe"
    context.user_data["new_prod_cat"] = category
    await query.message.reply_text("📦 Enter the <b>product name</b> (e.g. Free Fire 500 Diamonds):")
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["new_prod_name"] = name
    await update.message.reply_text("📝 Enter a <b>short description</b>:")
    return ADMIN_ADD_PROD_DESC

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["new_prod_desc"] = desc
    await update.message.reply_text(
        "💎 Now enter the packages in JSON format:\n"
        "Example:\n"
        '<code>[{"amount": "100 Diamonds", "price": 100}, {"amount": "200 Diamonds", "price": 200}]</code>'
    )
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    opts_raw = update.message.text.strip()
    try:
        json.loads(opts_raw)
    except ValueError:
        await update.message.reply_text("❌ Invalid JSON. Please try again:")
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
    await update.message.reply_text("✅ Product added successfully!")
    return ConversationHandler.END

# ─────────────────────────────────────────────────────────────────
# 👤 PROFILE & GENERAL VIEWS
# ─────────────────────────────────────────────────────────────────
async def show_balance_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    msg = (
        f"💰 <b>My Wallet Balance</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 {UIBuilder.safe_text(user_row['name'])}\n"
        f"💳 Balance: ৳{user_row['balance']:,.2f}\n"
        f"🎁 Reward Points: {user_row['reward_points']:,} pts\n\n"
        f"Recharge instantly 👇"
    )
    keyboard = [
        [InlineKeyboardButton("➕ Instant Recharge", callback_data="recharge")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(update, msg, InlineKeyboardMarkup(keyboard))

async def show_profile_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_row = get_user(str(update.effective_user.id))
    await edit_or_reply(
        update,
        f"👤 <b>My Profile</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 Name: {UIBuilder.safe_text(user_row['name'])}\n"
        f"📧 Email: <code>{user_row['email']}</code>\n"
        f"🏅 Rank: {user_row['rank']}\n"
        f"💳 Balance: ৳{user_row['balance']:.2f}\n"
        f"📅 Joined: {user_row['created_at']}",
        UIBuilder.back_button("back_main")
    )

async def show_settings_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "⚙️ <b>Settings & Security</b>\n\nMore features coming soon.", UIBuilder.back_button("back_main"))

async def show_help_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_reply(update, "💬 <b>24/7 Customer Support</b>\n\nFor any issues, contact @SkyTopUpSupport", UIBuilder.back_button("back_main"))

async def show_orders_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 5",
            (str(update.effective_user.id),)
        ).fetchall()
    if not orders:
        await edit_or_reply(update, "📭 You have no orders yet.", UIBuilder.back_button("back_main"))
        return
    lines = ["📦 <b>Your Last 5 Orders:</b>\n"]
    for o in orders:
        lines.append(f"🆔 <code>{o['order_id']}</code> | 📦 {o['product_name']} | ৳{o['price']} | {o['status']}")
    await edit_or_reply(update, "\n\n".join(lines), UIBuilder.back_button("back_main"))

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

# ─────────────────────────────────────────────────────────────────
# 🚀 MAIN RUNNER
# ─────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(Config.BOT_TOKEN).build()

    # Registration
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

    # Order
    order_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected_handler, pattern=r"^package_\d+_\d+$")],
        states={
            ORDER_DETAILS_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Deposit
    deposit_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_recharge_instructions_ui, pattern=r"^recharge_(bkash|nagad|rocket)$")],
        states={
            ADD_MONEY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_amount_handler)],
            ADD_MONEY_TRX: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_money_trx_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Balance
    admin_balance_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_balance_set, pattern="^adm_balance_set$")],
        states={
            ADMIN_SET_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_id_received)],
            ADMIN_SET_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_amt_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Add Product
    admin_product_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_product_add, pattern="^adm_product_add$")],
        states={
            ADMIN_ADD_PROD_CAT: [CallbackQueryHandler(prod_cat_received, pattern="^cat_sel_")],
            ADMIN_ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_name_received)],
            ADMIN_ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_desc_received)],
            ADMIN_ADD_PROD_OPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_opts_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Restore
    admin_restore_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_db_restore_process, pattern="^adm_restore_db$")],
        states={
            ADMIN_RESTORE_DB_STATE: [MessageHandler(filters.Document.ALL, db_file_restore_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Broadcast
    admin_broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u,c: ADMIN_BROADCAST_MSG, pattern="^adm_broadcast$")],
        states={
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin Search User
    admin_search_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u,c: ADMIN_SEARCH_USER, pattern="^adm_search_user$")],
        states={
            ADMIN_SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_user_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    app.add_handler(reg_handler)
    app.add_handler(order_handler)
    app.add_handler(deposit_handler)
    app.add_handler(admin_balance_handler)
    app.add_handler(admin_product_handler)
    app.add_handler(admin_restore_handler)
    app.add_handler(admin_broadcast_handler)
    app.add_handler(admin_search_handler)

    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern=r"^(?!package_)(?!adm_)"))

    logger.info("🌟 SKY TopUp Enterprise Bot started...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
