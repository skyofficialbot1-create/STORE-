#!/usr/bin/env python3
"""
SKY TopUp Telegram Bot — Ultimate Enterprise v6.0
────────────────────────────────────────────────
• Fully DYNAMIC categories — add "YouTube Premium", "Proxy", or ANY new
  category from the Admin Panel and it instantly appears in the user shop.
  No more hardcoded Game/VPN/Streaming — the bot builds the menu from
  whatever categories exist in the database.
• Auto‑delivery (email/password/activation key) OR manual (user ID) —
  chosen per‑product when the admin creates it.
• Clean, single‑column "premium" button layout everywhere (no cramped
  side‑by‑side rows) — built to feel like a polished storefront.
• VPN / Proxy / Streaming / YouTube Premium accounts auto‑delivery
• Duration‑based expiry calculation & display
• Stock management for digital goods
• Click‑driven recharge with preset amounts
• Full admin panel (orders, deposits, balance, products, categories,
  stock, DB backup/restore, broadcast, search)
"""

import logging, os, json, sqlite3, hashlib, secrets, shutil
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

# ─────────────────────────────────────────────
# 🎛️ CONFIG
# ─────────────────────────────────────────────
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk")
    BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01742958563")
    NAGAD_NUMBER = os.getenv("NAGAD_NUMBER", "01748506069")
    ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01742958563")
    MIN_DEPOSIT = 50.0
    MIN_PASSWORD_LENGTH = 6
    DB_PATH = os.getenv("DB_PATH", "skytopup.db")
    ADMIN_USER_ID = 7689218221
    BRAND_NAME = "SKY TOPUP"

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("SkyTopUp")

