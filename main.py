import logging
import os
import json
import random
import string
import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from contextlib import contextmanager

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
# CONFIG
# ──────────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")        # the Gmail address the bot sends FROM
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")  # Gmail App Password (not your normal password)

# If SMTP credentials aren't set, the bot falls back to "dev mode" and shows
# the OTP directly in chat, with a clear warning. This is intentional so the
# bot doesn't crash if you haven't configured email yet — but real
# registration in production REQUIRES SMTP_EMAIL / SMTP_PASSWORD to be set,
# otherwise anyone can register with any email address without proving they
# own it.
EMAIL_SENDING_ENABLED = bool(SMTP_EMAIL and SMTP_PASSWORD)

OTP_VALID_MINUTES = 5
DB_PATH = os.getenv("DB_PATH", "skytopup.db")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Conversation states
EMAIL, OTP, PASSWORD, CONFIRM_PASSWORD = range(4)
ORDER_DETAILS = 100


# ──────────────────────────────────────────────────────────────────────────
# DATABASE
# ──────────────────────────────────────────────────────────────────────────
@contextmanager
def db():
    """Context-managed sqlite connection with dict-like rows."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as conn:
        c = conn.cursor()

        c.execute(
            """CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id TEXT UNIQUE,
                      email TEXT UNIQUE,
                      password TEXT,
                      name TEXT,
                      balance REAL DEFAULT 0,
                      reward_points INTEGER DEFAULT 0,
                      rank TEXT DEFAULT 'Bronze',
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS otp_codes
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id TEXT,
                      otp_code TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS orders
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      order_id TEXT UNIQUE,
                      telegram_id TEXT,
                      product_name TEXT,
                      package TEXT,
                      price REAL,
                      user_details TEXT,
                      status TEXT DEFAULT 'Pending',
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
        )

        c.execute(
            """CREATE TABLE IF NOT EXISTS products
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT,
                      category TEXT,
                      icon TEXT,
                      options TEXT)"""
        )

        c.execute("SELECT count(*) FROM products")
        if c.fetchone()[0] == 0:
            products = [
                ("Free Fire Diamonds", "game", "💎",
                 json.dumps([{"amount": "100 Diamonds", "price": 100},
                             {"amount": "310 Diamonds", "price": 300},
                             {"amount": "520 Diamonds", "price": 500},
                             {"amount": "1060 Diamonds", "price": 1000}])),
                ("PUBG Mobile UC", "game", "🔫",
                 json.dumps([{"amount": "60 UC", "price": 120},
                             {"amount": "325 UC", "price": 600},
                             {"amount": "660 UC", "price": 1150}])),
                ("Netflix Premium", "subscribe", "🎬",
                 json.dumps([{"amount": "1 Month", "price": 200},
                             {"amount": "3 Months", "price": 500},
                             {"amount": "12 Months", "price": 1800}])),
                ("YouTube Premium", "subscribe", "▶️",
                 json.dumps([{"amount": "1 Month", "price": 120},
                             {"amount": "12 Months", "price": 1200}])),
                ("Spotify Premium", "subscribe", "🎵",
                 json.dumps([{"amount": "1 Month", "price": 130},
                             {"amount": "3 Months", "price": 350}])),
                ("Crunchyroll Premium", "subscribe", "🎌",
                 json.dumps([{"amount": "1 Month", "price": 150},
                             {"amount": "3 Months", "price": 400}])),
            ]
            c.executemany(
                "INSERT INTO products (name, category, icon, options) VALUES (?, ?, ?, ?)",
                products,
            )
    logger.info("Database ready at %s", DB_PATH)


def get_user(telegram_id: str):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()


def get_user_by_email(email: str):
    with db() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()


def update_balance(telegram_id: str, amount: float):
    with db() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE telegram_id = ?",
            (amount, telegram_id),
        )


# ──────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────
def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def hash_password(password: str) -> str:
    # sha256 with a per-app pepper is still weak for password storage;
    # bcrypt/argon2 would be stronger, but sha256 is kept here to avoid
    # adding a new dependency. Swap for `passlib`'s bcrypt if you can.
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()


