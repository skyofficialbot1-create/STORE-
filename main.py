#!/usr/bin/env python3
import asyncio, os, sys, sqlite3, json
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, F, BaseMiddleware
    from aiogram.filters import Command, CommandStart
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, TelegramObject
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError:
    print("Installing dependencies...")
    os.system("pip install aiogram")
    sys.exit(1)

# ─── CONFIG ───
BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
SUPPORT_USERNAME = "FBSKYSUPPORT"

# ─── DATABASE ───
class Database:
    def __init__(self, path="store.db"):
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
            # Users
            conn.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT, username TEXT,
                balance REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # Orders
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
            
            # Transactions
            conn.execute("""CREATE TABLE IF NOT EXISTS transactions(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER, amount REAL,
                type TEXT, method TEXT,
                trx_id TEXT, note TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            # Categories
            conn.execute("""CREATE TABLE IF NOT EXISTS categories(
                id TEXT PRIMARY KEY,
                parent_id TEXT, name TEXT,
                description TEXT, icon TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )""")
            
            # Products
            conn.execute("""CREATE TABLE IF NOT EXISTS products(
                id TEXT PRIMARY KEY,
                category_id TEXT, name TEXT,
                price REAL, bonus REAL DEFAULT 0,
                stock_type TEXT,
                expiry_days INTEGER DEFAULT 30,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )""")
            
            # Stock
            conn.execute("""CREATE TABLE IF NOT EXISTS stock(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT, stock_type TEXT,
                email TEXT, password TEXT,
                key_data TEXT, expiry_days INTEGER DEFAULT 30,
                is_used INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
            cur = conn.execute("SELECT COUNT(*) FROM categories")
            if cur.fetchone()[0] == 0:
                self._seed_data(conn)
            
            conn.commit()
    
    def _seed_data(self, conn):
        categories = [
            ("youtube", None, "YouTube Premium", "Ad-free YouTube", "▶️", 1),
            ("netflix", None, "Netflix Premium", "Netflix Accounts", "🎬", 2),
            ("crunchyroll", None, "Crunchyroll", "Anime Streaming", "🍿", 3),
            ("vpn", None, "VPN Services", "Premium VPN Services", "🔐", 4),
            ("proxy", None, "Proxy Services", "Proxy Services", "🌐", 5),
        ]
        for cat in categories:
            conn.execute("""INSERT INTO categories(id,parent_id,name,description,icon,sort_order) 
                           VALUES(?,?,?,?,?,?)""", cat)
        
        products = [
            ("yt_1m", "youtube", "▶️ YouTube Premium 1 Month", 100, 0, "email_pass", 30),
            ("yt_7d", "youtube", "▶️ YouTube Premium 7 Days", 30, 0, "email_pass", 7),
            ("cr_1m", "crunchyroll", "🍿 Crunchyroll 1 Month", 200, 0, "email_pass", 30),
            ("vpn_hma", "vpn", "🚀 HMA VPN 1 Month", 150, 0, "email_pass", 30),
            ("proxy_resi", "proxy", "🌐 Residential Proxy", 500, 0, "key_only", 30),
        ]
        for prod in products:
            conn.execute("""INSERT INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) 
                           VALUES(?,?,?,?,?,?,?)""", prod)
        conn.commit()

    # User methods
    def get_user(self, uid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,))
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
    
    def add_transaction(self, uid, amt, typ, method, trid, note=""):
        with self._get_conn() as conn:
            conn.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note) VALUES(?,?,?,?,?,?)",
                        (uid, amt, typ, method, trid, note))
            conn.commit()
    
    # Category methods
    def get_categories(self, parent_id=None):
        with self._get_conn() as conn:
            if parent_id:
                cur = conn.execute("SELECT * FROM categories WHERE parent_id=? AND is_active=1 ORDER BY sort_order", (parent_id,))
            else:
                cur = conn.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY sort_order")
            return [dict(r) for r in cur.fetchall()]
    
    def get_category(self, cid):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cid,))
            r = cur.fetchone()
            return dict(r) if r else None
    
    def add_category(self, cid, parent_id, name, desc="", icon="", sort=0):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO categories(id,parent_id,name,description,icon,sort_order) VALUES(?,?,?,?,?,?)",
                        (cid, parent_id, name, desc, icon, sort))
            conn.commit()
    
    def delete_category(self, cid):
        with self._get_conn() as conn:
            conn.execute("UPDATE categories SET is_active=0 WHERE id=?", (cid,))
            conn.execute("UPDATE products SET is_active=0 WHERE category_id=?", (cid,))
            conn.commit()
    
    # Product methods
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
            conn.execute("""INSERT OR REPLACE INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) 
                           VALUES(?,?,?,?,?,?,?)""",
                        (pid, category_id, name, price, bonus, stock_type, expiry_days))
            conn.commit()
    
    def update_product(self, pid, **kwargs):
        with self._get_conn() as conn:
            for key, value in kwargs.items():
                if value is not None:
                    conn.execute(f"UPDATE products SET {key}=? WHERE id=?", (value, pid))
            conn.commit()
    
    def delete_product(self, pid):
        with self._get_conn() as conn:
            conn.execute("UPDATE products SET is_active=0 WHERE id=?", (pid,))
            conn.commit()
    
    def get_all_products(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY category_id, sort_order")
            return [dict(r) for r in cur.fetchall()]
    
    # Order methods
    def add_order(self, uid, pid, pname, catid, amt, uinput, pmethod, trid):
        with self._get_conn() as conn:
            cur = conn.execute("""INSERT INTO orders(user_id,product_id,product_name,category_id,amount,user_input,payment_method,transaction_id) 
                                 VALUES(?,?,?,?,?,?,?,?)""",
                              (uid, pid, pname, catid, amt, uinput, pmethod, trid))
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
    
    # Stock methods
    def add_stock(self, product_id, stock_type, email=None, password=None, key_data=None, expiry_days=30):
        with self._get_conn() as conn:
            conn.execute("""INSERT INTO stock(product_id,stock_type,email,password,key_data,expiry_days) 
                           VALUES(?,?,?,?,?,?)""",
                        (product_id, stock_type, email, password, key_data, expiry_days))
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
            cur = conn.execute("""SELECT product_id, stock_type, COUNT(*) as cnt 
                                 FROM stock WHERE is_used=0 GROUP BY product_id""")
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

db = Database()

# ─── BOT SETUP ───
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ─── SECURITY MIDDLEWARE ───
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

# ─── STATES ───
class YTOrder(StatesGroup):
    gmail = State()

class CROrder(StatesGroup):
    gmail = State()
    whatsapp = State()

class DepositState(StatesGroup):
    trxid = State()

class Admin(StatesGroup):
    addbal_uid = State()
    addbal_amt = State()
    deliver_oid = State()
    deliver_file = State()
    broadcast_msg = State()
    ban_uid = State()
    unban_uid = State()
    addcat_id = State()
    addcat_name = State()
    addcat_desc = State()
    editcat_id = State()
    editcat_name = State()
    editcat_desc = State()
    addprod_id = State()
    addprod_name = State()
    addprod_price = State()
    addprod_bonus = State()
    addprod_expiry = State()
    addprod_stocktype = State()
    addprod_select_cat = State()
    editprod_pid = State()
    editprod_field = State()
    editprod_value = State()
    stock_pid = State()
    stock_data = State()

# ─── HELPERS ───
def fmt(amount):
    return f"৳{amount:,.0f}"

WELCOME = """
╭─────────────────────────────╮
│   🌟  SKY STORE BD  🌟      │
│   ⚡ Premium Digital Store   │
├─────────────────────────────┤
│  ▶️ YouTube  •  🎬 Netflix   │
│  🍿 Crunchyroll • 🔐 VPN    │
│        🌐 Proxy             │
├─────────────────────────────┤
│   Support: @FBSKYSUPPORT    │
│  ⚡ Instant  • 🛡️ Trusted    │
╰─────────────────────────────╯

👇 নিচের যেকোনো একটি ক্যাটাগরি বেছে নিন:
"""

# ─── KEYBOARDS (2-COLUMN GRID LAYOUT) ───
def main_menu(uid):
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    
    # 2-Column Grid Layout for Medium & Elegant Look
    for i in range(0, len(cats), 2):
        row_btns = []
        row_btns.append(InlineKeyboardButton(
            text=f"{cats[i].get('icon', '📦')} {cats[i]['name']}",
            callback_data=f"cat_{cats[i]['id']}"
        ))
        if i + 1 < len(cats):
            row_btns.append(InlineKeyboardButton(
                text=f"{cats[i+1].get('icon', '📦')} {cats[i+1]['name']}",
                callback_data=f"cat_{cats[i+1]['id']}"
            ))
        kb.row(*row_btns)
    
    kb.row(
        InlineKeyboardButton(text="📜 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💳 Top-up Balance", callback_data="my_wallet")
    )
    kb.row(InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    
    return kb.as_markup()

def products_kb(cat_id):
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    
    for p in prods:
        txt = f"{p['name']} — {fmt(p['price'])}"
        kb.row(InlineKeyboardButton(text=txt, callback_data=f"order_{p['id']}"))
        
    kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"),
        InlineKeyboardButton(text="📦 Orders", callback_data="admin_orders")
    )
    kb.row(
        InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"),
        InlineKeyboardButton(text="📦 Deliver", callback_data="admin_deliver")
    )
    kb.row(
        InlineKeyboardButton(text="📂 Categories", callback_data="admin_cats"),
        InlineKeyboardButton(text="📦 Products", callback_data="admin_prods")
    )
    kb.row(
        InlineKeyboardButton(text="🔑 Stock", callback_data="admin_stock"),
        InlineKeyboardButton(text="✏️ Edit Product", callback_data="admin_editprod")
    )
    kb.row(
        InlineKeyboardButton(text="⛔ Ban User", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban")
    )
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="⏳ Pending", callback_data="orders_pending"),
        InlineKeyboardButton(text="✅ Delivered", callback_data="orders_delivered")
    )
    kb.row(InlineKeyboardButton(text="📋 All Orders", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    for i in range(0, len(cats), 2):
        row_btns = [InlineKeyboardButton(text=f"{cats[i].get('icon', '📦')} {cats[i]['name']}", callback_data=f"admincat_{cats[i]['id']}")]
        if i + 1 < len(cats):
            row_btns.append(InlineKeyboardButton(text=f"{cats[i+1].get('icon', '📦')} {cats[i+1]['name']}", callback_data=f"admincat_{cats[i+1]['id']}"))
        kb.row(*row_btns)
    kb.row(InlineKeyboardButton(text="➕ Add Category", callback_data="addcat_root"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_prods_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        prods = db.get_products(cat["id"])
        kb.row(InlineKeyboardButton(text=f"📂 {cat['name']} ({len(prods)})", callback_data=f"adminprods_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data="addprod_select"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Stock Status", callback_data="stock_status"),
        InlineKeyboardButton(text="➕ Add Stock", callback_data="stock_add")
    )
    kb.row(InlineKeyboardButton(text="🗑️ Delete Stock", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def delivery_kb(oid):
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    return kb.as_markup()

# ─── COMMANDS ───
@dp.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
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
    
    prods = db.get_products(cat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} {cat['name']}"
        await call.message.edit_text(f"📦 *{title}*\n\nনিচের তালিকা থেকে প্রোডাক্টটি সিলেক্ট করুন:", 
                                    reply_markup=products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ এই ক্যাটাগরিতে বর্তমানে কোনো প্রোডাক্ট নেই", show_alert=True)

# ─── DYNAMIC ORDER FLOWS ───
@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    
    uid = call.from_user.id
    bal = db.get_balance(uid)
    price = prod["price"]
    
    # 1. Check Balance
    if bal < price:
        lines = [
            "❌ *পর্যাপ্ত ব্যালেন্স নেই!*",
            "",
            f"প্রয়োজনীয় মূল্য: {fmt(price)}",
            f"আপনার বর্তমান ব্যালেন্স: {fmt(bal)}",
            "",
            "👉 অনুগ্রহ করে ওয়ালেটে ব্যালেন্স টপআপ করুন।"
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="💳 Top-up Balance", callback_data="my_wallet"))
        kb.row(InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    
    # 2. Deduct Balance Directly
    db.deduct_balance(uid, price)
    cat_id = prod["category_id"]
    await state.update_data(order_pid=pid, order_prod=prod)
    
    # YouTube Premium Flow
    if cat_id == "youtube":
        lines = [
            f"▶️ *{prod['name']}*",
            f"💰 মূল্য: {fmt(prod['price'])} (কাটা হয়েছে)",
            "",
            "📧 *আপনার জিমেইলটি (Gmail) সুন্দরভাবে নিচে দিন:*",
            "*(যে জিমেইলে YouTube Premium এক্সেস চান)*"
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(YTOrder.gmail)
        
    # Crunchyroll Flow
    elif cat_id == "crunchyroll":
        lines = [
            f"🍿 *{prod['name']}*",
            f"💰 মূল্য: {fmt(prod['price'])} (কাটা হয়েছে)",
            "",
            "📧 *আপনার জিমেইলটি (Gmail) সুন্দরভাবে দিন:*",
            "*(যে জিমেইলে Crunchyroll Premium নিতে চান)*"
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(CROrder.gmail)
        
    # VPN / Proxy / Instant Delivery Flow
    elif cat_id in ["vpn", "proxy"]:
        stock = db.get_available_stock(prod["id"])
        days = prod.get("expiry_days", 30)
        now = datetime.now()
        start_date = now.strftime("%Y-%m-%d")
        exp_date = (now + timedelta(days=days)).strftime("%Y-%m-%d")
        
        if stock:
            oid = db.add_order(uid, prod["id"], prod["name"], cat_id, price, "Auto Delivery", "Wallet Balance", f"WAL{now:%Y%m%d%H%M%S}")
            db.update_order(oid, "delivered")
            
            lines = [
                "╭─────────────────────────────╮",
                f"│  🔐 {prod['name'].upper()}   │",
                "├─────────────────────────────┤",
            ]
            if stock["stock_type"] == "key_only":
                lines.append(f"│ 🔑 Key: `{stock['key_data']}`")
            else:
                lines.append(f"│ 📧 Email: `{stock['email']}`")
                lines.append(f"│ 🔐 Password: `{stock['password']}`")
            
            lines.extend([
                "│ 🟢 Status: Active",
                f"│ 📅 Active Date: {start_date}",
                f"│ ⌛ Expire Date: {exp_date} ({days} Days)",
                "├─────────────────────────────┤",
                "│  ⚡ Thank you for shopping!  │",
                "╰─────────────────────────────╯"
            ])
            await call.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
            
            # Notify Admin
            admin_text = f"⚡ *Auto Delivery Done*\n\nOrder #{oid}\nUser: `{uid}`\nProduct: {prod['name']}"
            for aid in ADMIN_IDS:
                try: await bot.send_message(aid, admin_text, parse_mode="Markdown")
                except: pass
        else:
            oid = db.add_order(uid, prod["id"], prod["name"], cat_id, price, "Stock Pending", "Wallet Balance", f"WAL{now:%Y%m%d%H%M%S}")
            db.update_order(oid, "pending")
            await call.message.edit_text(f"⏳ *অর্ডার #{oid} কনফার্ম হয়েছে!*\nস্টক খালি থাকায় এডমিন দ্রুত তথ্য প্রদান করবে।", reply_markup=main_menu(uid), parse_mode="Markdown")
            
            for aid in ADMIN_IDS:
                try: await bot.send_message(aid, f"🚨 *VPN Stock Out Order!*\nOrder #{oid}\nUser: `{uid}`\nProduct: {prod['name']}", reply_markup=delivery_kb(oid), parse_mode="Markdown")
                except: pass
        await state.clear()
        
    # Other Categories
    else:
        lines = [f"📦 *{prod['name']}*", f"💰 মূল্য: {fmt(prod['price'])}", "", "📧 আপনার বিবরণ প্রদান করুন:"]
        await call.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")

# YouTube Gmail Handler
@dp.message(YTOrder.gmail)
async def yt_gmail_rec(msg: Message, state: FSMContext):
    gmail = msg.text.strip()
    data = await state.get_data()
    prod = data["order_prod"]
    uid = msg.from_user.id
    price = prod["price"]
    
    now = datetime.now()
    oid = db.add_order(uid, prod["id"], prod["name"], "youtube", price, f"Gmail: {gmail}", "Wallet Balance", f"WAL{now:%Y%m%d%H%M%S}")
    
    await msg.answer("✅ **আপনার অর্ডারটি সফলভাবে এডমিনের কাছে পৌঁছে গেছে।**\n\nকিছুক্ষণ ওয়েট করুন, আপনার অর্ডারটি কনফার্ম করে দেওয়া হবে।", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify Admin
    admin_lines = [
        "▶️ *NEW YOUTUBE PREMIUM ORDER*",
        "",
        f"🆔 Order ID: #{oid}",
        f"👤 User ID: `{uid}`",
        f"📦 Product: {prod['name']}",
        f"📧 Gmail: `{gmail}`",
        f"💰 Price: {fmt(price)} (Paid)",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Confirm Order", callback_data=f"confirm_yt_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid, "\n".join(admin_lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        except: pass
        
    await state.clear()

# Crunchyroll Gmail & WhatsApp Handlers
@dp.message(CROrder.gmail)
async def cr_gmail_rec(msg: Message, state: FSMContext):
    gmail = msg.text.strip()
    await state.update_data(cr_gmail=gmail)
    
    lines = [
        "📱 *আপনার সঙ্গে স্বাচ্ছন্দ্যে কন্টাক্ট করার জন্য WhatsApp নম্বরটি দিন:*",
        "*(যেমন: 01700000000)*"
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(CROrder.whatsapp)

@dp.message(CROrder.whatsapp)
async def cr_wa_rec(msg: Message, state: FSMContext):
    wa_num = msg.text.strip()
    data = await state.get_data()
    prod = data["order_prod"]
    gmail = data["cr_gmail"]
    uid = msg.from_user.id
    price = prod["price"]
    
    now = datetime.now()
    uinput = f"Gmail: {gmail} | WA: {wa_num}"
    oid = db.add_order(uid, prod["id"], prod["name"], "crunchyroll", price, uinput, "Wallet Balance", f"WAL{now:%Y%m%d%H%M%S}")
    
    await msg.answer("✅ **আপনার অর্ডারটি সফলভাবে এডমিনের কাছে পৌঁছে গেছে।**\n\nএডমিন এটি অতি দ্রুত কনফার্ম করে দেবে।", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify Admin
    admin_lines = [
        "🍿 *NEW CRUNCHYROLL ORDER*",
        "",
        f"🆔 Order ID: #{oid}",
        f"👤 User ID: `{uid}`",
        f"📦 Product: {prod['name']}",
        f"📧 Gmail: `{gmail}`",
        f"📱 WhatsApp: `{wa_num}`",
        f"💰 Price: {fmt(price)} (Paid)",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Confirm Order", callback_data=f"confirm_cr_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid, "\n".join(admin_lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        except: pass
        
    await state.clear()

# Admin Confirm YT / CR Order
@dp.callback_query(lambda c: c.data.startswith("confirm_yt_") or c.data.startswith("confirm_cr_"))
async def confirm_admin_order(call: CallbackQuery):
    await call.answer("Confirming...")
    parts = call.data.split("_")
    order_type = parts[1].upper()
    oid = int(parts[2])
    
    order = db.get_order(oid)
    if not order:
        return await call.message.edit_text("❌ Order not found!")
        
    prod = db.get_product(order["product_id"])
    expiry_days = prod.get("expiry_days", 30) if prod else 30
    
    now = datetime.now()
    start_date = now.strftime("%Y-%m-%d")
    exp_date = (now + timedelta(days=expiry_days)).strftime("%Y-%m-%d")
    
    db.update_order(oid, "delivered")
    uinput = order.get("user_input", "")
    
    service_title = "YOUTUBE PREMIUM" if order_type == "YT" else "CRUNCHYROLL PREMIUM"
    icon = "▶️" if order_type == "YT" else "🍿"
    
    user_msg = [
        "╭─────────────────────────────╮",
        f"│ {icon}  {service_title} ACTIVATED │",
        "├─────────────────────────────┤",
        f"│ 📝 Info: {uinput}",
        "│ 🟢 Status: Active",
        f"│ 📅 Active Date: {start_date}",
        f"│ ⌛ Expire Date: {exp_date} ({expiry_days} Days)",
        "├─────────────────────────────┤",
        "│  🎉 Your Premium is Live!   │",
        "│  Thank you for choosing us. │",
        "╰─────────────────────────────╯"
    ]
    
    try:
        await bot.send_message(order["user_id"], "\n".join(user_msg), parse_mode="Markdown")
    except:
        pass
        
    await call.message.edit_text(f"✅ *Order #{oid} confirmed and activated!*", parse_mode="Markdown")

# ─── DEPOSIT SYSTEM ───
@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    uid = call.from_user.id
    bal = db.get_balance(uid)
    
    lines = [
        "💳 *ডিরেক্ট ওয়ালেট ডিপোজিট*",
        "─────────────────────────────",
        f"💰 আপনার বর্তমান ব্যালেন্স: *{fmt(bal)}*",
        "─────────────────────────────",
        "📌 *টাকা পয়েন্ট যুক্ত করার উপায়:*",
        "১. নিচের যেকোনো নম্বরে Send Money করুন:",
        "   • 💖 *bKash:* `01742958563`",
        "   • 🟠 *Nagad:* `01748506069`",
        "   • 🚀 *Rocket:* `01742958563`",
        "",
        "২. টাকা পাঠানোর পর নিচে আপনার পাঠানো *টাকার পরিমাণ* এবং *TrxID* প্রদান করুন।",
        "   *(যেমন: 200 TRX123456)*",
    ]
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="❌ Cancel Deposit", callback_data="main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositState.trxid)

@dp.message(DepositState.trxid)
async def deposit_trx_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    uid = msg.from_user.id
    
    admin_text = [
        "💰 *NEW DEPOSIT REQUEST*",
        "",
        f"👤 User ID: `{uid}`",
        f"📛 Name: {msg.from_user.first_name}",
        f"📝 Text Sent: `{text}`",
    ]
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid, "\n".join(admin_text), parse_mode="Markdown")
        except: pass
            
    await msg.answer("✅ আপনার ডিপোজিট রিকোয়েস্টটি এডমিনের কাছে পাঠানো হয়েছে! ভেরিফাই করে ব্যালেন্স যুক্ত করা হবে।", reply_markup=main_menu(uid))
    await state.clear()

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    
    if not orders:
        lines = ["📦 *Your Orders*", "", "আপনার কোনো অর্ডার হিস্ট্রি পাওয়া যায়নি।"]
    else:
        lines = ["📜 *আপনার সাম্প্রতিক অর্ডারসমূহ:*", ""]
        for o in orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name']}")
            lines.append(f"   মূল্য: {fmt(o['amount'])} - Status: {o['status']}")
            lines.append("")
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ─── ADMIN PANEL HANDLERS ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text("⚡ *Admin Panel Control Center*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    
    lines = [
        "📊 *Dashboard Overview*",
        "",
        f"👥 মোট ইউজার: {len(users)}",
        f"⏳ পেন্ডিং অর্ডার: {pending}",
        "",
        "🔑 *বর্তমান স্টক স্ট্যাটাস:*",
    ]
    if stock:
        for s in stock:
            lines.append(f"• `{s['product_id']}`: {s['cnt']} টি")
    else:
        lines.append("কোনো স্টক খালি নেই")
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["💰 *Add User Balance*", "", "ইউজারের Telegram User ID দিন:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        user = db.get_user(uid)
        if not user:
            return await msg.answer("❌ কোনো ইউজার পাওয়া যায়নি।")
        
        await state.update_data(uid=uid)
        lines = [
            "💰 *Add Balance*",
            "",
            f"👤 User: {user['first_name']}",
            f"💳 বর্তমান ব্যালেন্স: {fmt(user['balance'])}",
            "",
            "কত টাকা যোগ করতে চান লিখে পাঠান:",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.addbal_amt)
    except:
        await msg.answer("❌ ইউজার আইডি সঠিক নয়।")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        data = await state.get_data()
        uid = data["uid"]
        
        db.update_balance(uid, amt)
        new_bal = db.get_balance(uid)
        
        lines = ["✅ *ব্যালেন্স যুক্ত করা সফল হয়েছে!*", f"নতুন ব্যালেন্স: {fmt(new_bal)}"]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
        
        try: await bot.send_message(uid, f"🎉 *আপনার ওয়ালেটে {fmt(amt)} যুক্ত করা হয়েছে!*", parse_mode="Markdown")
        except: pass
    except:
        await msg.answer("❌ টাকার পরিমাণ সঠিক নয়।")
    await state.clear()

# ─── EASY STOCK ADDITION (NO CATEGORY ID ASKED) ───
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management Center*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    if not counts:
        lines = ["কোনো স্টক এভেইলেবল নেই।"]
    else:
        lines = ["🔑 *স্টক স্ট্যাটাস list:*", ""]
        for s in counts:
            lines.append(f"📦 Product: `{s['product_id']}` - অবশিষ্ট: {s['cnt']} টি")
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        return await call.message.edit_text("❌ কোনো প্রোডাক্ট নেই। আগে প্রোডাক্ট যোগ করুন।", reply_markup=admin_stock_kb())
    
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.row(InlineKeyboardButton(text=f"📦 {p['name']}", callback_data=f"addstockprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    
    await call.message.edit_text("🔑 **যে প্রোডাক্টের স্টক যোগ করতে চান সেটি সিলেক্ট করুন:**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addstockprod_"))
async def addstockprod_sel(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[13:]
    prod = db.get_product(pid)
    
    await state.update_data(stock_pid=pid, stock_type=prod.get("stock_type", "key_only"))
    
    if prod.get("stock_type") == "key_only":
        lines = ["🔑 প্রতি লাইনে ১টি করে Key/Code সেন্ড করুন:"]
    else:
        lines = ["📧 প্রতি লাইনে `email:password` ফরম্যাটে অ্যাকাউন্ট পাঠান:"]
        
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.stock_data)

@dp.message(Admin.stock_data, F.text)
async def stock_data_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_pid"]
    stype = data["stock_type"]
    lines_input = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    
    for line in lines_input:
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
    
    lines_msg = [f"✅ *{added} টি স্টক যুক্ত করা হয়েছে!*"]
    await msg.answer("\n".join(lines_msg), reply_markup=admin_stock_kb(), parse_mode="Markdown")
    await state.clear()

# ─── PRODUCT EDITING & MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_editprod")
async def editprod_list(call: CallbackQuery):
    await call.answer()
    prods = db.get_all_products()
    
    if not prods:
        return await call.message.edit_text("এডিট করার মতো কোনো প্রোডাক্ট নেই।", reply_markup=admin_kb())
    
    kb = InlineKeyboardBuilder()
    for p in prods[:20]:
        kb.row(InlineKeyboardButton(text=f"✏️ {p['name']} — {fmt(p['price'])}", callback_data=f"editprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    
    await call.message.edit_text("এডিট করতে প্রোডাক্ট নির্বাচন করুন:", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod:
        return
    
    lines = [
        f"📦 *{prod['name']}*",
        f"ID: `{pid}`",
        f"💰 মূল্য: {fmt(prod['price'])}",
        f"⏰ মেয়াদ: {prod.get('expiry_days', 30)} Days",
        "",
        "কোন ফিল্ডটি এডিট করতে চান?",
    ]
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Name", callback_data=f"editfield_{pid}_name"))
    kb.row(InlineKeyboardButton(text="💰 Price", callback_data=f"editfield_{pid}_price"))
    kb.row(InlineKeyboardButton(text="⏰ Expiry Days", callback_data=f"editfield_{pid}_expiry_days"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Product", callback_data=f"delprod_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_editprod"))
    
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editfield_"))
async def editfield_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_")
    pid = parts[1]
    field = parts[2]
    await state.update_data(editprod_pid=pid, editprod_field=field)
    
    lines = [f"✏️ *Edit {field.capitalize()}*", f"Product ID: `{pid}`", "", "নতুন মানটি লিখে পাঠান:"]
    await call.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.editprod_value)

@dp.message(Admin.editprod_value)
async def editprod_value(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["editprod_pid"]
    field = data["editprod_field"]
    val = msg.text.strip()
    
    try:
        if field == "name":
            db.update_product(pid, name=val)
        elif field == "price":
            db.update_product(pid, price=float(val))
        elif field == "expiry_days":
            db.update_product(pid, expiry_days=int(val))
            
        await msg.answer("✅ *প্রোডাক্ট সফলভাবে আপডেট করা হয়েছে!*", reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]
    db.delete_product(pid)
    await call.message.edit_text(f"🗑️ *Product Deleted: {pid}*", reply_markup=admin_kb(), parse_mode="Markdown")

# ─── MAIN FUNCTION ───
async def main():
    print("🚀 Bot starting...")
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
