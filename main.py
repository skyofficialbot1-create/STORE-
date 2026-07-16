#!/usr/bin/env python3
import asyncio, os, sys, sqlite3, json
from datetime import datetime
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError as e:
    print(f"Installing dependencies...")
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
            
            # Seed default data if empty
            cur = conn.execute("SELECT COUNT(*) FROM categories")
            if cur.fetchone()[0] == 0:
                self._seed_data(conn)
            
            conn.commit()
    
    def _seed_data(self, conn):
        # Main Categories - UPDATED
        categories = [
            ("youtube", None, "YouTube Premium", "Ad-free YouTube", "▶️", 1),
            ("netflix", None, "Netflix Premium", "Netflix Accounts", "🎬", 2),
            ("crunchyroll", None, "Crunchyroll", "Anime Streaming", "", 3),
            ("vpn", None, "VPN", "Premium VPN Services", "", 4),
            ("proxy", None, "Proxy", "Proxy Services", "", 5),
        ]
        for cat in categories:
            conn.execute("""INSERT INTO categories(id,parent_id,name,description,icon,sort_order) 
                           VALUES(?,?,?,?,?,?)""", cat)
        
        # Products - UPDATED
        products = [
            # YouTube Premium
            ("yt_1m", "youtube", "▶️ 1 Month", 100, 0, "email_pass", 30),
            ("yt_3m", "youtube", "▶️ 3 Months", 200, 0, "email_pass", 90),
            ("yt_6m", "youtube", "▶️ 6 Months", 300, 0, "email_pass", 180),
            ("yt_1y", "youtube", "▶️ 1 Year", 490, 0, "email_pass", 365),
            # Netflix
            ("nf_1m", "netflix", "🎬 1 Month", 150, 0, "email_pass", 30),
            ("nf_3m", "netflix", "🎬 3 Months", 400, 0, "email_pass", 90),
            ("nf_6m", "netflix", "🎬 6 Months", 750, 0, "email_pass", 180),
            ("nf_1y", "netflix", "🎬 1 Year", 1400, 0, "email_pass", 365),
            # Crunchyroll
            ("cr_1m", "crunchyroll", "🍿 1 Month", 200, 0, "email_pass", 30),
            ("cr_3m", "crunchyroll", "🍿 3 Months", 550, 0, "email_pass", 90),
            ("cr_1y", "crunchyroll", " 1 Year", 1840, 0, "email_pass", 365),
            # VPN - Only VPN services
            ("vpn_express", "vpn", " ExpressVPN 1M", 350, 0, "email_pass", 30),
            ("vpn_hma", "vpn", " HMA VPN 1M", 250, 0, "key_only", 30),
            ("vpn_nord", "vpn", "🔐 NordVPN 1M", 320, 0, "email_pass", 30),
            ("vpn_proton", "vpn", "🔐 ProtonVPN 1M", 300, 0, "email_pass", 30),
            ("vpn_surf", "vpn", "🔐 Surfshark 1M", 280, 0, "email_pass", 30),
            ("vpn_vanish", "vpn", " VanishVPN 1M", 260, 0, "email_pass", 30),
            # Proxy - Only Proxy services
            ("proxy_resi", "proxy", "🌐 Residential Proxy", 500, 0, "key_only", 30),
            ("proxy_dc", "proxy", "🌐 Datacenter Proxy", 300, 0, "key_only", 30),
            ("proxy_mobile", "proxy", " Mobile Proxy", 600, 0, "key_only", 30),
        ]
        for prod in products:
            conn.execute("""INSERT INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) 
                           VALUES(?,?,?,?,?,?,?)""", prod)
        
        conn.commit()
        print("✅ Database initialized with updated categories")
    
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

# ─── STATES ───
class Order(StatesGroup):
    input = State()
    payment = State()
    trxid = State()

class Admin(StatesGroup):
    addbal_uid = State()
    addbal_amt = State()
    deliver_oid = State()
    broadcast_msg = State()
    ban_uid = State()
    unban_uid = State()
    addcat_id = State()
    addcat_name = State()
    addcat_desc = State()
    addprod_id = State()
    addprod_name = State()
    addprod_price = State()
    addprod_bonus = State()
    addprod_expiry = State()
    addprod_stocktype = State()
    editprod_pid = State()
    editprod_field = State()
    editprod_value = State()
    stock_pid = State()
    stock_data = State()
    stock_days = State()

