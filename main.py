#!/usr/bin/env python3
"""
SKY STORE BD — Premium Digital Store Telegram Bot
Version 5.0 — Hierarchical editing, stock, and UI improvements
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
TIMEZONE_OFFSET = 6
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
            if proxy == "Owl":
                pid = f"proxy_{proxy.lower()}_30d"
                conn.execute("INSERT INTO products(id,category_id,name,price,stock_type,expiry_days) VALUES(?,?,?,?,?,?)",
                             (pid, subcat_id, "🦉 Owl Proxy 30 Days", 10, "ip_port", 30))
            else:
                pid = f"proxy_{proxy.lower()}_30d"
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
    addcat_parent = State()
    addcat_name = State()
    addcat_desc = State()
    addcat_icon = State()
    addcat_autodeliver = State()
    editcat_target = State()
    editcat_name = State()
    editcat_desc = State()
    editcat_autodeliver = State()
    addprod_name = State()
    addprod_price = State()
    addprod_expiry = State()
    addprod_stocktype = State()
    editprod_field = State()
    editprod_value = State()
    stock_target = State()
    stock_input = State()
    stock_type_choice = State()
    stock_cat_select = State()  # new: for hierarchical stock category selection
    promo_code = State()
    promo_amount = State()
    promo_discount = State()
    promo_uses = State()
    promo_expiry = State()
    restore_file = State()
    deliver_oid = State()
    deliver_file = State()


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user:
            u = db.get_user(user.id)
            if u and u.get("is_banned") == 1:
                if isinstance(event, Message):
                    await event.answer("❌ You are banned from using this bot.")
                elif isinstance(event, CallbackQuery):
                    await event.answer("❌ You are banned.", show_alert=True)
                return
        return await handler(event, data)


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
        kb.button(text=f"{emoji} {cat['name']}", callback_data=f"cat_{cat['id']}")
    kb.adjust(2)
    kb.row(btn("📜 My Orders", "my_orders"), btn("💳 Wallet / Deposit", "my_wallet"))
    if uid in ADMIN_IDS:
        kb.row(btn("⚙️ Admin Panel", "admin_menu"))
    return kb.as_markup()

def cat_products_kb(cat_id):
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"🛒 {p['name']} — {fmt(p['price'])}", callback_data=f"order_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Main Menu", "main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("💰 Wallet Balance", "pay_wallet"))
    kb.row(btn("💖 bKash", "pay_bkash"), btn("🟠 Nagad", "pay_nagad"))
    kb.row(btn("🚀 Rocket", "pay_rocket"))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Stats", "admin_dash"), btn("💰 Add Balance", "admin_addbal"))
    kb.row(btn("📂 Categories", "admin_cats"), btn("📦 Edit Product", "admin_editprod"))
    kb.row(btn("🔑 Stock", "admin_stock"), btn("📨 Broadcast", "admin_broadcast"))
    kb.row(btn("💾 Backup DB", "admin_backup"), btn("🔄 Restore DB", "admin_restore"))
    kb.row(btn("📦 Manual Deliver", "admin_deliver"))
    kb.row(btn("⛔ Ban", "admin_ban"), btn("✅ Unban", "admin_unban"))
    kb.row(btn("🏠 Main Menu", "main_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_all_categories():
        kb.button(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"admincat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("➕ Add Category", "addcat_start"))
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Stock Status", "stock_status"), btn("➕ Add Stock", "stock_add"))
    kb.row(btn("🗑️ Delete Stock", "stock_del"))
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    return kb.as_markup()

def delivery_kb(oid):
    kb = InlineKeyboardBuilder()
    kb.row(btn("✅ Approve", f"approve_{oid}"), btn("❌ Reject", f"reject_{oid}"))
    return kb.as_markup()


async def process_payment(call_or_msg, state, pmethod, trx):
    data = await state.get_data()
    prod = data.get("order_prod")
    if not prod:
        return
    uid = call_or_msg.from_user.id if hasattr(call_or_msg, 'from_user') else call_or_msg.from_user.id
    price = prod["price"]
    cat = db.get_category(prod["category_id"])
    is_auto = cat.get("auto_deliver", 0) == 1 if cat else False

    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price):
            bal = db.get_balance(uid)
            kb = InlineKeyboardBuilder()
            kb.row(btn("💳 Add Balance", "my_wallet"))
            kb.row(btn("🔙 Main Menu", "main_menu"))
            txt = f"❌ *Insufficient Balance!*\nRequired: {fmt(price)}\nYour Balance: {fmt(bal)}"
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")
            else:
                await call_or_msg.answer(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")
            return

    oid = db.add_order(uid, prod["id"], prod["name"], prod["category_id"], price, data.get("user_input", ""), pmethod, trx)

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
            delivery_data["server"] = data.get("user_input", "Auto")
            delivery_data["expires_days"] = stock_expiry
            now = now_local()
            expiry_date = now + timedelta(days=stock_expiry)
            db.update_order(oid, "delivered", delivery_data)
            box = generate_box("✅ AUTO-DELIVERED", [
                f"📦 {prod['name']}",
                f"🆔 Order: #{oid}",
                "",
                cred_part,
                f"🌍 Server: {data.get('user_input', 'Auto')}",
                "",
                f"✅ Activated: {now.strftime('%d %b %Y %I:%M %p')}",
                f"⏰ Validity: {stock_expiry} days",
                f"📅 Expires: {expiry_date.strftime('%d %B %Y')}",
                f"✅ Status: Active",
            ])
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text(box, parse_mode="Markdown")
            else:
                await call_or_msg.answer(box, parse_mode="Markdown")
            await bot.send_message(uid, "✅ Your order has been delivered successfully!\nSKY STORE BD", reply_markup=main_menu_kb(uid))
        else:
            db.update_order(oid, "pending")
            txt = f"⏳ *No stock available!*\n🆔 Order ID: #{oid}\nWaiting for admin to add stock."
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text(txt, reply_markup=main_menu_kb(uid), parse_mode="Markdown")
            else:
                await call_or_msg.answer(txt, reply_markup=main_menu_kb(uid), parse_mode="Markdown")
            for aid in ADMIN_IDS:
                await bot.send_message(aid, f"📦 *STOCK OUT* — Order #{oid}\nProduct: {prod['name']}", parse_mode="Markdown")
        await state.clear()
        return

    # Manual
    db.update_order(oid, "pending")
    txt = f"✅ *Order received!*\n🆔 Order ID: #{oid}\n⏳ Wait for admin confirmation."
    if isinstance(call_or_msg, CallbackQuery):
        await call_or_msg.message.edit_text(txt, parse_mode="Markdown")
    else:
        await call_or_msg.answer(txt, parse_mode="Markdown")
    for aid in ADMIN_IDS:
        await bot.send_message(aid, f"📦 *NEW ORDER* #{oid}\nProduct: {prod['name']}\nPrice: {fmt(price)}", reply_markup=delivery_kb(oid), parse_mode="Markdown")
    await state.clear()


# ═══ USER HANDLERS ═══
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    db.create_user(msg.from_user.id, msg.from_user.first_name, msg.from_user.username)
    await msg.answer("🌟 *SKY STORE BD*\nSelect a category:", reply_markup=main_menu_kb(msg.from_user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "main_menu")
async def main_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text("🌟 *SKY STORE BD*\nSelect a category:", reply_markup=main_menu_kb(call.from_user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[4:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    subcats = db.get_categories(parent_id=cat_id)
    if subcats:
        kb = InlineKeyboardBuilder()
        for sc in subcats:
            kb.button(text=f"{sc.get('icon', '📦')} {sc['name']}", callback_data=f"subcat_{sc['id']}")
        kb.adjust(1)
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await call.message.edit_text(f"{cat.get('icon', '')} *{cat['name']}*\nSelect a subcategory:", reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        prods = db.get_products(cat_id)
        if prods:
            await call.message.edit_text(f"{cat.get('icon', '')} *{cat['name']}*", reply_markup=cat_products_kb(cat_id), parse_mode="Markdown")
        else:
            await call.answer("No products.", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("subcat_"))
async def subcat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    subcat_id = call.data[7:]
    cat = db.get_category(subcat_id)
    if not cat:
        return
    await call.message.edit_text(f"{cat.get('icon', '')} *{cat['name']}*", reply_markup=cat_products_kb(subcat_id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    await state.update_data(order_pid=pid, order_prod=prod)
    cat = db.get_category(prod["category_id"])
    is_auto = cat.get("auto_deliver", 0) == 1 if cat else False
    if is_auto:
        kb = InlineKeyboardBuilder()
        kb.row(btn("⚡ Auto Location", "vpn_auto"))
        kb.row(btn("🔙 Main Menu", "main_menu"))
        await call.message.edit_text(f"📦 *{prod['name']}*\n💰 {fmt(prod['price'])}\n⏰ {prod['expiry_days']} days\n🌍 Enter server or tap Auto:", reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)
    elif cat.get("id") == "crunchyroll":
        await call.message.edit_text(f"📦 *{prod['name']}*\n💰 {fmt(prod['price'])}\n📧 Enter your Gmail address:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Main Menu", "main_menu")).as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)
    else:
        await call.message.edit_text(f"📦 *{prod['name']}*\n💰 {fmt(prod['price'])}\n📧 Enter your Gmail address:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Main Menu", "main_menu")).as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(user_input="Auto")
    await call.message.edit_text(f"📦 *{ (await state.get_data())['order_prod']['name'] }*\n🌍 Auto\n💰 {fmt((await state.get_data())['order_prod']['price'])}\n💳 Payment method:", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.message(OrderFlow.waiting_input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please provide valid info.")
    await state.update_data(user_input=text)
    data = await state.get_data()
    prod = data["order_prod"]
    if prod["category_id"] == "crunchyroll":
        await msg.answer(f"📦 *{prod['name']}*\n📧 {text}\n📱 Enter WhatsApp/Phone number:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Main Menu", "main_menu")).as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_extra)
        return
    await msg.answer(f"📦 *{prod['name']}*\n📧 {text}\n💰 {fmt(prod['price'])}\n💳 Payment method:", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.message(OrderFlow.waiting_extra)
async def extra_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 5:
        return await msg.answer("❌ Invalid phone number.")
    data = await state.get_data()
    gmail = data.get("user_input", "")
    await state.update_data(user_input=f"{gmail} | Phone: {text}")
    await msg.answer(f"👤 Enter Telegram username (e.g., @username):")
    await state.set_state(OrderFlow.waiting_tg)

@dp.message(OrderFlow.waiting_tg)
async def tg_input(msg: Message, state: FSMContext):
    tg = msg.text.strip()
    if not tg.startswith("@"):
        tg = "@" + tg
    data = await state.get_data()
    existing = data.get("user_input", "")
    gmail = existing.split(" | ")[0]
    phone = existing.split(" | Phone: ")[1] if " | Phone: " in existing else ""
    full = f"{gmail} | Phone: {phone} | TG: {tg}"
    await state.update_data(user_input=full)
    prod = data["order_prod"]
    kb = InlineKeyboardBuilder()
    kb.row(btn(f"📞 Contact Admin", f"https://t.me/{SUPPORT_USERNAME}"))
    kb.row(btn("💳 Proceed to Payment", "go_payment"))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await msg.answer(f"📋 *Order Summary*\n📦 {prod['name']}\n💰 {fmt(prod['price'])}\n📧 {gmail}\n📱 {phone}\n👤 {tg}\n✅ Details recorded.", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.callback_query(lambda c: c.data == "go_payment")
async def go_payment(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    prod = data["order_prod"]
    await call.message.edit_text(f"📦 *{prod['name']}*\n💰 {fmt(prod['price'])}\n💳 Payment method:", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderFlow.waiting_payment)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data[4:]
    await state.update_data(pay_method=method)
    data = await state.get_data()
    prod = data.get("order_prod")
    if not prod:
        await call.message.edit_text("Session expired.", reply_markup=main_menu_kb(call.from_user.id))
        return
    price = prod["price"]
    if method == "wallet":
        if db.get_balance(call.from_user.id) < price:
            kb = InlineKeyboardBuilder()
            kb.row(btn("💳 Add Balance", "my_wallet"))
            kb.row(btn("🔙 Main Menu", "main_menu"))
            await call.message.edit_text(f"❌ Insufficient balance!\nRequired: {fmt(price)}\nYour Balance: {fmt(db.get_balance(call.from_user.id))}", reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
        await process_payment(call, state, "Wallet Balance", f"WAL{now_local():%Y%m%d%H%M%S}{random.randint(100,999)}")
    else:
        nums = {"bkash": "01742958563", "nagad": "01748506069", "rocket": "01742958563"}
        kb = InlineKeyboardBuilder()
        kb.row(btn("❌ Cancel", "main_menu"))
        await call.message.edit_text(f"💳 *{method.upper()}*\n💰 Amount: {fmt(price)}\n🔢 Number: `{nums.get(method, '')}`\nSend money & enter TrxID:", reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(OrderFlow.waiting_trxid)

@dp.message(OrderFlow.waiting_trxid)
async def get_trx(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx:
        return
    data = await state.get_data()
    mn = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}.get(data.get("pay_method"), "Manual")
    await process_payment(msg, state, mn, trx)

# Wallet / Deposit
@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    bal = db.get_balance(call.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(btn("🎁 Apply Promo Code", "apply_promo"))
    kb.row(btn("💳 Submit Deposit", "submit_deposit"))
    kb.row(btn("🔙 Main Menu", "main_menu"))
    await call.message.edit_text(f"💳 *Wallet*\n💰 Balance: *{fmt(bal)}*\n\nSend money to:\n💖 bKash: `01742958563`\n🟠 Nagad: `01748506069`\n🚀 Rocket: `01742958563`", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "apply_promo")
async def promo_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("🎁 Enter promo code:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "my_wallet")).as_markup())
    await state.set_state(DepositFlow.waiting_promo)

@dp.message(DepositFlow.waiting_promo)
async def promo_apply(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()
    promo = db.get_promo(code)
    if not promo:
        return await msg.answer("❌ Invalid promo code.")
    if promo.get("expires_at"):
        try:
            if now_local() > datetime.strptime(promo["expires_at"], "%Y-%m-%d"):
                return await msg.answer("❌ Expired.")
        except:
            pass
    if promo["max_uses"] and promo["used_count"] >= promo["max_uses"]:
        return await msg.answer("❌ Limit reached.")
    db.update_balance(msg.from_user.id, promo["amount"])
    db.add_transaction(msg.from_user.id, promo["amount"], "promo", "PromoCode", f"PROMO_{code}")
    db.use_promo(code)
    await msg.answer(f"✅ Promo {code} applied! +{fmt(promo['amount'])}", reply_markup=main_menu_kb(msg.from_user.id))
    await state.clear()

@dp.callback_query(lambda c: c.data == "submit_deposit")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("💳 Send amount, sender number, TrxID (e.g., `500 017xxx TRX123`)")
    await state.set_state(DepositFlow.waiting_trxid)

@dp.message(DepositFlow.waiting_trxid)
async def deposit_trx_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    parts = text.split()
    amount_str, sender, trx = "?", "N/A", "N/A"
    if len(parts) >= 3:
        amount_str, sender, trx = parts[0], parts[1], " ".join(parts[2:])
    elif len(parts) == 2:
        amount_str, trx = parts[0], parts[1]
    else:
        m = re.search(r'(\d+\.?\d*)', text)
        amount_str = m.group(1) if m else "?"
        trx = text
    if sender == "N/A":
        phone = re.search(r'01[3-9]\d{8}', text)
        sender = phone.group(0) if phone else "N/A"
    db.add_transaction(msg.from_user.id, float(amount_str) if amount_str != "?" else 0, "deposit_pending", "Manual", trx, f"Sender: {sender}")
    for aid in ADMIN_IDS:
        await bot.send_message(aid, f"💰 Deposit request\nUser: {msg.from_user.id}\nAmount: {amount_str}\nSender: {sender}\nTrxID: {trx}")
    await msg.answer("✅ Deposit request submitted! Admin will verify.", reply_markup=main_menu_kb(msg.from_user.id))
    await state.clear()

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    user_orders = db.get_user_orders(call.from_user.id, 10)
    if not user_orders:
        await call.message.edit_text("📜 No orders.", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Main Menu", "main_menu")).as_markup())
        return
    lines = ["📜 *Your Orders:*", ""]
    for o in user_orders:
        emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
        lines.append(f"{emoji} #{o['id']} — {o['product_name']}")
        lines.append(f"   {fmt(o['amount'])} | {o['status']}")
        if o.get("delivery_data"):
            dd = o["delivery_data"]
            if dd.get("key"): lines.append(f"   🔑 Key: `{dd['key']}`")
            if dd.get("email"): lines.append(f"   📧 Email: `{dd['email']}`")
            if dd.get("password"): lines.append(f"   🔐 Pass: `{dd['password']}`")
            if dd.get("ip_port"): lines.append(f"   🌐 IP:Port:User:Pass: `{dd['ip_port']}`")
            if dd.get("expires_days"): lines.append(f"   ⏰ Validity: {dd['expires_days']} days")
        lines.append("")
    await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardBuilder().row(btn("🔙 Main Menu", "main_menu")).as_markup(), parse_mode="Markdown")


# ═══ ADMIN HANDLERS ═══
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS: return
    await state.clear()
    await call.message.edit_text("⚙️ Admin Panel", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    bal_total = sum(u['balance'] for u in users)
    await call.message.edit_text(f"📊 *Dashboard*\n👥 Users: {len(users)}\n⏳ Pending: {db.pending_count()}\n💰 Total Balance: {fmt(bal_total)}", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("💰 Enter user ID or @username:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_menu")).as_markup())
    await state.set_state(AdminFlow.addbal_uid)

@dp.message(AdminFlow.addbal_uid)
async def addbal_uid_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    uid = None
    if text.startswith("@"):
        u = db.get_user_by_username(text.lstrip("@"))
        if u: uid = u["user_id"]
    else:
        try: uid = int(text)
        except: pass
    if not uid or not db.get_user(uid):
        return await msg.answer("❌ User not found.")
    await state.update_data(addbal_uid=uid)
    await msg.answer(f"Enter amount to add for user {uid}:")
    await state.set_state(AdminFlow.addbal_amt)

@dp.message(AdminFlow.addbal_amt)
async def addbal_amount_received(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        if amt <= 0: return await msg.answer("❌ Positive amount required.")
        data = await state.get_data()
        uid = data["addbal_uid"]
        db.update_balance(uid, amt)
        db.add_transaction(uid, amt, "admin_add", "Admin", f"ADMIN_{now_local():%Y%m%d%H%M%S}")
        new_bal = db.get_balance(uid)
        try: await bot.send_message(uid, generate_box("💰 BALANCE UPDATED", [f"Amount: {fmt(amt)}", f"New Balance: {fmt(new_bal)}"]), parse_mode="Markdown")
        except: pass
        await msg.answer(f"✅ Added {fmt(amt)} to user {uid}. New balance: {fmt(new_bal)}", reply_markup=admin_kb())
    except: await msg.answer("❌ Invalid amount.")
    await state.clear()

# ── Categories ──
@dp.callback_query(lambda c: c.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📂 Category Management", reply_markup=admin_cats_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery):
    await call.answer()
    cid = call.data[9:]
    cat = db.get_category(cid)
    if not cat: return
    subcats = db.get_categories(parent_id=cid)
    prods = db.get_products(cid)
    auto = "✅ Auto" if cat.get("auto_deliver") else "❌ Manual"
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Edit", f"editcat_{cid}"), btn("⚙️ Toggle Auto", f"toggleauto_{cid}"))
    if cid not in ("youtube","netflix","crunchyroll","vpn","proxy"):
        kb.row(btn("🗑️ Delete", f"delcat_{cid}"))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text(f"📂 *{cat['name']}*\nID: `{cid}`\nSubcats: {len(subcats)}\nProducts: {len(prods)}\nDelivery: {auto}", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("toggleauto_"))
async def toggle_auto(call: CallbackQuery):
    await call.answer()
    cid = call.data[11:]
    cat = db.get_category(cid)
    if not cat: return
    new = 0 if cat["auto_deliver"] else 1
    db.update_category(cid, auto_deliver=new)
    await admin_cat_view(call)
    await call.answer(f"Auto-Deliver {'enabled' if new else 'disabled'}.")

@dp.callback_query(lambda c: c.data == "addcat_start")
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    kb = InlineKeyboardBuilder()
    kb.row(btn("📂 Main Category", "addcat_root"))
    for p in db.get_categories():
        kb.row(btn(f"↪️ Sub of {p['name']}", f"addcat_child_{p['id']}"))
    kb.row(btn("🔙 Back", "admin_cats"))
    await call.message.edit_text("➕ Add New Category\nChoose parent:", reply_markup=kb.as_markup())
    await state.set_state(AdminFlow.addcat_parent)

@dp.callback_query(lambda c: c.data.startswith("addcat_root") or c.data.startswith("addcat_child_"))
async def addcat_parent_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent = None if call.data == "addcat_root" else call.data[13:]
    await state.update_data(addcat_parent=parent)
    await call.message.edit_text("Enter category name (with emoji):", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_cats")).as_markup())
    await state.set_state(AdminFlow.addcat_name)

@dp.message(AdminFlow.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    await msg.answer("Enter description (or skip):")
    await state.set_state(AdminFlow.addcat_desc)
@dp.message(AdminFlow.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    await state.update_data(addcat_desc=msg.text.strip() if msg.text.strip().lower() != "skip" else "")
    await msg.answer("Enter icon emoji (or skip):")
    await state.set_state(AdminFlow.addcat_icon)
@dp.message(AdminFlow.addcat_icon)
async def addcat_icon(msg: Message, state: FSMContext):
    await state.update_data(addcat_icon=msg.text.strip() if msg.text.strip().lower() != "skip" else "📦")
    await msg.answer("Auto-Deliver? yes/no")
    await state.set_state(AdminFlow.addcat_autodeliver)
@dp.message(AdminFlow.addcat_autodeliver)
async def addcat_autodeliver(msg: Message, state: FSMContext):
    auto = 1 if msg.text.strip().lower() == "yes" else 0
    data = await state.get_data()
    db.add_category(generate_id("cat_"), data["addcat_parent"], data["addcat_name"], data.get("addcat_desc",""), data["addcat_icon"], auto_deliver=auto)
    await msg.answer("✅ Category created!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cid = call.data[8:]
    await state.update_data(editcat_target=cid)
    await call.message.edit_text("Enter new name (or skip):", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", f"admincat_{cid}")).as_markup())
    await state.set_state(AdminFlow.editcat_name)
@dp.message(AdminFlow.editcat_name)
async def editcat_name(msg: Message, state: FSMContext):
    if msg.text.strip().lower() != "skip":
        db.update_category((await state.get_data())["editcat_target"], name=msg.text.strip())
    await msg.answer("Enter new description (or skip):")
    await state.set_state(AdminFlow.editcat_desc)
@dp.message(AdminFlow.editcat_desc)
async def editcat_desc(msg: Message, state: FSMContext):
    if msg.text.strip().lower() != "skip":
        db.update_category((await state.get_data())["editcat_target"], description=msg.text.strip())
    await msg.answer("Auto-deliver? yes/no/skip:")
    await state.set_state(AdminFlow.editcat_autodeliver)
@dp.message(AdminFlow.editcat_autodeliver)
async def editcat_autodeliver(msg: Message, state: FSMContext):
    val = msg.text.strip().lower()
    cid = (await state.get_data())["editcat_target"]
    if val == "yes": db.update_category(cid, auto_deliver=1)
    elif val == "no": db.update_category(cid, auto_deliver=0)
    await msg.answer("✅ Category updated!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer()
    if not db.delete_category(call.data[7:]):
        await call.answer("❌ Cannot delete main category.", show_alert=True)
    else:
        await call.message.edit_text("🗑️ Category deleted.", reply_markup=admin_cats_kb())

# ── Edit Product (hierarchical) ──
@dp.callback_query(lambda c: c.data == "admin_editprod")
async def admin_editprod_list(call: CallbackQuery):
    await call.answer()
    main_cats = db.get_categories()  # only top-level
    kb = InlineKeyboardBuilder()
    for cat in main_cats:
        kb.button(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"editprods_cat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Admin Menu", "admin_menu"))
    await call.message.edit_text("📦 *Edit Products*\nSelect main category:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprods_cat_"))
async def editprods_cat(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[14:]
    cat = db.get_category(cat_id)
    if not cat: return
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    if subcats:
        for sc in subcats:
            kb.button(text=f"📂 {sc.get('icon', '')} {sc['name']}", callback_data=f"editprods_cat_{sc['id']}")
    if prods:
        for p in prods:
            kb.button(text=f"✏️ {p['name']} — {fmt(p['price'])}", callback_data=f"editprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("➕ Add Product Here", f"addprod_now_{cat_id}"))
    kb.row(btn("🔙 Back", "admin_editprod"))
    title = f"📦 *{cat.get('icon', '')} {cat['name']}*"
    if subcats and not prods:
        title += "\nSelect a subcategory:"
    elif prods:
        title += "\nSelect a product to edit:"
    await call.message.edit_text(title, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod: return
    await state.update_data(editprod_target=pid)
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Name", f"editprod_field_name"), btn("💰 Price", f"editprod_field_price"))
    kb.row(btn("⏰ Expiry", f"editprod_field_expiry"), btn("🗑️ Delete", f"delprod_{pid}"))
    kb.row(btn("🔙 Back", "admin_editprod"))
    await call.message.edit_text(
        f"📦 *{prod['name']}*\nID: `{pid}`\n💰 Price: {fmt(prod['price'])}\n⏰ Expiry: {prod['expiry_days']} days\nStock Type: {prod['stock_type']}\n\nSelect field to edit:",
        reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_field)

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"))
async def editprod_field_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    field = call.data[16:]
    await state.update_data(editprod_field=field)
    await call.message.edit_text(f"✏️ Enter new value for *{field}*:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_editprod")).as_markup(), parse_mode="Markdown")
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
        await msg.answer("✅ Product updated!", reply_markup=admin_kb())
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    db.delete_product(call.data[8:])
    await call.message.edit_text("🗑️ Product deleted.", reply_markup=admin_kb())

# ── Add Product (remains same) ──
@dp.callback_query(lambda c: c.data.startswith("addprod_now_"))
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[12:]
    await state.update_data(addprod_cat=cat_id)
    await call.message.edit_text("➕ Enter product name:")
    await state.set_state(AdminFlow.addprod_name)

@dp.message(AdminFlow.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    await msg.answer("Enter price:")
    await state.set_state(AdminFlow.addprod_price)

@dp.message(AdminFlow.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        await state.update_data(addprod_price=float(msg.text.strip()))
        await msg.answer("Enter expiry days:")
        await state.set_state(AdminFlow.addprod_expiry)
    except: await msg.answer("❌ Invalid number.")

@dp.message(AdminFlow.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        data = await state.get_data()
        cat = db.get_category(data["addprod_cat"])
        is_auto = cat.get("auto_deliver") == 1 if cat else False
        if is_auto:
            await state.update_data(addprod_expiry=expiry)
            await msg.answer("Stock type: `email_pass`, `key_only`, `ip_port`")
            await state.set_state(AdminFlow.addprod_stocktype)
        else:
            pid = generate_id("prod_")
            db.add_product(pid, data["addprod_cat"], data["addprod_name"], data["addprod_price"], stock_type="manual", expiry_days=expiry)
            await msg.answer(f"✅ Product added!\nName: {data['addprod_name']}\nID: {pid}\nPrice: {fmt(data['addprod_price'])}\nExpiry: {expiry} days", reply_markup=admin_kb())
            await state.clear()
    except: await msg.answer("❌ Invalid days.")

@dp.message(AdminFlow.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ("email_pass","key_only","ip_port"):
        return await msg.answer("❌ Invalid type.")
    data = await state.get_data()
    pid = generate_id("prod_")
    db.add_product(pid, data["addprod_cat"], data["addprod_name"], data["addprod_price"], stock_type=stype, expiry_days=data["addprod_expiry"])
    await msg.answer(f"✅ Product added! Stock type: {stype}", reply_markup=admin_kb())
    await state.clear()

# ── Stock Management (hierarchical) ──
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 Stock Management", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    lines = ["🔑 *Stock Status*", ""]
    if counts:
        for s in counts:
            lines.append(f"📦 `{s['product_id']}` ({s['stock_type']}): {s['cnt']} available")
    else:
        lines.append("No stock.")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    main_cats = db.get_categories()
    kb = InlineKeyboardBuilder()
    for cat in main_cats:
        kb.button(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"stkcat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🔑 *Add Stock*\nSelect main category:", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_cat_select)

@dp.callback_query(lambda c: c.data.startswith("stkcat_"), AdminFlow.stock_cat_select)
async def stock_cat_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[7:]
    cat = db.get_category(cat_id)
    if not cat: return
    subcats = db.get_categories(parent_id=cat_id)
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    if subcats:
        for sc in subcats:
            kb.button(text=f"📂 {sc.get('icon', '')} {sc['name']}", callback_data=f"stkcat_{sc['id']}")
    if prods:
        for p in prods:
            kb.button(text=f"📦 {p['name']} [{p['stock_type']}]", callback_data=f"stkprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "stock_add"))
    title = f"🔑 *{cat.get('icon', '')} {cat['name']}*"
    if subcats and not prods:
        title += "\nSelect a subcategory:"
    elif prods:
        title += "\nSelect a product to add stock:"
    await call.message.edit_text(title, reply_markup=kb.as_markup(), parse_mode="Markdown")
    # stay in stock_cat_select state until product is chosen

@dp.callback_query(lambda c: c.data.startswith("stkprod_"))
async def stock_target_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[8:]
    prod = db.get_product(pid)
    if not prod: return
    await state.update_data(stock_target=pid)
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔑 Key Only", f"stktype_keyonly_{pid}"), btn("📧 Email & Password", f"stktype_emailpass_{pid}"))
    kb.row(btn("🌐 IP:Port:User:Pass", f"stktype_ip_port_{pid}"))
    kb.row(btn("🔙 Back", "stock_add"))
    await call.message.edit_text(f"🔑 *Add Stock to:* {prod['name']}\nExpiry: {prod['expiry_days']} days\nSelect stock type:", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_type_choice)

@dp.callback_query(lambda c: c.data.startswith("stktype_"), AdminFlow.stock_type_choice)
async def stock_type_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_", 2)
    if len(parts) < 3: return
    chosen = parts[1]
    pid = parts[2]
    prod = db.get_product(pid)
    if not prod: return
    stype = "key_only" if chosen == "keyonly" else ("email_pass" if chosen == "emailpass" else "ip_port")
    await state.update_data(stock_target=pid, stock_type=stype)
    lines = [f"🔑 *Add Stock to:* {prod['name']}", f"Stock Type: *{stype}*", "Expiry: {} days".format(prod['expiry_days']), "", "Send data (one per line) or upload `.txt` file."]
    if stype == "key_only": lines.append("🔑 Key(s): `ABC123`")
    elif stype == "email_pass": lines.append("📧 email:pass pairs")
    else: lines.append("🌐 IP:Port:Username:Password")
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Change Type", f"stkprod_{pid}"))
    kb.row(btn("🔙 Menu", "admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_input)

@dp.message(AdminFlow.stock_input, F.text)
async def stock_input_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    prod = db.get_product(pid)
    expiry = prod["expiry_days"] if prod else 30
    added = 0
    for line in msg.text.strip().split("\n"):
        line = line.strip()
        if not line: continue
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
    await msg.answer(f"✅ {added} stock items added (expiry: {expiry} days).", reply_markup=admin_stock_kb())
    await state.clear()

@dp.message(AdminFlow.stock_input, F.document)
async def stock_file_upload(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    prod = db.get_product(pid)
    expiry = prod["expiry_days"] if prod else 30
    doc = msg.document
    if not doc.file_name.endswith(".txt"): return await msg.answer("❌ Only .txt files.")
    file = await bot.get_file(doc.file_id)
    path = f"/tmp/{doc.file_id}.txt"
    await bot.download_file(file.file_path, destination=path)
    try:
        with open(path) as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
    except:
        return await msg.answer("❌ Couldn't read file.")
    os.remove(path)
    added = 0
    for line in lines:
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
    await msg.answer(f"✅ {added} stock items from file (expiry: {expiry} days).", reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del_list(call: CallbackQuery):
    await call.answer()
    all_stock = db.get_all_stock()
    kb = InlineKeyboardBuilder()
    for s in all_stock[:20]:
        display = s.get('key_data') or s.get('email') or f"ID:{s['id']}"
        kb.button(text=f"{'📦' if not s['is_used'] else '✅'} #{s['id']} {display[:25]}", callback_data=f"delstock_{s['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🗑️ Select stock to delete:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    db.delete_stock(int(call.data.split("_")[1]))
    await stock_del_list(call)

# ── Backup / Restore ──
@dp.callback_query(lambda c: c.data == "admin_backup")
async def admin_backup(call: CallbackQuery):
    await call.answer("💾 Creating backup...")
    try:
        path = db.backup()
        await bot.send_document(call.from_user.id, FSInputFile(path), caption="Database backup")
        await call.message.edit_text("✅ Backup sent!", reply_markup=admin_kb())
    except Exception as e:
        await call.message.edit_text(f"❌ {e}", reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_restore")
async def admin_restore_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("🔄 Send the backup .db file to restore.", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Cancel", "admin_menu")).as_markup())
    await state.set_state(AdminFlow.restore_file)

@dp.message(AdminFlow.restore_file, F.document)
async def admin_restore_file(msg: Message, state: FSMContext):
    doc = msg.document
    if not doc.file_name.endswith(".db"): return await msg.answer("❌ Invalid file.")
    file = await bot.get_file(doc.file_id)
    path = f"/tmp/restore_{doc.file_id}.db"
    await bot.download_file(file.file_path, destination=path)
    try:
        if db.restore(path):
            await msg.answer("✅ Database restored!", reply_markup=admin_kb())
        else:
            await msg.answer("❌ Restore failed.", reply_markup=admin_kb())
    except Exception as e:
        await msg.answer(f"❌ {e}", reply_markup=admin_kb())
    finally:
        if os.path.exists(path): os.remove(path)
    await state.clear()

# ── Broadcast ──
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("📨 Send text or video to broadcast:", reply_markup=InlineKeyboardBuilder().row(btn("🔙 Back", "admin_menu")).as_markup())
    await state.set_state(AdminFlow.broadcast_msg)

@dp.message(AdminFlow.broadcast_msg, F.text)
async def broadcast_text(msg: Message, state: FSMContext):
    users = db.get_all_users()
    sent = sum(1 for u in users if not u["is_banned"] and (await bot.send_message(u["user_id"], msg.text), True))
    await msg.answer(f"✅ Broadcast sent to {sent}/{len(users)}.", reply_markup=admin_kb())
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
            except: pass
    await msg.answer(f"✅ Video broadcast sent to {sent}/{len(users)}.", reply_markup=admin_kb())
    await state.clear()

# ── Ban / Unban ──
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("⛔ Enter user ID to ban:")
    await state.set_state(AdminFlow.ban_uid)
@dp.message(AdminFlow.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        db.set_ban(int(msg.text.strip()), True)
        await msg.answer("✅ Banned.", reply_markup=admin_kb())
    except: await msg.answer("❌ Invalid ID.")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("✅ Enter user ID to unban:")
    await state.set_state(AdminFlow.unban_uid)
@dp.message(AdminFlow.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        db.set_ban(int(msg.text.strip()), False)
        await msg.answer("✅ Unbanned.", reply_markup=admin_kb())
    except: await msg.answer("❌ Invalid ID.")
    await state.clear()

# ── Manual Delivery ──
@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("📦 Enter order ID:")
    await state.set_state(AdminFlow.deliver_oid)
@dp.message(AdminFlow.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text.strip())
        order = db.get_order(oid)
        if not order: return await msg.answer("❌ Order not found.")
        await state.update_data(oid=oid)
        await msg.answer("Enter delivery details (email:pass, KEY, IP:Port:User:Pass):")
        await state.set_state(AdminFlow.deliver_file)
    except: await msg.answer("❌ Invalid ID.")
@dp.message(AdminFlow.deliver_file)
async def deliver_file(msg: Message, state: FSMContext):
    data = await state.get_data()
    oid = data["oid"]
    order = db.get_order(oid)
    text = msg.text.strip()
    if re.match(r'\d+\.\d+\.\d+\.\d+:\d+:', text):
        dd = {"ip_port": text}
    elif ":" in text:
        e, p = text.split(":", 1)
        dd = {"email": e.strip(), "password": p.strip()}
    else:
        dd = {"key": text}
    prod = db.get_product(order["product_id"])
    expiry = prod["expiry_days"] if prod else 30
    now = now_local()
    db.update_order(oid, "delivered", dd)
    box = generate_box("✅ MANUAL DELIVERY", [
        f"📦 {order['product_name']}",
        f"🆔 Order: #{oid}",
        "",
        f"🔑 Key: `{text}`" if "key" in dd else (f"📧 Email: `{dd.get('email')}`\n🔐 Pass: `{dd.get('password')}`" if "email" in dd else f"🌐 IP:Port:User:Pass: `{dd.get('ip_port')}`"),
        "",
        f"✅ Delivered: {now.strftime('%d %b %Y %I:%M %p')}",
        f"⏰ Validity: {expiry} days",
        f"📅 Expires: {(now+timedelta(days=expiry)).strftime('%d %B %Y')}"
    ])
    try: await bot.send_message(order["user_id"], box, parse_mode="Markdown")
    except: pass
    await msg.answer(f"✅ Order #{oid} delivered.", reply_markup=admin_kb())
    await state.clear()

# ── Approve / Reject ──
@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order: return
    prod = db.get_product(order["product_id"])
    expiry = prod["expiry_days"] if prod else 30
    now = now_local()
    db.update_order(oid, "delivered", {"expires": (now+timedelta(days=expiry)).strftime("%d %B %Y"), "expiry_days": expiry})
    try: await bot.send_message(order["user_id"], generate_box("✅ ORDER CONFIRMED", [f"Order #{oid} approved!", f"Validity: {expiry} days"]), parse_mode="Markdown")
    except: pass
    await call.message.edit_text(f"✅ Order #{oid} Approved & Delivered!", reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order: return
    db.update_order(oid, "cancelled")
    try: await bot.send_message(order["user_id"], f"❌ Order #{oid} cancelled.")
    except: pass
    await call.message.edit_text(f"❌ Order #{oid} Rejected.", reply_markup=admin_kb())

async def main():
    print("🚀 SKY STORE BD v5.0 starting...")
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
