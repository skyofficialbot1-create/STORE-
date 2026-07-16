#!/usr/bin/env python3
import asyncio, os, sys, sqlite3
from datetime import datetime
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import Message, CallbackQuery
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError:
    print("pip install aiogram")
    sys.exit(1)

BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
SUPPORT_USERNAME = "FBSKYSUPPORT"

# ═══════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════
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
            c.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT, username TEXT,
                balance REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS orders(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, product_id TEXT,
                product_name TEXT, category_id TEXT,
                amount REAL, user_input TEXT,
                payment_method TEXT, transaction_id TEXT,
                status TEXT DEFAULT 'pending',
                delivery_photo TEXT, note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount REAL,
                type TEXT, method TEXT,
                trx_id TEXT, note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS categories(
                id TEXT PRIMARY KEY,
                parent_id TEXT, name TEXT,
                description TEXT, sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS products(
                id TEXT PRIMARY KEY,
                category_id TEXT, name TEXT,
                price REAL, bonus REAL DEFAULT 0,
                stock_type TEXT,
                expiry_days INTEGER DEFAULT 30,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )""")
            c.execute("""CREATE TABLE IF NOT EXISTS stock(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT, stock_type TEXT,
                email TEXT, password TEXT,
                key_data TEXT, expiry_days INTEGER DEFAULT 30,
                is_used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            self._seed_if_empty()
    
    def _seed_if_empty(self):
        with self._conn() as c:
            count = c.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
            if count > 0:
                return
            # Only seed if completely empty
            mains = [
                ("freefire", None, "🔥 Free Fire BD", "Diamonds, Weekly, Lite, Likes"),
                ("subscriptions", None, " Premium Subscriptions", "Netflix, YouTube, Crunchyroll"),
                ("vpn_plus", None, " VPN Plus", "ExpressVPN, HMA, Proxy, VPS"),
                ("topup", None, "💰 Wallet Top-Up", "Add balance instantly")
            ]
            for cid, pid, name, desc in mains:
                c.execute("INSERT INTO categories(id,parent_id,name,description) VALUES(?,?,?,?)",
                         (cid, pid, name, desc))
            
            subs = [
                ("ff_diamonds", "freefire", "💎 Diamonds"),
                ("ff_weekly", "freefire", "📆 Weekly"),
                ("ff_lite", "freefire", "⭐ Weekly Lite"),
                ("ff_like", "freefire", "❤️ Like Service"),
                ("netflix", "subscriptions", " Netflix Premium"),
                ("youtube", "subscriptions", "▶️ YouTube Premium"),
                ("crunchyroll", "subscriptions", "🍿 Crunchyroll")
            ]
            for cid, pid, name in subs:
                c.execute("INSERT INTO categories(id,parent_id,name) VALUES(?,?,?)", (cid, pid, name))
            
            prods = [
                ("ff_25d","ff_diamonds","💎 25 Diamond",20,0,None,30),
                ("ff_50d","ff_diamonds","💎 50 Diamond",35,0,None,30),
                ("ff_115d","ff_diamonds","💎 115 Diamond",79,0,None,30),
                ("ff_240d","ff_diamonds","💎 240 Diamond",156,0,None,30),
                ("ff_355d","ff_diamonds","💎 355 Diamond",237,0,None,30),
                ("ff_505d","ff_diamonds","💎 505 Diamond",336,0,None,30),
                ("ff_610d","ff_diamonds","💎 610 Diamond",390,0,None,30),
                ("ff_850d","ff_diamonds","💎 850 Diamond",558,0,None,30),
                ("ff_1090d","ff_diamonds"," 1090 Diamond",716,0,None,30),
                ("ff_1240d","ff_diamonds","💎 1240 Diamond",795,0,None,30),
                ("ff_2530d","ff_diamonds","💎 2530 Diamond",1580,0,None,30),
                ("ff_5060d","ff_diamonds","💎 5060 Diamond",3160,0,None,30),
                ("ffw_1","ff_weekly","📆 1x Weekly",155,0,None,7),
                ("ffw_2","ff_weekly","📆 2x Weekly",310,0,None,14),
                ("ffw_3","ff_weekly"," 3x Weekly",465,0,None,21),
                ("ffw_5","ff_weekly","📆 5x Weekly",775,0,None,35),
                ("ffw_m","ff_weekly","📆 Monthly",765,0,None,30),
                ("ffw_2m","ff_weekly","📆 2x Monthly",1540,0,None,60),
                ("ffw_3m","ff_weekly"," 3x Monthly",2295,0,None,90),
                ("ffw_5m","ff_weekly","📆 5x Monthly",3825,0,None,150),
                ("ffl_1","ff_lite","⭐ 1x Weekly Lite",40,0,None,7),
                ("ffl_2","ff_lite","⭐ 2x Weekly Lite",80,0,None,14),
                ("ffl_3","ff_lite","⭐ 3x Weekly Lite",120,0,None,21),
                ("ffl_5","ff_lite","⭐ 5x Weekly Lite",200,0,None,35),
                ("fflk_200","ff_like","❤️ 200 Likes",20,0,None,30),
                ("fflk_1000","ff_like","❤️ 1000 Likes",100,0,None,30),
                ("fflk_2000","ff_like","❤️ 2000 Likes",200,0,None,30),
                ("fflk_5000","ff_like","❤️ 5000 Likes",500,0,None,30),
                ("nf_single","netflix","🎬 Single Profile (1M)",400,0,None,30),
                ("nf_full","netflix","🎬 Full Account (1M)",1830,0,None,30),
                ("yt_1m","youtube","▶️ 1 Month",100,0,None,30),
                ("yt_3m","youtube","▶️ 3 Months",200,0,None,90),
                ("yt_6m","youtube","▶️ 6 Months",300,0,None,180),
                ("yt_1y","youtube","▶️ 1 Year",490,0,None,365),
                ("cr_shared","crunchyroll","🍿 Shared (1M)",200,0,None,30),
                ("cr_full1","crunchyroll","🍿 Full (1M)",450,0,None,30),
                ("cr_full12","crunchyroll","🍿 Full (12M)",1840,0,None,365),
                ("vpn_express","vpn_plus","🔑 ExpressVPN (1M)",350,0,"email_pass",30),
                ("vpn_hma","vpn_plus","🔑 HMA VPN (1M)",250,0,"key_only",30),
                ("vpn_vpnip","vpn_plus","🔑 VPN IP (1M)",300,0,"email_pass",30),
                ("vpn_vanish","vpn_plus","🔑 Vanish VPN (1M)",280,0,"email_pass",30),
                ("vpn_proton","vpn_plus","🔑 Proton VPN (1M)",320,0,"email_pass",30),
                ("proxy_dedicated","vpn_plus","🌐 Dedicated Proxy IP (1M)",200,0,"key_only",30),
                ("vps_basic","vpn_plus","️ Basic VPS (1M)",800,0,"email_pass",30),
                ("vps_premium","vpn_plus","🖥️ Premium VPS (1M)",1500,0,"email_pass",30),
                ("bal_100","topup","💰 100 Tk",100,0,None,0),
                ("bal_200","topup","💰 200 Tk (+5 Bonus)",200,5,None,0),
                ("bal_500","topup"," 500 Tk (+20 Bonus)",500,20,None,0),
                ("bal_1000","topup","💰 1000 Tk (+50 Bonus)",1000,50,None,0),
                ("bal_2000","topup"," 2000 Tk (+120 Bonus)",2000,120,None,0),
                ("bal_5000","topup","💰 5000 Tk (+350 Bonus)",5000,350,None,0),
            ]
            for pid, catid, name, price, bonus, stype, exp in prods:
                c.execute("""INSERT INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) 
                             VALUES(?,?,?,?,?,?,?)""", (pid, catid, name, price, bonus, stype, exp))
    
    # ─── USER ───
    def get_user(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        return dict(r) if r else None
    
    def create_user(self, uid, fn, un):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id,first_name,username) VALUES(?,?,?)", (uid, fn, un))
    
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
    
    def get_all_users(self):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
        return [dict(r) for r in rows]
    
    def add_transaction(self, uid, amt, typ, method, trid, note=""):
        with self._conn() as c:
            c.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note) VALUES(?,?,?,?,?,?)",
                     (uid, amt, typ, method, trid, note))
    
    # ─── CATEGORIES ───
    def get_main_categories(self):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY sort_order, id").fetchall()
        return [dict(r) for r in rows]
    
    def get_subcategories(self, parent_id):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM categories WHERE parent_id=? AND is_active=1 ORDER BY sort_order, id", (parent_id,)).fetchall()
        return [dict(r) for r in rows]
    
    def get_category(self, cid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM categories WHERE id=?", (cid,)).fetchone()
        return dict(r) if r else None
    
    def add_category(self, cid, parent_id, name, desc=""):
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO categories(id,parent_id,name,description) VALUES(?,?,?,?)",
                     (cid, parent_id, name, desc))
    
    def delete_category(self, cid):
        with self._conn() as c:
            c.execute("UPDATE categories SET is_active=0 WHERE id=?", (cid,))
            c.execute("UPDATE products SET is_active=0 WHERE category_id=?", (cid,))
    
    def update_category(self, cid, name=None, desc=None):
        with self._conn() as c:
            if name:
                c.execute("UPDATE categories SET name=? WHERE id=?", (name, cid))
            if desc is not None:
                c.execute("UPDATE categories SET description=? WHERE id=?", (desc, cid))
    
    # ─── PRODUCTS ───
    def get_product(self, pid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
        return dict(r) if r else None
    
    def get_products(self, category_id):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM products WHERE category_id=? AND is_active=1 ORDER BY sort_order, price", (category_id,)).fetchall()
        return [dict(r) for r in rows]
    
    def add_product(self, pid, category_id, name, price, bonus=0, stock_type=None, expiry_days=30):
        with self._conn() as c:
            c.execute("""INSERT OR REPLACE INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) 
                         VALUES(?,?,?,?,?,?,?)""",
                     (pid, category_id, name, price, bonus, stock_type, expiry_days))
    
    def update_product(self, pid, name=None, price=None, bonus=None, stock_type=None, expiry_days=None):
        with self._conn() as c:
            if name:
                c.execute("UPDATE products SET name=? WHERE id=?", (name, pid))
            if price is not None:
                c.execute("UPDATE products SET price=? WHERE id=?", (price, pid))
            if bonus is not None:
                c.execute("UPDATE products SET bonus=? WHERE id=?", (bonus, pid))
            if stock_type:
                c.execute("UPDATE products SET stock_type=? WHERE id=?", (stock_type, pid))
            if expiry_days is not None:
                c.execute("UPDATE products SET expiry_days=? WHERE id=?", (expiry_days, pid))
    
    def delete_product(self, pid):
        with self._conn() as c:
            c.execute("UPDATE products SET is_active=0 WHERE id=?", (pid,))
    
    def get_all_products(self):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM products WHERE is_active=1 ORDER BY category_id, sort_order").fetchall()
        return [dict(r) for r in rows]
    
    # ─── ORDERS ───
    def add_order(self, uid, pid, pname, catid, amt, uinput, pmethod, trid):
        with self._conn() as c:
            cur = c.execute("""INSERT INTO orders(user_id,product_id,product_name,category_id,amount,user_input,payment_method,transaction_id) 
                              VALUES(?,?,?,?,?,?,?,?)""",
                           (uid, pid, pname, catid, amt, uinput, pmethod, trid))
            return cur.lastrowid
    
    def update_order(self, oid, status, photo="", note=""):
        with self._conn() as c:
            c.execute("UPDATE orders SET status=?,delivery_photo=?,note=? WHERE id=?", (status, photo, note, oid))
    
    def get_order(self, oid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        return dict(r) if r else None
    
    def get_user_orders(self, uid, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (uid, limit)).fetchall()
        return [dict(r) for r in rows]
    
    def get_all_orders(self, status=None, limit=50):
        with self._conn() as c:
            if status:
                rows = c.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT ?", (status, limit)).fetchall()
            else:
                rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    
    def pending_count(self):
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM orders WHERE status='pending'").fetchone()[0]
    
    # ─── STOCK ───
    def add_stock(self, product_id, stock_type, email=None, password=None, key_data=None, expiry_days=30):
        with self._conn() as c:
            c.execute("""INSERT INTO stock(product_id,stock_type,email,password,key_data,expiry_days) 
                         VALUES(?,?,?,?,?,?)""",
                     (product_id, stock_type, email, password, key_data, expiry_days))
    
    def get_available_stock(self, product_id):
        with self._conn() as c:
            r = c.execute("SELECT * FROM stock WHERE product_id=? AND is_used=0 ORDER BY id LIMIT 1", (product_id,)).fetchone()
            if r:
                c.execute("UPDATE stock SET is_used=1 WHERE id=?", (r["id"],))
                return dict(r)
            return None
    
    def get_stock_counts(self):
        with self._conn() as c:
            rows = c.execute("""SELECT product_id, stock_type, COUNT(*) as cnt 
                               FROM stock WHERE is_used=0 GROUP BY product_id""").fetchall()
        return [dict(r) for r in rows]
    
    def get_all_stock(self, product_id=None):
        with self._conn() as c:
            if product_id:
                rows = c.execute("SELECT * FROM stock WHERE product_id=? ORDER BY id DESC LIMIT 100", (product_id,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM stock ORDER BY product_id, id DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]
    
    def delete_stock(self, sid):
        with self._conn() as c:
            c.execute("DELETE FROM stock WHERE id=?", (sid,))

db = DB()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

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
    ban_uid = State()
    unban_uid = State()
    restore_db = State()
    # Category
    addcat_parent = State()
    addcat_id = State()
    addcat_name = State()
    addcat_desc = State()
    editcat_id = State()
    editcat_name = State()
    editcat_desc = State()
    # Product
    addprod_cat = State()
    addprod_id = State()
    addprod_name = State()
    addprod_price = State()
    addprod_bonus = State()
    addprod_expiry = State()
    addprod_stocktype = State()
    editprod_pid = State()
    editprod_field = State()
    editprod_value = State()
    # Stock
    stock_pid = State()
    stock_data = State()
    stock_days = State()

def fmt(amount):
    return f"৳{amount:,.0f}"

def box(title, lines):
    w = 38
    txt = f"┌{'─' * w}┐\n"
    txt += f"│ {title:^{w}} │\n"
    txt += f"├{'─' * w}┤\n"
    for line in lines:
        txt += f"│ {line:<{w}} │\n"
    txt += f"└{'─' * w}┘"
    return txt

WELCOME = """
╭─────────────────────────────╮
│   🌟  SKY STORE BD  🌟      │
│   ⚡ Premium Digital Store   │
─────────────────────────────┤
│   Free Fire • 💎 Diamonds │
│   Netflix • ▶️ YouTube     │
│  🌐 VPN Plus • 💰 Top-Up    │
├─────────────────────────────┤
│  📞 Support: @FBSKYSUPPORT  │
│  ⚡ Instant • 🛡️ Trusted    │
╰─────────────────────────────╯

👇 Select a category to start!
"""

# ═══════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════
def main_menu(uid):
    kb = InlineKeyboardBuilder()
    for cat in db.get_main_categories():
        kb.row(InlineKeyboardButton(text=cat["name"], callback_data=f"cat_{cat['id']}"))
    kb.row(
        InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💰 My Wallet", callback_data="my_wallet")
    )
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

def products_kb(cat_id):
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    for p in prods:
        if p.get("bonus", 0) > 0:
            txt = f"{p['name']} (+{fmt(p['bonus'])}) — {fmt(p['price'])}"
        else:
            txt = f"{p['name']} — {fmt(p['price'])}"
        kb.row(InlineKeyboardButton(text=txt, callback_data=f"order_{p['id']}"))
    if cat_id in ADMIN_IDS or True:  # show add button for everyone, admin-only logic in handler
        pass
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💰 Wallet Balance", callback_data="pay_wallet"))
    kb.row(
        InlineKeyboardButton(text=" bKash", callback_data="pay_bkash"),
        InlineKeyboardButton(text="💳 Nagad", callback_data="pay_nagad")
    )
    kb.row(InlineKeyboardButton(text="💳 Rocket", callback_data="pay_rocket"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"))
    kb.row(
        InlineKeyboardButton(text="📦 All Orders", callback_data="admin_orders"),
        InlineKeyboardButton(text=" Users", callback_data="admin_users")
    )
    kb.row(
        InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"),
        InlineKeyboardButton(text="📦 Deliver", callback_data="admin_deliver")
    )
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(
        InlineKeyboardButton(text="📂 Categories", callback_data="admin_cats"),
        InlineKeyboardButton(text="📦 Products", callback_data="admin_prods")
    )
    kb.row(
        InlineKeyboardButton(text="🔑 Stock Manage", callback_data="admin_stock"),
        InlineKeyboardButton(text="✏️ Edit Product", callback_data="admin_editprod")
    )
    kb.row(
        InlineKeyboardButton(text="⛔ Ban", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban", callback_data="admin_unban")
    )
    kb.row(InlineKeyboardButton(text=" Restore DB", callback_data="admin_restore"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ Pending", callback_data="orders_pending"))
    kb.row(InlineKeyboardButton(text="✅ Delivered", callback_data="orders_delivered"))
    kb.row(InlineKeyboardButton(text="❌ Cancelled", callback_data="orders_cancelled"))
    kb.row(InlineKeyboardButton(text="📋 All", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_main_categories():
        kb.row(InlineKeyboardButton(text=cat["name"], callback_data=f"admincat_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Add Main Category", callback_data="addcat_root"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_prods_kb():
    kb = InlineKeyboardBuilder()
    cats = db.get_main_categories()
    for cat in cats:
        subs = db.get_subcategories(cat["id"])
        if subs:
            for s in subs:
                kb.row(InlineKeyboardButton(text=f"  └ {s['name']}", callback_data=f"adminprods_{s['id']}"))
        else:
            kb.row(InlineKeyboardButton(text=f"  └ {cat['name']}", callback_data=f"adminprods_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="stock_status"))
    kb.row(InlineKeyboardButton(text="➕ Add Stock", callback_data="stock_add"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Stock", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def edit_product_kb(pid):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Edit Name", callback_data=f"editprod_field_{pid}_name"))
    kb.row(InlineKeyboardButton(text="💰 Edit Price", callback_data=f"editprod_field_{pid}_price"))
    kb.row(InlineKeyboardButton(text="🎁 Edit Bonus", callback_data=f"editprod_field_{pid}_bonus"))
    kb.row(InlineKeyboardButton(text="⏰ Edit Expiry Days", callback_data=f"editprod_field_{pid}_expiry"))
    kb.row(InlineKeyboardButton(text=" Edit Stock Type", callback_data=f"editprod_field_{pid}_stocktype"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Product", callback_data=f"delprod_{pid}"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_editprod"))
    return kb.as_markup()

# ═══════════════════════════════════════
# USER COMMANDS
# ═══════════════════════════════════════
@dp.message(CommandStart())
async def start(msg: Message):
    user = msg.from_user
    db.create_user(user.id, user.first_name, user.username)
    await msg.answer(WELCOME, reply_markup=main_menu(user.id))

@dp.callback_query(lambda c: c.data == "main_menu")
async def go_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu(call.from_user.id))

@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def view_category(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[4:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    await state.update_data(view_cat=cat_id)
    subs = db.get_subcategories(cat_id)
    prods = db.get_products(cat_id)
    if subs:
        kb = InlineKeyboardBuilder()
        for s in subs:
            kb.row(InlineKeyboardButton(text=s["name"], callback_data=f"cat_{s['id']}"))
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
        lines = [f"📂 {cat['name']}", "", "Select a subcategory:"]
        await call.message.edit_text(box("Category", lines), reply_markup=kb.as_markup())
    elif prods:
        lines = [f"📦 {cat['name']}", f"Total: {len(prods)} products"]
        await call.message.edit_text(box("Products", lines), reply_markup=products_kb(cat_id))
    else:
        lines = [f" {cat['name']}", "", "No products yet."]
        await call.message.edit_text(box("Empty", lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="main_menu")]
        ]))

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    await state.update_data(order_pid=pid, order_prod=prod)
    cat_id = prod["category_id"]
    if cat_id == "topup":
        await state.update_data(user_input="Wallet TopUp")
        lines = [f"📦 {prod['name']}", f"💰 Price: {fmt(prod['price'])}"]
        if prod.get("bonus", 0) > 0:
            lines.append(f"🎁 Bonus: +{fmt(prod['bonus'])}")
        lines.extend(["", "Select payment method:"])
        await call.message.edit_text(box("Payment", lines), reply_markup=payment_kb())
        await state.set_state(Order.payment)
        return
    if cat_id == "vpn_plus":
        lines = [f"📦 {prod['name']}", f"💰 Price: {fmt(prod['price'])}", f"⏰ Valid: {prod.get('expiry_days', 30)} days", "", "🌍 Enter server location", "(or type 'auto')"]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="⚡ Auto", callback_data="vpn_auto"))
        kb.row(InlineKeyboardButton(text=" Back", callback_data="main_menu"))
        await call.message.edit_text(box("VPN Config", lines), reply_markup=kb.as_markup())
        await state.set_state(Order.input)
        return
    prompt = " Enter your Player ID:" if "ff_" in cat_id else "📧 Enter your Email:"
    lines = [f"📦 {prod['name']}", f"💰 Price: {fmt(prod['price'])}", "", prompt]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
    await call.message.edit_text(box("Order Info", lines), reply_markup=kb.as_markup())
    await state.set_state(Order.input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [f"📦 {prod['name']}", f"🌍 Server: Auto", f"💰 Price: {fmt(prod['price'])}", "", "Select payment method:"]
    await call.message.edit_text(box("Payment", lines), reply_markup=payment_kb())
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please enter valid details")
    await state.update_data(user_input=text)
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [f"📦 {prod['name']}", f"💰 Price: {fmt(prod['price'])}", "", "Select payment method:"]
    await msg.answer(box("Payment", lines), reply_markup=payment_kb())
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def pay_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data[4:]
    await state.update_data(pay_method=method)
    data = await state.get_data()
    prod = data["order_prod"]
    price = prod["price"]
    uid = call.from_user.id
    if method == "wallet":
        bal = db.get_balance(uid)
        if bal < price:
            lines = ["❌ Insufficient Balance", "", f"Need: {fmt(price)}", f"Have: {fmt(bal)}"]
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="💰 Top Up", callback_data="cat_topup"))
            kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment"))
            await call.message.edit_text(box("Error", lines), reply_markup=kb.as_markup())
            return
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    else:
        nums = {"bkash": "01742958563", "nagad": "01748506069", "rocket": "01742958563"}
        lines = [f"💰 Amount: {fmt(price)}", f"📱 Method: {method.upper()}", f"🔢 Number: {nums.get(method, '')}", "", "Send payment & enter TrxID:"]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment"))
        await call.message.edit_text(box("Send Payment", lines), reply_markup=kb.as_markup())
        await state.set_state(Order.trxid)

async def process_payment(call_or_msg, state: FSMContext, pmethod, trx):
    data = await state.get_data()
    prod = data["order_prod"]
    cat_id = prod["category_id"]
    uinput = data.get("user_input", "")
    uid = call_or_msg.from_user.id
    price = prod["price"]
    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price):
            return
    oid = db.add_order(uid, prod["id"], prod["name"], cat_id, price, uinput, pmethod, trx)
    if cat_id == "topup":
        bonus = prod.get("bonus", 0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        bal = db.get_balance(uid)
        lines = ["✅ Top-Up Successful!", "", f"Added: {fmt(total)}"]
        if bonus > 0:
            lines.append(f"🎁 Bonus: +{fmt(bonus)}")
        lines.append(f"💳 Balance: {fmt(bal)}")
        await call_or_msg.message.edit_text(box("Success", lines), reply_markup=main_menu(uid))
    elif cat_id == "vpn_plus":
        stock = db.get_available_stock(prod["id"])
        if stock:
            db.update_order(oid, "delivered")
            if stock["stock_type"] == "key_only":
                lines = ["✅ VPN Delivered!", "", f" Key: {stock['key_data']}", f"🌍 Server: {uinput or 'Auto'}", f"⏰ Expires: {stock['expiry_days']} days"]
            else:
                lines = ["✅ VPN Delivered!", "", f" Email: {stock['email']}", f" Password: {stock['password']}", f"🌍 Server: {uinput or 'Auto'}", f"⏰ Expires: {stock['expiry_days']} days"]
            await call_or_msg.message.edit_text(box("Success", lines), reply_markup=main_menu(uid))
        else:
            db.update_order(oid, "pending")
            lines = [" Order Placed!", "", f"Order ID: #{oid}", "Status: Pending (No Stock)", "Admin will deliver soon"]
            await call_or_msg.message.edit_text(box("Pending", lines), reply_markup=main_menu(uid))
    else:
        db.update_order(oid, "pending")
        lines = ["✅ Order Placed!", "", f"Order ID: #{oid}", "Status: Pending Verification"]
        await call_or_msg.message.edit_text(box("Success", lines), reply_markup=main_menu(uid))
    user = db.get_user(uid)
    order = db.get_order(oid)
    admin_lines = [f"🆔 Order: #{oid}", f"👤 User: {uid}", f"📛 Name: {user['first_name']}", f"📦 Product: {prod['name']}", f"💰 Amount: {fmt(price)}", f"📝 Input: {uinput}", f"💳 Payment: {pmethod}", f"🔢 TrxID: {trx}", f"⏰ {order['created_at']}"]
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, box(" NEW ORDER", admin_lines), reply_markup=kb.as_markup())
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
    await process_payment(msg, state, mn, trx)

@dp.callback_query(lambda c: c.data == "back_to_payment")
async def back_pay(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [f"📦 {prod['name']}", f"💰 Price: {fmt(prod['price'])}", "", "Select payment method:"]
    await call.message.edit_text(box("Payment", lines), reply_markup=payment_kb())
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data == "back_to_products")
async def back_prod(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    cat_id = data.get("order_prod", {}).get("category_id") if isinstance(data.get("order_prod"), dict) else None
    if cat_id:
        await call.message.edit_text(box("Products", [f"📦 Select a product"]), reply_markup=products_kb(cat_id))
        await state.set_state(None)

@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    bal = db.get_balance(uid)
    lines = [f" Balance: {fmt(bal)}"]
    await call.message.edit_text(box("Your Wallet", lines), reply_markup=main_menu(uid))

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    if not orders:
        lines = ["No orders yet."]
    else:
        lines = []
        for o in orders[:5]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} #{o['id']} {o['product_name'][:25]}")
            lines.append(f"   {fmt(o['amount'])} - {o['status']}")
            lines.append("")
    await call.message.edit_text(box("Your Orders", lines), reply_markup=main_menu(uid))

# ═══════════════════════════════════════
# ADMIN PANEL
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text(box("Admin Panel", ["🔐 Manage your store"]), reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    lines = [f"👥 Users: {len(users)}", f"⏳ Pending: {pending}", "", "🔑 Stock Status:"]
    if stock:
        for s in stock:
            lines.append(f"• {s['product_id']}: {s['cnt']}")
    else:
        lines.append("No stock")
    await call.message.edit_text(box("Dashboard", lines), reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_orders")
async def all_orders_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(box("Orders", [" Select category"]), reply_markup=admin_orders_kb())

@dp.callback_query(lambda c: c.data.startswith("orders_"))
async def orders_by_status(call: CallbackQuery):
    await call.answer()
    status = call.data.split("_")[1]
    if status == "all":
        orders = db.get_all_orders(limit=20)
        title = "All Orders"
    else:
        orders = db.get_all_orders(status, limit=20)
        title = f"{status.capitalize()} Orders"
    if not orders:
        lines = ["No orders found."]
    else:
        lines = []
        for o in orders[:10]:
            emoji = {"pending": "", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "")
            lines.append(f"{emoji} #{o['id']} {o['product_name'][:20]}")
            lines.append(f"   {fmt(o['amount'])} by {o['user_id']}")
            lines.append("")
    await call.message.edit_text(box(title, lines), reply_markup=admin_orders_kb())

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    await call.answer("✅ Approving...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    db.update_order(oid, "delivered")
    lines = [f"✅ Order #{oid} Approved!", f"Status: Delivered"]
    await call.message.edit_text(box("Success", lines), reply_markup=admin_kb())
    try:
        await bot.send_message(order["user_id"], box("Order Delivered", [f"✅ Order #{oid}", f"📦 {order['product_name']}"]))
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer("❌ Rejecting...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    db.update_order(oid, "cancelled")
    lines = [f"❌ Order #{oid} Rejected!", f"Status: Cancelled"]
    await call.message.edit_text(box("Rejected", lines), reply_markup=admin_kb())
    try:
        await bot.send_message(order["user_id"], box("Order Cancelled", [f"❌ Order #{oid}", f"📦 {order['product_name']}"]))
    except:
        pass

@dp.callback_query(lambda c: c.data == "admin_users")
async def users_list(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    lines = []
    for u in users[:15]:
        status = "🔒" if u['is_banned'] else "👤"
        lines.append(f"{status} {u['user_id']} {u['first_name'][:15]}")
        lines.append(f"   Balance: {fmt(u['balance'])}")
        lines.append("")
    if not lines:
        lines = ["No users yet."]
    await call.message.edit_text(box(f"Users ({len(users)})", lines), reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["💰 Send User ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text(box("Add Balance", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        user = db.get_user(uid)
        if not user:
            return await msg.answer("❌ User not found")
        await state.update_data(uid=uid)
        lines = [f"👤 User: {user['first_name']}", f"💳 Current: {fmt(user['balance'])}", "", "Send amount to add:"]
        await msg.answer(box("Add Balance", lines))
        await state.set_state(Admin.addbal_amt)
    except:
        await msg.answer("❌ Invalid User ID")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text)
        data = await state.get_data()
        uid = data["uid"]
        db.update_balance(uid, amt)
        db.add_transaction(uid, amt, "admin_add", "Admin", f"ADMIN_{datetime.now():%Y%m%d%H%M%S}")
        new_bal = db.get_balance(uid)
        lines = ["✅ Balance Added!", "", f"Amount: {fmt(amt)}", f"New Balance: {fmt(new_bal)}", f"Time: {datetime.now():%H:%M}"]
        await msg.answer(box("Success", lines), reply_markup=admin_kb())
        try:
            await bot.send_message(uid, box("Balance Added", [f"💰 Amount: {fmt(amt)}", f"💳 New Balance: {fmt(new_bal)}", f"Added by: Admin"]))
        except:
            pass
    except:
        await msg.answer("❌ Invalid amount")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [" Send Order ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text(box("Deliver Order", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        if not order:
            return await msg.answer("❌ Not found")
        await state.update_data(oid=oid)
        lines = [f"Order #{oid}", f"Product: {order['product_name']}", f"User: {order['user_id']}", f"Amount: {fmt(order['amount'])}", "", "Send photo or type 'done':"]
        await msg.answer(box("Deliver", lines))
        await state.set_state(Admin.deliver_file)
    except:
        await msg.answer("❌ Invalid Order ID")

@dp.message(Admin.deliver_file)
async def deliver_file(msg: Message, state: FSMContext):
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
    lines = [f"✅ Order #{oid} Delivered!"]
    await msg.answer(box("Success", lines), reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📨 Send message to broadcast:"]
    await call.message.edit_text(box("Broadcast", lines))
    await state.set_state(Admin.broadcast_msg)

@dp.message(Admin.broadcast_msg)
async def broadcast_do(msg: Message, state: FSMContext):
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
    lines = [f"✅ Sent to {sent}/{len(users)} users"]
    await msg.answer(box("Broadcast", lines), reply_markup=admin_kb())
    await state.clear()

# ═══════════════════════════════════════
# CATEGORY MANAGEMENT (FULL CRUD)
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(box("Categories", ["📂 Manage categories"]), reply_markup=admin_cats_kb())

@dp.callback_query(lambda c: c.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    cat = db.get_category(cat_id)
    subs = db.get_subcategories(cat_id)
    prods = db.get_products(cat_id)
    lines = [f"📂 {cat['name']}", f"ID: {cat_id}", f"Subcategories: {len(subs)}", f"Products: {len(prods)}"]
    if cat.get("description"):
        lines.append(f"Desc: {cat['description']}")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Subcategory", callback_data=f"addcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="✏️ Edit Category", callback_data=f"editcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="📦 View Products", callback_data=f"adminprods_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Category", callback_data=f"delcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats"))
    await call.message.edit_text(box("Category Details", lines), reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("addcat_"))
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = call.data[7:]
    await state.update_data(addcat_parent=parent_id)
    lines = ["➕ Add New Category", "", "Send category ID (no spaces):", "Example: nord_vpn"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats" if parent_id == "root" else f"admincat_{parent_id}"))
    await call.message.edit_text(box("Add Category", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.addcat_id)

@dp.message(Admin.addcat_id)
async def addcat_id(msg: Message, state: FSMContext):
    cid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addcat_id=cid)
    lines = ["Send category name:", "Example: 🔑 NordVPN"]
    await msg.answer(box("Add Category", lines))
    await state.set_state(Admin.addcat_name)

@dp.message(Admin.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    lines = ["Send description (optional):", "Type 'skip' to skip"]
    await msg.answer(box("Add Category", lines))
    await state.set_state(Admin.addcat_desc)

@dp.message(Admin.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    data = await state.get_data()
    db.add_category(data["addcat_id"], data["addcat_parent"], data["addcat_name"], desc)
    lines = ["✅ Category Added!", "", f"ID: {data['addcat_id']}", f"Name: {data['addcat_name']}"]
    await msg.answer(box("Success", lines), reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_id=cat_id)
    lines = ["✏️ Edit Category", "", "Send new name:", "Type 'skip' to keep current"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"admincat_{cat_id}"))
    await call.message.edit_text(box("Edit Category", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.editcat_name)

@dp.message(Admin.editcat_name)
async def editcat_name(msg: Message, state: FSMContext):
    if msg.text.strip().lower() != "skip":
        data = await state.get_data()
        db.update_category(data["editcat_id"], name=msg.text.strip())
    lines = ["Send new description:", "Type 'skip' to keep current"]
    await msg.answer(box("Edit Category", lines))
    await state.set_state(Admin.editcat_desc)

@dp.message(Admin.editcat_desc)
async def editcat_desc(msg: Message, state: FSMContext):
    data = await state.get_data()
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else None
    if desc is not None:
        db.update_category(data["editcat_id"], desc=desc)
    cat = db.get_category(data["editcat_id"])
    lines = ["✅ Category Updated!", "", f"Name: {cat['name']}"]
    await msg.answer(box("Success", lines), reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer("️ Deleting...")
    cid = call.data[7:]
    db.delete_category(cid)
    lines = [f"🗑️ Category deleted: {cid}"]
    await call.message.edit_text(box("Deleted", lines), reply_markup=admin_cats_kb())

# ═══════════════════════════════════════
# PRODUCT MANAGEMENT (FULL CRUD)
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_prods")
async def admin_prods(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(box("Products", [" Select category"]), reply_markup=admin_prods_kb())

@dp.callback_query(lambda c: c.data.startswith("adminprods_"))
async def admin_prods_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[11:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    lines = [f"📂 {cat['name']}", f"Products: {len(prods)}", ""]
    for p in prods[:10]:
        exp = f" ({p.get('expiry_days', 30)}d)" if p.get('expiry_days') else ""
        lines.append(f"• {p['name']}: {fmt(p['price'])}{exp}")
    if not prods:
        lines.append("No products yet.")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_prods"))
    await call.message.edit_text(box("Products", lines), reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("addprod_"))
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(addprod_cat=cat_id)
    lines = ["➕ Add New Product", "", "Send product ID (no spaces):", "Example: vpn_nord_1m"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"adminprods_{cat_id}"))
    await call.message.edit_text(box("Add Product", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.addprod_id)

@dp.message(Admin.addprod_id)
async def addprod_id(msg: Message, state: FSMContext):
    pid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addprod_id=pid)
    lines = ["Send product name:", "Example: 🔑 NordVPN (1M)"]
    await msg.answer(box("Add Product", lines))
    await state.set_state(Admin.addprod_name)

@dp.message(Admin.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    lines = ["Send price (numbers only):", "Example: 350"]
    await msg.answer(box("Add Product", lines))
    await state.set_state(Admin.addprod_price)

@dp.message(Admin.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        lines = ["Send bonus (0 if none):", "Example: 0 or 20"]
        await msg.answer(box("Add Product", lines))
        await state.set_state(Admin.addprod_bonus)
    except:
        await msg.answer("❌ Invalid price. Send numbers only.")

@dp.message(Admin.addprod_bonus)
async def addprod_bonus(msg: Message, state: FSMContext):
    try:
        bonus = float(msg.text.strip())
        await state.update_data(addprod_bonus=bonus)
        lines = ["Send expiry days (0 if none):", "Example: 30 or 0"]
        await msg.answer(box("Add Product", lines))
        await state.set_state(Admin.addprod_expiry)
    except:
        await msg.answer("❌ Invalid bonus")

@dp.message(Admin.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        await state.update_data(addprod_expiry=expiry)
        data = await state.get_data()
        cat_id = data["addprod_cat"]
        # For VPN category, ask stock type
        if cat_id == "vpn_plus":
            lines = ["Select stock type:", "• email_pass = Email + Password", "• key_only = Key only (HMA style)", "", "Type: email_pass or key_only"]
            await msg.answer(box("Add Product", lines))
            await state.set_state(Admin.addprod_stocktype)
        else:
            db.add_product(data["addprod_id"], cat_id, data["addprod_name"], 
                          data["addprod_price"], data["addprod_bonus"], None, expiry)
            lines = ["✅ Product Added!", "", f"ID: {data['addprod_id']}", f"Name: {data['addprod_name']}", f"Price: {fmt(data['addprod_price'])}", f"Bonus: {fmt(data['addprod_bonus'])}", f"Expiry: {expiry} days"]
            await msg.answer(box("Success", lines), reply_markup=admin_kb())
            await state.clear()
    except:
        await msg.answer("❌ Invalid expiry days")

@dp.message(Admin.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ["email_pass", "key_only"]:
        return await msg.answer("❌ Type 'email_pass' or 'key_only'")
    data = await state.get_data()
    db.add_product(data["addprod_id"], data["addprod_cat"], data["addprod_name"], 
                   data["addprod_price"], data["addprod_bonus"], stype, data["addprod_expiry"])
    lines = ["✅ Product Added!", "", f"ID: {data['addprod_id']}", f"Name: {data['addprod_name']}", f"Price: {fmt(data['addprod_price'])}", f"Stock Type: {stype}", f"Expiry: {data['addprod_expiry']} days"]
    await msg.answer(box("Success", lines), reply_markup=admin_kb())
    await state.clear()

# ═══════════════════════════════════════
# EDIT PRODUCT (FIELD BY FIELD)
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_editprod")
async def editprod_list(call: CallbackQuery):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        lines = ["No products to edit."]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
        return await call.message.edit_text(box("Edit Product", lines), reply_markup=kb.as_markup())
    
    kb = InlineKeyboardBuilder()
    for p in prods[:20]:
        kb.row(InlineKeyboardButton(text=f"✏️ {p['name'][:25]} - {fmt(p['price'])}", callback_data=f"editprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    lines = ["Select product to edit:"]
    await call.message.edit_text(box("Edit Product", lines), reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("editprod_") and not c.data.startswith("editprod_field_") and not c.data.startswith("editprod_del_"))
async def editprod_select(call: CallbackQuery):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod:
        return
    lines = [
        f"📦 {prod['name']}",
        f"ID: {pid}",
        f"💰 Price: {fmt(prod['price'])}",
        f"🎁 Bonus: {fmt(prod.get('bonus', 0))}",
        f" Expiry: {prod.get('expiry_days', 30)} days",
        f"🔄 Stock: {prod.get('stock_type', 'N/A')}",
    ]
    await call.message.edit_text(box("Edit Product", lines), reply_markup=edit_product_kb(pid))

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"))
async def editprod_field(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_")
    # editprod_field_{pid}_{field}
    pid = parts[3]
    field = parts[4]
    await state.update_data(editprod_pid=pid, editprod_field=field)
    
    field_names = {
        "name": "name",
        "price": "price (numbers)",
        "bonus": "bonus (numbers)",
        "expiry": "expiry days (numbers)",
        "stocktype": "stock type (email_pass or key_only)"
    }
    lines = [f"✏️ Edit {field_names.get(field, field)}", "", f"Product: {pid}", "", "Send new value:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"editprod_{pid}"))
    await call.message.edit_text(box("Edit Field", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.editprod_value)

@dp.message(Admin.editprod_value)
async def editprod_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["editprod_pid"]
    field = data["editprod_field"]
    value = msg.text.strip()
    
    try:
        if field == "name":
            db.update_product(pid, name=value)
        elif field == "price":
            db.update_product(pid, price=float(value))
        elif field == "bonus":
            db.update_product(pid, bonus=float(value))
        elif field == "expiry":
            db.update_product(pid, expiry_days=int(value))
        elif field == "stocktype":
            if value not in ["email_pass", "key_only"]:
                return await msg.answer("❌ Must be 'email_pass' or 'key_only'")
            db.update_product(pid, stock_type=value)
        
        # Show updated product
        prod = db.get_product(pid)
        lines = [
            "✅ Product Updated!",
            "",
            f"📦 {prod['name']}",
            f"💰 Price: {fmt(prod['price'])}",
            f"🎁 Bonus: {fmt(prod.get('bonus', 0))}",
            f" Expiry: {prod.get('expiry_days', 30)} days",
            f" Stock: {prod.get('stock_type', 'N/A')}",
        ]
        await msg.answer(box("Success", lines), reply_markup=edit_product_kb(pid))
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]
    db.delete_product(pid)
    lines = [f"️ Product deleted: {pid}"]
    await call.message.edit_text(box("Deleted", lines), reply_markup=admin_kb())

# ═══════════════════════════════════════
# STOCK MANAGEMENT
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text(box("Stock Management", ["🔑 Manage stock"]), reply_markup=admin_stock_kb())

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    if not counts:
        lines = ["No stock available."]
    else:
        lines = []
        for s in counts:
            lines.append(f"📦 {s['product_id']}")
            lines.append(f"   Type: {s['stock_type']}")
            lines.append(f"   Available: {s['cnt']}")
            lines.append("")
    await call.message.edit_text(box("Stock Status", lines), reply_markup=admin_stock_kb())

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["➕ Add Stock", "", "Send Product ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text(box("Add Stock", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.stock_pid)

@dp.message(Admin.stock_pid)
async def stock_pid(msg: Message, state: FSMContext):
    pid = msg.text.strip()
    prod = db.get_product(pid)
    if not prod:
        return await msg.answer("❌ Product not found")
    await state.update_data(stock_pid=pid, stock_type=prod.get("stock_type", "key_only"))
    if prod.get("stock_type") == "key_only":
        lines = [f" {prod['name']}", f"Type: Key Only", "", "Send keys (one per line)", "Or send a .txt file"]
    else:
        lines = [f"📦 {prod['name']}", f"Type: Email + Password", "", "Send in format:", "email:password", "or email|password", "One per line or .txt file"]
    await msg.answer(box("Add Stock", lines))
    await state.set_state(Admin.stock_data)

@dp.message(Admin.stock_data, F.text)
async def stock_data_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_pid"]
    stype = data["stock_type"]
    lines = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    for line in lines:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            if ":" in line:
                email, password = line.split(":", 1)
            elif "|" in line:
                email, password = line.split("|", 1)
            else:
                continue
            db.add_stock(pid, "email_pass", email=email.strip(), password=password.strip())
            added += 1
    lines_msg = ["✅ Stock Added!", "", f"Product: {pid}", f"Added: {added} items", "", "Send expiry days (or 'skip'):"]
    await msg.answer(box("Add Stock", lines_msg))
    await state.set_state(Admin.stock_days)

@dp.message(Admin.stock_data, F.document)
async def stock_data_file(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_pid"]
    stype = data["stock_type"]
    try:
        file = await bot.get_file(msg.document.file_id)
        file_data = await bot.download_file(file.file_path)
        content = file_data.read().decode('utf-8')
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        added = 0
        for line in lines:
            if stype == "key_only":
                db.add_stock(pid, "key_only", key_data=line)
                added += 1
            else:
                if ":" in line:
                    email, password = line.split(":", 1)
                elif "|" in line:
                    email, password = line.split("|", 1)
                else:
                    continue
                db.add_stock(pid, "email_pass", email=email.strip(), password=password.strip())
                added += 1
        lines_msg = ["✅ Stock Added from File!", "", f"Product: {pid}", f"Added: {added} items", "", "Send expiry days (or 'skip'):"]
        await msg.answer(box("Add Stock", lines_msg))
        await state.set_state(Admin.stock_days)
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")

@dp.message(Admin.stock_days)
async def stock_days(msg: Message, state: FSMContext):
    try:
        days = int(msg.text.strip())
    except:
        days = 30
    lines = ["✅ Stock Ready!", "", f"Expiry: {days} days", "Stock is now available for auto-delivery"]
    await msg.answer(box("Success", lines), reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del(call: CallbackQuery):
    await call.answer()
    stock = db.get_all_stock()
    if not stock:
        lines = ["No stock to delete."]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
        return await call.message.edit_text(box("Delete Stock", lines), reply_markup=kb.as_markup())
    kb = InlineKeyboardBuilder()
    for s in stock[:15]:
        status = "✅" if s['is_used'] else "📦"
        display = s['key_data'] or s['email'] or "N/A"
        kb.row(InlineKeyboardButton(
            text=f"{status} #{s['id']} {display[:25]}...",
            callback_data=f"delstock_{s['id']}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    lines = ["️ Select stock to delete:"]
    await call.message.edit_text(box("Delete Stock", lines), reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del(call)

# ═══════════════════════════════════════
# BAN/UNBAN/RESTORE
# ═══════════════════════════════════════
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["⛔ Send User ID to ban:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
    await call.message.edit_text(box("Ban User", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        db.set_ban(uid, True)
        lines = [f" User {uid} banned!"]
        await msg.answer(box("Banned", lines), reply_markup=admin_kb())
        try:
            await bot.send_message(uid, box("Banned", ["❌ You have been banned."]))
        except:
            pass
    except:
        await msg.answer("❌ Invalid User ID")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["✅ Send User ID to unban:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text(box("Unban User", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        db.set_ban(uid, False)
        lines = [f"✅ User {uid} unbanned!"]
        await msg.answer(box("Unbanned", lines), reply_markup=admin_kb())
        try:
            await bot.send_message(uid, box("Unbanned", ["✅ You have been unbanned!"]))
        except:
            pass
    except:
        await msg.answer(" Invalid User ID")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_restore")
async def restore_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["💾 Send .db file to restore:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text(box("Restore DB", lines), reply_markup=kb.as_markup())
    await state.set_state(Admin.restore_db)

@dp.message(Admin.restore_db, F.document)
async def restore_db(msg: Message, state: FSMContext):
    doc = msg.document
    if not doc.file_name.endswith('.db'):
        return await msg.answer("❌ Only .db files")
    await msg.answer("⏳ Restoring...")
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, db.path)
        db._init()
        lines = ["✅ Database restored!"]
        await msg.answer(box("Success", lines), reply_markup=admin_kb())
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

async def main():
    print("🚀 Bot running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
