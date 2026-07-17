#!/usr/bin/env python3
"""
SKY STORE BD — Premium Digital Store Telegram Bot
Version 5.1 — FIXED: Category Hierarchy Navigation & Product Editing
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
                is_active INTEGER DEFAULT 1,
                auto_deliver INTEGER DEFAULT 0
            )""")
            try:
                conn.execute("ALTER TABLE categories ADD COLUMN auto_deliver INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass

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
            cur = conn.execute("SELECT COUNT(*) FROM categories WHERE parent_id IS NULL")
            if cur.fetchone()[0] == 0:
                self._seed_data(conn)
            conn.commit()

    def _seed_data(self, conn):
        main_cats = [
            ("youtube", None, "YouTube Premium", "Ad-free YouTube", "▶️", 1, 0),
            ("netflix", None, "Netflix Premium", "Premium Netflix", "🎬", 2, 0),
            ("crunchyroll", None, "Crunchyroll", "Anime streaming", "🍿", 3, 0),
            ("vpn", None, "VPN Services", "Premium VPNs", "🔐", 4, 1),
            ("proxy", None, "IP / Proxy Services", "Residential proxies", "🌐", 5, 1)
        ]
        for cat in main_cats:
            conn.execute("INSERT INTO categories(id,parent_id,name,description,icon,sort_order,auto_deliver) VALUES(?,?,?,?,?,?,?)", cat)

        conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                     ("yt_1m", "youtube", "▶️ YouTube Premium 1 Month", 100, "manual", 30))
        conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                     ("nf_1m", "netflix", "🎬 Netflix Premium 1 Month", 200, "manual", 30))
        conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                     ("cr_7d", "crunchyroll", "🍿 Crunchyroll 7 Days", 70, "manual", 7))
        conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                     ("cr_1m", "crunchyroll", "🍿 Crunchyroll 1 Month", 200, "manual", 30))

        vpn_names = ["HMA", "Nord", "Express", "G-VPN", "IPVanish"]
        for vpn in vpn_names:
            subcat_id = f"vpn_{vpn.lower()}"
            conn.execute("INSERT INTO categories(id,parent_id,name,description,icon,sort_order,auto_deliver) VALUES(?,?,?,?,?,?,?)",
                         (subcat_id, "vpn", f"🔐 {vpn} VPN", f"{vpn} VPN Service", "🔐", 1, 1))
            pid = f"vpn_{vpn.lower()}_7d"
            conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                         (pid, subcat_id, f"🔐 {vpn} VPN 7 Days", 0, "email_pass", 7))

        proxy_names = ["Rapid", "DataPlus", "ProxySeller", "ABC", "Chill", "Owl"]
        for i, proxy in enumerate(proxy_names):
            subcat_id = f"proxy_{proxy.lower()}"
            conn.execute("INSERT INTO categories(id,parent_id,name,description,icon,sort_order,auto_deliver) VALUES(?,?,?,?,?,?,?)",
                         (subcat_id, "proxy", f"🌐 {proxy} Proxy", f"{proxy} Proxy Service", "🌐", i+1, 1))
            pid = f"proxy_{proxy.lower()}_30d"
            if proxy == "Owl":
                conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                             (pid, subcat_id, "🦉 Owl Proxy 30 Days", 10, "ip_port", 30))
            else:
                conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                             (pid, subcat_id, f"🌐 {proxy} Proxy 30 Days", 500, "key_only", 30))
        conn.commit()

    # ── Users ──
    def get_user(self, uid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_user_by_username(self, username):
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

    def get_all_main_categories(self):
        """Return only root-level (parent_id IS NULL) categories."""
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY sort_order")
            return [dict(r) for r in cur.fetchall()]

    def get_category(self, cid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cid,))
            r = cur.fetchone()
            return dict(r) if r else None

    def add_category(self, cid, parent_id, name, desc="", icon="📦", sort=0, auto_deliver=0):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO categories(id,parent_id,name,description,icon,sort_order,auto_deliver) VALUES(?,?,?,?,?,?,?)", (cid, parent_id, name, desc, icon, sort, auto_deliver))
            conn.commit()

    def update_category(self, cid, **kwargs):
        with self._get_conn() as conn:
            for key, value in kwargs.items():
                if value is not None:
                    allowed = ["name", "description", "icon", "sort_order", "auto_deliver", "is_active", "parent_id"]
                    if key in allowed:
                        conn.execute(f"UPDATE categories SET {key}=? WHERE id=?", (value, cid))
            conn.commit()

    def delete_category(self, cid):
        if cid in ("youtube", "netflix", "crunchyroll", "vpn", "proxy"):
            return False
        with self._get_conn() as conn:
            conn.execute("UPDATE categories SET is_active=0 WHERE id=?", (cid,))
            conn.execute("UPDATE products SET is_active=0 WHERE category_id=?", (cid,))
            conn.commit()
            return True

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
                    allowed = ["name", "price", "bonus", "stock_type", "expiry_days", "is_active", "sort_order", "category_id"]
                    if key in allowed:
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

    def get_products_by_categories(self, category_ids):
        if not category_ids:
            return []
        placeholders = ",".join("?" for _ in category_ids)
        with self._get_conn() as conn:
            cur = conn.execute(f"SELECT * FROM products WHERE category_id IN ({placeholders}) AND is_active=1 ORDER BY sort_order, price", category_ids)
            return [dict(r) for r in cur.fetchall()]

    def get_subcategory_ids(self, parent_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT id FROM categories WHERE parent_id=? AND is_active=1", (parent_id,))
            return [r["id"] for r in cur.fetchall()]

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
        if backup_path is None:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            ts = now_local().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(BACKUP_DIR, f"store_backup_{ts}.db")
        shutil.copy2(self.path, backup_path)
        return backup_path

    def restore(self, backup_path):
        if not os.path.exists(backup_path):
            return False
        try:
            conn = sqlite3.connect(backup_path)
            conn.execute("SELECT COUNT(*) FROM users")
            conn.close()
        except:
            return False
        shutil.copy2(backup_path, self.path)
        return True

    def export_json(self):
        data = {}
        with self._get_conn() as conn:
            for table in ["users", "orders", "transactions", "categories", "products", "stock", "promo_codes"]:
                cur = conn.execute(f"SELECT * FROM {table}")
                rows = [dict(r) for r in cur.fetchall()]
                data[table] = rows
        return data


# ─── GLOBALS ──────────────────────────────────────────────────────────────────
db = Database()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ─── STATES ───────────────────────────────────────────────────────────────────
class OrderFlow(StatesGroup):
    waiting_input = State()
    waiting_extra = State()
    waiting_tg = State()
    waiting_payment = State()
    waiting_trxid = State()

class DepositFlow(StatesGroup):
    waiting_trxid = State()
    waiting_promo = State()

class AdminFlow(StatesGroup):
    addbal_uid = State()
    addbal_amt = State()
    ban_uid = State()
    unban_uid = State()
    broadcast_msg = State()

    # Product editing - hierarchical
    editprod_maincat = State()      # waiting for main category choice
    editprod_subcat = State()       # waiting for subcategory choice
    editprod_select = State()       # waiting for product choice
    editprod_field = State()        # which field to edit
    editprod_value = State()        # new value for field

    # Add product - hierarchical
    addprod_maincat = State()
    addprod_subcat = State()
    addprod_name = State()
    addprod_price = State()
    addprod_expiry = State()
    addprod_stocktype = State()

    # Add stock - hierarchical
    stock_maincat = State()
    stock_subcat = State()
    stock_product = State()
    stock_target = State()
    stock_type_choice = State()
    stock_input = State()

    # Category management
    addcat_parent = State()
    addcat_name = State()
    addcat_desc = State()
    addcat_icon = State()
    addcat_autodeliver = State()
    editcat_target = State()
    editcat_name = State()
    editcat_desc = State()
    editcat_autodeliver = State()

    # Other admin
    promo_code = State()
    promo_amount = State()
    promo_discount = State()
    promo_uses = State()
    promo_expiry = State()
    restore_file = State()
    deliver_oid = State()
    deliver_file = State()


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
    kb.row(btn("📦 Manual Deliver", "admin_deliver", ButtonStyle.PRIMARY))
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
    data = await state.get_data()
    prod = data.get("order_prod")
    if not prod:
        return
    cat_id = prod["category_id"]
    uinput = data.get("user_input", "")
    uid = call_or_msg.from_user.id if hasattr(call_or_msg, 'from_user') else call_or_msg.from_user.id
    price = prod["price"]

    cat = db.get_category(cat_id)
    is_auto = cat.get("auto_deliver", 0) == 1 if cat else False

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
            stock_expiry = stock.get("expiry_days") or prod.get("expiry_days", 30)
            delivery_data = {}
            if stock["stock_type"] == "key_only":
                delivery_data["key"] = stock["key_data"]
                cred_part = f"🔑 Key: `{stock['key_data']}`"
            elif stock["stock_type"] == "email_pass":
                delivery_data["email"] = stock["email"]
                delivery_data["password"] = stock["password"]
                cred_part = f"📧 Email: `{stock['email']}`\n🔐 Pass: `{stock['password']}`"
            elif stock["stock_type"] == "ip_port":
                delivery_data["ip_port"] = stock["key_data"]
                cred_part = f"🌐 IP:Port:User:Pass: `{stock['key_data']}`"
            else:
                cred_part = "Unknown stock type"
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

    # Manual
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

@dp.callback_query(F.data == "main_menu")
async def go_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    welcome = "🌟 *SKY STORE BD* 🌟\n\n👇 *Select a category below:*"
    await call.message.edit_text(welcome, reply_markup=main_menu_kb(call.from_user.id), parse_mode="Markdown")

# ── CATEGORIES ────────────────────────────────────────────────────────────────
@dp.callback_query(F.data.startswith("cat_"))
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
        title = f"{cat.get('icon', '📦')} *{cat['name']}\nSelect a subcategory:*"
        await call.message.edit_text(title, reply_markup=kb.as_markup(), parse_mode="Markdown")
        return
    prods = db.get_products(cat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} *{cat['name']}\nSelect a product:*"
        await call.message.edit_text(title, reply_markup=cat_products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ No products available.", show_alert=True)

@dp.callback_query(F.data.startswith("subcat_"))
async def view_subcategory(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subcat_id = call.data[7:]
    cat = db.get_category(subcat_id)
    if not cat:
        return
    prods = db.get_products(subcat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} *{cat['name']}\nSelect a product:*"
        await call.message.edit_text(title, reply_markup=cat_products_kb(subcat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ No products.", show_alert=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text("⚙️ *Admin Panel*\nSelect an option:", reply_markup=admin_kb(), parse_mode="Markdown")

# ── STATS ─────────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    user_count = len(users)
    pending = db.pending_count()
    sales = db.get_sales_summary()
    balance_total = sum(u['balance'] for u in users)
    lines = [
        "📊 *Dashboard*",
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

@dp.callback_query(F.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💰 *Add Balance*",
        "Enter the user's Telegram *User ID* (numeric) or *@username*:",
        "Examples: `123456789`, `@username`"
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
    if text.startswith("@") or (not text.isdigit() and not text.lstrip('-').isdigit()):
        clean_username = text.lstrip("@")
        user = db.get_user_by_username(clean_username)
        if user:
            uid = user["user_id"]
        else:
            return await msg.answer("❌ *User not found!*", reply_markup=admin_kb(), parse_mode="Markdown")
    else:
        try:
            uid = int(text)
            user = db.get_user(uid)
            if not user:
                return await msg.answer(f"❌ *User ID `{uid}` not found.*", reply_markup=admin_kb(), parse_mode="Markdown")
        except ValueError:
            return await msg.answer("❌ Invalid input.", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.update_data(addbal_uid=uid)
    lines = [
        f"💰 *Add Balance*",
        f"👤 User: {user['first_name']} (@{user['username'] or 'N/A'})",
        f"🆔 ID: `{uid}`",
        f"💳 Current Balance: {fmt(user['balance'])}",
        "",
        "Enter amount to add (BDT):"
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
        box_body = [
            f"💰 Balance Added!",
            f"Amount: {fmt(amt)}",
            f"New Balance: {fmt(new_bal)}",
            f"Date: {now_local().strftime('%d %b %Y %I:%M %p')}",
        ]
        user_msg = generate_box("💰 BALANCE UPDATED", box_body)
        try:
            await bot.send_message(uid, user_msg, parse_mode="Markdown")
        except:
            pass
        await msg.answer(
            f"✅ *Balance added successfully!*\n\nAmount: +{fmt(amt)}\nUser ID: `{uid}`\nNew Balance: {fmt(new_bal)}",
            reply_markup=admin_kb(), parse_mode="Markdown"
        )
    except ValueError:
        await msg.answer("❌ Invalid amount. Enter a number.")
    await state.clear()

# ── CATEGORY MANAGEMENT ───────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📂 *Category Management*", reply_markup=admin_cats_kb(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    auto_status = "✅ Auto-Deliver" if cat.get("auto_deliver") else "❌ Manual"
    lines = [
        f"📂 *{cat.get('icon', '')} {cat['name']}*",
        f"ID: `{cat_id}`",
        f"Subcategories: {len(subcats)}",
        f"Products: {len(prods)}",
        f"Delivery Mode: {auto_status}",
    ]
    if prods:
        lines.append("")
        for p in prods[:5]:
            lines.append(f"• {p['name']} — {fmt(p['price'])}")
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Edit Name/Desc", f"editcat_{cat_id}", ButtonStyle.PRIMARY))
    kb.row(btn("⚙️ Toggle Auto-Deliver", f"toggleauto_{cat_id}", ButtonStyle.PRIMARY))
    if cat_id not in ("youtube", "netflix", "crunchyroll", "vpn", "proxy"):
        kb.row(btn("🗑️ Delete Category", f"delcat_{cat_id}", ButtonStyle.DANGER))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("toggleauto_"))
async def toggle_auto_deliver(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[11:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    new_val = 0 if cat["auto_deliver"] else 1
    db.update_category(cat_id, auto_deliver=new_val)
    await admin_cat_view(call, None)
    await call.answer(f"Auto-Deliver {'enabled' if new_val else 'disabled'}.")

@dp.callback_query(F.data == "addcat_start")
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["➕ *Add New Category*", "Is this a main category or a subcategory?"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("📂 Main Category", "addcat_root", ButtonStyle.PRIMARY))
    for p in db.get_categories():
        kb.row(btn(f"↪️ Sub of: {p.get('icon', '')} {p['name']}", f"addcat_child_{p['id']}"))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_parent)

@dp.callback_query(F.data.startswith("addcat_root"), AdminFlow.addcat_parent)
@dp.callback_query(F.data.startswith("addcat_child_"), AdminFlow.addcat_parent)
async def addcat_parent_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = None if call.data == "addcat_root" else call.data[13:]
    await state.update_data(addcat_parent=parent_id)
    lines = ["➕ *Add Category*", "Enter category name (with emoji):", "Example: `🔵 NordVPN`"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_name)

@dp.message(AdminFlow.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    await msg.answer("Enter a short description (or type 'skip'):")
    await state.set_state(AdminFlow.addcat_desc)

@dp.message(AdminFlow.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    await state.update_data(addcat_desc=desc)
    await msg.answer("Enter an icon emoji (or type 'skip' for default 📦):")
    await state.set_state(AdminFlow.addcat_icon)

@dp.message(AdminFlow.addcat_icon)
async def addcat_icon(msg: Message, state: FSMContext):
    icon = msg.text.strip() if msg.text.strip().lower() != "skip" else "📦"
    await state.update_data(addcat_icon=icon)
    await msg.answer("⚡ *Auto-Delivery Mode?*\n\nType `yes` to enable auto-deliver, or `no` for manual.")
    await state.set_state(AdminFlow.addcat_autodeliver)

@dp.message(AdminFlow.addcat_autodeliver)
async def addcat_autodeliver(msg: Message, state: FSMContext):
    auto = 1 if msg.text.strip().lower() == "yes" else 0
    data = await state.get_data()
    parent_id = data.get("addcat_parent")
    name = data["addcat_name"]
    desc = data.get("addcat_desc", "")
    icon = data["addcat_icon"]
    auto_id = generate_id("cat_")
    db.add_category(auto_id, parent_id, name, desc, icon, auto_deliver=auto)
    await msg.answer(
        f"✅ *Category Created!*\n\nName: {name}\nID: `{auto_id}`\nAuto-Deliver: {'Yes' if auto else 'No'}",
        reply_markup=admin_kb(), parse_mode="Markdown"
    )
    await state.clear()

@dp.callback_query(F.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_target=cat_id)
    lines = ["✏️ *Edit Category*", "Enter new name (or type 'skip' to keep current):"]
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
    await msg.answer("Enter new description (or type 'skip'):")
    await state.set_state(AdminFlow.editcat_desc)

@dp.message(AdminFlow.editcat_desc)
async def editcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip()
    cat_id = (await state.get_data())["editcat_target"]
    if desc.lower() != "skip":
        db.update_category(cat_id, description=desc)
    await msg.answer("Toggle auto-deliver? Type `yes` to enable, `no` to disable, or `skip`:")
    await state.set_state(AdminFlow.editcat_autodeliver)

@dp.message(AdminFlow.editcat_autodeliver)
async def editcat_autodeliver(msg: Message, state: FSMContext):
    val = msg.text.strip().lower()
    if val == "yes":
        db.update_category((await state.get_data())["editcat_target"], auto_deliver=1)
    elif val == "no":
        db.update_category((await state.get_data())["editcat_target"], auto_deliver=0)
    await msg.answer("✅ *Category Updated!*", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    cid = call.data[7:]
    success = db.delete_category(cid)
    if not success:
        await call.answer("❌ Cannot delete main categories.", show_alert=True)
        return
    await call.answer("🗑️ Deleting...")
    await call.message.edit_text(f"🗑️ Category `{cid}` deleted.", reply_markup=admin_cats_kb(), parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIXED: HIERARCHICAL PRODUCT EDITING
#  Uses unique callback_data prefixes to avoid handler collisions
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_editprod")
async def admin_editprod_main(call: CallbackQuery, state: FSMContext):
    """Step 1: Select Main Category"""
    await call.answer()
    await state.set_state(AdminFlow.editprod_maincat)
    await call.message.edit_text(
        "📦 *Edit Product — Step 1/3*\n\nSelect a *Main Category*:",
        reply_markup=main_category_kb("epm_"),  # epm_ = Edit Product Main
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("editprod_main_"))
async def editprod_main_selected(call: CallbackQuery, state: FSMContext):
    await call.answer()
    
    # ব্যাক বাটনের জন্য লজিক
    if call.data == "editprod_main_back":
        await admin_editprod_main(call, state)
        return

    cat_id = call.data.replace("editprod_main_", "")
    cat = db.get_category(cat_id)
    if not cat:
        await call.answer("Category not found!")
        return
    
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    
    await state.update_data(editprod_maincat=cat_id)
    
    kb = InlineKeyboardBuilder()

    if subcats:
        for sc in subcats:
            emoji = sc.get('icon', '📦')
            kb.button(text=f"{emoji} {sc['name']}", callback_data=f"editprod_sub_{sc['id']}")
    elif prods:
        for p in prods:
            kb.button(text=f"✏️ {p['name']}", callback_data=f"editprod_sel_{p['id']}")
    
    kb.adjust(1)
    kb.row(btn("➕ Add New Product Here", f"addprod_start_{cat_id}", ButtonStyle.SUCCESS))
    kb.row(btn("🔙 Back to Main Menu", "admin_editprod", ButtonStyle.DANGER))
    
    await call.message.edit_text(
        f"📦 Editing products in: *{cat['name']}*",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminFlow.editprod_select)

        kb = InlineKeyboardBuilder()
        for sc in subcats:
            emoji = sc.get('icon', '📦')
            kb.button(
                text=f"{emoji} {sc['name']}",
                callback_data=f"eps_{sc['id']}",  # eps_ = Edit Product Sub
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("➕ Add Product in this Category", f"apd_{cat_id}", ButtonStyle.SUCCESS))  # apd_ = Add Product Direct
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nSelect a subcategory:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    elif prods:
        # Show products for editing
        await state.set_state(AdminFlow.editprod_select)
        kb = InlineKeyboardBuilder()
        for p in prods:
            kb.button(
                text=f"✏️ {p['name']} — {fmt(p['price'])}",
                callback_data=f"epsel_{p['id']}",  # epsel_ = Edit Product Select
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("➕ Add New Product", f"apd_{cat_id}", ButtonStyle.SUCCESS))
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nSelect a product to edit:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await state.set_state(AdminFlow.editprod_select)
        kb = InlineKeyboardBuilder()
        kb.row(btn("➕ Add First Product", f"apd_{cat_id}", ButtonStyle.SUCCESS))
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nNo products yet. Add one:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

# Back button for edit product flow — registered BEFORE subcategory handler to take priority
@dp.callback_query(F.data == "ep_back")
async def editprod_back_to_main(call: CallbackQuery, state: FSMContext):
    """Back to main category selection"""
    await state.set_state(AdminFlow.editprod_maincat)
    await call.message.edit_text(
        "📦 *Edit Product — Step 1/3*\n\nSelect a *Main Category*:",
        reply_markup=main_category_kb("epm_"),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("eps_"), AdminFlow.editprod_subcat)
async def editprod_sub_selected(call: CallbackQuery, state: FSMContext):
    """Step 2b: Subcategory selected, show products"""
    await call.answer()
    subcat_id = call.data[4:]  # Remove "eps_" prefix
    
    subcat = db.get_category(subcat_id)
    if not subcat:
        return
    
    prods = db.get_products(subcat_id)
    await state.update_data(editprod_subcat=subcat_id)
    await state.set_state(AdminFlow.editprod_select)
    
    if prods:
        kb = InlineKeyboardBuilder()
        for p in prods:
            kb.button(
                text=f"✏️ {p['name']} — {fmt(p['price'])}",
                callback_data=f"epsel_{p['id']}",
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("➕ Add New Product Here", f"apd_{subcat_id}", ButtonStyle.SUCCESS))
        maincat_id = (await state.get_data()).get("editprod_maincat", "")
        kb.row(btn("🔙 Back to Subcategories", f"epm_{maincat_id}", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{subcat.get('icon', '')} {subcat['name']}*\nSelect a product to edit:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        kb = InlineKeyboardBuilder()
        kb.row(btn("➕ Add First Product", f"apd_{subcat_id}", ButtonStyle.SUCCESS))
        maincat_id = (await state.get_data()).get("editprod_maincat", "")
        kb.row(btn("🔙 Back", f"epm_{maincat_id}", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{subcat.get('icon', '')} {subcat['name']}*\nNo products yet. Add one:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

# Intermediate handler to go back from subcategory to subcategory listing
# This is distinct from ep_back (which goes to main category selection)
@dp.callback_query(F.data.startswith("epm_"))
async def editprod_show_maincat_products(call: CallbackQuery, state: FSMContext):
    """Show products of a main category (going back from subcategory)"""
    await call.answer()
    cat_id = call.data[4:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    
    await state.update_data(editprod_maincat=cat_id)
    
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    
    if subcats:
        await state.set_state(AdminFlow.editprod_subcat)
        kb = InlineKeyboardBuilder()
        for sc in subcats:
            emoji = sc.get('icon', '📦')
            kb.button(
                text=f"{emoji} {sc['name']}",
                callback_data=f"eps_{sc['id']}",
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nSelect a subcategory:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    elif prods:
        await state.set_state(AdminFlow.editprod_select)
        kb = InlineKeyboardBuilder()
        for p in prods:
            kb.button(
                text=f"✏️ {p['name']} — {fmt(p['price'])}",
                callback_data=f"epsel_{p['id']}",
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nSelect a product:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await state.set_state(AdminFlow.editprod_select)
        kb = InlineKeyboardBuilder()
        kb.row(btn("🔙 Back to Main Categories", "ep_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"📦 *{cat.get('icon', '')} {cat['name']}*\nNo products.",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )

@dp.callback_query(F.data.startswith("epsel_"), AdminFlow.editprod_select)
async def editprod_show_details(call: CallbackQuery, state: FSMContext):
    """Show product details and editing options"""
    await call.answer()
    pid = call.data[6:]  # Remove "epsel_" prefix
    prod = db.get_product(pid)
    if not prod:
        await call.answer("Product not found!", show_alert=True)
        return
    
    await state.update_data(editprod_target=pid)
    await state.set_state(AdminFlow.editprod_field)
    
    lines = [
        f"📦 *Current Product Details*",
        "",
        f"📛 Name: `{prod['name']}`",
        f"💰 Price: {fmt(prod['price'])}",
        f"⏰ Expiry: {prod.get('expiry_days', 30)} days",
        f"📦 Stock Type: {prod.get('stock_type', 'N/A')}",
        f"🆔 ID: `{pid}`",
        "",
        "✏️ *What do you want to edit?*",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Change Name", "epf_name", ButtonStyle.PRIMARY))
    kb.row(btn("💰 Change Price", "epf_price", ButtonStyle.PRIMARY))
    kb.row(btn("⏰ Change Expiry Days", "epf_expiry", ButtonStyle.PRIMARY))
    kb.row(btn("🗑️ Delete This Product", f"delprod_{pid}", ButtonStyle.DANGER))
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# Product field editing — uses button prefix "epf_" (Edit Product Field)
@dp.callback_query(F.data.startswith("epf_"), AdminFlow.editprod_field)
async def editprod_field_prompt(call: CallbackQuery, state: FSMContext):
    """Ask for new value for selected field"""
    await call.answer()
    field = call.data[4:]  # Remove "epf_" prefix
    field_names = {"name": "Name", "price": "Price", "expiry": "Expiry Days"}
    await state.update_data(editprod_field=field)
    
    lines = [f"✏️ Enter new *{field_names.get(field, field)}*:"]
    if field == "price":
        lines.append("Example: `350`")
    elif field == "expiry":
        lines.append("Example: `60` (days)")
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_value)

@dp.message(AdminFlow.editprod_value)
async def editprod_value_received(msg: Message, state: FSMContext):
    """Save the new value"""
    data = await state.get_data()
    pid = data["editprod_target"]
    field = data["editprod_field"]
    value = msg.text.strip()
    
    try:
        if field == "name":
            if len(value) < 2:
                return await msg.answer("❌ Name must be at least 2 characters.")
            db.update_product(pid, name=value)
            await msg.answer(f"✅ Name updated to: `{value}`", reply_markup=admin_kb(), parse_mode="Markdown")
        elif field == "price":
            price = float(value)
            if price < 0:
                return await msg.answer("❌ Price cannot be negative.")
            db.update_product(pid, price=price)
            await msg.answer(f"✅ Price updated to: {fmt(price)}", reply_markup=admin_kb(), parse_mode="Markdown")
        elif field == "expiry":
            expiry = int(value)
            if expiry < 1:
                return await msg.answer("❌ Expiry must be at least 1 day.")
            db.update_product(pid, expiry_days=expiry)
            await msg.answer(f"✅ Expiry updated to: {expiry} days", reply_markup=admin_kb(), parse_mode="Markdown")
        else:
            await msg.answer("❌ Unknown field.", reply_markup=admin_kb(), parse_mode="Markdown")
    except ValueError:
        await msg.answer("❌ Invalid value. Please enter a valid number." if field != "name" else "❌ Invalid name.")
    await state.clear()

@dp.callback_query(F.data.startswith("delprod_"))
async def delprod_now(call: CallbackQuery):
    """Delete a product"""
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]  # Remove "delprod_" prefix
    db.delete_product(pid)
    await call.message.edit_text(f"🗑️ Product `{pid}` deleted.", reply_markup=admin_kb(), parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
#  HIERARCHICAL ADD PRODUCT
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data.startswith("apd_"))
async def addprod_begin(call: CallbackQuery, state: FSMContext):
    """Start adding product (called from edit product flow with category context)"""
    await call.answer()
    cat_id = call.data[4:]  # Remove "apd_" prefix
    await state.update_data(addprod_cat=cat_id)
    await state.set_state(AdminFlow.addprod_name)
    
    cat = db.get_category(cat_id)
    cat_name = cat['name'] if cat else 'Unknown'
    lines = [
        f"➕ *Add Product in: {cat_name}*",
        "",
        "Enter product name:",
        "Example: `🔵 NordVPN 6 Months`"
    ]
    await call.message.edit_text("\n".join(lines), parse_mode="Markdown")

@dp.message(AdminFlow.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    await msg.answer("Enter price (number only):\nExample: `650`")
    await state.set_state(AdminFlow.addprod_price)

@dp.message(AdminFlow.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        await msg.answer("Enter expiry in days (e.g., `30` for 1 month):")
        await state.set_state(AdminFlow.addprod_expiry)
    except ValueError:
        await msg.answer("❌ Enter a valid number.")

@dp.message(AdminFlow.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        data = await state.get_data()
        cat_id = data["addprod_cat"]
        cat = db.get_category(cat_id)
        is_auto = cat.get("auto_deliver", 0) == 1 if cat else False

        if is_auto:
            await state.update_data(addprod_expiry=expiry)
            await msg.answer("Stock type:\n• `email_pass` — Email + Password\n• `key_only` — Just a key/code\n• `ip_port` — IP:Port:Username:Password")
            await state.set_state(AdminFlow.addprod_stocktype)
        else:
            auto_id = generate_id("prod_")
            db.add_product(auto_id, cat_id, data["addprod_name"], data["addprod_price"], 0, "manual", expiry)
            await msg.answer(
                f"✅ *Product Added!*\n\nName: {data['addprod_name']}\nID: `{auto_id}`\nPrice: {fmt(data['addprod_price'])}\nExpiry: {expiry} days\nType: Manual",
                reply_markup=admin_kb(), parse_mode="Markdown"
            )
            await state.clear()
    except ValueError:
        await msg.answer("❌ Enter a valid number of days.")

@dp.message(AdminFlow.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ["email_pass", "key_only", "ip_port"]:
        return await msg.answer("❌ Please type `email_pass`, `key_only`, or `ip_port`.")
    data = await state.get_data()
    auto_id = generate_id("prod_")
    db.add_product(auto_id, data["addprod_cat"], data["addprod_name"], data["addprod_price"], 0, stype, data["addprod_expiry"])
    await msg.answer(
        f"✅ *Product Added!*\n\nName: {data['addprod_name']}\nID: `{auto_id}`\nPrice: {fmt(data['addprod_price'])}\nExpiry: {data['addprod_expiry']} days\nStock Type: {stype}",
        reply_markup=admin_kb(), parse_mode="Markdown"
    )
    await state.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  HIERARCHICAL STOCK MANAGEMENT (fixed with unique prefixes)
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(F.data == "stock_status")
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

@dp.callback_query(F.data == "stock_add")
async def stock_add_select_main(call: CallbackQuery, state: FSMContext):
    """Step 1: Select Main Category for stock addition"""
    await call.answer()
    await state.set_state(AdminFlow.stock_maincat)
    await call.message.edit_text(
        "🔑 *Add Stock — Step 1/3*\n\nFirst, select a *Main Category*:",
        reply_markup=main_category_kb("stkm_"),  # stkm_ = Stock Main
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("stkm_"), AdminFlow.stock_maincat)
async def stock_add_select_sub(call: CallbackQuery, state: FSMContext):
    """Step 2: Select Subcategory or show products"""
    await call.answer()
    cat_id = call.data[5:]  # Remove "stkm_" prefix
    
    cat = db.get_category(cat_id)
    if not cat:
        return
    
    await state.update_data(stock_maincat=cat_id)
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    
    if subcats:
        await state.set_state(AdminFlow.stock_subcat)
        kb = InlineKeyboardBuilder()
        for sc in subcats:
            emoji = sc.get('icon', '📦')
            kb.button(text=f"{emoji} {sc['name']}", callback_data=f"stks_{sc['id']}", style=ButtonStyle.PRIMARY)  # stks_ = Stock Sub
        kb.adjust(1)
        kb.row(btn("🔙 Back to Main Categories", "stk_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"🔑 *{cat.get('icon', '')} {cat['name']}*\nSelect a subcategory:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    elif prods:
        await state.set_state(AdminFlow.stock_product)
        kb = InlineKeyboardBuilder()
        for p in prods:
            kb.button(
                text=f"📦 {p['name']} [{p.get('stock_type', 'N/A')}]",
                callback_data=f"stkp_{p['id']}",  # stkp_ = Stock Product
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        kb.row(btn("🔙 Back to Main Categories", "stk_back", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"🔑 *{cat.get('icon', '')} {cat['name']}*\nSelect a product to add stock to:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await call.answer("❌ No products in this category.", show_alert=True)
        await stock_add_select_main(call, state)

@dp.callback_query(F.data == "stk_back")
async def stock_back_to_main(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFlow.stock_maincat)
    await call.message.edit_text(
        "🔑 *Add Stock — Step 1/3*\n\nSelect a *Main Category*:",
        reply_markup=main_category_kb("stkm_"),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("stks_"), AdminFlow.stock_subcat)
async def stock_subcategory_selected(call: CallbackQuery, state: FSMContext):
    """Step 3: Show products in selected subcategory"""
    await call.answer()
    subcat_id = call.data[5:]  # Remove "stks_" prefix
    cat = db.get_category(subcat_id)
    if not cat:
        return
    
    await state.update_data(stock_subcat=subcat_id)
    await state.set_state(AdminFlow.stock_product)
    
    prods = db.get_products(subcat_id)
    if prods:
        kb = InlineKeyboardBuilder()
        for p in prods:
            kb.button(
                text=f"📦 {p['name']} [{p.get('stock_type', 'N/A')}]",
                callback_data=f"stkp_{p['id']}",
                style=ButtonStyle.PRIMARY
            )
        kb.adjust(1)
        maincat_id = (await state.get_data()).get("stock_maincat", "")
        kb.row(btn("🔙 Back", f"stkm_{maincat_id}", ButtonStyle.PRIMARY))
        await call.message.edit_text(
            f"🔑 *{cat.get('icon', '')} {cat['name']}*\nSelect a product to add stock to:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await call.answer("❌ No products in this subcategory.", show_alert=True)
        await stock_add_select_sub(call, state)

@dp.callback_query(F.data.startswith("stkp_"), AdminFlow.stock_product)
async def stock_product_selected(call: CallbackQuery, state: FSMContext):
    """Product selected for stock addition - choose stock type"""
    await call.answer()
    pid = call.data[5:]  # Remove "stkp_" prefix
    prod = db.get_product(pid)
    if not prod:
        return
    
    await state.update_data(stock_target=pid)
    await state.set_state(AdminFlow.stock_type_choice)
    
    lines = [
        f"🔑 *Add Stock to:* {prod['name']}",
        f"Product ID: `{pid}`",
        f"Default Expiry: {prod.get('expiry_days', 30)} days",
        "",
        "📌 Select the type of data you want to add:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(
        btn("🔑 Key Only", f"skty_keyonly_{pid}", ButtonStyle.PRIMARY),
        btn("📧 Email & Password", f"skty_emailpass_{pid}", ButtonStyle.PRIMARY),
        btn("🌐 IP:Port:User:Pass", f"skty_ip_port_{pid}", ButtonStyle.PRIMARY)
    )
    kb.row(btn("🔙 Back", "stock_add"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("skty_"), AdminFlow.stock_type_choice)
async def stock_type_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    # Expected format: skty_keyonly_{pid} or skty_emailpass_{pid} or skty_ip_port_{pid}
    # Extract: we need to separate the type from the pid
    prefix_len = 5  # "skty_"
    rest = call.data[prefix_len:]  # e.g., "keyonly_vpn_nord_7d"
    # The first part before the first _ is the type, rest is the pid
    # But pid can contain underscores too! So we need to find the right split.
    # Types: keyonly, emailpass, ip_port
    if rest.startswith("keyonly_"):
        chosen_type = "key_only"
        pid = rest[8:]
    elif rest.startswith("emailpass_"):
        chosen_type = "email_pass"
        pid = rest[10:]
    elif rest.startswith("ip_port_"):
        chosen_type = "ip_port"
        pid = rest[8:]
    else:
        return
    
    prod = db.get_product(pid)
    if not prod:
        return
    
    await state.update_data(stock_type=chosen_type)

    lines = [
        f"🔑 *Add Stock to:* {prod['name']}",
        f"Stock Type: *{chosen_type}*",
        f"Expiry: {prod.get('expiry_days', 30)} days",
        "",
        "📤 Now send your data (one per line) or upload a `.txt` file.",
    ]
    if chosen_type == "key_only":
        lines.append("🔑 Send Key(s) — one per line:")
        lines.append("Example: `ABC123XYZ`")
    elif chosen_type == "email_pass":
        lines.append("📧 Send email:password pairs — one per line:")
        lines.append("Example: `email@example.com:password123`")
    else:
        lines.append("🌐 Send IP:Port:Username:Password — one per line:")
        lines.append("Example: `192.168.1.1:8080:user:pass`")
    
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Change Type", f"stkp_{pid}", ButtonStyle.PRIMARY))
    kb.row(btn("🔙 Back to Menu", "admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_input)


# ── STOCK HANDLERS (Text & File) ──────────────────────────────────────────────
@dp.message(AdminFlow.stock_input, F.text)
async def stock_input_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    prod = db.get_product(pid)
    expiry = prod["expiry_days"] if prod else 30
    lines_input = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    for line in lines_input:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line, expiry_days=expiry)
            added += 1
        elif stype == "email_pass":
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip(), expiry_days=expiry)
                added += 1
        else:
            db.add_stock(pid, "ip_port", key_data=line, expiry_days=expiry)
            added += 1
    await msg.answer(f"✅ {added} stock items added (expiry: {expiry} days)!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.message(AdminFlow.stock_input, F.document)
async def stock_file_upload(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    prod = db.get_product(pid)
    expiry = prod["expiry_days"] if prod else 30
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
            db.add_stock(pid, "key_only", key_data=line, expiry_days=expiry)
            added += 1
        elif stype == "email_pass":
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip(), expiry_days=expiry)
                added += 1
        else:
            db.add_stock(pid, "ip_port", key_data=line, expiry_days=expiry)
            added += 1
    await msg.answer(f"✅ {added} stock items added from file (expiry: {expiry} days)!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(F.data == "stock_del")
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

@dp.callback_query(F.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del_list(call)

# ── BACKUP DATABASE ───────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_backup")
async def admin_backup(call: CallbackQuery):
    await call.answer("💾 Creating backup...")
    try:
        backup_path = db.backup()
        file_size = os.path.getsize(backup_path)
        doc = FSInputFile(backup_path)
        await bot.send_document(call.from_user.id, doc, caption=f"📦 Backup {now_local().strftime('%d %B %Y %I:%M %p')}")
        await call.message.edit_text("✅ *Backup sent!*", reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await call.message.edit_text(f"❌ Backup failed: {e}", reply_markup=admin_kb(), parse_mode="Markdown")

# ── RESTORE DATABASE ─────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_restore")
async def admin_restore_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "🔄 *Restore Database*",
        "⚠️ *WARNING:* This will OVERWRITE the current database!",
        "Send the backup `.db` file to restore."
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Cancel", "admin_menu", ButtonStyle.DANGER))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.restore_file)

@dp.message(AdminFlow.restore_file, F.document)
async def admin_restore_file(msg: Message, state: FSMContext):
    doc = msg.document
    if not doc.file_name.endswith(".db"):
        return await msg.answer("❌ Please upload a `.db` file.")
    file = await bot.get_file(doc.file_id)
    restore_path = f"/tmp/restore_{doc.file_id}.db"
    await bot.download_file(file.file_path, destination=restore_path)
    try:
        success = db.restore(restore_path)
        if success:
            await msg.answer("✅ *Database restored successfully!*", reply_markup=admin_kb(), parse_mode="Markdown")
        else:
            await msg.answer("❌ Restore failed.", reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}", reply_markup=admin_kb(), parse_mode="Markdown")
    finally:
        if os.path.exists(restore_path):
            os.remove(restore_path)
    await state.clear()

# ── BROADCAST ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📨 *Broadcast Message*", "Send the text or video with caption to broadcast:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.broadcast_msg)

@dp.message(AdminFlow.broadcast_msg, F.text)
async def broadcast_text(msg: Message, state: FSMContext):
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_message(u["user_id"], msg.text)
                sent += 1
            except:
                pass
    await msg.answer(f"✅ Broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

@dp.message(AdminFlow.broadcast_msg, F.video)
async def broadcast_video(msg: Message, state: FSMContext):
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_video(u["user_id"], msg.video.file_id, caption=msg.caption or "")
                sent += 1
            except:
                pass
    await msg.answer(f"✅ Video broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

# ── BAN / UNBAN ──────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("⛔ *Ban User*\nEnter User ID:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_menu")).as_markup(), parse_mode="Markdown")
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

@dp.callback_query(F.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("✅ *Unban User*\nEnter User ID:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_menu")).as_markup(), parse_mode="Markdown")
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
@dp.callback_query(F.data.startswith("approve_"))
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
    ]
    user_text = generate_box("✅ ORDER CONFIRMED", box_body)
    try:
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    except:
        pass
    await call.message.edit_text(f"✅ Order #{oid} Approved & Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer("❌ Rejecting...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    db.update_order(oid, "cancelled")
    try:
        await bot.send_message(order["user_id"], f"❌ Order #{oid} has been cancelled.\nContact @{SUPPORT_USERNAME}")
    except:
        pass
    await call.message.edit_text(f"❌ Order #{oid} Rejected.", reply_markup=admin_kb(), parse_mode="Markdown")

# ── DELIVER (Manual) ──────────────────────────────────────────────────────────
@dp.callback_query(F.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📦 *Manual Delivery*", "Enter Order ID:"]
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
            "• For IP:Port:User:Pass: `192.168.1.1:8080:user:pass`",
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
    if re.match(r'\d+\.\d+\.\d+\.\d+:\d+:', delivery_text):
        delivery_data = {"ip_port": delivery_text}
    elif ":" in delivery_text:
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
    elif "ip_port" in delivery_data:
        cred_part = f"🌐 IP:Port:User:Pass: `{delivery_data['ip_port']}`"
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
    ]
    user_text = generate_box("✅ MANUAL DELIVERY", box_body)
    try:
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    except:
        pass
    await msg.answer(f"✅ Order #{oid} Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()


# ═══════════════════════════════════════════════════════════════════════════════
#  ORDER FLOW HANDLERS (user-side — kept separate to avoid admin handler collisions)
# ═══════════════════════════════════════════════════════════════════════════════

@dp.callback_query(F.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    cat_id = prod["category_id"]
    cat = db.get_category(cat_id)
    await state.update_data(order_pid=pid, order_prod=prod)

    is_auto = cat.get("auto_deliver", 0) == 1 if cat else False

    if is_auto:
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

@dp.callback_query(F.data == "vpn_auto")
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

@dp.callback_query(F.data == "go_payment")
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
@dp.callback_query(F.data.startswith("pay_"))
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
@dp.callback_query(F.data == "my_wallet")
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

@dp.callback_query(F.data == "apply_promo")
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
        return await msg.answer("❌ Invalid or expired promo code.")
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
    ]
    await msg.answer("\n".join(lines), reply_markup=main_menu_kb(uid), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "submit_deposit")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💳 *Submit Deposit*",
        "",
        "📌 Send the *amount*, *sender number*, and *TrxID* in one message like this:",
        "`500 01742958563 TRX1234567`",
        "",
        "Format: `<amount> <sender_number> <TrxID>`",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "my_wallet"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositFlow.waiting_trxid)

@dp.message(DepositFlow.waiting_trxid)
async def deposit_trx_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    uid = msg.from_user.id
    parts = text.split()
    amount_str = "?"
    sender_number = "N/A"
    trx_id = "N/A"
    if len(parts) >= 3:
        amount_str = parts[0]
        sender_number = parts[1]
        trx_id = " ".join(parts[2:])
    elif len(parts) == 2:
        amount_str = parts[0]
        trx_id = parts[1]
    else:
        match = re.search(r'(\d+[\.]?\d*)', text)
        amount_str = match.group(1) if match else "?"
        trx_id = text
    if sender_number == "N/A":
        phone = re.search(r'(01[3-9]\d{8})', text)
        if phone:
            sender_number = phone.group(1)
    db.add_transaction(uid, float(amount_str) if amount_str != "?" else 0, "deposit_pending", "Manual Deposit", trx_id,
                       f"Sender: {sender_number} | Amount: {amount_str}")
    admin_text = [
        "💰 *NEW DEPOSIT REQUEST*",
        f"👤 User ID: `{uid}`",
        f"📛 Name: {msg.from_user.first_name}",
        f"👤 Username: @{msg.from_user.username or 'N/A'}",
        f"📝 Raw: `{text}`",
        f"💵 Amount: {amount_str}",
        f"📱 Sender: {sender_number}",
        f"🔢 TrxID: {trx_id}",
    ]
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_text), parse_mode="Markdown")
        except:
            pass
    await msg.answer(
        f"✅ *Deposit request submitted!*\n\n"
        f"📝 Amount: `{amount_str}`\n"
        f"📱 Sender: `{sender_number}`\n"
        f"🔢 TrxID: `{trx_id}`\n\n"
        f"⏳ Admin will verify and add balance shortly.\n"
        f"📞 Contact: @{SUPPORT_USERNAME}",
        reply_markup=main_menu_kb(uid), parse_mode="Markdown"
    )
    await state.clear()

# ── MY ORDERS ─────────────────────────────────────────────────────────────────
@dp.callback_query(F.data == "my_orders")
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
                if dd.get("ip_port"):
                    lines.append(f"   🌐 IP:Port:User:Pass: `{dd['ip_port']}`")
                if dd.get("expires_days"):
                    lines.append(f"   ⏰ Validity: {dd['expires_days']} days")
            lines.append("")
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("🚀 SKY STORE BD Bot v5.1 (Fixed Hierarchy) started...")
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