def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Actually sends the OTP by email via SMTP (Gmail by default).
    Returns True if the email was sent, False otherwise.

    Requires SMTP_EMAIL and SMTP_PASSWORD env vars (a Gmail "App Password",
    not your normal Gmail login password — Google requires this for SMTP).
    """
    if not EMAIL_SENDING_ENABLED:
        logger.warning("SMTP not configured — OTP email NOT actually sent.")
        return False

    msg = MIMEMultipart()
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email
    msg["Subject"] = "SKY TopUp — আপনার ভেরিফিকেশন কোড"

    body = (
        f"আপনার SKY TopUp OTP কোড: {otp}\n\n"
        f"এই কোডটি {OTP_VALID_MINUTES} মিনিটের জন্য বৈধ। কারো সাথে শেয়ার করবেন না।"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, to_email, msg.as_string())
        return True
    except Exception as exc:
        logger.error("Failed to send OTP email to %s: %s", to_email, exc)
        return False


async def send_reply(update: Update, text: str, reply_markup=None):
    """Works whether the update came from a normal message or a button press."""
    if update.callback_query:
        await update.callback_query.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=reply_markup
        )


# ──────────────────────────────────────────────────────────────────────────
# REGISTRATION FLOW
# ──────────────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing_user = get_user(str(user.id))

    if existing_user:
        await show_main_menu(update, context)
        return ConversationHandler.END

    await update.message.reply_text(
        f"🌤️ <b>SKY TopUp-এ স্বাগতম!</b>\n\n"
        f"হ্যালো {user.first_name}! 👋\n\n"
        f"আমাদের সেবা ব্যবহার করতে প্রথমে রেজিস্ট্রেশন করুন।\n\n"
        f"📧 আপনার Gmail ইমেইল দিন:",
        parse_mode=ParseMode.HTML,
    )
    return EMAIL


async def receive_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text(
            "❌ ভুল ইমেইল! দয়া করে সঠিক Gmail ইমেইল দিন:\n\n"
            "উদাহরণ: yourname@gmail.com"
        )
        return EMAIL

    if get_user_by_email(email):
        await update.message.reply_text(
            "ℹ️ এই ইমেইল দিয়ে আগেই রেজিস্টার করা হয়েছে।\n\n"
            "অনুগ্রহ করে /start দিয়ে আবার চেষ্টা করুন অথবা সাপোর্টে যোগাযোগ করুন।"
        )
        return ConversationHandler.END

    otp = generate_otp()

    with db() as conn:
        # clear any stale OTPs for this user first
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (str(update.effective_user.id),))
        conn.execute(
            "INSERT INTO otp_codes (telegram_id, otp_code) VALUES (?, ?)",
            (str(update.effective_user.id), otp),
        )

    context.user_data["email"] = email

    sent = send_otp_email(email, otp)

    if sent:
        await update.message.reply_text(
            f"📬 <b>OTP Verification</b>\n\n"
            f"আপনার ইমেইলে ({email}) একটি ৬-সংখ্যার কোড পাঠানো হয়েছে।\n"
            f"এটি {OTP_VALID_MINUTES} মিনিটের জন্য বৈধ থাকবে।\n\n"
            f"কোডটি এখানে লিখুন:",
            parse_mode=ParseMode.HTML,
        )
    else:
        # Dev-mode fallback ONLY — do not ship this to real users.
        # Shown so the bot remains testable if SMTP isn't configured yet.
        await update.message.reply_text(
            f"⚠️ <b>ইমেইল পাঠানো যায়নি (SMTP কনফিগার করা নেই)</b>\n\n"
            f"ডেভেলপমেন্ট মোড — আপনার OTP: <code>{otp}</code>\n\n"
            f"⚠️ প্রোডাকশনে যাওয়ার আগে অবশ্যই SMTP_EMAIL এবং SMTP_PASSWORD "
            f"এনভায়রনমেন্ট ভেরিয়েবল সেট করুন, নাহলে যেকেউ যেকোনো ইমেইল "
            f"দিয়ে রেজিস্টার করতে পারবে ইমেইলের মালিকানা যাচাই ছাড়াই।\n\n"
            f"কোডটি এখানে লিখুন:",
            parse_mode=ParseMode.HTML,
        )

    return OTP


async def receive_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    entered = update.message.text.strip()
    telegram_id = str(update.effective_user.id)

    with db() as conn:
        row = conn.execute(
            "SELECT otp_code, created_at FROM otp_codes WHERE telegram_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (telegram_id,),
        ).fetchone()

    if not row:
        await update.message.reply_text("❌ কোনো OTP পাওয়া যায়নি। /start দিয়ে আবার শুরু করুন।")
        return ConversationHandler.END

    created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.utcnow() - created_at > timedelta(minutes=OTP_VALID_MINUTES):
        await update.message.reply_text(
            "⌛ OTP-এর মেয়াদ শেষ হয়ে গেছে। /start দিয়ে আবার শুরু করুন।"
        )
        return ConversationHandler.END

    if entered != row["otp_code"]:
        await update.message.reply_text("❌ ভুল OTP! আবার চেষ্টা করুন:")
        return OTP

    with db() as conn:
        conn.execute("DELETE FROM otp_codes WHERE telegram_id = ?", (telegram_id,))

    await update.message.reply_text(
        "✅ <b>OTP সফলভাবে যাচাই করা হয়েছে!</b>\n\n"
        "🔐 এখন একটি পাসওয়ার্ড দিন (ন্যূনতম ৬ অক্ষর):",
        parse_mode=ParseMode.HTML,
    )
    return PASSWORD


async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()

    if len(password) < 6:
        await update.message.reply_text(
            "❌ পাসওয়ার্ড ন্যূনতম ৬ অক্ষরের হতে হবে!\n\nআবার পাসওয়ার্ড দিন:"
        )
        return PASSWORD

    # delete the plaintext password message from chat history for privacy
    try:
        await update.message.delete()
    except Exception:
        pass

    context.user_data["password"] = password
    await send_reply(update, "🔐 পাসওয়ার্ড আবার নিশ্চিত করুন:")
    return CONFIRM_PASSWORD


async def confirm_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    confirm_pass = update.message.text.strip()
    password = context.user_data.get("password")

    try:
        await update.message.delete()
    except Exception:
        pass

    if confirm_pass != password:
        await send_reply(update, "❌ পাসওয়ার্ড মিলছে না! আবার পাসওয়ার্ড দিন:")
        return PASSWORD

    email = context.user_data.get("email")
    telegram_id = str(update.effective_user.id)
    name = update.effective_user.first_name or "User"

    with db() as conn:
        conn.execute(
            "INSERT INTO users (telegram_id, email, password, name) VALUES (?, ?, ?, ?)",
            (telegram_id, email, hash_password(password), name),
        )

    context.user_data.clear()

    await send_reply(
        update,
        f"🎉 <b>অভিনন্দন!</b>\n\n"
        f"আপনার অ্যাকাউন্ট সফলভাবে তৈরি হয়েছে!\n\n"
        f"📧 ইমেইল: {email}\n"
        f"👤 নাম: {name}\n\n"
        f"🔽 নিচের মেনু থেকে বেছে নিন:",
    )
    await show_main_menu(update, context)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await send_reply(update, "❌ বাতিল করা হয়েছে। আবার শুরু করতে /start লিখুন।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# MAIN MENU
# ──────────────────────────────────────────────────────────────────────────
def main_menu_keyboard(user_row) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🛒 প্রোডাক্ট কিনুন", callback_data="shop")],
        [
            InlineKeyboardButton("💰 আমার ব্যালেন্স", callback_data="balance"),
            InlineKeyboardButton("📦 আমার অর্ডার", callback_data="orders"),
        ],
        [InlineKeyboardButton("➕ রিচার্জ করুন", callback_data="recharge")],
        [
            InlineKeyboardButton("👤 প্রোফাইল", callback_data="profile"),
            InlineKeyboardButton("⚙️ সেটিংস", callback_data="settings"),
        ],
        [InlineKeyboardButton("❓ সাহায্য", callback_data="help")],
    ]
    if user_row and user_row["id"] == 1:  # first registered user = admin
        keyboard.append([InlineKeyboardButton("🔧 এডমিন প্যানেল", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_user.id))
    text = (
        f"🌤️ <b>SKY TopUp</b>\n\n"
        f"👤 স্বাগতম, {user['name'] if user else 'User'}!\n\n"
        f"💰 ব্যালেন্স: ৳{user['balance'] if user else 0}\n"
        f"🏆 র‍্যাংক: {user['rank'] if user else 'Bronze'}\n\n"
        f"কী করতে চান?"
    )
    await send_reply(update, text, reply_markup=main_menu_keyboard(user))


# ──────────────────────────────────────────────────────────────────────────
# BUTTON CALLBACKS (non-order navigation)
# ──────────────────────────────────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    routes = {
        "shop": show_categories,
        "balance": show_balance,
        "orders": show_orders,
        "recharge": recharge_balance,
        "profile": show_profile,
        "settings": show_settings,
        "help": show_help,
        "admin": show_admin_panel,
        "back_main": show_main_menu,
        "back_shop": show_categories,
    }

    if data in routes:
        await routes[data](update, context)
    elif data.startswith("category_"):
        await show_products(update, context, data.replace("category_", ""))
    elif data.startswith("product_"):
        await select_package(update, context, int(data.replace("product_", "")))
    elif data.startswith("recharge_"):
        await show_recharge_instructions(update, context, data.replace("recharge_", ""))


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 গেম টপ-আপ", callback_data="category_game")],
        [InlineKeyboardButton("🎬 সাবস্ক্রিপশন", callback_data="category_subscribe")],
        [InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_main")],
    ]
    await send_reply(update, "📂 <b>ক্যাটাগরি নির্বাচন করুন:</b>", InlineKeyboardMarkup(keyboard))


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    with db() as conn:
        products = conn.execute(
            "SELECT * FROM products WHERE category = ?", (category,)
        ).fetchall()

    if not products:
        await send_reply(update, "😕 এই ক্যাটাগরিতে এখন কোনো প্রোডাক্ট নেই।")
        return

    keyboard = [
        [InlineKeyboardButton(f"{p['icon']} {p['name']}", callback_data=f"product_{p['id']}")]
        for p in products
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])

    category_names = {"game": "🎮 গেম টপ-আপ", "subscribe": "🎬 সাবস্ক্রিপশন"}
    await send_reply(
        update,
        f"📦 <b>{category_names.get(category, category)}</b>\n\nপ্রোডাক্ট নির্বাচন করুন:",
        InlineKeyboardMarkup(keyboard),
    )


async def select_package(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    with db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if not product:
        await send_reply(update, "❌ প্রোডাক্ট পাওয়া যায়নি!")
        return

    options = json.loads(product["options"])
    keyboard = [
        [InlineKeyboardButton(
            f"{opt['amount']} - ৳{opt['price']}",
            callback_data=f"package_{product_id}_{idx}",
        )]
        for idx, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_shop")])

    await send_reply(
        update,
        f"📦 <b>{product['name']}</b>\n\nপ্যাকেজ নির্বাচন করুন:",
        InlineKeyboardMarkup(keyboard),
    )


# ──────────────────────────────────────────────────────────────────────────
# ORDER FLOW (its own ConversationHandler — entry point is the package button)
# ──────────────────────────────────────────────────────────────────────────
async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, product_id, package_idx = query.data.split("_")
    product_id, package_idx = int(product_id), int(package_idx)

    with db() as conn:
        product = conn.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        ).fetchone()

    if not product:
        await query.message.reply_text("❌ প্রোডাক্ট পাওয়া যায়নি!")
        return ConversationHandler.END

    options = json.loads(product["options"])
    selected_package = options[package_idx]
    user = get_user(str(update.effective_user.id))

    if not user:
        await query.message.reply_text("দয়া করে প্রথমে /start দিয়ে রেজিস্টার করুন।")
        return ConversationHandler.END

    if user["balance"] < selected_package["price"]:
        await query.message.reply_text(
            f"❌ <b>পর্যাপ্ত ব্যালেন্স নেই!</b>\n\n"
            f"আপনার ব্যালেন্স: ৳{user['balance']}\n"
            f"প্রয়োজন: ৳{selected_package['price']}\n\n"
            f"ব্যালেন্স যোগ করতে মেনু থেকে 'রিচার্জ করুন' চাপুন।",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    context.user_data["order_product_name"] = product["name"]
    context.user_data["order_package"] = selected_package

    await query.message.reply_text(
        f"📦 <b>অর্ডার নিশ্চিত করুন</b>\n\n"
        f"প্রোডাক্ট: {product['name']}\n"
        f"প্যাকেজ: {selected_package['amount']}\n"
        f"মূল্য: ৳{selected_package['price']}\n\n"
        f"আপনার {product['name'].split()[0]} ID/ইউজারনেম/ইমেইল দিন "
        f"(অথবা /cancel দিয়ে বাতিল করুন):",
        parse_mode=ParseMode.HTML,
    )
    return ORDER_DETAILS


async def receive_order_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "order_product_name" not in context.user_data:
        return ConversationHandler.END

    user_details = update.message.text.strip()
    product_name = context.user_data["order_product_name"]
    package = context.user_data["order_package"]
    price = package["price"]

    telegram_id = str(update.effective_user.id)
    order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    with db() as conn:
        conn.execute(
            """INSERT INTO orders
               (order_id, telegram_id, product_name, package, price, user_details)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (order_id, telegram_id, product_name, package["amount"], price, user_details),
        )
        conn.execute(
            "UPDATE users SET balance = balance - ? WHERE telegram_id = ?",
            (price, telegram_id),
        )
        conn.execute(
            "UPDATE users SET reward_points = reward_points + ? WHERE telegram_id = ?",
            (int(price) // 10, telegram_id),
        )

    context.user_data.clear()

    await update.message.reply_text(
        f"✅ <b>অর্ডার সফল!</b>\n\n"
        f"📦 অর্ডার ID: <code>{order_id}</code>\n"
        f"প্রোডাক্ট: {product_name}\n"
        f"প্যাকেজ: {package['amount']}\n"
        f"মূল্য: ৳{price}\n\n"
        f"আপনার অর্ডার প্রসেসিং হচ্ছে। ধন্যবাদ! 🎉",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("order_product_name", None)
    context.user_data.pop("order_package", None)
    await update.message.reply_text("❌ অর্ডার বাতিল করা হয়েছে।")
    return ConversationHandler.END


# ──────────────────────────────────────────────────────────────────────────
# ACCOUNT SCREENS
# ──────────────────────────────────────────────────────────────────────────
async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_user.id))
    await send_reply(
        update,
        f"💰 <b>আমার ব্যালেন্স</b>\n\n"
        f"👤 নাম: {user['name']}\n"
        f"💵 ব্যালেন্স: ৳{user['balance']}\n"
        f"🎁 রিওয়ার্ড পয়েন্ট: {user['reward_points']}\n"
        f"🏆 র‍্যাংক: {user['rank']}\n\n"
        f"ব্যালেন্স যোগ করতে মেনু থেকে 'রিচার্জ করুন' চাপুন।",
    )


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as conn:
        orders = conn.execute(
            "SELECT * FROM orders WHERE telegram_id = ? ORDER BY created_at DESC LIMIT 10",
            (str(update.effective_user.id),),
        ).fetchall()

    if not orders:
        await send_reply(update, "📭 কোনো অর্ডার নেই!")
        return

    status_emoji = {"Completed": "✅", "Pending": "⏳", "Processing": "🔄", "Cancelled": "❌"}
    lines = ["📦 <b>আমার অর্ডার:</b>\n"]
    for o in orders:
        emoji = status_emoji.get(o["status"], "🔄")
        lines.append(
            f"{emoji} <code>{o['order_id']}</code>\n"
            f"   {o['product_name']} - {o['package']}\n"
            f"   মূল্য: ৳{o['price']} | স্ট্যাটাস: {o['status']}\n"
        )
    await send_reply(update, "\n".join(lines))