# ─── HELPERS ───
def fmt(amount):
    return f"৳{amount:,.0f}"

# ─── WELCOME MESSAGE ───
WELCOME = """
╭─────────────────────────────╮
│   🌟  SKY STORE BD  🌟      │
│   ⚡ Premium Digital Store   │
├─────────────────────────────┤
│  ▶️ YouTube •  Netflix    │
│  🍿 Crunchyroll • 🔐 VPN    │
│        🌐 Proxy             │
─────────────────────────────┤
│   Support: @FBSKYSUPPORT  │
│  ⚡ Instant • 🛡️ Trusted    │
╰─────────────────────────────╯

👇 Select a category to start!
"""

# ─── KEYBOARDS ───
def main_menu(uid):
    """Main menu with 2-column layout"""
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    
    # Add categories in pairs (2 per row)
    for i in range(0, len(cats), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=f"{cats[i].get('icon', '📦')} {cats[i]['name']}",
            callback_data=f"cat_{cats[i]['id']}"
        ))
        if i + 1 < len(cats):
            row.append(InlineKeyboardButton(
                text=f"{cats[i+1].get('icon', '📦')} {cats[i+1]['name']}",
                callback_data=f"cat_{cats[i+1]['id']}"
            ))
        kb.row(*row)
    
    # Bottom menu
    kb.row(
        InlineKeyboardButton(text=" My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💰 Deposit", callback_data="my_wallet")
    )
    kb.row(InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    
    return kb.as_markup()

def products_kb(cat_id):
    """Products in 2-column layout"""
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    
    for i in range(0, len(prods), 2):
        row = []
        p1 = prods[i]
        txt1 = f"{p1['name']}\n{fmt(p1['price'])}"
        if p1.get("bonus", 0) > 0:
            txt1 += f"\n(+{fmt(p1['bonus'])})"
        row.append(InlineKeyboardButton(text=txt1, callback_data=f"order_{p1['id']}"))
        
        if i + 1 < len(prods):
            p2 = prods[i+1]
            txt2 = f"{p2['name']}\n{fmt(p2['price'])}"
            if p2.get("bonus", 0) > 0:
                txt2 += f"\n(+{fmt(p2['bonus'])})"
            row.append(InlineKeyboardButton(text=txt2, callback_data=f"order_{p2['id']}"))
        
        kb.row(*row)
    
    kb.row(InlineKeyboardButton(text="🔙 Back to Categories", callback_data="main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💰 Wallet Balance", callback_data="pay_wallet"))
    kb.row(
        InlineKeyboardButton(text=" bKash", callback_data="pay_bkash"),
        InlineKeyboardButton(text="💳 Nagad", callback_data="pay_nagad")
    )
    kb.row(InlineKeyboardButton(text=" Rocket", callback_data="pay_rocket"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products"))
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
        InlineKeyboardButton(text=" Stock", callback_data="admin_stock"),
        InlineKeyboardButton(text="✏️ Edit", callback_data="admin_editprod")
    )
    kb.row(
        InlineKeyboardButton(text="⛔ Ban", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban", callback_data="admin_unban")
    )
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=" Pending", callback_data="orders_pending"),
        InlineKeyboardButton(text="✅ Delivered", callback_data="orders_delivered")
    )
    kb.row(InlineKeyboardButton(text="📋 All Orders", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        kb.row(InlineKeyboardButton(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"admincat_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Add Category", callback_data="addcat_root"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_prods_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        prods = db.get_products(cat["id"])
        if prods:
            kb.row(InlineKeyboardButton(text=f" {cat['name']} ({len(prods)})", callback_data=f"adminprods_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data="addprod_select"))
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
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
    
    prods = db.get_products(cat_id)
    if prods:
        title = f"{cat.get('icon', '📦')} {cat['name']}"
        await call.message.edit_text(f"📦 *{title}*\n\nSelect a product:", 
                                    reply_markup=products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("No products in this category yet", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    
    await state.update_data(order_pid=pid, order_prod=prod)
    cat = db.get_category(prod["category_id"])
    
    # Check if VPN or Proxy service
    if prod["category_id"] in ["vpn", "proxy"]:
        lines = [
            f" *{prod['name']}*",
            f"💰 Price: {fmt(prod['price'])}",
            f"⏰ Valid: {prod.get('expiry_days', 30)} days",
            "",
            "🌍 Enter server/location:",
            "*(or type 'auto')*",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="⚡ Auto", callback_data="vpn_auto"))
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(Order.input)
    else:
        # Other products - ask for email
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 Price: {fmt(prod['price'])}",
            "",
            "📧 Enter your Email:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(Order.input)

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
        "Select payment method:",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please enter valid details")
    
    await state.update_data(user_input=text)
    data = await state.get_data()
    prod = data["order_prod"]
    
    lines = [
        f"📦 *{prod['name']}*",
        f"💰 Price: {fmt(prod['price'])}",
        "",
        "Select payment method:",
    ]
    await msg.answer("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
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
            lines = [
                "❌ *Insufficient Balance*",
                "",
                f"Need: {fmt(price)}",
                f"Have: {fmt(bal)}",
            ]
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="💰 Top Up", callback_data="my_wallet"))
            kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment"))
            await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
        
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    else:
        nums = {"bkash": "01742958563", "nagad": "01748506069", "rocket": "01742958563"}
        lines = [
            "💳 *Send Payment*",
            "",
            f"💰 Amount: {fmt(price)}",
            f"📱 Method: {method.upper()}",
            f"🔢 Number: `{nums.get(method, '')}`",
            "",
            "Send payment & enter TrxID:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
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
    
    # Handle VPN/Proxy - auto delivery if stock available
    if cat_id in ["vpn", "proxy"]:
        stock = db.get_available_stock(prod["id"])
        if stock:
            db.update_order(oid, "delivered")
            
            if stock["stock_type"] == "key_only":
                delivery_text = f"🔑 *Key:*\n`{stock['key_data']}`\n\n"
            else:
                delivery_text = f"📧 *Email:*\n`{stock['email']}`\n\n"
                delivery_text += f"🔐 *Password:*\n`{stock['password']}`\n\n"
            
            delivery_text += f"🌍 Server: {uinput or 'Auto'}\n"
            delivery_text += f"⏰ Expires: {stock['expiry_days']} days"
            
            lines = [
                "✅ *Delivered!*",
                "",
                delivery_text,
            ]
            await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
        else:
            db.update_order(oid, "pending")
            lines = [
                "⏳ *Order Placed!*",
                "",
                f"Order ID: #{oid}",
                "Status: Pending (No Stock)",
                "Admin will deliver soon",
            ]
            await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        # Other products - pending
        db.update_order(oid, "pending")
        lines = [
            "✅ *Order Placed!*",
            "",
            f"Order ID: #{oid}",
            "Status: Pending Verification",
        ]
        await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify admin
    user = db.get_user(uid)
    order = db.get_order(oid)
    admin_lines = [
        "📦 *NEW ORDER*",
        "",
        f"🆔 Order: #{oid}",
        f"👤 User: {uid}",
        f"📛 Name: {user['first_name']}",
        f"📦 Product: {prod['name']}",
        f"💰 Amount: {fmt(price)}",
        f"📝 Input: {uinput}",
        f"💳 Payment: {pmethod}",
        f"🔢 TrxID: {trx}",
    ]
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_lines), reply_markup=delivery_kb(oid), parse_mode="Markdown")
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
    lines = [
        f"📦 *{prod['name']}*",
        f"💰 Price: {fmt(prod['price'])}",
        "",
        "Select payment method:",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data == "back_to_products")
async def back_prod(call: CallbackQuery, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    cat_id = data.get("order_prod", {}).get("category_id")
    if cat_id:
        await call.message.edit_text(f"📦 Select a product:", reply_markup=products_kb(cat_id))
        await state.set_state(None)

@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    bal = db.get_balance(uid)
    lines = [
        " *Your Wallet*",
        "",
        f"💳 Balance: {fmt(bal)}",
        "",
        "To add balance:",
        "1. Send money to:",
        "   bKash: 01742958563",
        "   Nagad: 01748506069",
        "2. Send TrxID with amount",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    
    if not orders:
        lines = ["📦 *Your Orders*", "", "No orders yet."]
    else:
        lines = ["📦 *Your Orders*", ""]
        for o in orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name']}")
            lines.append(f"   {fmt(o['amount'])} - {o['status']}")
            
            # Show delivery data if available
            if o.get("delivery_data"):
                dd = o["delivery_data"]
                if dd.get("key"):
                    lines.append(f"   🔑 Key: `{dd['key']}`")
                if dd.get("email"):
                    lines.append(f"   📧 Email: `{dd['email']}`")
                if dd.get("password"):
                    lines.append(f"   🔐 Pass: `{dd['password']}`")
            lines.append("")
    
    await call.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")

# ─── ADMIN PANEL ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text(" *Admin Panel*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    
    lines = [
        "📊 *Dashboard*",
        "",
        f"👥 Users: {len(users)}",
        f"⏳ Pending Orders: {pending}",
        "",
        "🔑 *Stock Status:*",
    ]
    if stock:
        for s in stock:
            lines.append(f"• {s['product_id']}: {s['cnt']}")
    else:
        lines.append("No stock available")
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_orders")
async def all_orders_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Orders*", reply_markup=admin_orders_kb(), parse_mode="Markdown")

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
        lines = [f"📦 *{title}*", "", "No orders found."]
    else:
        lines = [f"📦 *{title}*", ""]
        for o in orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name'][:20]}")
            lines.append(f"   {fmt(o['amount'])} by {o['user_id']}")
            lines.append("")
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_orders_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    await call.answer("✅ Approving...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    
    # For VPN/Proxy, generate delivery data
    prod = db.get_product(order["product_id"])
    if prod["category_id"] in ["vpn", "proxy"]:
        stock = db.get_available_stock(prod["id"])
        if stock:
            if stock["stock_type"] == "key_only":
                delivery_data = {"key": stock["key_data"]}
            else:
                delivery_data = {"email": stock["email"], "password": stock["password"]}
            delivery_data["server"] = order.get("user_input", "Auto")
            delivery_data["expires"] = f"{stock['expiry_days']} days"
            db.update_order(oid, "delivered", delivery_data)
            
            # Notify user
            user_text = f"✅ *Order Delivered!*\n\n"
            if stock["stock_type"] == "key_only":
                user_text += f"🔑 *Key:*\n`{stock['key_data']}`\n\n"
            else:
                user_text += f"📧 *Email:*\n`{stock['email']}`\n\n"
                user_text += f"🔐 *Password:*\n`{stock['password']}`\n\n"
            user_text += f"🌍 Server: {order.get('user_input', 'Auto')}\n"
            user_text += f"⏰ Expires: {stock['expiry_days']} days"
            
            try:
                await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
            except:
                pass
        else:
            db.update_order(oid, "delivered")
    else:
        db.update_order(oid, "delivered")
        try:
            await bot.send_message(order["user_id"], f"✅ *Order #{oid} Delivered!*\n\n📦 {order['product_name']}", parse_mode="Markdown")
        except:
            pass
    
    lines = [f"✅ *Order #{oid} Approved!*", f"Status: Delivered"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer("❌ Rejecting...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    
    db.update_order(oid, "cancelled")
    
    try:
        await bot.send_message(order["user_id"], f"❌ *Order #{oid} Cancelled*\n\n {order['product_name']}", parse_mode="Markdown")
    except:
        pass
    
    lines = [f"❌ *Order #{oid} Rejected!*", f"Status: Cancelled"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_users")
async def users_list(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    lines = ["👥 *Users*", ""]
    for u in users[:15]:
        status = "🔒" if u['is_banned'] else "👤"
        lines.append(f"{status} {u['user_id']} - {u['first_name'][:15]}")
        lines.append(f"   Balance: {fmt(u['balance'])}")
        lines.append("")
    
    if not lines:
        lines = ["No users yet."]
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["💰 *Add Balance*", "", "Send User ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        user = db.get_user(uid)
        if not user:
            return await msg.answer("❌ User not found")
        
        await state.update_data(uid=uid)
        lines = [
            "💰 *Add Balance*",
            "",
            f"👤 User: {user['first_name']}",
            f"💳 Current: {fmt(user['balance'])}",
            "",
            "Send amount to add:",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
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
        
        lines = [
            "✅ *Balance Added!*",
            "",
            f"Amount: {fmt(amt)}",
            f"New Balance: {fmt(new_bal)}",
            f"Time: {datetime.now():%H:%M}",
        ]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            user_text = [
                "💰 *Balance Added!*",
                "",
                f"Amount: {fmt(amt)}",
                f"New Balance: {fmt(new_bal)}",
                f"Added by: Admin",
            ]
            await bot.send_message(uid, "\n".join(user_text), parse_mode="Markdown")
        except:
            pass
    except:
        await msg.answer("❌ Invalid amount")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [" *Deliver Order*", "", "Send Order ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        if not order:
            return await msg.answer("❌ Not found")
        
        await state.update_data(oid=oid)
        lines = [
            f"📦 *Order #{oid}*",
            f"Product: {order['product_name']}",
            f"User: {order['user_id']}",
            f"Amount: {fmt(order['amount'])}",
            "",
            "Send delivery data:",
            "For VPN/Proxy: email:password or key",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.deliver_file)
    except:
        await msg.answer("❌ Invalid Order ID")

@dp.message(Admin.deliver_file)
async def deliver_file(msg: Message, state: FSMContext):
    data = await state.get_data()
    oid = data["oid"]
    order = db.get_order(oid)
    
    delivery_text = msg.text.strip()
    
    # Parse delivery data
    if ":" in delivery_text:
        email, password = delivery_text.split(":", 1)
        delivery_data = {"email": email.strip(), "password": password.strip()}
    else:
        delivery_data = {"key": delivery_text}
    
    db.update_order(oid, "delivered", delivery_data)
    
    # Notify user
    user_text = f"✅ *Order #{oid} Delivered!*\n\n"
    if "key" in delivery_data:
        user_text += f"🔑 *Key:*\n`{delivery_data['key']}`\n"
    else:
        user_text += f"📧 *Email:*\n`{delivery_data['email']}`\n\n"
        user_text += f"🔐 *Password:*\n`{delivery_data['password']}`\n"
    
    try:
        await bot.send_message(order["user_id"], user_text, parse_mode="Markdown")
    except:
        pass
    
    lines = [f"✅ *Order #{oid} Delivered!*"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📨 *Broadcast*", "", "Send message to broadcast:"]
    await call.message.edit_text("\n".join(lines), parse_mode="Markdown")
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
    
    lines = [f"✅ *Broadcast Sent!*", "", f"Sent to {sent}/{len(users)} users"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

# ─── CATEGORY MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📂 *Categories*", reply_markup=admin_cats_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    
    lines = [
        f"📂 *{cat.get('icon', '')} {cat['name']}*",
        f"ID: {cat_id}",
        f"Products: {len(prods)}",
    ]
    if cat.get("description"):
        lines.append(f"Desc: {cat['description']}")
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="✏️ Edit Category", callback_data=f"editcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats"))
    
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addcat_"))
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = call.data[7:]
    await state.update_data(addcat_parent=parent_id)
    
    lines = [
        "➕ *Add Category*",
        "",
        "Send category ID (no spaces):",
        "Example: nord_vpn",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_cats" if parent_id == "root" else f"admincat_{parent_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addcat_id)

@dp.message(Admin.addcat_id)
async def addcat_id(msg: Message, state: FSMContext):
    cid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addcat_id=cid)
    
    lines = [
        "Send category name:",
        "Example: 🔑 NordVPN",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addcat_name)

@dp.message(Admin.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    
    lines = [
        "Send description (optional):",
        "Type 'skip' to skip",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addcat_desc)

@dp.message(Admin.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    data = await state.get_data()
    
    db.add_category(data["addcat_id"], data["addcat_parent"], data["addcat_name"], desc)
    
    lines = [
        "✅ *Category Added!*",
        "",
        f"ID: {data['addcat_id']}",
        f"Name: {data['addcat_name']}",
    ]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_id=cat_id)
    
    lines = [
        "✏️ *Edit Category*",
        "",
        "Send new name:",
        "Type 'skip' to keep current",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data=f"admincat_{cat_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addcat_name)

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    cid = call.data[7:]
    db.delete_category(cid)
    
    lines = [f"🗑️ *Category deleted: {cid}*"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_cats_kb(), parse_mode="Markdown")

# ─── PRODUCT MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_prods")
async def admin_prods(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Products*", reply_markup=admin_prods_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("adminprods_"))
async def admin_prods_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[11:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    
    lines = [
        f" *{cat.get('icon', '')} {cat['name']}*",
        f"Products: {len(prods)}",
        "",
    ]
    for p in prods[:10]:
        exp = f" ({p.get('expiry_days', 30)}d)" if p.get('expiry_days') else ""
        lines.append(f"• {p['name']}: {fmt(p['price'])}{exp}")
    
    if not prods:
        lines.append("No products yet.")
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_prods"))
    
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addprod_"))
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:] if "_" in call.data else "select"
    await state.update_data(addprod_cat=cat_id)
    
    lines = [
        "➕ *Add Product*",
        "",
        "Send product ID (no spaces):",
        "Example: vpn_nord_1m",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_prods"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addprod_id)

@dp.message(Admin.addprod_id)
async def addprod_id(msg: Message, state: FSMContext):
    pid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addprod_id=pid)
    
    lines = [
        "Send product name:",
        "Example: 🔑 NordVPN (1M)",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addprod_name)

@dp.message(Admin.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    
    lines = [
        "Send price (numbers only):",
        "Example: 350",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addprod_price)

@dp.message(Admin.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        
        lines = [
            "Send bonus (0 if none):",
            "Example: 0 or 20",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.addprod_bonus)
    except:
        await msg.answer("❌ Invalid price. Send numbers only.")

@dp.message(Admin.addprod_bonus)
async def addprod_bonus(msg: Message, state: FSMContext):
    try:
        bonus = float(msg.text.strip())
        await state.update_data(addprod_bonus=bonus)
        
        lines = [
            "Send expiry days (0 if none):",
            "Example: 30 or 0",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
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
        
        # For VPN/Proxy categories, ask stock type
        if cat_id in ["vpn", "proxy"]:
            lines = [
                "Select stock type:",
                "• email_pass = Email + Password",
                "• key_only = Key only",
                "",
                "Type: email_pass or key_only",
            ]
            await msg.answer("\n".join(lines), parse_mode="Markdown")
            await state.set_state(Admin.addprod_stocktype)
        else:
            db.add_product(data["addprod_id"], cat_id, data["addprod_name"], 
                          data["addprod_price"], data["addprod_bonus"], None, expiry)
            
            lines = [
                "✅ *Product Added!*",
                "",
                f"ID: {data['addprod_id']}",
                f"Name: {data['addprod_name']}",
                f"Price: {fmt(data['addprod_price'])}",
                f"Bonus: {fmt(data['addprod_bonus'])}",
                f"Expiry: {expiry} days",
            ]
            await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
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
    
    lines = [
        "✅ *Product Added!*",
        "",
        f"ID: {data['addprod_id']}",
        f"Name: {data['addprod_name']}",
        f"Price: {fmt(data['addprod_price'])}",
        f"Stock Type: {stype}",
        f"Expiry: {data['addprod_expiry']} days",
    ]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_editprod")
async def editprod_list(call: CallbackQuery):
    await call.answer()
    prods = db.get_all_products()
    
    if not prods:
        lines = ["No products to edit."]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_menu"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    
    kb = InlineKeyboardBuilder()
    for p in prods[:20]:
        kb.row(InlineKeyboardButton(text=f"✏️ {p['name'][:25]} - {fmt(p['price'])}", callback_data=f"editprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    
    lines = ["Select product to edit:"]
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod:
        return
    
    lines = [
        f"📦 *{prod['name']}*",
        f"ID: {pid}",
        f"💰 Price: {fmt(prod['price'])}",
        f"🎁 Bonus: {fmt(prod.get('bonus', 0))}",
        f"⏰ Expiry: {prod.get('expiry_days', 30)} days",
        f"🔄 Stock: {prod.get('stock_type', 'N/A')}",
        "",
        "Select field to edit:",
    ]
    
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Name", callback_data=f"editprod_field_{pid}_name"))
    kb.row(InlineKeyboardButton(text="💰 Price", callback_data=f"editprod_field_{pid}_price"))
    kb.row(InlineKeyboardButton(text="🎁 Bonus", callback_data=f"editprod_field_{pid}_bonus"))
    kb.row(InlineKeyboardButton(text=" Expiry", callback_data=f"editprod_field_{pid}_expiry"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delprod_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_editprod"))
    
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"))
async def editprod_field(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_")
    pid = parts[3]
    field = parts[4]
    await state.update_data(editprod_pid=pid, editprod_field=field)
    
    field_names = {
        "name": "name",
        "price": "price (numbers)",
        "bonus": "bonus (numbers)",
        "expiry": "expiry days (numbers)",
    }
    
    lines = [
        f"✏️ *Edit {field_names.get(field, field)}*",
        "",
        f"Product: {pid}",
        "",
        "Send new value:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"editprod_{pid}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
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
        
        prod = db.get_product(pid)
        lines = [
            "✅ *Product Updated!*",
            "",
            f"📦 {prod['name']}",
            f"💰 Price: {fmt(prod['price'])}",
            f"🎁 Bonus: {fmt(prod.get('bonus', 0))}",
            f"⏰ Expiry: {prod.get('expiry_days', 30)} days",
        ]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]
    db.delete_product(pid)
    
    lines = [f"🗑️ *Product deleted: {pid}*"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

# ─── STOCK MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    
    if not counts:
        lines = ["No stock available."]
    else:
        lines = ["🔑 *Stock Status*", ""]
        for s in counts:
            lines.append(f"📦 {s['product_id']}")
            lines.append(f"   Type: {s['stock_type']}")
            lines.append(f"   Available: {s['cnt']}")
            lines.append("")
    
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "➕ *Add Stock*",
        "",
        "Send Product ID:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=" Back", callback_data="admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.stock_pid)

@dp.message(Admin.stock_pid)
async def stock_pid(msg: Message, state: FSMContext):
    pid = msg.text.strip()
    prod = db.get_product(pid)
    if not prod:
        return await msg.answer("❌ Product not found")
    
    await state.update_data(stock_pid=pid, stock_type=prod.get("stock_type", "key_only"))
    
    if prod.get("stock_type") == "key_only":
        lines = [
            f"📦 {prod['name']}",
            f"Type: Key Only",
            "",
            "Send keys (one per line)",
            "Or send a .txt file",
        ]
    else:
        lines = [
            f"📦 {prod['name']}",
            f"Type: Email + Password",
            "",
            "Send in format:",
            "email:password",
            "or email|password",
            "One per line or .txt file",
        ]
    
    await msg.answer("\n".join(lines), parse_mode="Markdown")
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
    
    lines_msg = [
        "✅ *Stock Added!*",
        "",
        f"Product: {pid}",
        f"Added: {added} items",
        "",
        "Send expiry days (or 'skip'):",
    ]
    await msg.answer("\n".join(lines_msg), parse_mode="Markdown")
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
        
        lines_msg = [
            "✅ *Stock Added from File!*",
            "",
            f"Product: {pid}",
            f"Added: {added} items",
            "",
            "Send expiry days (or 'skip'):",
        ]
        await msg.answer("\n".join(lines_msg), parse_mode="Markdown")
        await state.set_state(Admin.stock_days)
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")

@dp.message(Admin.stock_days)
async def stock_days(msg: Message, state: FSMContext):
    try:
        days = int(msg.text.strip())
    except:
        days = 30
    
    lines = [
        "✅ *Stock Ready!*",
        "",
        f"Expiry: {days} days",
        "Stock is now available for auto-delivery",
    ]
    await msg.answer("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del(call: CallbackQuery):
    await call.answer()
    stock = db.get_all_stock()
    
    if not stock:
        lines = ["No stock to delete."]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    
    kb = InlineKeyboardBuilder()
    for s in stock[:15]:
        status = "✅" if s['is_used'] else "📦"
        display = s['key_data'] or s['email'] or "N/A"
        kb.row(InlineKeyboardButton(
            text=f"{status} #{s['id']} {display[:25]}...",
            callback_data=f"delstock_{s['id']}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    
    lines = ["🗑️ *Select stock to delete:*"]
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del(call)

# ─── BAN/UNBAN ───
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [" *Ban User*", "", "Send User ID to ban:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        db.set_ban(uid, True)
        
        lines = [f" *User {uid} banned!*"]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            await bot.send_message(uid, "❌ You have been banned.")
        except:
            pass
    except:
        await msg.answer("❌ Invalid User ID")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["✅ *Unban User*", "", "Send User ID to unban:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        db.set_ban(uid, False)
        
        lines = [f"✅ *User {uid} unbanned!*"]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
        
        try:
            await bot.send_message(uid, "✅ You have been unbanned!")
        except:
            pass
    except:
        await msg.answer("❌ Invalid User ID")
    await state.clear()

# ─── MAIN ──
async def main():
    print(" Bot starting...")
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