# ─────────────────────────────────────────────
# 🗄️ DATABASE
# ─────────────────────────────────────────────
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
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                telegram_id TEXT NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                package TEXT NOT NULL,
                price REAL NOT NULL,
                user_details TEXT,
                delivered_details TEXT,
                status TEXT DEFAULT '⏳ Pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        # NOTE: category is now a free‑text, admin‑defined value — not a
        # fixed enum. delivery_type controls whether checkout asks the
        # buyer for an ID (manual) or ships stock instantly (auto).
        c.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                delivery_type TEXT DEFAULT 'manual',
                icon TEXT DEFAULT '📦',
                description TEXT,
                options TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '📦',
                display_order INTEGER DEFAULT 0,
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
                status TEXT DEFAULT '⏳ Pending',
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

        # Stock table for auto‑delivery accounts (VPN / Proxy / YouTube / Streaming / etc.)
        c.execute("""
            CREATE TABLE IF NOT EXISTS account_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                email TEXT NOT NULL,
                password TEXT NOT NULL,
                activation_key TEXT,
                status TEXT DEFAULT 'available',
                order_id TEXT,
                sold_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # seed default categories
        c.execute("SELECT COUNT(*) FROM categories")
        if c.fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO categories (name, icon, display_order) VALUES (?,?,?)",
                [
                    ("Game Top-Up", "🎮", 1),
                    ("VPN Premium", "🔐", 2),
                    ("Proxy", "🌐", 3),
                    ("YouTube Premium", "▶️", 4),
                    ("Streaming", "🍿", 5),
                ]
            )

        # seed products if empty
        c.execute("SELECT COUNT(*) FROM products")
        if c.fetchone()[0] == 0:
            c.executemany(
                "INSERT INTO products (name, category, delivery_type, icon, description, options) VALUES (?,?,?,?,?,?)",
                [
                    ("Free Fire Diamonds", "Game Top-Up", "manual", "💎",
                     "ফ্রি ফায়ার ডায়মন্ড টপ-আপ",
                     json.dumps([
                         {"amount": "💎 100 Diamonds", "price": 100, "valid_days": 0},
                         {"amount": "💎 310 Diamonds", "price": 300, "valid_days": 0},
                         {"amount": "💎 520 Diamonds", "price": 500, "valid_days": 0},
                     ])),
                    ("Netflix Premium", "Streaming", "auto", "🎬",
                     "নেটফ্লিক্স প্রিমিয়াম সাবস্ক্রিপশন",
                     json.dumps([
                         {"amount": "🎬 1 Month Screen", "price": 200, "valid_days": 30},
                         {"amount": "🎬 3 Months Premium", "price": 500, "valid_days": 90},
                     ])),
                    ("Nord VPN", "VPN Premium", "auto", "🔐",
                     "নর্ড ভিপিএন প্রিমিয়াম অ্যাকাউন্ট",
                     json.dumps([
                         {"amount": "🔐 1 Month", "price": 150, "valid_days": 30},
                         {"amount": "🔐 3 Months", "price": 400, "valid_days": 90},
                     ])),
                    ("World's Best VPN Proxy", "Proxy", "auto", "🌐",
                     "পৃথিবীর সবচেয়ে দ্রুত ও নিরাপদ ভিপিএন প্রক্সি সার্ভিস",
                     json.dumps([
                         {"amount": "🌐 1 Month", "price": 180, "valid_days": 30},
                         {"amount": "🌐 3 Months", "price": 450, "valid_days": 90},
                     ])),
                    ("YouTube Premium", "YouTube Premium", "auto", "▶️",
                     "ইউটিউব প্রিমিয়াম — বিজ্ঞাপনমুক্ত + ব্যাকগ্রাউন্ড প্লে",
                     json.dumps([
                         {"amount": "▶️ 1 Month", "price": 120, "valid_days": 30},
                         {"amount": "▶️ 3 Months", "price": 320, "valid_days": 90},
                         {"amount": "▶️ 1 Year", "price": 900, "valid_days": 365},
                     ])),
                    ("Crunchyroll Premium", "Streaming", "auto", "🍿",
                     "ক্রাঞ্চিরোল প্রিমিয়াম অ্যানিমে স্ট্রিমিং",
                     json.dumps([
                         {"amount": "🍿 1 Month", "price": 100, "valid_days": 30},
                         {"amount": "🍿 3 Months", "price": 250, "valid_days": 90},
                     ])),
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

def get_active_categories():
    """Only returns categories that currently have at least one active product —
    so the shop menu is always 100% in sync with what admins have added."""
    with db() as conn:
        rows = conn.execute("""
            SELECT c.name AS name, c.icon AS icon, COUNT(p.id) AS cnt
            FROM categories c
            JOIN products p ON p.category = c.name AND p.is_active = 1
            GROUP BY c.name
            ORDER BY c.display_order ASC, c.name ASC
        """).fetchall()
    return rows

def get_all_categories():
    with db() as conn:
        return conn.execute("SELECT * FROM categories ORDER BY display_order ASC, name ASC").fetchall()

def ensure_category(name: str, icon: str = "📦"):
    with db() as conn:
        exists = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
        if not exists:
            nxt = conn.execute("SELECT COALESCE(MAX(display_order),0)+1 FROM categories").fetchone()[0]
            conn.execute("INSERT INTO categories (name, icon, display_order) VALUES (?,?,?)", (name, icon, nxt))

# ─────────────────────────────────────────────
# 🎨 PREMIUM UI  (single‑column, scroll‑friendly layout)
# ─────────────────────────────────────────────
class UIBuilder:
    @staticmethod
    def safe_text(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    @staticmethod
    def main_menu(user_row=None) -> InlineKeyboardMarkup:
        keyboard = [
            [InlineKeyboardButton("🛍️ Buy Products", callback_data="shop")],
            [InlineKeyboardButton("💳 My Balance", callback_data="balance")],
            [InlineKeyboardButton("➕ Instant Recharge", callback_data="recharge")],
            [InlineKeyboardButton("📦 Order Track", callback_data="orders")],
            [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
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

# ─────────────────────────────────────────────
# 🔹 CONVERSATION STATES
# ─────────────────────────────────────────────
REG_PASSWORD, REG_CONFIRM_PASSWORD = range(2)
ORDER_DETAILS_STATE = 100
ADD_MONEY_AMOUNT, ADD_MONEY_TRX = range(10, 12)
ADMIN_SET_BAL_ID, ADMIN_SET_BAL_AMT = range(20, 22)
(ADMIN_ADD_PROD_CAT, ADMIN_ADD_PROD_NEWCAT_NAME, ADMIN_ADD_PROD_NEWCAT_ICON,
 ADMIN_ADD_PROD_DELIVERY, ADMIN_ADD_PROD_NAME, ADMIN_ADD_PROD_DESC,
 ADMIN_ADD_PROD_OPTS) = range(30, 37)
ADMIN_ADD_STOCK_PROD, ADMIN_ADD_STOCK_EMAIL, ADMIN_ADD_STOCK_PASSWORD, ADMIN_ADD_STOCK_ACTIVATION = range(40, 44)
ADMIN_RESTORE_DB_STATE = 50
ADMIN_BROADCAST_MSG = 60
ADMIN_SEARCH_USER = 70

DEPOSIT_AMOUNTS = [50, 100, 200, 500, 1000]

def deposit_amount_keyboard() -> InlineKeyboardMarkup:
    kb = [[InlineKeyboardButton(f"৳{a}", callback_data=f"depamt_{a}")] for a in DEPOSIT_AMOUNTS]
    kb.append([InlineKeyboardButton("✏️ Custom Amount", callback_data="depamt_custom")])
    kb.append([InlineKeyboardButton("⬅️ Cancel", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)

# ─────────────────────────────────────────────
# 👋 START & REGISTRATION
# ─────────────────────────────────────────────
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
            "🌌 <b>✨ SKY TOPUP · PREMIUM STORE ✨</b>\n"
            "┏━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"┃ 👋 স্বাগতম, <b>{UIBuilder.safe_text(user_row['name'])}</b>\n"
            "┗━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"💵 <b>ব্যালেন্স:</b> ৳{user_row['balance']:,.2f}\n"
            f"🏅 <b>র‍্যাংক:</b> {user_row['rank']}\n"
            f"🎁 <b>পয়েন্ট:</b> {user_row['reward_points']} pts\n\n"
            "🛍️ VPN · Proxy · YouTube Premium · Streaming · Game Top-Up\n"
            "সবকিছু এক জায়গায়, ইনস্ট্যান্ট ডেলিভারি সহ ⚡\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "👇 নিচ থেকে একটি অপশন বেছে নিন:"
        )
        await smart_reply(update, welcome, UIBuilder.main_menu(user_row))
        return ConversationHandler.END
    welcome = (
        "🌌 <b>✨ SKY TOPUP · PREMIUM STORE ✨</b>\n"
        "┏━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"┃ হ্যালো, <b>{UIBuilder.safe_text(user.first_name or 'User')}</b> 👋\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "🔐 শুরু করতে একটি নিরাপদ পাসওয়ার্ড দিন\n"
        "<i>(কমপক্ষে ৬ ক্যারেক্টার)</i>\n\n"
        "👉 <b>এখন আপনার পাসওয়ার্ড টাইপ করুন:</b>"
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
    await update.message.reply_text("🎉 <b>Registration complete!</b> You got ৳10 as a welcome gift.", parse_mode=ParseMode.HTML)
    user_row = get_user(tid)
    await update.message.reply_text("✨ Use the menu:", reply_markup=UIBuilder.main_menu(user_row))
    return ConversationHandler.END

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# 🛒 SHOP & ORDER — fully dynamic category tree
# ─────────────────────────────────────────────
async def show_categories_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_active_categories()
    if not cats:
        await edit_or_reply(update, "⚠️ এখনো কোনো প্রোডাক্ট যোগ করা হয়নি।", UIBuilder.back_button())
        return
    keyboard = [
        [InlineKeyboardButton(f"{c['icon']} {c['name']}  ({c['cnt']})", callback_data=f"category_{c['name']}")]
        for c in cats
    ]
    keyboard.append([InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")])
    await edit_or_reply(
        update,
        "📂 <b>প্রোডাক্ট ক্যাটাগরি</b>\n━━━━━━━━━━━━━━━━━━━━\nযা কিনতে চান সেটি বেছে নিন 👇",
        InlineKeyboardMarkup(keyboard)
    )

async def show_products_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute("SELECT * FROM products WHERE category = ? AND is_active = 1", (category,)).fetchall()
    if not products:
        await edit_or_reply(update, "⚠️ No products found.", UIBuilder.back_button("shop"))
        return
    keyboard = [[InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")] for p in products]
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="shop")])
    await edit_or_reply(update, f"📦 <b>{UIBuilder.safe_text(category)}</b>\n━━━━━━━━━━━━━━━━━━━━\nProduct বেছে নিন:", InlineKeyboardMarkup(keyboard))

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
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"category_{product['category']}")])
    await edit_or_reply(
        update,
        f"⚡ <b>{product['icon']} {product['name']}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 {product['description']}\n\n"
        f"একটি প্যাকেজ বেছে নিন:",
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
    price = selected_package["price"]
    if user_row["balance"] < price:
        await query.message.reply_text(
            f"❌ <b>Insufficient balance</b>\n"
            f"Your balance: ৳{user_row['balance']:.2f}\n"
            f"Needed: ৳{price:.2f}\n\n"
            f"➕ Recharge your wallet first.",
            parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    context.user_data["order_product_id"] = product_id
    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package
    context.user_data["order_delivery_type"] = product["delivery_type"]

    if product["delivery_type"] == "manual":
        await query.message.reply_text(
            f"🛒 <b>Confirm Checkout</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📦 {product['name']}\n"
            f"📎 {selected_package['amount']}\n"
            f"💰 Price: ৳{price}\n\n"
            f"👉 Enter your <b>Game ID / UID</b> (min 3 chars):",
            parse_mode=ParseMode.HTML
        )
        return ORDER_DETAILS_STATE
    else:  # auto‑delivery – no user input needed, place order directly
        return await place_order_for_digital_product(update, context)

async def place_order_for_digital_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    product_id = context.user_data["order_product_id"]
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    tid = str(update.effective_user.id)
    order_id = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"

    with db() as conn:
        conn.execute(
            "INSERT INTO orders (order_id, telegram_id, product_id, product_name, package, price, user_details, status) VALUES (?,?,?,?,?,?,?,'⏳ Pending')",
            (order_id, tid, product_id, product_name, package["amount"], price, "")
        )
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, tid))
    delivery_type = context.user_data.get("order_delivery_type", "auto")
    context.user_data.clear()

    await smart_reply(update,
        f"🎉 <b>Order Placed!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{order_id}</code>\n"
        f"💰 Deducted: ৳{price}\n"
        f"⚡ Admin will process within 5–15 mins."
    )
    try:
        await update.effective_chat.bot.send_message(
            Config.ADMIN_USER_ID,
            f"🔔 <b>New Order</b>\n"
            f"👤 {tid}\n"
            f"🆔 <code>{order_id}</code>\n"
            f"📦 {product_name} ({package['amount']})\n"
            f"Delivery: {delivery_type}",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin notify: {e}")
    return ConversationHandler.END

async def receive_order_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = update.message.text.strip()
    if len(details) < 3:
        await update.message.reply_text("❌ Too short! Provide a valid ID:")
        return ORDER_DETAILS_STATE
    context.user_data["order_user_details"] = details

    product_id = context.user_data["order_product_id"]
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]
    tid = str(update.effective_user.id)
    order_id = f"SKY-{int(datetime.now().timestamp())}-{secrets.token_hex(2).upper()}"
    with db() as conn:
        conn.execute(
            "INSERT INTO orders (order_id, telegram_id, product_id, product_name, package, price, user_details, status) VALUES (?,?,?,?,?,?,?,'⏳ Pending')",
            (order_id, tid, product_id, product_name, package["amount"], price, details)
        )
        conn.execute("UPDATE users SET balance = balance - ? WHERE telegram_id = ?", (price, tid))
    context.user_data.clear()
    await update.message.reply_text(
        f"🎉 <b>Order Placed!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 <code>{order_id}</code>\n"
        f"💰 Deducted: ৳{price}\n"
        f"⚡ Admin will process within 5–15 mins.",
        parse_mode=ParseMode.HTML
    )
    try:
        await update.effective_chat.bot.send_message(
            Config.ADMIN_USER_ID,
            f"🔔 <b>New Order</b>\n"
            f"👤 {tid}\n"
            f"🆔 <code>{order_id}</code>\n"
            f"📦 {product_name} ({package['amount']})\n"
            f"ℹ️ UID: <code>{details}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{order_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{order_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin notify: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# 💰 DEPOSIT (single‑column preset buttons)
# ─────────────────────────────────────────────
async def show_recharge_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 bKash", callback_data="recharge_bkash")],
        [InlineKeyboardButton("📱 Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("📱 Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ Main Menu", callback_data="back_main")]
    ]
    await edit_or_reply(update, "💳 <b>Instant Recharge</b>\n━━━━━━━━━━━━━━━\nমেথড বেছে নিন:", InlineKeyboardMarkup(keyboard))

async def show_recharge_instructions_ui(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    numbers = {"bkash": Config.BKASH_NUMBER, "nagad": Config.NAGAD_NUMBER, "rocket": Config.ROCKET_NUMBER}
    context.user_data["recharge_method"] = method
    await edit_or_reply(
        update,
        f"💳 <b>{method.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"এই নাম্বারে টাকা পাঠান: <code>{numbers[method]}</code>\n"
        f"তারপর যত টাকা পাঠিয়েছেন সেই এমাউন্ট বেছে নিন:",
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
            await query.message.reply_text("💬 যত টাকা পাঠিয়েছেন সেটি লিখুন (৳):")
            return ADD_MONEY_AMOUNT
        amount = float(amt_str)
        context.user_data["recharge_amount"] = amount
        await query.message.reply_text("🔑 এবার <b>Transaction ID (TrxID)</b> পাঠান:", parse_mode=ParseMode.HTML)
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
    await update.message.reply_text("🔑 এবার <b>Transaction ID (TrxID)</b> পাঠান:", parse_mode=ParseMode.HTML)
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
        f"⚡ Verification in 2–5 minutes.",
        parse_mode=ParseMode.HTML
    )
    try:
        await update.effective_chat.bot.send_message(
            Config.ADMIN_USER_ID,
            f"🔔 <b>New Deposit</b>\n"
            f"👤 {tid}\n"
            f"💳 {method.upper()}  |  ৳{amount:.2f}\n"
            f"🔑 <code>{trx}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{req_id}")],
                [InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{req_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Admin notify: {e}")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# 🛡️ ADMIN PANEL & ORDER PROCESSING
# ─────────────────────────────────────────────
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
        [InlineKeyboardButton("📊 Orders", callback_data="adm_view_orders")],
        [InlineKeyboardButton("💰 Deposits", callback_data="adm_view_deposits")],
        [InlineKeyboardButton("👤 Edit Balance", callback_data="adm_balance_set")],
        [InlineKeyboardButton("📦 Add Product", callback_data="adm_product_add")],
        [InlineKeyboardButton("🗂️ Manage Categories", callback_data="adm_view_categories")],
        [InlineKeyboardButton("➕ Add Stock", callback_data="adm_add_stock")],
        [InlineKeyboardButton("🗄️ Stock List", callback_data="adm_view_stock")],
        [InlineKeyboardButton("📤 Backup DB", callback_data="adm_backup_db")],
        [InlineKeyboardButton("📥 Restore DB", callback_data="adm_restore_db")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="adm_broadcast")],
        [InlineKeyboardButton("🔍 Search User", callback_data="adm_search_user")],
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

async def show_categories_admin_ui(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = get_all_categories()
    if not cats:
        await update.callback_query.message.reply_text("📭 কোনো ক্যাটাগরি নেই।")
        return
    with db() as conn:
        lines = ["🗂️ <b>All Categories</b>\n━━━━━━━━━━━━━━━━━━━━"]
        for c in cats:
            cnt = conn.execute("SELECT COUNT(*) FROM products WHERE category=? AND is_active=1", (c["name"],)).fetchone()[0]
            lines.append(f"{c['icon']} <b>{UIBuilder.safe_text(c['name'])}</b> — {cnt} active product(s)")
    await update.callback_query.message.reply_text(
        "\n".join(lines) + "\n\n➕ নতুন প্রোডাক্ট যোগ করার সময় নতুন ক্যাটাগরিও তৈরি করা যায়।",
        parse_mode=ParseMode.HTML
    )

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

    elif data == "adm_view_categories":
        await show_categories_admin_ui(update, context)

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
                f"ℹ️ {o['user_details'] or 'No details'}",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Approve", callback_data=f"adm_ord_approve_{o['order_id']}")],
                    [InlineKeyboardButton("❌ Reject", callback_data=f"adm_ord_reject_{o['order_id']}")]
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
                    [InlineKeyboardButton("✅ Approve", callback_data=f"adm_dep_approve_{d['request_id']}")],
                    [InlineKeyboardButton("❌ Reject", callback_data=f"adm_dep_reject_{d['request_id']}")]
                ])
            )
    elif data == "adm_view_stock":
        with db() as conn:
            stock = conn.execute("SELECT a.*, p.name FROM account_stock a JOIN products p ON a.product_id = p.id WHERE a.status='available' LIMIT 20").fetchall()
        if not stock:
            await query.message.reply_text("📭 No stock available.")
            return
        msg = "🗄️ <b>Available Stock</b>\n"
        for s in stock:
            msg += f"• {s['name']} | {s['email']} | status: {s['status']}\n"
        await query.message.reply_text(msg, parse_mode=ParseMode.HTML)

    elif data.startswith("adm_ord_approve_"):
        oid = data.replace("adm_ord_approve_", "")
        await process_order_approval(update, context, oid, approve=True)
    elif data.startswith("adm_ord_reject_"):
        oid = data.replace("adm_ord_reject_", "")
        await process_order_approval(update, context, oid, approve=False)

    elif data.startswith("adm_dep_approve_"):
        rid = data.replace("adm_dep_approve_", "")
        await process_deposit(update, context, rid, approve=True)
    elif data.startswith("adm_dep_reject_"):
        rid = data.replace("adm_dep_reject_", "")
        await process_deposit(update, context, rid, approve=False)

    elif data == "adm_broadcast":
        await query.message.reply_text("📢 Type the message to broadcast:")
        return ADMIN_BROADCAST_MSG
    elif data == "adm_search_user":
        await query.message.reply_text("🔍 Enter Telegram ID of the user:")
        return ADMIN_SEARCH_USER

async def process_order_approval(update: Update, context: ContextTypes.DEFAULT_TYPE, order_id: str, approve: bool):
    with db() as conn:
        order = conn.execute("SELECT * FROM orders WHERE order_id=? AND status='⏳ Pending'", (order_id,)).fetchone()
        if not order:
            await edit_or_reply(update, f"⚠️ Order {order_id} already processed.")
            return
        if approve:
            conn.execute("UPDATE orders SET status='✅ Completed' WHERE order_id=?", (order_id,))
            await edit_or_reply(update, f"✅ Order {order_id} completed.")
            if order["product_id"]:
                product = conn.execute("SELECT delivery_type FROM products WHERE id=?", (order["product_id"],)).fetchone()
                if product and product["delivery_type"] == "auto":
                    stock = conn.execute("SELECT * FROM account_stock WHERE product_id=? AND status='available' LIMIT 1", (order["product_id"],)).fetchone()
                    if stock:
                        conn.execute("UPDATE account_stock SET status='sold', order_id=?, sold_at=CURRENT_TIMESTAMP WHERE id=?",
                                     (order_id, stock["id"]))
                        options = json.loads(conn.execute("SELECT options FROM products WHERE id=?", (order["product_id"],)).fetchone()["options"])
                        pkg = next((o for o in options if o["amount"] == order["package"]), None)
                        valid_days = pkg.get("valid_days", 30) if pkg else 30
                        expiry_date = (datetime.now() + timedelta(days=valid_days)).strftime("%d %b %Y")
                        details_msg = (
                            f"📧 <b>Email:</b> <code>{stock['email']}</code>\n"
                            f"🔑 <b>Password:</b> <code>{stock['password']}</code>"
                        )
                        if stock["activation_key"]:
                            details_msg += f"\n🔐 <b>Activation Key:</b> <code>{stock['activation_key']}</code>"
                        details_msg += f"\n📅 <b>Expires:</b> {expiry_date}"
                        conn.execute("UPDATE orders SET delivered_details=? WHERE order_id=?", (details_msg, order_id))
                        try:
                            await context.bot.send_message(
                                order["telegram_id"],
                                f"🎉 <b>Your order has been delivered!</b>\n"
                                f"━━━━━━━━━━━━━━━━━━━━\n"
                                f"{details_msg}\n\n"
                                f"Enjoy your premium service! ✨",
                                parse_mode=ParseMode.HTML
                            )
                        except Exception as e:
                            logger.error(f"Delivery notify failed: {e}")
                    else:
                        await context.bot.send_message(
                            Config.ADMIN_USER_ID,
                            f"⚠️ <b>No stock available</b> for order {order_id} ({order['product_name']}). Please add stock manually.",
                            parse_mode=ParseMode.HTML
                        )
        else:
            conn.execute("UPDATE orders SET status='❌ Rejected' WHERE order_id=?", (order_id,))
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (order["price"], order["telegram_id"]))
            await edit_or_reply(update, f"❌ Order {order_id} rejected (refunded).")
            try:
                await context.bot.send_message(order["telegram_id"], f"❌ Order <code>{order_id}</code> rejected. ৳{order['price']} refunded.", parse_mode=ParseMode.HTML)
            except Exception:
                pass

async def process_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: str, approve: bool):
    with db() as conn:
        dep = conn.execute("SELECT * FROM deposit_requests WHERE request_id=? AND status='⏳ Pending'", (request_id,)).fetchone()
        if not dep:
            await edit_or_reply(update, f"⚠️ Request {request_id} already processed.")
            return
        if approve:
            conn.execute("UPDATE deposit_requests SET status='✅ Approved' WHERE request_id=?", (request_id,))
            conn.execute("UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (dep["amount"], dep["telegram_id"]))
            await edit_or_reply(update, f"✅ Deposit {request_id} approved.")
            try:
                await context.bot.send_message(dep["telegram_id"], f"💰 ৳{dep['amount']} added to your wallet.")
            except Exception:
                pass
        else:
            conn.execute("UPDATE deposit_requests SET status='❌ Rejected' WHERE request_id=?", (request_id,))
            await edit_or_reply(update, f"❌ Deposit {request_id} rejected.")
            try:
                await context.bot.send_message(dep["telegram_id"], "❌ Your recharge was rejected. Contact support.")
            except Exception:
                pass

# ─────────────────────────────────────────────
# ➕ ADMIN PRODUCT ADDITION
# — this is the flow that fixes "নতুন ক্যাটাগরি এড করলে ইউজার দেখে না":
# every product is tied to a category, and show_categories_ui always
# re‑reads the DB, so a brand‑new category shows up immediately.
# ─────────────────────────────────────────────
async def start_product_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    cats = get_all_categories()
    kb = [[InlineKeyboardButton(f"{c['icon']} {c['name']}", callback_data=f"cat_{c['name']}")] for c in cats]
    kb.append([InlineKeyboardButton("➕ নতুন ক্যাটাগরি তৈরি করুন", callback_data="cat_new")])
    await update.callback_query.message.reply_text(
        "🗂️ কোন ক্যাটাগরিতে প্রোডাক্ট যোগ করবেন?\n"
        "(নতুন কিছু বিক্রি করতে চাইলে — যেমন Proxy বা YouTube Premium — নিচে থেকে <b>➕ নতুন ক্যাটাগরি</b> চাপুন)",
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML
    )
    return ADMIN_ADD_PROD_CAT

async def prod_cat_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cat_new":
        await query.message.reply_text("✏️ নতুন ক্যাটাগরির নাম লিখুন (যেমন: YouTube Premium):")
        return ADMIN_ADD_PROD_NEWCAT_NAME
    cat_name = query.data.replace("cat_", "", 1)
    context.user_data["new_prod_cat"] = cat_name
    return await ask_delivery_type(update, context)

async def prod_newcat_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_new_cat_name"] = update.message.text.strip()
    await update.message.reply_text("🎨 এই ক্যাটাগরির জন্য একটি ইমোজি আইকন পাঠান (যেমন: ▶️, 🌐, 🎮):")
    return ADMIN_ADD_PROD_NEWCAT_ICON

async def prod_newcat_icon_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    icon = update.message.text.strip() or "📦"
    name = context.user_data.pop("pending_new_cat_name")
    ensure_category(name, icon)
    context.user_data["new_prod_cat"] = name
    return await ask_delivery_type(update, context, use_message=True)

async def ask_delivery_type(update: Update, context: ContextTypes.DEFAULT_TYPE, use_message: bool = False):
    kb = [
        [InlineKeyboardButton("🔑 অটো ডেলিভারি (Stock থেকে Email/Password)", callback_data="deliv_auto")],
        [InlineKeyboardButton("🎮 ম্যানুয়াল (কাস্টমারের Game ID/UID লাগবে)", callback_data="deliv_manual")],
    ]
    text = "🚚 ডেলিভারি টাইপ বেছে নিন:"
    if use_message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_ADD_PROD_DELIVERY

async def prod_delivery_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["new_prod_delivery"] = "auto" if query.data == "deliv_auto" else "manual"
    await query.message.reply_text("📦 এখন প্রোডাক্টের <b>নাম</b> লিখুন (যেমন: World Best VPN Proxy):", parse_mode=ParseMode.HTML)
    return ADMIN_ADD_PROD_NAME

async def prod_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_name"] = update.message.text.strip()
    await update.message.reply_text("🎨 প্রোডাক্টের জন্য একটি ইমোজি আইকন পাঠান (যেমন: 🌐):")
    return ADMIN_ADD_PROD_DESC  # icon collected here then description next below, reuse state chain

async def prod_icon_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_icon"] = update.message.text.strip() or "📦"
    await update.message.reply_text("📝 একটি সংক্ষিপ্ত বিবরণ (description) লিখুন:")
    return ADMIN_ADD_PROD_OPTS  # placeholder, real desc handled below

async def prod_desc_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_prod_desc"] = update.message.text.strip()
    await update.message.reply_text(
        "💎 এবার <b>প্যাকেজগুলো JSON আকারে</b> পাঠান:\n"
        "প্রতিটি প্যাকেজে <code>amount</code>, <code>price</code>, <code>valid_days</code> থাকতে হবে\n"
        "উদাহরণ:\n"
        '<code>[{"amount":"1 Month","price":150,"valid_days":30},{"amount":"3 Months","price":400,"valid_days":90}]</code>\n\n'
        "(ওয়ান-টাইম আইটেমের জন্য <code>valid_days</code> এ 0 দিন)",
        parse_mode=ParseMode.HTML
    )
    return ADMIN_ADD_PROD_OPTS

async def prod_opts_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text.strip()
    try:
        opts = json.loads(raw)
        for o in opts:
            if not all(k in o for k in ("amount", "price", "valid_days")):
                raise ValueError("Missing fields")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid JSON: {e}\nআবার চেষ্টা করুন:")
        return ADMIN_ADD_PROD_OPTS
    cat = context.user_data["new_prod_cat"]
    delivery = context.user_data["new_prod_delivery"]
    name = context.user_data["new_prod_name"]
    icon = context.user_data.get("new_prod_icon", "📦")
    desc = context.user_data["new_prod_desc"]
    with db() as conn:
        conn.execute(
            "INSERT INTO products (name, category, delivery_type, icon, description, options) VALUES (?,?,?,?,?,?)",
            (name, cat, delivery, icon, desc, raw)
        )
    context.user_data.clear()
    await update.message.reply_text(
        f"✅ <b>{UIBuilder.safe_text(name)}</b> এখন <b>{UIBuilder.safe_text(cat)}</b> ক্যাটাগরিতে লাইভ!\n"
        f"ইউজাররা এখনই শপ মেনু থেকে এটি দেখতে ও কিনতে পারবে। 🎉",
        parse_mode=ParseMode.HTML
    )
    return ConversationHandler.END

# ─────────────────────────────────────────────
# ➕ ADMIN STOCK ADDITION (auto‑delivery products only)
# ─────────────────────────────────────────────
async def start_stock_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    with db() as conn:
        products = conn.execute("SELECT id, name FROM products WHERE delivery_type = 'auto'").fetchall()
    if not products:
        await update.callback_query.message.reply_text("❌ কোনো অটো-ডেলিভারি প্রোডাক্ট নেই। আগে একটি প্রোডাক্ট যোগ করুন।")
        return ConversationHandler.END
    kb = [[InlineKeyboardButton(p["name"], callback_data=f"stockprod_{p['id']}")] for p in products]
    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="back_main")])
    await update.callback_query.message.reply_text("📦 কোন প্রোডাক্টের জন্য স্টক যোগ করবেন?", reply_markup=InlineKeyboardMarkup(kb))
    return ADMIN_ADD_STOCK_PROD

async def stock_prod_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    prod_id = int(query.data.split("_")[1])
    context.user_data["stock_product_id"] = prod_id
    await query.message.reply_text("📧 এই অ্যাকাউন্টের <b>email</b> দিন:", parse_mode=ParseMode.HTML)
    return ADMIN_ADD_STOCK_EMAIL

async def stock_email_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["stock_email"] = update.message.text.strip()
    await update.message.reply_text("🔑 <b>password</b> দিন:", parse_mode=ParseMode.HTML)
    return ADMIN_ADD_STOCK_PASSWORD

async def stock_password_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["stock_password"] = update.message.text.strip()
    await update.message.reply_text("🔐 এক্টিভেশন কী থাকলে দিন, না থাকলে 'skip' লিখুন:")
    return ADMIN_ADD_STOCK_ACTIVATION

async def stock_activation_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = update.message.text.strip()
    if key.lower() == "skip":
        key = None
    context.user_data["stock_activation_key"] = key
    return await save_stock(update, context)

async def save_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pid = context.user_data.get("stock_product_id")
    email = context.user_data.get("stock_email")
    password = context.user_data.get("stock_password")
    activation_key = context.user_data.get("stock_activation_key")
    with db() as conn:
        conn.execute(
            "INSERT INTO account_stock (product_id, email, password, activation_key) VALUES (?,?,?,?)",
            (pid, email, password, activation_key)
        )
    context.user_data.clear()
    await update.message.reply_text("✅ Stock added successfully!")
    return ConversationHandler.END

# ─────────────────────────────────────────────
# 👤 BALANCE EDIT, RESTORE, BROADCAST, SEARCH
# ─────────────────────────────────────────────
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
    except ValueError:
        await update.message.reply_text("❌ Invalid amount. Try again:")
        return ADMIN_SET_BAL_AMT
    tid = context.user_data.get("tgt_bal_id")
    with db() as conn:
        conn.execute("UPDATE users SET balance=? WHERE telegram_id=?", (amt, tid))
    context.user_data.clear()
    await update.message.reply_text(f"✅ Balance updated to ৳{amt:.2f}")
    return ConversationHandler.END

async def start_db_restore_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("📥 Send your backup <code>.db</code> file.\n⚠️ This will replace current data.", parse_mode=ParseMode.HTML)
    return ADMIN_RESTORE_DB_STATE

async def db_file_restore_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".db"):
        await update.message.reply_text("❌ Only .db files accepted.")
        return ADMIN_RESTORE_DB_STATE
    msg = await update.message.reply_text("⏳ Restoring...")
    try:
        file = await context.bot.get_file(doc.file_id)
        temp = "temp_restore.db"
        await file.download_to_drive(temp)
        test = sqlite3.connect(temp)
        test.execute("SELECT name FROM sqlite_master WHERE type='table'")
        test.close()
        shutil.copyfile(temp, Config.DB_PATH)
        os.remove(temp)
        await msg.edit_text("✅ Database restored successfully!")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {e}")
    return ConversationHandler.END

async def broadcast_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    text = update.message.text
    with db() as conn:
        users = conn.execute("SELECT telegram_id FROM users").fetchall()
    sent = 0
    for u in users:
        try:
            await context.bot.send_message(u["telegram_id"], text)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ Broadcast sent to {sent}/{len(users)} users.")
    return ConversationHandler.END

async def search_user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(get_user(str(update.effective_user.id))):
        return ConversationHandler.END
    q = update.message.text.strip()
    user = get_user(q)
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

# ─────────────────────────────────────────────
# 👤 PROFILE & MISC
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# 🔄 MAIN CALLBACK ROUTER
# ─────────────────────────────────────────────
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
        await show_products_ui(update, context, data.replace("category_", "", 1))
    elif data.startswith("product_"):
        await select_package_ui(update, context, int(data.replace("product_", "")))
    elif data.startswith("depamt_"):
        await deposit_amount_button(update, context)

# ─────────────────────────────────────────────
# 🚀 MAIN
# ─────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(Config.BOT_TOKEN).build()

    reg_handler = ConversationHandler(
        entry_points=[CommandHandler("start", cmd_start)],
        states={
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
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

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

    admin_bal_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_balance_set, pattern="^adm_balance_set$")],
        states={
            ADMIN_SET_BAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_id_received)],
            ADMIN_SET_BAL_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, bal_amt_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # Admin product add — dynamic category + delivery-type flow
    admin_prod_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_product_add, pattern="^adm_product_add$")],
        states={
            ADMIN_ADD_PROD_CAT: [CallbackQueryHandler(prod_cat_received, pattern="^cat_")],
            ADMIN_ADD_PROD_NEWCAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_newcat_name_received)],
            ADMIN_ADD_PROD_NEWCAT_ICON: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_newcat_icon_received)],
            ADMIN_ADD_PROD_DELIVERY: [CallbackQueryHandler(prod_delivery_received, pattern="^deliv_")],
            ADMIN_ADD_PROD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_name_received)],
            # chain: icon -> description -> options, reusing enum slots in order
            ADMIN_ADD_PROD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_icon_received)],
            ADMIN_ADD_PROD_OPTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, prod_desc_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    admin_stock_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_stock_add, pattern="^adm_add_stock$")],
        states={
            ADMIN_ADD_STOCK_PROD: [CallbackQueryHandler(stock_prod_selected, pattern="^stockprod_")],
            ADMIN_ADD_STOCK_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, stock_email_received)],
            ADMIN_ADD_STOCK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, stock_password_received)],
            ADMIN_ADD_STOCK_ACTIVATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, stock_activation_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    admin_restore_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_db_restore_process, pattern="^adm_restore_db$")],
        states={
            ADMIN_RESTORE_DB_STATE: [MessageHandler(filters.Document.ALL, db_file_restore_received)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    broadcast_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: ADMIN_BROADCAST_MSG, pattern="^adm_broadcast$")],
        states={
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_message_handler)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    search_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(lambda u, c: ADMIN_SEARCH_USER, pattern="^adm_search_user$")],
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
    app.add_handler(admin_stock_handler)
    app.add_handler(admin_restore_handler)
    app.add_handler(broadcast_handler)
    app.add_handler(search_handler)

    app.add_handler(CallbackQueryHandler(admin_callback_router, pattern=r"^adm_"))
    app.add_handler(CallbackQueryHandler(
        button_callback,
        pattern=r"^(?!package_)(?!adm_)(?!depamt_)(?!cat_)(?!deliv_)(?!stockprod_)"
    ))

    logger.info("💫 SKY TopUp Ultimate launched...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
