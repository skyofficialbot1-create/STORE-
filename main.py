#!/usr/bin/env python3
"""
SKY STORE BD — Premium Digital Store Telegram Bot
Version 3.0 — All bugs fixed + Database Backup/Restore
"""
import asyncio, os, sys, sqlite3, json, re, random, string, shutil
from datetime import datetime, timedelta
from uuid import uuid4
from io import BytesIO

try:
    from aiogram import Bot, Dispatcher, F, BaseMiddleware
    from aiogram.filters import Command, CommandStart, StateFilter
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardButton, TelegramObject,
        ContentType, FSInputFile
    )
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.enums.button_style import ButtonStyle
except ImportError as e:
    print(f"[!] Missing: {e}")
    print("[*] Installing aiogram...")
    os.system("pip install -q aiogram")
    from aiogram import Bot, Dispatcher, F, BaseMiddleware
    from aiogram.filters import Command, CommandStart, StateFilter
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardButton, TelegramObject,
        ContentType, FSInputFile
    )
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.enums.button_style import ButtonStyle

# ─── CONFIG ───────────────────────────────────────────────────────────────────
BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
SUPPORT_USERNAME = "FBSKYSUPPORT"
TIMEZONE_OFFSET = 6  # Bangladesh (BST)
DB_PATH = "store.db"
BACKUP_DIR = "backups"

def now_local():
    return datetime.utcnow() + timedelta(hours=TIMEZONE_OFFSET)

def fmt(amount):
    return f"৳{amount:,.0f}"

def generate_id(prefix="", length=8):
    chars = string.ascii_lowercase + string.digits
    rand = ''.join(random.choices(chars, k=length))
    return f"{prefix}{rand}" if prefix else rand

def get_expiry_date(days):
    dt = now_local() + timedelta(days=days)
    return dt.strftime("%d %B %Y")

def generate_box(title, body_lines, width=38):
    top = f"╔{'═'*(width-2)}╗"
    mid = f"║ {title}{' '*(width-3-len(title))}║"
    sep = f"╠{'═'*(width-2)}╣"
    bot = f"╚{'═'*(width-2)}╝"
    lines = [top, mid, sep]
    for line in body_lines:
        clean = line.strip()
        if len(clean) > width-4:
            clean = clean[:width-4]
        lines.append(f"║ {clean}{' '*(width-3-len(clean))}║")
    lines.append(bot)
    return "\n".join(lines)

