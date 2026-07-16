#!/usr/bin/env python3
import asyncio, os, sys, sqlite3, random
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError:
    print("pip install aiogram")
    sys.exit(1)

BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
BOT_USERNAME = "@SKY_STOR_BOT"
SUPPORT_USERNAME = "FBSKYSUPPORT"

# ─── EMOJIS ──
E = {
    "ok":"✅","no":"❌","back":"","home":"🏠",
    "wallet":"💰","admin":"🔐","light":"⚡","rocket":"🚀",
    "star":"✨","money":"💸","box":"📦","clock":"⏰",
    "bell":"🔔","lock":"","unlock":"🔓","key":"",
    "globe":"🌍","chart":"📊","users":"👥","msg":"📨",
    "vpn":"","stock":"🔑","ban":"","unban":"✅",
    "edit":"✏️","delete":"🗑️","add":"➕"
}

# ─── DATABASE ───
class DB:
    def __init__(self, path="store.db"):
        self.path = path
        self._init()
    
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init(self):
        with self._conn() as c:
            # Users table
            c.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                balance REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # Orders table
            c.execute("""CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                category_name TEXT,
                amount REAL,
                user_input TEXT,
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT DEFAULT 'pending',
                delivery_photo TEXT,
                note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # Transactions table
            c.execute("""CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                method TEXT,
                trx_id TEXT,
                note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # VPN configs table
            c.execute("""CREATE TABLE IF NOT EXISTS vpn_configs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                config_type TEXT,
                config_data TEXT,
                server_location TEXT,
                expiry_days INTEGER,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # VPN Stock table (NEW - for email/pass or key_only)
            c.execute("""CREATE TABLE IF NOT EXISTS vpn_stock(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                stock_type TEXT,
                email TEXT,
                password TEXT,
                key_data TEXT,
                is_used INTEGER DEFAULT 0,
                expiry_days INTEGER DEFAULT 30,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # Products table (FIXED - proper schema)
            c.execute("""CREATE TABLE IF NOT EXISTS products(
                id TEXT PRIMARY KEY,
                subcategory TEXT,
                name TEXT,
                price REAL,
                bonus REAL DEFAULT 0,
                stock_type TEXT,
                is_active INTEGER DEFAULT 1
            )""")
            
            # Initialize default products
            self._init_default_products()
    
    def _init_default_products(self):
        """Initialize default products if not exists"""
        with self._conn() as c:
            # Check if products already exist
            count = c.execute("SELECT COUNT(*) FROM products").fetchone()[0]
            if count > 0:
                return  # Products already exist
            
            # Free Fire Diamonds
            ff_diamonds = [
                ("ff_25d", "💎 25 Diamond", 20, 0, None),
                ("ff_50d", "💎 50 Diamond", 35, 0, None),
                ("ff_115d", "💎 115 Diamond", 79, 0, None),
                ("ff_240d", "💎 240 Diamond", 156, 0, None),
                ("ff_355d", "💎 355 Diamond", 237, 0, None),
                ("ff_505d", "💎 505 Diamond", 336, 0, None),
                ("ff_610d", "💎 610 Diamond", 390, 0, None),
                ("ff_850d", "💎 850 Diamond", 558, 0, None),
                ("ff_1090d", "💎 1090 Diamond", 716, 0, None),
                ("ff_1240d", "💎 1240 Diamond", 795, 0, None),
                ("ff_2530d", "💎 2530 Diamond", 1580, 0, None),
                ("ff_5060d", "💎 5060 Diamond", 3160, 0, None),
                ("ff_7590d", "💎 7590 Diamond", 4800, 0, None),
                ("ff_10120d", "💎 10120 Diamond", 6400, 0, None)
            ]
            for pid, name, price, bonus, stock_type in ff_diamonds:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "ff_diamonds", name, price, bonus, stock_type))
            
            # Free Fire Weekly
            ff_weekly = [
                ("ffw_1", "📆 1x Weekly", 155, 0, None),
                ("ffw_2", "📆 2x Weekly", 310, 0, None),
                ("ffw_3", "📆 3x Weekly", 465, 0, None),
                ("ffw_5", " 5x Weekly", 775, 0, None),
                ("ffw_m", "📆 Monthly", 765, 0, None),
                ("ffw_2m", "📆 2x Monthly", 1540, 0, None),
                ("ffw_3m", "📆 3x Monthly", 2295, 0, None),
                ("ffw_5m", "📆 5x Monthly", 3825, 0, None),
                ("ffw_1w1m", "📆 1Week+1Month", 930, 0, None),
                ("ffw_4w1m", "📆 4Week+1Month", 1395, 0, None)
            ]
            for pid, name, price, bonus, stock_type in ff_weekly:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "ff_weekly", name, price, bonus, stock_type))
            
            # Free Fire Lite
            ff_lite = [
                ("ffl_1", "⭐ 1x Weekly Lite", 40, 0, None),
                ("ffl_2", "⭐ 2x Weekly Lite", 80, 0, None),
                ("ffl_3", "⭐ 3x Weekly Lite", 120, 0, None),
                ("ffl_5", "⭐ 5x Weekly Lite", 200, 0, None)
            ]
            for pid, name, price, bonus, stock_type in ff_lite:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "ff_lite", name, price, bonus, stock_type))
            
            # Free Fire Likes
            ff_like = [
                ("fflk_200", "❤️ 200 Likes", 20, 0, None),
                ("fflk_1000", "❤️ 1000 Likes", 100, 0, None),
                ("fflk_2000", "❤️ 2000 Likes", 200, 0, None),
                ("fflk_3000", "❤️ 3000 Likes", 300, 0, None),
                ("fflk_4000", "❤️ 4000 Likes", 400, 0, None),
                ("fflk_5000", "❤️ 5000 Likes", 500, 0, None),
                ("fflk_6000", "❤️ 6000 Likes", 600, 0, None),
                ("fflk_12000", "❤️ 12000 Likes", 1200, 0, None),
                ("fflk_24000", "❤️ 24000 Likes", 2400, 0, None),
                ("fflk_48000", "❤️ 48000 Likes", 4800, 0, None)
            ]
            for pid, name, price, bonus, stock_type in ff_like:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "ff_like", name, price, bonus, stock_type))
            
            # Netflix
            netflix = [
                ("nf_single", "🎬 Single Profile (1M)", 400, 0, None),
                ("nf_full", " Full Account (1M)", 1830, 0, None)
            ]
            for pid, name, price, bonus, stock_type in netflix:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "netflix", name, price, bonus, stock_type))
            
            # YouTube
            youtube = [
                ("yt_1m", "▶️ 1 Month", 100, 0, None),
                ("yt_3m", "▶️ 3 Months", 200, 0, None),
                ("yt_6m", "▶️ 6 Months", 300, 0, None),
                ("yt_1y", "▶️ 1 Year", 490, 0, None)
            ]
            for pid, name, price, bonus, stock_type in youtube:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "youtube", name, price, bonus, stock_type))
            
            # Crunchyroll
            crunchyroll = [
                ("cr_shared", "🍿 Shared (1M)", 200, 0, None),
                ("cr_full1", "🍿 Full (1M)", 450, 0, None),
                ("cr_full12", "🍿 Full (12M)", 1840, 0, None)
            ]
            for pid, name, price, bonus, stock_type in crunchyroll:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "crunchyroll", name, price, bonus, stock_type))
            
            # VPN Plus (with stock_type)
            vpn_plus = [
                ("vpn_express", "🔑 ExpressVPN (1M)", 350, 0, "email_pass"),
                ("vpn_hma", "🔑 HMA VPN (1M)", 250, 0, "key_only"),
                ("vpn_vpnip", "🔑 VPN IP (1M)", 300, 0, "email_pass"),
                ("vpn_vanish", "🔑 Vanish VPN (1M)", 280, 0, "email_pass"),
                ("vpn_proton", " Proton VPN (1M)", 320, 0, "email_pass"),
                ("proxy_dedicated", "🌐 Dedicated Proxy IP (1M)", 200, 0, "key_only"),
                ("vps_basic", "🖥️ Basic VPS (1M)", 800, 0, "email_pass"),
                ("vps_premium", "🖥️ Premium VPS (1M)", 1500, 0, "email_pass")
            ]
            for pid, name, price, bonus, stock_type in vpn_plus:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "vpn_plus", name, price, bonus, stock_type))
            
            # Topup
            topup = [
                ("bal_100", "💰 100 Tk", 100, 0, None),
                ("bal_200", "💰 200 Tk (+5 Bonus)", 200, 5, None),
                ("bal_500", "💰 500 Tk (+20 Bonus)", 500, 20, None),
                ("bal_1000", "💰 1000 Tk (+50 Bonus)", 1000, 50, None),
                ("bal_2000", "💰 2000 Tk (+120 Bonus)", 2000, 120, None),
                ("bal_5000", "💰 5000 Tk (+350 Bonus)", 5000, 350, None)
            ]
            for pid, name, price, bonus, stock_type in topup:
                c.execute("""INSERT INTO products(id, subcategory, name, price, bonus, stock_type) 
                             VALUES(?,?,?,?,?,?)""",
                         (pid, "topup", name, price, bonus, stock_type))
    
    def get_user(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return dict(r) if r else None
    
    def create_user(self, uid, fn, un):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id, first_name, username) VALUES(?,?,?)", (uid, fn, un))
    
    def get_balance(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        return r["balance"] if r else 0
    
    def update_balance(self, uid, amt):
        with self._conn() as c:
            c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amt, uid))
    
    def deduct_balance(self, uid, amt):
        with self._conn() as c:
            cur = c.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?", (amt, uid, amt))
            return cur.rowcount > 0
    
    def set_ban(self, uid, ban=True):
        with self._conn() as c:
            c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, uid))
    
    def add_order(self, uid, pname, cat, amt, uinput, pmethod, trid):
        with self._conn() as c:
            cur = c.execute("""INSERT INTO orders(user_id, product_name, category_name, amount, user_input, payment_method, transaction_id) 
                              VALUES(?,?,?,?,?,?,?)""", (uid, pname, cat, amt, uinput, pmethod, trid))
            return cur.lastrowid
    
    def update_order(self, oid, status, photo="", note=""):
        with self._conn() as c:
            c.execute("UPDATE orders SET status=?, delivery_photo=?, note=? WHERE id=?", (status, photo, note, oid))
    
    def get_order(self, oid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        return dict(r) if r else None
    
    def get_user_orders(self, uid, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def get_all_orders(self, status=None, category=None, limit=50):
        with self._conn() as c:
            query = "SELECT * FROM orders WHERE 1=1"
            params = []
            if status:
                query += " AND status=?"
                params.append(status)
            if category:
                query += " AND category_name=?"
                params.append(category)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = c.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    
    def pending_count(self):
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) as cnt FROM orders WHERE status='pending'").fetchone()["cnt"]
    
    def get_all_users(self):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
        return [dict(r) for r in rows]
    
    def add_transaction(self, uid, amt, typ, method, trid, note=""):
        with self._conn() as c:
            c.execute("INSERT INTO transactions(user_id, amount, type, method, trx_id, note) VALUES(?,?,?,?,?,?)", 
                     (uid, amt, typ, method, trid, note))
    
    # ─── PRODUCT MANAGEMENT ───
    def get_product(self, pid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None
    
    def get_products_by_subcategory(self, subcat):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM products WHERE subcategory=? AND is_active=1 ORDER BY price", (subcat,)).fetchall()
        return [dict(r) for r in rows]
    
    def update_product_price(self, pid, new_price):
        with self._conn() as c:
            c.execute("UPDATE products SET price=? WHERE id=?", (new_price, pid))
    
    def add_product(self, pid, subcat, name, price, bonus=0, stock_type=None):
        with self._conn() as c:
            c.execute("""INSERT OR REPLACE INTO products(id, subcategory, name, price, bonus, stock_type) 
                        VALUES(?,?,?,?,?,?)""",
                     (pid, subcat, name, price, bonus, stock_type))
    
    def delete_product(self, pid):
        with self._conn() as c:
            c.execute("DELETE FROM products WHERE id=?", (pid,))
    
    # ─── VPN STOCK MANAGEMENT ───
    def add_vpn_stock(self, product_id, stock_type, email=None, password=None, key_data=None, days=30):
        with self._conn() as c:
            c.execute("""INSERT INTO vpn_stock(product_id, stock_type, email, password, key_data, expiry_days) 
                        VALUES(?,?,?,?,?,?)""", (product_id, stock_type, email, password, key_data, days))
    
    def get_available_vpn_stock(self, product_id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM vpn_stock WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1", (product_id,)).fetchone()
            if r:
                c.execute("UPDATE vpn_stock SET is_used=1 WHERE id=?", (r["id"],))
                return dict(r)
            return None
    
    def get_vpn_stock_counts(self):
        with self._conn() as c:
            rows = c.execute("""SELECT product_id, stock_type, COUNT(*) as cnt 
                               FROM vpn_stock WHERE is_used=0 
                               GROUP BY product_id, stock_type""").fetchall()
        return [dict(r) for r in rows]
    
    def get_all_vpn_stock(self, product_id=None):
        with self._conn() as c:
            if product_id:
                rows = c.execute("SELECT * FROM vpn_stock WHERE product_id=? ORDER BY id DESC LIMIT 100", (product_id,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM vpn_stock ORDER BY product_id, id DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]
    
    def delete_vpn_stock(self, sid):
        with self._conn() as c:
            c.execute("DELETE FROM vpn_stock WHERE id=?", (sid,))

db = DB()

# ─── BOT SETUP ───
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ─── STATES ───
class Order(StatesGroup):
    input = State()
    payment = State()
    trxid = State()

class Admin(StatesGroup):
    addbal_uid = State()
    addbal_amt = State()
    deliver_oid = State()
    deliver_file = State()
    broadcast_msg = State()
    vpn_oid = State()
    vpn_data = State()
    vpn_loc = State()
    stock_product = State()
    stock_data = State()
    ban_uid = State()
    unban_uid = State()
    restore_db = State()
    edit_price_pid = State()
    edit_price_new = State()
    add_product_subcat = State()
    add_product_id = State()
    add_product_name = State()
    add_product_price = State()

# ─── WELCOME MESSAGE (Stylish Design) ───
WELCOME = f"""╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
      🌟 *SKY STORE BD* 🌟
      ⚡ Premium Digital Store
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

🔥 *Free Fire* • 💎 Diamonds • 📆 Weekly
 *Netflix* • ▶️ YouTube •  Crunchyroll  
🌐 *VPN Plus* • 💰 Wallet Top-Up

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮
📞 Support: @{SUPPORT_USERNAME}
 Instant Delivery • 🛡️ 100% Trusted
╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯

👇 *Select a category to start!*"""

# ─── KEYBOARDS ───
def main_menu(uid):
    kb = InlineKeyboardBuilder()
    
    categories = [
        {"id": "freefire", "name": "🔥 Free Fire BD"},
        {"id": "subscriptions", "name": "🎬 Premium Subscriptions"},
        {"id": "vpn_plus", "name": "🌐 VPN Plus"},
        {"id": "topup", "name": "💰 Wallet Top-Up"}
    ]
    
    for cat in categories:
        kb.row(InlineKeyboardButton(text=cat["name"], callback_data=f"main_{cat['id']}"))
    
    kb.row(
        InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💰 My Wallet", callback_data="my_wallet")
    )
    
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    
    return kb.as_markup()

def subcategory_kb(main_cat):
    subcats = {
        "freefire": [
            {"id": "ff_diamonds", "name": "💎 Diamonds"},
            {"id": "ff_weekly", "name": "📆 Weekly"},
            {"id": "ff_lite", "name": "⭐ Weekly Lite"},
            {"id": "ff_like", "name": "❤️ Like Service"}
        ],
        "subscriptions": [
            {"id": "netflix", "name": "🎬 Netflix Premium"},
            {"id": "youtube", "name": "▶️ YouTube Premium"},
            {"id": "crunchyroll", "name": "🍿 Crunchyroll"}
        ]
    }
    
    subs = subcats.get(main_cat)
    if not subs:
        return products_kb(main_cat)
    
    kb = InlineKeyboardBuilder()
    for s in subs:
        kb.row(InlineKeyboardButton(text=s["name"], callback_data=f"sub_{main_cat}|{s['id']}"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="main_menu"))
    return kb.as_markup()

def products_kb(subcat):
    prods = db.get_products_by_subcategory(subcat)
    kb = InlineKeyboardBuilder()
    
    for p in prods:
        if p.get("bonus", 0) > 0:
            txt = f"{p['name']} (+{p['bonus']}) — ৳{p['price']:,.0f}"
        else:
            txt = f"{p['name']} — ৳{p['price']:,.0f}"
        kb.row(InlineKeyboardButton(text=txt, callback_data=f"order_{subcat}|{p['id']}"))
    
    kb.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="show_main"),
        InlineKeyboardButton(text=" Home", callback_data="main_menu")
    )
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💰 Wallet Balance", callback_data="pay_wallet"))
    kb.row(
        InlineKeyboardButton(text="💳 bKash", callback_data="pay_bkash"),
        InlineKeyboardButton(text="💳 Nagad", callback_data="pay_nagad")
    )
    kb.row(InlineKeyboardButton(text="💳 Rocket", callback_data="pay_rocket"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"))
    kb.row(
        InlineKeyboardButton(text="📦 All Orders", callback_data="admin_all_orders"),
        InlineKeyboardButton(text="👥 Users", callback_data="admin_users")
    )
    kb.row(
        InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"),
        InlineKeyboardButton(text=" Deliver", callback_data="admin_deliver")
    )
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(
        InlineKeyboardButton(text=" VPN Stock", callback_data="admin_vpn_stock"),
        InlineKeyboardButton(text="📦 Product Manage", callback_data="admin_product_manage")
    )
    kb.row(
        InlineKeyboardButton(text=" Ban User", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban")
    )
    kb.row(InlineKeyboardButton(text="💾 Restore DB", callback_data="admin_restore"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ Pending Orders", callback_data="orders_pending"))
    kb.row(InlineKeyboardButton(text="✅ Delivered Orders", callback_data="orders_delivered"))
    kb.row(InlineKeyboardButton(text=" Cancelled Orders", callback_data="orders_cancelled"))
    kb.row(InlineKeyboardButton(text=" All Orders", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_product_manage_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Edit Price", callback_data="edit_price"))
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data="add_product"))
    kb.row(InlineKeyboardButton(text="️ Delete Product", callback_data="delete_product"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_vpn_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="vpn_stock_status"))
    kb.row(InlineKeyboardButton(text="➕ Add Stock", callback_data="vpn_add_stock"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Stock", callback_data="vpn_delete_stock"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

# ─── COMMANDS ───
@dp.message(CommandStart())
async def start(msg: Message):
    user = msg.from_user
    db.create_user(user.id, user.first_name, user.username)
    await msg.answer(WELCOME, reply_markup=main_menu(user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "main_menu")
async def go_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu(call.from_user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "show_main")
async def show_main_cats(call: CallbackQuery, state: FSMContext):
    await state.clear()
    txt = "╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += "      📂 *Select Category*\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    await call.message.edit_text(txt, reply_markup=main_menu(call.from_user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("main_"))
async def main_cat(call: CallbackQuery, state: FSMContext):
    main_id = call.data.split("_")[1]
    await state.update_data(main_cat=main_id)
    
    cat_names = {
        "freefire": " Free Fire BD",
        "subscriptions": "🎬 Premium Subscriptions",
        "vpn_plus": "🌐 VPN Plus",
        "topup": "💰 Wallet Top-Up"
    }
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   {cat_names.get(main_id, main_id)}\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=subcategory_kb(main_id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def sub_cat(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_", 1)
    main, sub = rest.split("|")
    await state.update_data(subcat_id=sub)
    
    sub_names = {
        "ff_diamonds": "💎 Diamonds",
        "ff_weekly": "📆 Weekly",
        "ff_lite": "⭐ Weekly Lite",
        "ff_like": "❤️ Like Service",
        "netflix": "🎬 Netflix Premium",
        "youtube": "▶️ YouTube Premium",
        "crunchyroll": "🍿 Crunchyroll"
    }
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   {sub_names.get(sub, sub)}\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=products_kb(sub), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_", 1)
    sub, pid = rest.split("|")
    prod = db.get_product(pid)
    
    if not prod:
        return await call.answer("❌ Invalid product")
    
    await state.update_data(subcat_id=sub, prod=prod)
    
    if sub == "vpn_plus":
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"    *VPN Configuration*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Product: {prod['name']}\n"
        txt += f"💰 Price: ৳{prod['price']:,.0f}\n\n"
        txt += f"🌍 Enter server location\n(or type 'auto')"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Auto", callback_data="vpn_auto")]
        ]), parse_mode="Markdown")
        await state.set_state(Order.input)
    
    elif sub == "topup":
        await state.update_data(user_input="Wallet TopUp")
        txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   💳 *Payment Details*\n"
        txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"📦 Product: {prod['name']}\n"
        txt += f"💰 Price: ৳{prod['price']:,.0f}\n"
        if prod.get("bonus", 0) > 0:
            txt += f"🎁 Bonus: +{prod['bonus']:,.0f}"
        
        await call.message.edit_text(txt, reply_markup=payment_kb(), parse_mode="Markdown")
        await state.set_state(Order.payment)
    
    else:
        prompt = "🎮 Enter your Player ID:" if "ff_" in sub else "📧 Enter your Email:"
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   📝 *Order Information*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Product: {prod['name']}\n"
        txt += f"💰 Price: {prod['price']:,.0f}\n\n"
        txt += f"{prompt}"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products")]
        ]), parse_mode="Markdown")
        await state.set_state(Order.input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    
    txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💳 *Payment Details*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📦 Product: {data['prod']['name']}\n"
    txt += f"🌍 Server: Auto\n"
    txt += f"💰 Price: ৳{data['prod']['price']:,.0f}"
    
    await call.message.edit_text(txt, reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please enter valid details")
    
    await state.update_data(user_input=text)
    data = await state.get_data()
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💳 *Payment Details*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Product: {data['prod']['name']}\n"
    txt += f"💰 Price: ৳{data['prod']['price']:,.0f}"
    
    await msg.answer(txt, reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay_select(call: CallbackQuery, state: FSMContext):
    method = call.data[4:]
    await state.update_data(pay_method=method)
    data = await state.get_data()
    prod = data["prod"]
    price = prod["price"]
    uid = call.from_user.id
    
    if method == "wallet":
        bal = db.get_balance(uid)
        if bal < price:
            txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            txt += f"   ❌ *Insufficient Balance*\n"
            txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            txt += f"💰 Need: {price:,.0f}\n"
            txt += f"💳 Have: {bal:,.0f}"
            
            return await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Top Up", callback_data="main_topup")]
            ]), parse_mode="Markdown")
        
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    
    else:
        nums = {
            "bkash": "01742958563",
            "nagad": "01748506069",
            "rocket": "01742958563"
        }
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   💳 *Send Payment*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"💰 Amount: ৳{price:,.0f}\n"
        txt += f"📱 Method: {method.upper()}\n"
        txt += f" Number: `{nums.get(method, '')}`\n\n"
        txt += f"📝 Send payment & enter TrxID"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment")]
        ]), parse_mode="Markdown")
        await state.set_state(Order.trxid)

async def process_payment(call: CallbackQuery, state: FSMContext, pmethod, trx):
    data = await state.get_data()
    prod = data["prod"]
    sub = data["subcat_id"]
    uinput = data.get("user_input", "")
    uid = call.from_user.id
    price = prod["price"]
    
    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price):
            return
    
    oid = db.add_order(uid, prod["name"], sub, price, uinput, pmethod, trx)
    
    # Handle different product types
    if sub == "topup":
        bonus = prod.get("bonus", 0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        
        bal = db.get_balance(uid)
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Top-Up Successful!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"💰 Added: ৳{total:,.0f}\n"
        if bonus > 0:
            txt += f"🎁 Bonus: +৳{bonus:,.0f}\n"
        txt += f"💳 Balance: ৳{bal:,.0f}"
        
        await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    elif sub == "vpn_plus":
        # VPN Auto Delivery
        stock = db.get_available_vpn_stock(prod["id"])
        
        if stock:
            db.update_order(oid, "delivered")
            
            if stock["stock_type"] == "key_only":
                # HMA or Proxy - only key
                txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                txt += f"   ✅ *VPN Delivered!*\n"
                txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                txt += f"🔑 Key: `{stock['key_data']}`\n"
                txt += f"🌍 Server: {uinput or 'Auto'}\n"
                txt += f"⏰ Expires: {stock['expiry_days']} days"
            else:
                # Other VPNs - email + password
                txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                txt += f"   ✅ *VPN Delivered!*\n"
                txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                txt += f"📧 Email: `{stock['email']}`\n"
                txt += f"🔐 Password: `{stock['password']}`\n"
                txt += f"🌍 Server: {uinput or 'Auto'}\n"
                txt += f" Expires: {stock['expiry_days']} days"
            
            await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
        else:
            # No stock - manual delivery needed
            db.update_order(oid, "pending")
            txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            txt += f"   ⏳ *Order Placed!*\n"
            txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            txt += f"📦 Order ID: #{oid}\n"
            txt += f"⏳ Status: Pending (No Stock)\n"
            txt += f"📝 Admin will deliver soon"
            
            await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    else:
        db.update_order(oid, "pending")
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Order Placed!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Order ID: #{oid}\n"
        txt += f"⏳ Status: Pending Verification"
        
        await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify admin
    user = db.get_user(uid)
    order = db.get_order(oid)
    
    admin_txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    admin_txt += f"    *NEW ORDER RECEIVED*\n"
    admin_txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    admin_txt += f"🆔 Order ID: #{oid}\n"
    admin_txt += f"👤 User ID: {uid}\n"
    admin_txt += f"📛 Name: {user['first_name']}\n"
    admin_txt += f"🔗 Username: @{user['username'] or 'N/A'}\n\n"
    admin_txt += f"📦 Product: {prod['name']}\n"
    admin_txt += f" Category: {sub}\n"
    admin_txt += f"💰 Amount: ৳{price:,.0f}\n\n"
    admin_txt += f" User Input: {uinput}\n"
    admin_txt += f"💳 Payment: {pmethod}\n"
    admin_txt += f"🔢 TrxID: {trx}\n\n"
    admin_txt += f"⏰ Time: {order['created_at']}"
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_txt, reply_markup=kb.as_markup(), parse_mode="Markdown")
        except:
            pass
    
    await state.clear()

@dp.message(Order.trxid)
async def get_trx(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx:
        return
    
    data = await state.get_data()
    method = data.get("pay_method", "Manual")
    mn = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}.get(method, method)
    
    await process_payment_msg(msg, state, mn, trx)

async def process_payment_msg(msg: Message, state: FSMContext, pmethod, trx):
    data = await state.get_data()
    prod = data["prod"]
    sub = data["subcat_id"]
    uinput = data.get("user_input", "")
    uid = msg.from_user.id
    price = prod["price"]
    
    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price):
            return
    
    oid = db.add_order(uid, prod["name"], sub, price, uinput, pmethod, trx)
    
    if sub == "topup":
        bonus = prod.get("bonus", 0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        
        bal = db.get_balance(uid)
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Top-Up Successful!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Added: ৳{total:,.0f}\n"
        if bonus > 0:
            txt += f"🎁 Bonus: +৳{bonus:,.0f}\n"
        txt += f"💳 Balance: ৳{bal:,.0f}"
        
        await msg.answer(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    elif sub == "vpn_plus":
        stock = db.get_available_vpn_stock(prod["id"])
        
        if stock:
            db.update_order(oid, "delivered")
            
            if stock["stock_type"] == "key_only":
                txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                txt += f"   ✅ *VPN Delivered!*\n"
                txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                txt += f"🔑 Key: `{stock['key_data']}`\n"
                txt += f"🌍 Server: {uinput or 'Auto'}\n"
                txt += f"⏰ Expires: {stock['expiry_days']} days"
            else:
                txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
                txt += f"   ✅ *VPN Delivered!*\n"
                txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
                txt += f"📧 Email: `{stock['email']}`\n"
                txt += f"🔐 Password: `{stock['password']}`\n"
                txt += f" Server: {uinput or 'Auto'}\n"
                txt += f"⏰ Expires: {stock['expiry_days']} days"
            
            await msg.answer(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
        else:
            db.update_order(oid, "pending")
            txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            txt += f"   ⏳ *Order Placed!*\n"
            txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            txt += f"📦 Order ID: #{oid}\n"
            txt += f"⏳ Status: Pending (No Stock)"
            
            await msg.answer(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    else:
        db.update_order(oid, "pending")
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Order Placed!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Order ID: #{oid}\n"
        txt += f"⏳ Status: Pending Verification"
        
        await msg.answer(txt, reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify admin
    user = db.get_user(uid)
    order = db.get_order(oid)
    
    admin_txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    admin_txt += f"   📦 *NEW ORDER RECEIVED*\n"
    admin_txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    admin_txt += f" Order ID: #{oid}\n"
    admin_txt += f"👤 User ID: {uid}\n"
    admin_txt += f" Name: {user['first_name']}\n"
    admin_txt += f"🔗 Username: @{user['username'] or 'N/A'}\n\n"
    admin_txt += f" Product: {prod['name']}\n"
    admin_txt += f"📂 Category: {sub}\n"
    admin_txt += f"💰 Amount: ৳{price:,.0f}\n\n"
    admin_txt += f"📝 User Input: {uinput}\n"
    admin_txt += f" Payment: {pmethod}\n"
    admin_txt += f"🔢 TrxID: {trx}\n\n"
    admin_txt += f"⏰ Time: {order['created_at']}"
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_txt, reply_markup=kb.as_markup(), parse_mode="Markdown")
        except:
            pass
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "back_to_payment")
async def back_pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💳 *Payment Details*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📦 Product: {data['prod']['name']}\n"
    txt += f"💰 Price: ৳{data['prod']['price']:,.0f}"
    
    await call.message.edit_text(txt, reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data == "back_to_products")
async def back_prod(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sub = data.get("subcat_id")
    if sub:
        await call.message.edit_text("📦 Select product:", reply_markup=products_kb(sub))
        await state.set_state(None)

@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery):
    uid = call.from_user.id
    bal = db.get_balance(uid)
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💰 *Your Wallet*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"💳 Balance: {bal:,.0f}"
    
    await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📦 *Your Orders*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    
    if orders:
        for o in orders[:5]:
            status_emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            txt += f"{status_emoji} #{o['id']} {o['product_name'][:20]}\n"
            txt += f"   ৳{o['amount']:,.0f} - {o['status']}\n\n"
    else:
        txt += "No orders yet."
    
    await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")

# ─── ADMIN PANEL ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("❌ Unauthorized")
    
    await state.clear()
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   🔐 *Admin Panel*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_vpn_stock_counts()
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📊 *Dashboard*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"👥 Total Users: {len(users)}\n"
    txt += f"⏳ Pending Orders: {pending}\n\n"
    txt += f" *VPN Stock Status:*\n"
    
    if stock:
        for s in stock:
            txt += f"• {s['product_id']}: {s['cnt']} ({s['stock_type']})\n"
    else:
        txt += "No stock available"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_all_orders")
async def all_orders_menu(call: CallbackQuery):
    await call.message.edit_text("📦 Select order category:", reply_markup=admin_orders_kb())

@dp.callback_query(lambda c: c.data.startswith("orders_"))
async def orders_by_status(call: CallbackQuery):
    status = call.data.split("_")[1]
    
    if status == "all":
        orders = db.get_all_orders(limit=20)
        title = "All Orders"
    else:
        orders = db.get_all_orders(status, limit=20)
        title = f"{status.capitalize()} Orders"
    
    if not orders:
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   📦 {title}\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += "No orders found."
        return await call.message.edit_text(txt, reply_markup=admin_orders_kb())
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📦 {title}\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    
    for o in orders[:10]:
        status_emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
        txt += f"{status_emoji} #{o['id']} {o['product_name'][:18]}\n"
        txt += f"   ৳{o['amount']:,.0f} by {o['user_id']}\n\n"
    
    await call.message.edit_text(txt, reply_markup=admin_orders_kb())

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    
    if not order:
        return await call.answer("❌ Order not found")
    
    db.update_order(oid, "delivered")
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✅ *Order Approved!*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📦 Order #{oid}\n"
    txt += f"✅ Status: Delivered"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")
    
    try:
        user_txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        user_txt += f"   ✅ *Order Delivered!*\n"
        user_txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        user_txt += f"📦 Order #{oid}\n"
        user_txt += f"📝 {order['product_name']}"
        
        await bot.send_message(order["user_id"], user_txt, parse_mode="Markdown")
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    
    if not order:
        return await call.answer("❌ Order not found")
    
    db.update_order(oid, "cancelled")
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ❌ *Order Rejected!*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Order #{oid}\n"
    txt += f"❌ Status: Cancelled"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")
    
    try:
        user_txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        user_txt += f"   ❌ *Order Cancelled*\n"
        user_txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        user_txt += f" Order #{oid}\n"
        user_txt += f"📝 {order['product_name']}"
        
        await bot.send_message(order["user_id"], user_txt, parse_mode="Markdown")
    except:
        pass

@dp.callback_query(lambda c: c.data == "admin_users")
async def users_list(call: CallbackQuery):
    users = db.get_all_users()
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   👥 *Users ({len(users)})*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    
    for u in users[:15]:
        status = "🔒" if u['is_banned'] else "👤"
        txt += f"{status} {u['user_id']} {u['first_name'][:15]}\n"
        txt += f"   Balance: ৳{u['balance']:,.0f}\n\n"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💰 *Add Balance*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Send User ID:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        user = db.get_user(uid)
        
        if not user:
            return await msg.answer("❌ User not found")
        
        await state.update_data(uid=uid)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   💰 *Add Balance*\n"
        txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"👤 User: {user['first_name']}\n"
        txt += f"💳 Current: ৳{user['balance']:,.0f}\n\n"
        txt += f"📝 Send amount to add:"
        
        await msg.answer(txt, parse_mode="Markdown")
        await state.set_state(Admin.addbal_amt)
    
    except:
        await msg.answer("❌ Invalid User ID")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext, bot: Bot):
    try:
        amt = float(msg.text)
        data = await state.get_data()
        uid = data["uid"]
        
        db.update_balance(uid, amt)
        db.add_transaction(uid, amt, "admin_add", "Admin", f"ADMIN_{datetime.now():%Y%m%d%H%M%S}")
        
        new_bal = db.get_balance(uid)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Balance Added!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"💰 Amount: ৳{amt:,.0f}\n"
        txt += f"💳 New Balance: ৳{new_bal:,.0f}\n"
        txt += f"👤 Added by: Admin\n"
        txt += f"⏰ Time: {datetime.now():%Y-%m-%d %H:%M}"
        
        await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            user_txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
            user_txt += f"   💰 *Balance Added!*\n"
            user_txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            user_txt += f"💰 Amount: ৳{amt:,.0f}\n"
            user_txt += f"💳 New Balance: ৳{new_bal:,.0f}\n"
            user_txt += f"👤 Added by: Admin\n"
            user_txt += f" Time: {datetime.now():%Y-%m-%d %H:%M}"
            
            await bot.send_message(uid, user_txt, parse_mode="Markdown")
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid amount")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📦 *Deliver Order*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Send Order ID:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        
        if not order:
            return await msg.answer("❌ Order not found")
        
        await state.update_data(oid=oid)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   📦 *Order #{oid}*\n"
        txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"📦 Product: {order['product_name']}\n"
        txt += f"👤 User: {order['user_id']}\n"
        txt += f" Amount: ৳{order['amount']:,.0f}\n\n"
        txt += f"📸 Send photo or type 'done':"
        
        await msg.answer(txt, parse_mode="Markdown")
        await state.set_state(Admin.deliver_file)
    
    except:
        await msg.answer("❌ Invalid Order ID")

@dp.message(Admin.deliver_file)
async def deliver_file(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    oid = data["oid"]
    order = db.get_order(oid)
    
    if msg.photo:
        file_id = msg.photo[-1].file_id
        note = msg.caption or "Delivered"
        db.update_order(oid, "delivered", file_id, note)
        
        try:
            await bot.send_photo(order["user_id"], file_id, caption=f"✅ Order #{oid} delivered!")
        except:
            pass
    else:
        db.update_order(oid, "delivered", note="Delivered")
        
        try:
            await bot.send_message(order["user_id"], f"✅ Order #{oid} delivered!")
        except:
            pass
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✅ *Order Delivered!*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📦 Order #{oid}"
    
    await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📨 *Broadcast Message*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📝 Send message to broadcast:"
    
    await call.message.edit_text(txt, parse_mode="Markdown")
    await state.set_state(Admin.broadcast_msg)

@dp.message(Admin.broadcast_msg)
async def broadcast_do(msg: Message, state: FSMContext, bot: Bot):
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
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✅ *Broadcast Sent!*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Sent: {sent}/{len(users)}"
    
    await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

# ─── VPN STOCK MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_vpn_stock")
async def vpn_stock_menu(call: CallbackQuery):
    txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   🌐 *VPN Stock Management*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=admin_vpn_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "vpn_stock_status")
async def vpn_stock_status(call: CallbackQuery):
    counts = db.get_vpn_stock_counts()
    
    txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   🔑 *Stock Status*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    
    if counts:
        for c in counts:
            txt += f"📦 {c['product_id']}\n"
            txt += f"   Type: {c['stock_type']}\n"
            txt += f"   Available: {c['cnt']}\n\n"
    else:
        txt += "No stock available"
    
    await call.message.edit_text(txt, reply_markup=admin_vpn_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "vpn_add_stock")
async def vpn_add_stock_start(call: CallbackQuery, state: FSMContext):
    vpn_products = [
        ("vpn_express", "🔑 ExpressVPN (Email+Pass)"),
        ("vpn_hma", "🔑 HMA VPN (Key Only)"),
        ("vpn_vpnip", "🔑 VPN IP (Email+Pass)"),
        ("vpn_vanish", "🔑 Vanish VPN (Email+Pass)"),
        ("vpn_proton", "🔑 Proton VPN (Email+Pass)"),
        ("proxy_dedicated", "🌐 Proxy (Key Only)"),
        ("vps_basic", "🖥️ Basic VPS (Email+Pass)"),
        ("vps_premium", "️ Premium VPS (Email+Pass)")
    ]
    
    kb = InlineKeyboardBuilder()
    for pid, name in vpn_products:
        kb.row(InlineKeyboardButton(text=name, callback_data=f"vpnstock_{pid}"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_vpn_stock"))
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ➕ *Add VPN Stock*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📝 Select product:"
    
    await call.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.stock_product)

@dp.callback_query(lambda c: c.data.startswith("vpnstock_"))
async def vpn_stock_product_selected(call: CallbackQuery, state: FSMContext):
    pid = call.data.split("_")[1]
    prod = db.get_product(pid)
    
    await state.update_data(stock_product_id=pid, stock_type=prod["stock_type"])
    
    if prod["stock_type"] == "key_only":
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ➕ *Add {prod['name']} Stock*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Send keys (one per line)\n"
        txt += f"📎 Or send a text file"
    else:
        txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ➕ *Add {prod['name']} Stock*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"📝 Send in format:\n"
        txt += f"`email:password`\n"
        txt += f"or `email|password`\n\n"
        txt += f"📎 Or send a text file"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=" Back", callback_data="vpn_add_stock")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.stock_data)

@dp.message(Admin.stock_data, F.text)
async def vpn_stock_data_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_product_id"]
    stock_type = data["stock_type"]
    
    lines = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    
    for line in lines:
        if stock_type == "key_only":
            db.add_vpn_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            # Parse email:password or email|password
            if ":" in line:
                email, password = line.split(":", 1)
            elif "|" in line:
                email, password = line.split("|", 1)
            else:
                continue
            
            db.add_vpn_stock(pid, "email_pass", email=email.strip(), password=password.strip())
            added += 1
    
    txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✅ *Stock Added!*\n"
    txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Product: {pid}\n"
    txt += f"📊 Added: {added} items"
    
    await msg.answer(txt, reply_markup=admin_vpn_stock_kb(), parse_mode="Markdown")
    await state.clear()

@dp.message(Admin.stock_data, F.document)
async def vpn_stock_data_file(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    pid = data["stock_product_id"]
    stock_type = data["stock_type"]
    
    try:
        file = await bot.get_file(msg.document.file_id)
        file_data = await bot.download_file(file.file_path)
        content = file_data.read().decode('utf-8')
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        
        added = 0
        for line in lines:
            if stock_type == "key_only":
                db.add_vpn_stock(pid, "key_only", key_data=line)
                added += 1
            else:
                if ":" in line:
                    email, password = line.split(":", 1)
                elif "|" in line:
                    email, password = line.split("|", 1)
                else:
                    continue
                
                db.add_vpn_stock(pid, "email_pass", email=email.strip(), password=password.strip())
                added += 1
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Stock Added from File!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Product: {pid}\n"
        txt += f"📊 Added: {added} items"
        
        await msg.answer(txt, reply_markup=admin_vpn_stock_kb(), parse_mode="Markdown")
    
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "vpn_delete_stock")
async def vpn_delete_stock(call: CallbackQuery):
    stock = db.get_all_vpn_stock()
    
    if not stock:
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   🗑️ *Delete Stock*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += "No stock to delete"
        return await call.message.edit_text(txt, reply_markup=admin_vpn_stock_kb(), parse_mode="Markdown")
    
    kb = InlineKeyboardBuilder()
    for s in stock[:15]:
        status = "✅" if s['is_used'] else "📦"
        display = s['key_data'] or s['email'] or "N/A"
        kb.row(InlineKeyboardButton(
            text=f"{status} #{s['id']} {display[:20]}...",
            callback_data=f"delvpnstock_{s['id']}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_vpn_stock"))
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   🗑️ *Select Stock to Delete*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delvpnstock_"))
async def del_vpn_stock(call: CallbackQuery):
    sid = int(call.data.split("_")[1])
    db.delete_vpn_stock(sid)
    
    await call.answer("✅ Deleted")
    await vpn_delete_stock(call)

# ─── PRODUCT MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_product_manage")
async def product_manage_menu(call: CallbackQuery):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   📦 *Product Management*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
    
    await call.message.edit_text(txt, reply_markup=admin_product_manage_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "edit_price")
async def edit_price_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✏️ *Edit Price*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📝 Send Product ID:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_product_manage")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.edit_price_pid)

@dp.message(Admin.edit_price_pid)
async def edit_price_pid(msg: Message, state: FSMContext):
    pid = msg.text.strip()
    prod = db.get_product(pid)
    
    if not prod:
        return await msg.answer("❌ Product not found")
    
    await state.update_data(edit_pid=pid)
    
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✏️ *Edit Price*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📦 Product: {prod['name']}\n"
    txt += f"💰 Current Price: ৳{prod['price']:,.0f}\n\n"
    txt += f"📝 Send new price:"
    
    await msg.answer(txt, parse_mode="Markdown")
    await state.set_state(Admin.edit_price_new)

@dp.message(Admin.edit_price_new)
async def edit_price_new(msg: Message, state: FSMContext):
    try:
        new_price = float(msg.text)
        data = await state.get_data()
        pid = data["edit_pid"]
        
        db.update_product_price(pid, new_price)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Price Updated!*\n"
        txt += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" Product: {pid}\n"
        txt += f"💰 New Price: {new_price:,.0f}"
        
        await msg.answer(txt, reply_markup=admin_product_manage_kb(), parse_mode="Markdown")
    
    except:
        await msg.answer("❌ Invalid price")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "add_product")
async def add_product_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ➕ *Add Product*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📝 Send subcategory:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_product_manage")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.add_product_subcat)

@dp.message(Admin.add_product_subcat)
async def add_product_subcat(msg: Message, state: FSMContext):
    await state.update_data(add_subcat=msg.text.strip())
    await msg.answer(" Send product ID:")
    await state.set_state(Admin.add_product_id)

@dp.message(Admin.add_product_id)
async def add_product_id(msg: Message, state: FSMContext):
    await state.update_data(add_pid=msg.text.strip())
    await msg.answer("📝 Send product name:")
    await state.set_state(Admin.add_product_name)

@dp.message(Admin.add_product_name)
async def add_product_name(msg: Message, state: FSMContext):
    await state.update_data(add_pname=msg.text.strip())
    await msg.answer("📝 Send price:")
    await state.set_state(Admin.add_product_price)

@dp.message(Admin.add_product_price)
async def add_product_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text)
        data = await state.get_data()
        
        db.add_product(
            data["add_pid"],
            data["add_subcat"],
            data["add_pname"],
            price
        )
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Product Added!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"📦 ID: {data['add_pid']}\n"
        txt += f"📝 Name: {data['add_pname']}\n"
        txt += f" Price: ৳{price:,.0f}"
        
        await msg.answer(txt, reply_markup=admin_product_manage_kb(), parse_mode="Markdown")
    
    except:
        await msg.answer("❌ Invalid price")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "delete_product")