async def recharge_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("bKash", callback_data="recharge_bkash")],
        [InlineKeyboardButton("Nagad", callback_data="recharge_nagad")],
        [InlineKeyboardButton("Rocket", callback_data="recharge_rocket")],
        [InlineKeyboardButton("⬅️ ফিরে যান", callback_data="back_main")],
    ]
    await send_reply(
        update,
        "💰 <b>ব্যালেন্স রিচার্জ</b>\n\nপেমেন্ট মেথড নির্বাচন করুন:",
        InlineKeyboardMarkup(keyboard),
    )


async def show_recharge_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE, method: str):
    # NOTE: Replace these with your real merchant/agent numbers.
    numbers = {
        "bkash": os.getenv("BKASH_NUMBER", "01XXXXXXXXX (Personal/Merchant)"),
        "nagad": os.getenv("NAGAD_NUMBER", "01XXXXXXXXX (Personal/Merchant)"),
        "rocket": os.getenv("ROCKET_NUMBER", "01XXXXXXXXX"),
    }
    await send_reply(
        update,
        f"💳 <b>{method.title()} দিয়ে পেমেন্ট</b>\n\n"
        f"নাম্বারে টাকা পাঠান: <code>{numbers.get(method, 'N/A')}</code>\n\n"
        f"পেমেন্ট করার পর ট্রানজেকশন ID সহ আমাদের সাপোর্টে স্ক্রিনশট পাঠান, "
        f"আমরা ম্যানুয়ালি যাচাই করে ব্যালেন্স যোগ করে দেব।",
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_user.id))
    await send_reply(
        update,
        f"👤 <b>প্রোফাইল</b>\n\n"
        f"নাম: {user['name']}\n"
        f"ইমেইল: {user['email']}\n"
        f"যোগদানের তারিখ: {user['created_at']}\n"
        f"র‍্যাংক: {user['rank']}",
    )


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_reply(
        update,
        "⚙️ <b>সেটিংস</b>\n\nপাসওয়ার্ড পরিবর্তন বা নোটিফিকেশন সেটিংসের জন্য শীঘ্রই আসছে।",
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_reply(
        update,
        "❓ <b>সাহায্য</b>\n\n"
        "যেকোনো সমস্যায় আমাদের সাপোর্টে যোগাযোগ করুন।\n\n"
        "কমান্ডসমূহ:\n"
        "/start - বট শুরু করুন / মেনু দেখুন\n"
        "/cancel - চলমান প্রক্রিয়া বাতিল করুন",
    )


async def show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(str(update.effective_user.id))
    if not user or user["id"] != 1:
        await send_reply(update, "⛔ এই মেনু শুধুমাত্র এডমিনের জন্য।")
        return

    with db() as conn:
        total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        pending_orders = conn.execute(
            "SELECT COUNT(*) c FROM orders WHERE status = 'Pending'"
        ).fetchone()["c"]

    await send_reply(
        update,
        f"🔧 <b>এডমিন প্যানেল</b>\n\n"
        f"👥 মোট ইউজার: {total_users}\n"
        f"⏳ পেন্ডিং অর্ডার: {pending_orders}\n",
    )


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main():
    if not BOT_TOKEN:
        raise SystemExit(
            "BOT_TOKEN environment variable is not set. Get one from @BotFather "
            "on Telegram and set it before running the bot."
        )
    if not EMAIL_SENDING_ENABLED:
        logger.warning(
            "SMTP_EMAIL / SMTP_PASSWORD not set — the bot will run in DEV MODE "
            "and show OTPs in chat instead of emailing them. Do not use this "
            "in production; anyone could register with an email they don't own."
        )

    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    registration_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_email)],
            OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_otp)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
            CONFIRM_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    order_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(package_selected, pattern=r"^package_\d+_\d+$")],
        states={
            ORDER_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_order_details)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
    )

    app.add_handler(registration_handler)
    app.add_handler(order_handler)
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