# ─── DATABASE ─────────────────────────────────────────────────────────────────
class Database:
    def __init__(self, path=DB_PATH):
        self.path = path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT, username TEXT,
                balance REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, product_id TEXT,
                product_name TEXT, category_id TEXT,
                amount REAL, user_input TEXT,
                payment_method TEXT, transaction_id TEXT,
                status TEXT DEFAULT 'pending',
                delivery_data TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount REAL,
                type TEXT, method TEXT,
                trx_id TEXT, note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS categories(
                id TEXT PRIMARY KEY,
                parent_id TEXT, name TEXT,
                description TEXT, icon TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS products(
                id TEXT PRIMARY KEY,
                category_id TEXT, name TEXT,
                price REAL, bonus REAL DEFAULT 0,
                stock_type TEXT,
                expiry_days INTEGER DEFAULT 30,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS stock(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT, stock_type TEXT,
                email TEXT, password TEXT,
                key_data TEXT, expiry_days INTEGER DEFAULT 30,
                is_used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS promo_codes(
                code TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                discount_pct REAL DEFAULT 0,
                max_uses INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            # Check if data exists
            cur = conn.execute("SELECT COUNT(*) FROM categories WHERE parent_id IS NULL")
            if cur.fetchone()[0] == 0:
                self._seed_data(conn)
            conn.commit()

    def _seed_data(self, conn):
        categories = [
            ("youtube", None, "YouTube Premium", "Ad-free YouTube", "▶️", 1),
            ("netflix", None, "Netflix Premium", "Premium Netflix", "🎬", 2),
            ("crunchyroll", None, "Crunchyroll", "Anime streaming", "🍿", 3),
            ("vpn", None, "VPN Services", "Premium VPN", "🔐", 4),
            ("proxy", None, "Proxy Services", "Residential proxies", "🌐", 5),
        ]
        for cat in categories:
            conn.execute("INSERT INTO categories(id,parent_id,name,description,icon,sort_order) VALUES(?,?,?,?,?,?)", cat)
        vpn_subs = [
            ("nordvpn_1m", "vpn", "🔵 NordVPN 1 Month", "NordVPN monthly", "🔵", 1),
            ("nordvpn_3m", "vpn", "🔵 NordVPN 3 Months", "NordVPN quarterly", "🔵", 2),
            ("expressvpn_1m", "vpn", "🔴 ExpressVPN 1 Month", "ExpressVPN", "🔴", 3),
        ]
        for cat in vpn_subs:
            conn.execute("INSERT INTO categories(id,parent_id,name,description,icon,sort_order) VALUES(?,?,?,?,?,?)", cat)
        products = [
            ("yt_1m", "youtube", "▶️ YouTube Premium 1 Month", 100, 0, "manual", 30),
            ("yt_3m", "youtube", "▶️ YouTube Premium 3 Months", 200, 0, "manual", 90),
            ("nf_1m", "netflix", "🎬 Netflix Premium 1 Month", 150, 0, "manual", 30),
            ("cr_1m", "crunchyroll", "🍿 Crunchyroll 1 Month", 200, 0, "manual", 30),
            ("vpn_auto", "vpn", "🚀 Auto-Assign VPN (1 Month)", 350, 0, "email_pass", 30),
            ("proxy_resi", "proxy", "🌐 Residential Proxy (30 Days)", 500, 0, "key_only", 30),
        ]
        for p in products:
            conn.execute("INSERT INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) VALUES(?,?,?,?,?,?,?)", p)
        conn.commit()

    # ── Users ──
    def get_user(self, uid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_user_by_username(self, username):
        """Find user by @username (without @ or with @)."""
        un = username.strip().lstrip("@")
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users WHERE username=?", (un,))
            r = cur.fetchone()
            return dict(r) if r else None

    def create_user(self, uid, fn, un):
        with self._get_conn() as conn:
            conn.execute("INSERT OR IGNORE INTO users(user_id,first_name,username) VALUES(?,?,?)", (uid, fn, un))
            conn.commit()

    def get_balance(self, uid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
            r = cur.fetchone()
            return r["balance"] if r else 0

    def update_balance(self, uid, amt):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
            conn.commit()

    def deduct_balance(self, uid, amt):
        with self._get_conn() as conn:
            cur = conn.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (amt, uid, amt))
            conn.commit()
            return cur.rowcount > 0

    def set_ban(self, uid, ban=True):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, uid))
            conn.commit()

    def get_all_users(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users ORDER BY joined_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def get_user_count(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]

    def add_transaction(self, uid, amt, typ, method, trid, note=""):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note) VALUES(?,?,?,?,?,?)", (uid, amt, typ, method, trid, note))
            conn.commit()

    # ── Categories ──
    def get_categories(self, parent_id=None):
        with self._get_conn() as conn:
            if parent_id is not None:
                cur = conn.execute("SELECT * FROM categories WHERE parent_id=? AND is_active=1 ORDER BY sort_order", (parent_id,))
            else:
                cur = conn.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY sort_order")
            return [dict(r) for r in cur.fetchall()]

    def get_all_categories(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order")
            return [dict(r) for r in cur.fetchall()]

    def get_category(self, cid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def add_category(self, cid, parent_id, name, desc="", icon="📦", sort=0):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO categories(id,parent_id,name,description,icon,sort_order) VALUES(?,?,?,?,?,?)", (cid, parent_id, name, desc, icon, sort))
            conn.commit()

    def update_category(self, cid, **kwargs):
        with self._get_conn() as conn:
            for key, value in kwargs.items():
                if value is not None:
                    conn.execute(f"UPDATE categories SET {key}=? WHERE id=?", (value, cid))
            conn.commit()

    def delete_category(self, cid):
        with self._get_conn() as conn:
            conn.execute("UPDATE categories SET is_active=0 WHERE id=?", (cid,))
            conn.execute("UPDATE products SET is_active=0 WHERE category_id=?", (cid,))
            conn.commit()

    # ── Products ──
    def get_product(self, pid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products WHERE id=?", (pid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_products(self, category_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1 ORDER BY sort_order, price", (category_id,))
            return [dict(r) for r in cur.fetchall()]

    def add_product(self, pid, category_id, name, price, bonus=0, stock_type=None, expiry_days=30):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) VALUES(?,?,?,?,?,?,?)", (pid, category_id, name, price, bonus, stock_type, expiry_days))
            conn.commit()

    def update_product(self, pid, **kwargs):
        with self._get_conn() as conn:
            for key, value in kwargs.items():
                if value is not None:
                    conn.execute(f"UPDATE products SET {key}=? WHERE id=?", (value, pid))
            conn.commit()

    def delete_product(self, pid):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM products WHERE id=?", (pid,))
            conn.commit()

    def get_all_products(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY category_id, sort_order")
            return [dict(r) for r in cur.fetchall()]

    # ── Orders ──
    def add_order(self, uid, pid, pname, catid, amt, uinput, pmethod, trid):
        with self._get_conn() as conn:
            cur = conn.execute("INSERT INTO orders(user_id,product_id,product_name,category_id,amount,user_input,payment_method,transaction_id) VALUES(?,?,?,?,?,?,?,?)", (uid, pid, pname, catid, amt, uinput, pmethod, trid))
            conn.commit()
            return cur.lastrowid

    def update_order(self, oid, status, delivery_data=None):
        with self._get_conn() as conn:
            if delivery_data:
                conn.execute("UPDATE orders SET status=?,delivery_data=? WHERE id=?", (status, json.dumps(delivery_data), oid))
            else:
                conn.execute("UPDATE orders SET status=? WHERE id=?", (status, oid))
            conn.commit()

    def get_order(self, oid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM orders WHERE id=?", (oid,))
            r = cur.fetchone()
            if r:
                d = dict(r)
                if d.get("delivery_data"):
                    d["delivery_data"] = json.loads(d["delivery_data"])
                return d
            return None

    def get_user_orders(self, uid, limit=10):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, limit))
            orders = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("delivery_data"):
                    d["delivery_data"] = json.loads(d["delivery_data"])
                orders.append(d)
            return orders

    def get_all_orders(self, status=None, limit=50):
        with self._get_conn() as conn:
            if status:
                cur = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit))
            else:
                cur = conn.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
            orders = []
            for r in cur.fetchall():
                d = dict(r)
                if d.get("delivery_data"):
                    d["delivery_data"] = json.loads(d["delivery_data"])
                orders.append(d)
            return orders

    def pending_count(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
            return cur.fetchone()[0]

    def get_sales_summary(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT product_name, COUNT(*) as cnt, SUM(amount) as total FROM orders WHERE status='delivered' GROUP BY product_id ORDER BY cnt DESC")
            return [dict(r) for r in cur.fetchall()]

    # ── Stock ──
    def add_stock(self, product_id, stock_type, email=None, password=None, key_data=None, expiry_days=30):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO stock(product_id,stock_type,email,password,key_data,expiry_days) VALUES(?,?,?,?,?,?)", (product_id, stock_type, email, password, key_data, expiry_days))
            conn.commit()

    def get_available_stock(self, product_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM stock WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1", (product_id,))
            r = cur.fetchone()
            if r:
                with self._get_conn() as conn2:
                    conn2.execute("UPDATE stock SET is_used=1 WHERE id=?", (r["id"],))
                    conn2.commit()
                return dict(r)
            return None

    def get_stock_counts(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT product_id, stock_type, COUNT(*) as cnt FROM stock WHERE is_used=0 GROUP BY product_id")
            return [dict(r) for r in cur.fetchall()]

    def get_all_stock(self, product_id=None):
        with self._get_conn() as conn:
            if product_id:
                cur = conn.execute("SELECT * FROM stock WHERE product_id=? ORDER BY id DESC LIMIT 100", (product_id,))
            else:
                cur = conn.execute("SELECT * FROM stock ORDER BY product_id, id DESC LIMIT 200")
            return [dict(r) for r in cur.fetchall()]

    def delete_stock(self, sid):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM stock WHERE id=?", (sid,))
            conn.commit()

    # ── Promo Codes ──
    def add_promo(self, code, amount, discount_pct=0, max_uses=0, expires_at=None):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO promo_codes(code,amount,discount_pct,max_uses,expires_at) VALUES(?,?,?,?,?)", (code.upper(), amount, discount_pct, max_uses, expires_at))
            conn.commit()

    def get_promo(self, code):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM promo_codes WHERE code=? AND is_active=1", (code.upper(),))
            r = cur.fetchone()
            return dict(r) if r else None

    def use_promo(self, code):
        with self._get_conn() as conn:
            conn.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code.upper(),))
            conn.commit()
            cur = conn.execute("SELECT used_count, max_uses FROM promo_codes WHERE code=?", (code.upper(),))
            r = cur.fetchone()
            if r:
                return r["used_count"] <= r["max_uses"] or r["max_uses"] == 0
            return False

    def get_all_promos(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM promo_codes ORDER BY created_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def delete_promo(self, code):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM promo_codes WHERE code=?", (code.upper(),))
            conn.commit()

    # ── Backup & Restore ──
    def backup(self, backup_path=None):
        """Create a backup of the database. Returns the backup file path."""
        if backup_path is None:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            ts = now_local().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"store_backup_{ts}.db")
        # Close all connections by using a fresh copy
        shutil.copy2(self.path, backup_path)
        return backup_path

    def restore(self, backup_path):
        """Restore database from a backup file. Returns True on success."""
        if not os.path.exists(backup_path):
            return False
        # Verify it's a valid SQLite db
        try:
            conn = sqlite3.connect(backup_path)
            conn.execute("SELECT COUNT(*) FROM users")
            conn.close()
        except:
            return False
        # Replace current DB with backup
        shutil.copy2(backup_path, self.path)
        return True

    def export_json(self):
        """Export full DB to JSON dict for inspection."""
        data = {}
        with self._get_conn() as conn:
            for table in ["users", "orders", "transactions", "categories", "products", "stock", "promo_codes"]:
                cur = conn.execute(f"SELECT * FROM {table}")
                rows = [dict(r) for r in cur.fetchall()]
                # Convert non-serializable
                data[table] = rows
        return data


# ─── GLOBALS ──────────────────────────────────────────────────────────────────
db = Database()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ─── STATES ───────────────────────────────────────────────────────────────────
class OrderFlow(StatesGroup):
    waiting_input = State()       # For initial input (email, server, etc.)
    waiting_extra = State()       # For Crunchyroll phone number
    waiting_tg = State()          # For Crunchyroll Telegram username
    waiting_payment = State()     # Payment method selection
    waiting_trxid = State()       # Transaction ID entry

class DepositFlow(StatesGroup):
    waiting_trxid = State()       # Deposit TrxID entry
    waiting_promo = State()       # Promo code entry

class AdminFlow(StatesGroup):
    # Add Balance
    addbal_uid = State()
    addbal_amt = State()
    # Ban/Unban
    ban_uid = State()
    unban_uid = State()
    # Broadcast
    broadcast_msg = State()
    # Category
    addcat_parent = State()
    addcat_name = State()
    addcat_desc = State()
    addcat_icon = State()
    editcat_target = State()
    editcat_name = State()
    editcat_desc = State()
    # Product
    addprod_name = State()
    addprod_price = State()
    addprod_expiry = State()
    addprod_stocktype = State()
    editprod_field = State()
    editprod_value = State()
    # Stock
    stock_target = State()
    stock_input = State()
    # Promo
    promo_code = State()
    promo_amount = State()
    promo_discount = State()
    promo_uses = State()
    promo_expiry = State()
    # Restore
    restore_file = State()


# ─── MIDDLEWARE ───────────────────────────────────────────────────────────────
class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user:
            u = db.get_user(user.id)
            if u and u.get("is_banned") == 1:
                if isinstance(event, Message):
                    await event.answer("❌ You are banned from using this bot.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("❌ You are banned from using this bot.", show_alert=True)
                return
        return await handler(event, data)


# ─── KEYBOARD HELPERS ────────────────────────────────────────────────────────
def btn(text, callback_data, style=None):
    kwargs = {"text": text, "callback_data": callback_data}
    if style:
        kwargs["style"] = style.value if hasattr(style, 'value') else style
    return InlineKeyboardButton(**kwargs)

def main_menu_kb(uid):
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    for cat in cats:
        emoji = cat.get('icon', '📦')
        kb.button(text=f"{emoji} {cat['name']}", callback_data=f"cat_{cat['id']}", style=ButtonStyle.PRIMARY)
    kb.adjust(2)
    kb.row(
        btn("📜 My Orders", "my_orders"),
        btn("💳 Wallet / Deposit", "my_wallet", ButtonStyle.SUCCESS)
    )
    if uid in ADMIN_IDS:
        kb.row(btn("⚙️ Admin Panel", "admin_menu", ButtonStyle.DANGER))
    return kb.as_markup()

def cat_products_kb(cat_id):
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"🛒 {p['name']} — {fmt(p['price'])}", callback_data=f"order_{p['id']}", style=ButtonStyle.PRIMARY)
    kb.adjust(1)
    kb.row(btn("🔙 Main Menu", "main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("💰 Wallet Balance", "pay_wallet", ButtonStyle.SUCCESS))
    kb.row(btn("💖 bKash", "pay_bkash", ButtonStyle.PRIMARY), btn("🟠 Nagad", "pay_nagad", ButtonStyle.PRIMARY))
    kb.row(btn("🚀 Rocket", "pay_rocket", ButtonStyle.PRIMARY))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Stats", "admin_dash", ButtonStyle.PRIMARY), btn("💰 Add Balance", "admin_addbal", ButtonStyle.SUCCESS))
    kb.row(btn("📂 Categories", "admin_cats", ButtonStyle.PRIMARY), btn("📦 Edit Product", "admin_editprod", ButtonStyle.PRIMARY))
    kb.row(btn("🔑 Stock", "admin_stock", ButtonStyle.PRIMARY), btn("📨 Broadcast", "admin_broadcast", ButtonStyle.PRIMARY))
    kb.row(btn("💾 Backup DB", "admin_backup", ButtonStyle.PRIMARY), btn("🔄 Restore DB", "admin_restore", ButtonStyle.PRIMARY))
    kb.row(btn("⛔ Ban", "admin_ban", ButtonStyle.DANGER), btn("✅ Unban", "admin_unban", ButtonStyle.SUCCESS))
    kb.row(btn("🏠 Main Menu", "main_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_all_categories():
        kb.button(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"admincat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("➕ Add Category", "addcat_start", ButtonStyle.SUCCESS))
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Stock Status", "stock_status", ButtonStyle.PRIMARY), btn("➕ Add Stock", "stock_add", ButtonStyle.SUCCESS))
    kb.row(btn("🗑️ Delete Stock", "stock_del", ButtonStyle.DANGER))
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    return kb.as_markup()

def delivery_kb(oid):
    kb = InlineKeyboardBuilder()
    kb.row(btn("✅ Approve", f"approve_{oid}", ButtonStyle.SUCCESS), btn("❌ Reject", f"reject_{oid}", ButtonStyle.DANGER))
    return kb.as_markup()


# ─── PAYMENT PROCESSOR ────────────────────────────────────────────────────────
async def process_payment(
    call_or_msg,
    state: FSMContext,
    pmethod: str,
    trx: str,
):
    """Central payment processing with auto-delivery for VPN/Proxy."""
    data = await state.get_data()
    prod = data.get("order_prod")
    if not prod:
        return
    cat_id = prod["category_id"]
    uinput = data.get("user_input", "")
    uid = call_or_msg.from_user.id if hasattr(call_or_msg, 'from_user') else call_or_msg.from_user.id
    price = prod["price"]

    cat = db.get_category(cat_id)
    parent_id = cat.get("parent_id") if cat else None
    is_auto = parent_id in ["vpn", "proxy"] or cat_id in ["vpn", "proxy"]

    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price):
            bal = db.get_balance(uid)
            lines = [
                "❌ *Insufficient Balance!*",
                "",
                f"Required: {fmt(price)}",
                f"Your Balance: {fmt(bal)}",
                "",
                "💳 Click below to add funds:",
            ]
            kb = InlineKeyboardBuilder()
            kb.row(btn("💳 Add Balance", "my_wallet", ButtonStyle.SUCCESS))
            kb.row(btn("🔙 Main Menu", "main_menu"))
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
            else:
                await call_or_msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
            return

    oid = db.add_order(uid, prod["id"], prod["name"], cat_id, price, uinput, pmethod, trx)

    if is_auto:
        stock = db.get_available_stock(prod["id"])
        if stock:
            stock_expiry = stock.get("expiry_days", prod.get("expiry_days", 30))
            delivery_data = {}
            if stock["stock_type"] == "key_only":
                delivery_data["key"] = stock["key_data"]
                cred_part = f"🔑 Key: `{stock['key_data']}`"
            else:
                delivery_data["email"] = stock["email"]
                delivery_data["password"] = stock["password"]
                cred_part = f"📧 Email: `{stock['email']}`\n🔐 Pass: `{stock['password']}`"
            delivery_data["server"] = uinput or "Auto"
            delivery_data["expires_days"] = stock_expiry

            now = now_local()
            expiry_date = now + timedelta(days=stock_expiry)
            db.update_order(oid, "delivered", delivery_data)

            box_body = [
                f"📦 {prod['name']}",
                f"🆔 Order: #{oid}",
                "",
                cred_part,
                f"🌍 Server: {uinput or 'Auto'}",
                "",
                f"✅ Activated: {now.strftime('%d %b %Y %I:%M %p')}",
                f"⏰ Validity: {stock_expiry} days",
                f"📅 Expires: {expiry_date.strftime('%d %B %Y')}",
                f"✅ Status: Active",
                "",
                f"🙏 Thank you! 👉 @{SUPPORT_USERNAME}"
            ]
            msg_text = generate_box("✅ AUTO-DELIVERED", box_body)

            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text(msg_text, reply_markup=None, parse_mode="Markdown")
            else:
                await call_or_msg.answer(msg_text, reply_markup=None, parse_mode="Markdown")

            await bot.send_message(
                uid,
                "✅ Your order has been delivered successfully! Thank you for choosing SKY STORE BD.",
                reply_markup=main_menu_kb(uid)
            )
        else:
            db.update_order(oid, "pending")
            lines = [
                "⏳ *No stock available!*",
                "",
                f"🆔 Order ID: #{oid}",
                "Waiting for admin to add stock. You'll be notified once delivered.",
            ]
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu_kb(uid), parse_mode="Markdown")
            else:
                await call_or_msg.answer("\n".join(lines), reply_markup=main_menu_kb(uid), parse_mode="Markdown")
            user = db.get_user(uid)
            admin_lines = [
                "📦 *STOCK OUT — Order Pending*",
                "",
                f"Order #{oid}",
                f"Product: {prod['name']}",
                f"User: {user['first_name'] if user else uid}",
                f"Info: {uinput}",
                f"Method: {pmethod}",
                f"TrxID: {trx}",
            ]
            for aid in ADMIN_IDS:
                try:
                    await bot.send_message(aid, "\n".join(admin_lines), parse_mode="Markdown")
                except:
                    pass
        await state.clear()
        return

    # Manual: YouTube / Netflix / Crunchyroll
    db.update_order(oid, "pending")
    lines = [
        "✅ *Your order has been received!*",
        "",
        f"🆔 Order ID: #{oid}",
        "⏳ Please wait for admin confirmation. You'll be notified once delivered.",
        "",
        f"📞 Support: @{SUPPORT_USERNAME}",
    ]
    if isinstance(call_or_msg, CallbackQuery):
        await call_or_msg.message.edit_text("\n".join(lines), reply_markup=None, parse_mode="Markdown")
    else:
        await call_or_msg.answer("\n".join(lines), reply_markup=None, parse_mode="Markdown")

    user = db.get_user(uid)
    admin_lines = [
        "📦 *NEW ORDER RECEIVED*",
        "",
        f"🆔 Order: #{oid}",
        f"👤 User ID: {uid}",
        f"📛 Name: {user['first_name'] if user else 'N/A'}",
        f"📦 Product: {prod['name']}",
        f"💰 Price: {fmt(price)}",
        f"📝 Info: {uinput}",
        f"💳 Method: {pmethod}",
        f"🔢 TrxID: {trx}",
    ]
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_lines), reply_markup=delivery_kb(oid), parse_mode="Markdown")
        except:
            pass
    await state.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  HANDLERS — USER SIDE
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    user = msg.from_user
    db.create_user(user.id, user.first_name, user.username)
    welcome = (
        "🌟 *WELCOME TO SKY STORE BD* 🌟\n\n"
        "⚡ *Premium Digital Store*\n"
        "▶️ YouTube  •  🎬 Netflix  •  🍿 Crunchyroll\n"
        "🔐 VPN Services  •  🌐 Proxy Services\n\n"
        "👇 *Select a category below:*"
    )
    await msg.answer(welcome, reply_markup=main_menu_kb(user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "main_menu")
async def go_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    welcome = "🌟 *SKY STORE BD* 🌟\n\n👇 *Select a category below:*"
    await call.message.edit_text(welcome, reply_markup=main_menu_kb(call.from_user.id), parse_mode="Markdown")

# ── CATEGORIES ────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def view_category(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[4:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    subcats = db.get_categories(parent_id=cat_id)
    if subcats:
        kb = InlineKeyboardBuilder()
        for sc in subcats:
            emoji = sc.get('icon', '📦')
            kb.button(text=f"{emoji} {sc['name']}", callback_data=f"subcat_{sc['id']}", style=ButtonStyle.PRIMARY)
        kb.adjust(1)
        kb.row(btn("🔙 Main Menu", "main_menu"))
        title = f"{cat.get('icon', '📦')} *{cat['name']}*\nSelect a subcategory:"
        await call.message.edit_text(title, reply_markup=kb.as_markup(), parse_mode="Markdown")
        return
    prods = db.get_products(cat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} *{cat['name']}*\nSelect a product:"
        await call.message.edit_text(title, reply_markup=cat_products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ No products available.", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("subcat_"))
async def view_subcategory(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subcat_id = call.data[7:]
    cat = db.get_category(subcat_id)
    if not cat:
        return
    prods = db.get_products(subcat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} *{cat['name']}*\nSelect a product:"
        await call.message.edit_text(title, reply_markup=cat_products_kb(subcat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ No products.", show_alert=True)

# ── ORDER FLOW ────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    cat_id = prod["category_id"]
    cat = db.get_category(cat_id)
    parent_id = cat.get("parent_id") if cat else None
    await state.update_data(order_pid=pid, order_prod=prod)

    is_vpn_proxy = parent_id in ["vpn", "proxy"] or cat_id in ["vpn", "proxy"]

    if is_vpn_proxy:
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 Price: {fmt(prod['price'])}",
            f"⏰ Validity: {prod.get('expiry_days', 30)} days",
            "",
            "🌍 Enter your preferred server/location, or tap Auto:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("⚡ Auto Location", "vpn_auto", ButtonStyle.PRIMARY))
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)
    elif cat_id == "crunchyroll":
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 Price: {fmt(prod['price'])}",
            f"⏰ Validity: {prod.get('expiry_days', 30)} days",
            "",
            "📧 Enter your Gmail address:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)
    else:
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 Price: {fmt(prod['price'])}",
            f"⏰ Validity: {prod.get('expiry_days', 30)} days",
            "",
            "📧 Enter your Gmail address:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [
        f"📦 *{prod['name']}*",
        f"🌍 Server: Auto",
        f"💰 Price: {fmt(prod['price'])}",
        "",
        "💳 Select payment method:",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.message(OrderFlow.waiting_input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please provide valid information.")
    await state.update_data(user_input=text)
    data = await state.get_data()
    prod = data["order_prod"]
    cat_id = prod["category_id"]

    if cat_id == "crunchyroll":
        lines = [
            f"📦 *{prod['name']}*",
            f"📧 Gmail: {text}",
            "",
            "📱 Enter your WhatsApp/Phone number:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_extra)
        return

    lines = [
        f"📦 *{prod['name']}*",
        f"📧 Info: {text}",
        f"💰 Price: {fmt(prod['price'])}",
        "",
        "💳 Select payment method:",
    ]
    await msg.answer("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.message(OrderFlow.waiting_extra)
async def get_extra_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 5:
        return await msg.answer("❌ Please enter a valid phone number.")
    data = await state.get_data()
    existing_gmail = data.get("user_input", "")
    await state.update_data(user_input=f"{existing_gmail} | Phone: {text}")
    lines = [
        f"📦 *{data['order_prod']['name']}*",
        f"📧 Gmail: {existing_gmail}",
        f"📱 Phone: {text}",
        "",
        "👤 Enter your Telegram username (e.g., @username):",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_tg)

@dp.message(OrderFlow.waiting_tg)
async def get_crunchyroll_tg(msg: Message, state: FSMContext):
    tg_user = msg.text.strip()
    if not tg_user.startswith("@"):
        tg_user = f"@{tg_user}"
    data = await state.get_data()
    existing = data.get("user_input", "")
    gmail = existing.split(" | ")[0]
    phone = existing.split(" | Phone: ")[1] if " | Phone: " in existing else ""
    full_input = f"{gmail} | Phone: {phone} | TG: {tg_user}"
    await state.update_data(user_input=full_input)
    prod = data["order_prod"]

    lines = [
        "📋 *Order Summary*",
        "",
        f"📦 Product: {prod['name']}",
        f"💰 Price: {fmt(prod['price'])}",
        f"📧 Gmail: {gmail}",
        f"📱 Phone: {phone}",
        f"👤 TG: {tg_user}",
        "",
        "✅ Your details have been recorded.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("📞 Contact Admin", f"https://t.me/{SUPPORT_USERNAME}", ButtonStyle.PRIMARY))
    kb.row(btn("💳 Proceed to Payment", "go_payment", ButtonStyle.SUCCESS))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.callback_query(lambda c: c.data == "go_payment")
async def go_payment_cb(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [
        f"📦 *{prod['name']}*",
        f"💰 Price: {fmt(prod['price'])}",
        "",
        "💳 Select payment method:",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

# ── PAYMENT ───────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data[4:]
    await state.update_data(pay_method=method)
    data = await state.get_data()
    prod = data.get("order_prod")
    if not prod:
        await call.message.edit_text("Session expired. Please start again.", reply_markup=main_menu_kb(call.from_user.id))
        return
    price = prod["price"]
    uid = call.from_user.id

    if method == "wallet":
        bal = db.get_balance(uid)
        if bal < price:
            lines = [
                "❌ *Insufficient Balance!*",
                "",
                f"Required: {fmt(price)}",
                f"Your Balance: {fmt(bal)}",
                "",
                "💳 Add funds or use another method:",
            ]
            kb = InlineKeyboardBuilder()
            kb.row(btn("💳 Add Balance", "my_wallet", ButtonStyle.SUCCESS))
            kb.row(btn("🔙 Main Menu", "main_menu"))
            await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
        trx = f"WAL{now_local():%Y%m%d%H%M%S}{random.randint(100,999)}"
        await process_payment(call, state, "Wallet Balance", trx)
    else:
        nums = {"bkash": "01742958563", "nagad": "01748506069", "rocket": "01742958563"}
        lines = [
            "💳 *Payment Instructions*",
            "",
            f"💰 Amount: {fmt(price)}",
            f"📱 Method: {method.upper()}",
            f"🔢 Number: `{nums.get(method, '')}` (Send Money)",
            "",
            "📌 After sending money, enter your Transaction ID (TrxID):",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("❌ Cancel", "main_menu", ButtonStyle.DANGER))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_trxid)

@dp.message(OrderFlow.waiting_trxid)
async def get_trx(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx:
        return
    data = await state.get_data()
    method = data.get("pay_method", "Manual")
    method_names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}
    mn = method_names.get(method, method)
    await process_payment(msg, state, mn, trx)

# ── WALLET & DEPOSIT ──────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    uid = call.from_user.id
    bal = db.get_balance(uid)
    lines = [
        "💳 *Wallet & Deposit*",
        "──────────────────────────",
        f"💰 Your Balance: *{fmt(bal)}*",
        "──────────────────────────",
        "📌 *To add balance:*",
        "1. Send money to any number below:",
        "   💖 *bKash:* `01742958563`",
        "   🟠 *Nagad:* `01748506069`",
        "   🚀 *Rocket:* `01742958563`",
        "",
        "2. Send the *amount* and *TrxID* below.",
        "",
        "🎁 *Have a promo code?* Tap below:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🎁 Apply Promo Code", "apply_promo", ButtonStyle.PRIMARY))
    kb.row(btn("💳 Submit Deposit", "submit_deposit", ButtonStyle.SUCCESS))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "apply_promo")
async def promo_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["🎁 *Apply Promo Code*", "", "Enter your promo code below:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "my_wallet"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositFlow.waiting_promo)

@dp.message(DepositFlow.waiting_promo)
async def promo_apply(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()
    promo = db.get_promo(code)
    if not promo:
        return await msg.answer("❌ Invalid or expired promo code. Try again or tap back.")

    uid = msg.from_user.id
    amount = promo.get("amount", 0)

    if promo.get("expires_at"):
        try:
            exp = datetime.strptime(promo["expires_at"], "%Y-%m-%d")
            if now_local() > exp:
                return await msg.answer("❌ This promo code has expired.")
        except:
            pass

    if promo.get("max_uses", 0) > 0 and promo["used_count"] >= promo["max_uses"]:
        return await msg.answer("❌ This promo code has reached its usage limit.")

    db.update_balance(uid, amount)
    trx_id = f"PROMO_{code}_{now_local():%Y%m%d%H%M%S}"
    db.add_transaction(uid, amount, "promo", "PromoCode", trx_id, f"Promo: {code}")
    db.use_promo(code)

    new_bal = db.get_balance(uid)
    lines = [
        "🎁 *Promo Code Applied!* ✅",
        "",
        f"Code: `{code}`",
        f"Bonus: {fmt(amount)}",
        f"New Balance: {fmt(new_bal)}",
        "",
        "Thank you!",
    ]
    await msg.answer("\n".join(lines), reply_markup=main_menu_kb(uid), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "submit_deposit")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💳 *Submit Deposit*",
        "",
        "Send the *amount* and *TrxID* like this:",
        "`500 TRX1234567`",
        "",
        "Or send them separately. Admin will verify and add balance.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "my_wallet"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositFlow.waiting_trxid)

@dp.message(DepositFlow.waiting_trxid)
async def deposit_trx_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    uid = msg.from_user.id
    # Try to extract amount
    amount_match = re.search(r'(\d+)', text)
    amount_str = amount_match.group(1) if amount_match else "?"
    admin_text = [
        "💰 *NEW DEPOSIT REQUEST*",
        "",
        f"👤 User ID: `{uid}`",
        f"📛 Name: {msg.from_user.first_name}",
        f"📝 Text: `{text}`",
        f"💵 Detected Amount: {amount_str}",
        "",
        "✅ Go to Admin Panel → Add Balance to credit this user.",
    ]
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_text), parse_mode="Markdown")
        except:
            pass
    await msg.answer(
        "✅ Your deposit request has been submitted!\n"
        "Admin will verify and add balance shortly.\n"
        f"📞 Contact: @{SUPPORT_USERNAME}",
        reply_markup=main_menu_kb(uid)
    )
    await state.clear()

# ── MY ORDERS ─────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    user_orders = db.get_user_orders(uid, 10)
    if not user_orders:
        lines = ["📦 *Your Orders*", "", "No orders found."]
    else:
        lines = ["📜 *Your Recent Orders:*", ""]
        for o in user_orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* — {o['product_name']}")
            lines.append(f"   {fmt(o['amount'])} | Status: *{o['status']}*")
            if o.get("delivery_data"):
                dd = o["delivery_data"]
                if dd.get("key"):
                    lines.append(f"   🔑 Key: `{dd['key']}`")
                if dd.get("email"):
                    lines.append(f"   📧 Email: `{dd['email']}`")
                if dd.get("password"):
                    lines.append(f"   🔐 Pass: `{dd['password']}`")
                if dd.get("expires_days"):
                    lines.append(f"   ⏰ Validity: {dd['expires_days']} days")
            lines.append("")
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text("⚙️ *Admin Panel*\nSelect an option:", reply_markup=admin_kb(), parse_mode="Markdown")

# ── STATS ─────────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    user_count = len(users)
    pending = db.pending_count()
    sales = db.get_sales_summary()
    balance_total = sum(u['balance'] for u in users)
    lines = [
        "📊 *Dashboard*",
        "",
        f"👥 Total Users: {user_count}",
        f"⏳ Pending Orders: {pending}",
        f"💰 Total Balance: {fmt(balance_total)}",
        "",
        "📦 *Sales Summary:*",
    ]
    if sales:
        for s in sales[:10]:
            lines.append(f"• {s['product_name']}: {s['cnt']}x ({fmt(s['total'])})")
    else:
        lines.append("No sales yet.")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

# ── ADD BALANCE (FIXED) ───────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💰 *Add Balance*",
        "",
        "Enter the user's Telegram *User ID* or *@username*:",
        "",
        "💡 To find User ID:",
        "• Ask user to message @userinfobot",
        "• Or look in order notifications",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addbal_uid)

@dp.message(AdminFlow.addbal_uid)
async def addbal_uid_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    user = None
    uid = None

    # Try as @username first
    if text.startswith("@") or text.isalpha():
        user = db.get_user_by_username(text)
        if user:
            uid = user["user_id"]
    else:
        try:
            uid = int(text)
            user = db.get_user(uid)
        except:
            pass

    if not user:
        return await msg.answer(
            "❌ User not found. Make sure the user has started the bot.\n"
            "Try using their numeric Telegram User ID.",
            reply_markup=admin_kb()
        )

    await state.update_data(addbal_uid=uid)
    lines = [
        "💰 *Add Balance*",
        "",
        f"👤 User: {user['first_name']} (@{user['username'] or 'N/A'})",
        f"🆔 ID: `{uid}`",
        f"💳 Current Balance: {fmt(user['balance'])}",
        "",
        "Enter amount to add:",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.addbal_amt)

@dp.message(AdminFlow.addbal_amt)
async def addbal_amount_received(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        if amt <= 0:
            return await msg.answer("❌ Amount must be positive.")
        data = await state.get_data()
        uid = data["addbal_uid"]

        db.update_balance(uid, amt)
        trx_id = f"ADMIN_{now_local():%Y%m%d%H%M%S}"
        db.add_transaction(uid, amt, "admin_add", "Admin", trx_id)
        new_bal = db.get_balance(uid)

        # Notify user
        box_body = [
            f"💰 Balance Added!",
            f"Amount: {fmt(amt)}",
            f"New Balance: {fmt(new_bal)}",
            f"Date: {now_local().strftime('%d %b %Y %I:%M %p')}",
            "",
            f"🙏 @{SUPPORT_USERNAME}"
        ]
        user_msg = generate_box("💰 BALANCE UPDATED", box_body)
        try:
            await bot.send_message(uid, user_msg, parse_mode="Markdown")
        except:
            pass

        lines = [
            "✅ *Balance added successfully!*",
            "",
            f"Amount: {fmt(amt)}",
            f"User ID: {uid}",
            f"New Balance: {fmt(new_bal)}",
            f"TrxID: {trx_id}",
        ]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    except ValueError:
        await msg.answer("❌ Invalid amount. Enter a number.")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

# ── CATEGORY MANAGEMENT ───────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📂 *Category Management*", reply_markup=admin_cats_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    lines = [
        f"📂 *{cat.get('icon', '')} {cat['name']}*",
        f"ID: `{cat_id}`",
        f"Subcategories: {len(subcats)}",
        f"Products: {len(prods)}",
    ]
    if prods:
        lines.append("")
        for p in prods[:5]:
            lines.append(f"• {p['name']} — {fmt(p['price'])}")
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Edit Name/Desc", f"editcat_{cat_id}", ButtonStyle.PRIMARY))
    kb.row(btn("🗑️ Delete Category", f"delcat_{cat_id}", ButtonStyle.DANGER))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "addcat_start")
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["➕ *Add New Category*", "", "Is this a main category or a subcategory?"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("📂 Main Category", "addcat_root", ButtonStyle.PRIMARY))
    for p in db.get_categories():
        kb.row(btn(f"↪️ Sub of: {p.get('icon', '')} {p['name']}", f"addcat_child_{p['id']}"))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_parent)

@dp.callback_query(lambda c: c.data.startswith("addcat_root") or c.data.startswith("addcat_child_"))
async def addcat_parent_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = None if call.data == "addcat_root" else call.data[13:]
    await state.update_data(addcat_parent=parent_id)
    lines = ["➕ *Add Category*", "", "Enter category name (with emoji):", "Example: `🔵 NordVPN`"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_name)

@dp.message(AdminFlow.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    lines = ["Enter a short description (or type 'skip'):"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_desc)

@dp.message(AdminFlow.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    await state.update_data(addcat_desc=desc)
    lines = ["Enter an icon emoji (or type 'skip' for default 📦):"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_icon)

@dp.message(AdminFlow.addcat_icon)
async def addcat_icon(msg: Message, state: FSMContext):
    icon = msg.text.strip() if msg.text.strip().lower() != "skip" else "📦"
    data = await state.get_data()
    parent_id = data.get("addcat_parent")
    name = data["addcat_name"]
    desc = data.get("addcat_desc", "")
    auto_id = generate_id("cat_")
    db.add_category(auto_id, parent_id, name, desc, icon)
    lines = [
        "✅ *Category Created!*",
        "",
        f"Name: {name}",
        f"ID: `{auto_id}` (auto-generated)",
        f"Icon: {icon}",
    ]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_target=cat_id)
    lines = ["✏️ *Edit Category*", "", "Enter new name (or type 'skip' to keep current):"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", f"admincat_{cat_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editcat_name)

@dp.message(AdminFlow.editcat_name)
async def editcat_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    cat_id = (await state.get_data())["editcat_target"]
    if name.lower() != "skip":
        db.update_category(cat_id, name=name)
    lines = ["Enter new description (or type 'skip'):"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.editcat_desc)

@dp.message(AdminFlow.editcat_desc)
async def editcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip()
    cat_id = (await state.get_data())["editcat_target"]
    if desc.lower() != "skip":
        db.update_category(cat_id, description=desc)
    await msg.answer("✅ *Category Updated!*", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    cid = call.data[7:]
    db.delete_category(cid)
    await call.message.edit_text(f"🗑️ Category `{cid}` deleted.", reply_markup=admin_cats_kb(), parse_mode="Markdown")

# ── EDIT PRODUCT ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_editprod")
async def admin_editprod_list(call: CallbackQuery):
    await call.answer()
    cats = db.get_all_categories()
    kb = InlineKeyboardBuilder()
    for cat in cats:
        prods = db.get_products(cat["id"])
        if prods:
            kb.button(text=f"{cat.get('icon', '📦')} {cat['name']} ({len(prods)})", callback_data=f"editprods_cat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    await call.message.edit_text("📦 *Edit Products*\nSelect a category:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprods_cat_"))
async def editprods_cat(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[14:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"✏️ {p['name']} — {fmt(p['price'])}", callback_data=f"editprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("➕ Add Product Here", f"addprod_now_{cat_id}", ButtonStyle.SUCCESS))
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text(f"Products in {cat.get('icon', '')} {cat['name']}:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod:
        return
    await state.update_data(editprod_target=pid)
    lines = [
        f"📦 *{prod['name']}*",
        f"ID: `{pid}`",
        f"💰 Price: {fmt(prod['price'])}",
        f"⏰ Expiry: {prod.get('expiry_days', 30)} days",
        f"📦 Stock Type: {prod.get('stock_type', 'N/A')}",
        "",
        "What do you want to edit?",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Name", f"editprod_field_name", ButtonStyle.PRIMARY))
    kb.row(btn("💰 Price", f"editprod_field_price", ButtonStyle.PRIMARY))
    kb.row(btn("⏰ Expiry Days", f"editprod_field_expiry", ButtonStyle.PRIMARY))
    kb.row(btn("🗑️ Delete Product", f"delprod_{pid}", ButtonStyle.DANGER))
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_field)

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"))
async def editprod_field_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    field = call.data[16:]
    await state.update_data(editprod_field=field)
    lines = [f"✏️ Enter new value for *{field}*:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_value)

@dp.message(AdminFlow.editprod_value)
async def editprod_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["editprod_target"]
    field = data["editprod_field"]
    value = msg.text.strip()
    try:
        if field == "name":
            db.update_product(pid, name=value)
        elif field == "price":
            db.update_product(pid, price=float(value))
        elif field == "expiry":
            db.update_product(pid, expiry_days=int(value))
        await msg.answer("✅ *Product Updated!*", reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]
    db.delete_product(pid)
    await call.message.edit_text(f"🗑️ Product `{pid}` deleted.", reply_markup=admin_kb(), parse_mode="Markdown")

# ── ADD PRODUCT ───────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("addprod_now_"))
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[12:]
    await state.update_data(addprod_cat=cat_id)
    lines = ["➕ *Add Product*", "", "Enter product name:", "Example: `🔵 NordVPN 6 Months`"]
    await call.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.addprod_name)

@dp.message(AdminFlow.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    await msg.answer("Enter price (number only):\nExample: `650`", parse_mode="Markdown")
    await state.set_state(AdminFlow.addprod_price)

@dp.message(AdminFlow.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        await msg.answer("Enter expiry in days (e.g., `30` for 1 month):", parse_mode="Markdown")
        await state.set_state(AdminFlow.addprod_expiry)
    except:
        await msg.answer("❌ Enter a valid number.")

@dp.message(AdminFlow.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        data = await state.get_data()
        cat_id = data["addprod_cat"]
        cat = db.get_category(cat_id)
        parent_id = cat.get("parent_id") if cat else None

        if parent_id in ["vpn", "proxy"] or cat_id in ["vpn", "proxy"]:
            await state.update_data(addprod_expiry=expiry)
            await msg.answer("Stock type:\n• `email_pass` — Email + Password\n• `key_only` — Just a key/code", parse_mode="Markdown")
            await state.set_state(AdminFlow.addprod_stocktype)
        else:
            auto_id = generate_id("prod_")
            db.add_product(auto_id, cat_id, data["addprod_name"], data["addprod_price"], 0, "manual", expiry)
            await msg.answer(
                f"✅ *Product Added!*\n\nName: {data['addprod_name']}\nID: `{auto_id}`\nPrice: {fmt(data['addprod_price'])}\nExpiry: {expiry} days\nType: Manual",
                reply_markup=admin_kb(), parse_mode="Markdown"
            )
            await state.clear()
    except:
        await msg.answer("❌ Enter a valid number of days.")

@dp.message(AdminFlow.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ["email_pass", "key_only"]:
        return await msg.answer("❌ Please type `email_pass` or `key_only`.")
    data = await state.get_data()
    auto_id = generate_id("prod_")
    db.add_product(auto_id, data["addprod_cat"], data["addprod_name"], data["addprod_price"], 0, stype, data["addprod_expiry"])
    await msg.answer(
        f"✅ *Product Added!*\n\nName: {data['addprod_name']}\nID: `{auto_id}`\nPrice: {fmt(data['addprod_price'])}\nExpiry: {data['addprod_expiry']} days\nStock Type: {stype}",
        reply_markup=admin_kb(), parse_mode="Markdown"
    )
    await state.clear()

# ── STOCK MANAGEMENT ──────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    lines = ["🔑 *Stock Status*", ""]
    if counts:
        for s in counts:
            lines.append(f"📦 `{s['product_id']}` ({s['stock_type']}): {s['cnt']} available")
    else:
        lines.append("No stock available.")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prods = db.get_all_products()
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"📦 {p['name']} [{p['stock_type']}]", callback_data=f"stkprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🔑 *Add Stock*\nSelect a product:", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_target)

@dp.callback_query(lambda c: c.data.startswith("stkprod_"))
async def stock_target_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[8:]
    prod = db.get_product(pid)
    if not prod:
        return
    await state.update_data(stock_target=pid, stock_type=prod.get("stock_type", "key_only"))
    lines = [
        f"🔑 *Add Stock to:* {prod['name']}",
        f"Stock Type: {prod.get('stock_type', 'N/A')}",
        f"Expiry: {prod.get('expiry_days', 30)} days",
        "",
        "📤 Send items (one per line) or upload a `.txt` file.",
        "",
        "For email:password:",
        "`email@example.com:password123`",
        "",
        "For key-only:",
        "`ABC123XYZ`",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "stock_add"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_input)

@dp.message(AdminFlow.stock_input, F.text)
async def stock_input_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    lines_input = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    for line in lines_input:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip())
                added += 1
    await msg.answer(f"✅ {added} stock items added!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.message(AdminFlow.stock_input, F.document)
async def stock_file_upload(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    doc = msg.document
    if not doc.file_name.endswith(".txt"):
        return await msg.answer("❌ Please upload a `.txt` file.")
    file = await bot.get_file(doc.file_id)
    file_path = f"/tmp/{doc.file_id}.txt"
    await bot.download_file(file.file_path, destination=file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines_input = [l.strip() for l in content.split("\n") if l.strip()]
    except:
        return await msg.answer("❌ Could not read file.")
    os.remove(file_path)
    added = 0
    for line in lines_input:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip())
                added += 1
    await msg.answer(f"✅ {added} stock items added from file!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del_list(call: CallbackQuery):
    await call.answer()
    all_stock = db.get_all_stock()
    kb = InlineKeyboardBuilder()
    for s in all_stock[:20]:
        status = "✅" if s['is_used'] else "📦"
        display = s.get('key_data') or s.get('email') or f"ID:{s['id']}"
        kb.button(text=f"{status} #{s['id']} {display[:25]}", callback_data=f"delstock_{s['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🗑️ *Select stock to delete:*", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del_list(call)

# ── BACKUP DATABASE ───────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_backup")
async def admin_backup(call: CallbackQuery):
    await call.answer("💾 Creating backup...")
    try:
        backup_path = db.backup()
        file_size = os.path.getsize(backup_path)
        await call.message.edit_text(
            f"💾 *Backup Created!*\n\n"
            f"📁 File: `{os.path.basename(backup_path)}`\n"
            f"📏 Size: {file_size/1024:.1f} KB\n\n"
            f"Sending file...",
            parse_mode="Markdown"
        )
        # Send the backup file to admin
        doc = FSInputFile(backup_path)
        await bot.send_document(
            call.from_user.id,
            doc,
            caption=f"📦 *SKY STORE BD - Database Backup*\n📅 {now_local().strftime('%d %B %Y %I:%M %p')}\n📏 {file_size/1024:.1f} KB",
            parse_mode="Markdown"
        )
        await call.message.edit_text(
            "✅ *Backup sent successfully!*\n\nThe backup file has been sent as a document above.",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await call.message.edit_text(
            f"❌ Backup failed: {e}",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )

# ── RESTORE DATABASE ─────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_restore")
async def admin_restore_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "🔄 *Restore Database*",
        "",
        "⚠️ *WARNING:* This will OVERWRITE the current database!",
        "",
        "Send the backup `.db` file to restore.",
        "The file should be a valid SQLite database.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Cancel", "admin_menu", ButtonStyle.DANGER))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.restore_file)

@dp.message(AdminFlow.restore_file, F.document)
async def admin_restore_file(msg: Message, state: FSMContext):
    doc = msg.document
    if not doc.file_name.endswith(".db"):
        return await msg.answer("❌ Please upload a `.db` file (SQLite database backup).")

    await msg.answer("🔄 Downloading and restoring database...")

    file = await bot.get_file(doc.file_id)
    restore_path = f"/tmp/restore_{doc.file_id}.db"
    await bot.download_file(file.file_path, destination=restore_path)

    try:
        success = db.restore(restore_path)
        if success:
            await msg.answer(
                "✅ *Database restored successfully!*\n\nThe bot is now using the restored data.",
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
        else:
            await msg.answer(
                "❌ Failed to restore database. The file may be corrupted or invalid.",
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
    except Exception as e:
        await msg.answer(
            f"❌ Restore error: {e}",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    finally:
        if os.path.exists(restore_path):
            os.remove(restore_path)
    await state.clear()

# ── BROADCAST ─────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "📨 *Broadcast Message*",
        "",
        "Send the text or video with caption to broadcast to all users:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.broadcast_msg)

@dp.message(AdminFlow.broadcast_msg, F.text)
async def broadcast_text(msg: Message, state: FSMContext):
    text = msg.text
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_message(u["user_id"], text)
                sent += 1
            except:
                pass
    await msg.answer(f"✅ Broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

@dp.message(AdminFlow.broadcast_msg, F.video)
async def broadcast_video(msg: Message, state: FSMContext):
    video = msg.video.file_id
    caption = msg.caption or ""
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_video(u["user_id"], video, caption=caption)
                sent += 1
            except:
                pass
    await msg.answer(f"✅ Video broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

# ── BAN / UNBAN ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["⛔ *Ban User*", "", "Enter User ID to ban:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.ban_uid)

@dp.message(AdminFlow.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, True)
        await msg.answer(f"⛔ User `{uid}` banned.", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ Invalid ID.")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["✅ *Unban User*", "", "Enter User ID to unban:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.unban_uid)

@dp.message(AdminFlow.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, False)
        await msg.answer(f"✅ User `{uid}` unbanned.", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ Invalid ID.")
    await state.clear()

# ── ADMIN ORDER APPROVE/REJECT ────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    await call.answer("✅ Approving...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    prod = db.get_product(order["product_id"])
    expiry_days = prod.get("expiry_days", 30) if prod else 30
    now = now_local()
    expiry_date = now + timedelta(days=expiry_days)
    db.update_order(oid, "delivered", {
        "approved_at": now.strftime("%d %B %Y %I:%M %p"),
        "expires": expiry_date.strftime("%d %B %Y"),
        "expiry_days": expiry_days,
        "info": order.get("user_input", "N/A")
    })
    box_body = [
        f"📦 {order['product_name']}",
        f"🆔 Order ID: #{oid}",
        f"📧 Info: {order.get('user_input', 'N/A')}",
        "",
        f"✅ Approved: {now.strftime('%d %b %Y %I:%M %p')}",
        f"⏰ Validity: {expiry_days} days",
        f"📅 Expires: {expiry_date.strftime('%d %B %Y')}",
        f"✅ Status: Active",
        "",
        f"🙏 Thank you! @{SUPPORT_USERNAME}"
    ]
    user_text = generate_box("✅ ORDER CONFIRMED", box_body)
    try:
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    except:
        pass
    await call.message.edit_text(f"✅ Order #{oid} Approved & Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer("❌ Rejecting...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    db.update_order(oid, "cancelled")
    try:
        await bot.send_message(order["user_id"], f"❌ Order #{oid} has been cancelled.\nContact @{SUPPORT_USERNAME} for details.", parse_mode="Markdown")
    except:
        pass
    await call.message.edit_text(f"❌ Order #{oid} Rejected.", reply_markup=admin_kb(), parse_mode="Markdown")

# ── DELIVER (Manual) ──────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📦 *Manual Delivery*", "", "Enter Order ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.deliver_oid)

@dp.message(AdminFlow.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text.strip())
        order = db.get_order(oid)
        if not order:
            return await msg.answer("❌ Order not found.")
        await state.update_data(oid=oid)
        lines = [
            f"📦 *Order #{oid}*",
            f"Product: {order['product_name']}",
            f"User ID: {order['user_id']}",
            f"Info: {order.get('user_input', 'N/A')}",
            "",
            "Enter delivery details:",
            "• For Email:Password: `email:password`",
            "• For Key only: `KEY123`",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(AdminFlow.deliver_file)
    except:
        await msg.answer("❌ Invalid Order ID.")

@dp.message(AdminFlow.deliver_file)
async def deliver_file(msg: Message, state: FSMContext):
    data = await state.get_data()
    oid = data["oid"]
    order = db.get_order(oid)
    delivery_text = msg.text.strip()
    if ":" in delivery_text:
        email, password = delivery_text.split(":", 1)
        delivery_data = {"email": email.strip(), "password": password.strip()}
    else:
        delivery_data = {"key": delivery_text}
    prod = db.get_product(order["product_id"])
    expiry_days = prod.get("expiry_days", 30) if prod else 30
    now = now_local()
    expiry_date = now + timedelta(days=expiry_days)
    db.update_order(oid, "delivered", delivery_data)
    cred_part = ""
    if "key" in delivery_data:
        cred_part = f"🔑 Key: `{delivery_data['key']}`"
    else:
        cred_part = f"📧 Email: `{delivery_data['email']}`\n🔐 Pass: `{delivery_data['password']}`"
    box_body = [
        f"📦 {order['product_name']}",
        f"🆔 Order ID: #{oid}",
        "",
        cred_part,
        "",
        f"✅ Delivered: {now.strftime('%d %b %Y %I:%M %p')}",
        f"⏰ Validity: {expiry_days} days",
        f"📅 Expires: {expiry_date.strftime('%d %B %Y')}",
        f"✅ Status: Active",
        "",
        f"🙏 Thank you! @{SUPPORT_USERNAME}"
    ]
    user_text = generate_box("✅ MANUAL DELIVERY", box_body)
    try:
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    except:
        pass
    await msg.answer(f"✅ Order #{oid} Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("🚀 SKY STORE BD Bot v3.0 starting...")
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