async def delete_product_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   🗑️ *Delete Product*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f"📝 Send Product ID:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_product_manage")]
    ]), parse_mode="Markdown")

@dp.message(lambda m: m.text and m.text.startswith("/delproduct_"))
async def delete_product_do(msg: Message):
    pid = msg.text.replace("/delproduct_", "").strip()
    db.delete_product(pid)
    await msg.answer(f"✅ Deleted {pid}")

@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ⛔ *Ban User*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Send User ID to ban:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, True)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ⛔ *User Banned!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f" User ID: {uid}"
        
        await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            await bot.send_message(uid, "❌ You have been banned from using this bot.")
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid User ID")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   ✅ *Unban User*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Send User ID to unban:"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, False)
        
        txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *User Unbanned!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
        txt += f"👤 User ID: {uid}"
        
        await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            await bot.send_message(uid, "✅ You have been unbanned! Welcome back!")
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid User ID")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_restore")
async def restore_start(call: CallbackQuery, state: FSMContext):
    txt = f"╭━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
    txt += f"   💾 *Restore Database*\n"
    txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
    txt += f" Send .db file to restore"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]), parse_mode="Markdown")
    await state.set_state(Admin.restore_db)

@dp.message(Admin.restore_db, F.document)
async def restore_db(msg: Message, state: FSMContext, bot: Bot):
    doc = msg.document
    
    if not doc.file_name.endswith('.db'):
        return await msg.answer("❌ Only .db files are supported")
    
    await msg.answer("⏳ Restoring database...")
    
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, db.path)
        db._init()
        
        txt = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╮\n"
        txt += f"   ✅ *Database Restored!*\n"
        txt += f"╰━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╯"
        
        await msg.answer(txt, reply_markup=admin_kb(), parse_mode="Markdown")
    
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    
    await state.clear()

# ─── MAIN ───
async def main():
    print("🚀 Bot is running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
