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
except ImportError as e:
    print(f"Installing dependencies...")
    os.system("pip install aiogram")
    sys.exit(1)

BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
SUPPORT_USERNAME = "FBSKYSUPPORT"

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
            conn.execute("""INSERT INTO categories(id,parent_id,name,description,icon,sort_order) VALUES(?,?,?,?,?,?)""", cat)
        products = [
            ("yt_1m", "youtube", "▶️ YouTube Premium 1 Month", 100, 0, "manual", 30),
            ("yt_3m", "youtube", "▶️ YouTube Premium 3 Months", 200, 0, "manual", 90),
            ("nf_1m", "netflix", "🎬 Netflix Premium 1 Month", 150, 0, "manual", 30),
            ("cr_1m", "crunchyroll", "🍿 Crunchyroll 1 Month", 200, 0, "manual", 30),
            ("vpn_express", "vpn", "🚀 ExpressVPN 1 Month", 350, 0, "email_pass", 30),
            ("proxy_resi", "proxy", "🌐 Residential Proxy", 500, 0, "key_only", 30),
        ]
        for prod in products:
            conn.execute("""INSERT INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) VALUES(?,?,?,?,?,?,?)""", prod)
        conn.commit()

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
            conn.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note) VALUES(?,?,?,?,?,?)", (uid, amt, typ, method, trid, note))
            conn.commit()
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
            conn.execute("""INSERT OR REPLACE INTO products(id,category_id,name,price,bonus,stock_type,expiry_days) VALUES(?,?,?,?,?,?,?)""", (pid, category_id, name, price, bonus, stock_type, expiry_days))
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
    def add_order(self, uid, pid, pname, catid, amt, uinput, pmethod, trid):
        with self._get_conn() as conn:
            cur = conn.execute("""INSERT INTO orders(user_id,product_id,product_name,category_id,amount,user_input,payment_method,transaction_id) VALUES(?,?,?,?,?,?,?,?)""", (uid, pid, pname, catid, amt, uinput, pmethod, trid))
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
    def add_stock(self, product_id, stock_type, email=None, password=None, key_data=None, expiry_days=30):
        with self._get_conn() as conn:
            conn.execute("""INSERT INTO stock(product_id,stock_type,email,password,key_data,expiry_days) VALUES(?,?,?,?,?,?)""", (product_id, stock_type, email, password, key_data, expiry_days))
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
            cur = conn.execute("""SELECT product_id, stock_type, COUNT(*) as cnt FROM stock WHERE is_used=0 GROUP BY product_id""")
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
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

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

class Order(StatesGroup):
    input = State()
    payment = State()
    trxid = State()
    extra_input = State()

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
    stock_days = State()

def fmt(amount):
    return f"৳{amount:,.0f}"

def get_expiry_date(days):
    dt = datetime.now() + timedelta(days=days)
    return dt.strftime("%d %B %Y")

def generate_box(title, body_lines, width=36):
    """Generate a nice ASCII box"""
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

def main_menu(uid):
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    row_buttons = []
    for cat in cats:
        row_buttons.append(InlineKeyboardButton(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"cat_{cat['id']}"))
        if len(row_buttons) == 2:
            kb.row(*row_buttons)
            row_buttons = []
    if row_buttons:
        kb.row(*row_buttons)
    kb.row(
        InlineKeyboardButton(text="📜 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💳 Deposit Balance", callback_data="my_wallet")
    )
    kb.row(InlineKeyboardButton(text="📞 Support", url=f"https://t.me/{SUPPORT_USERNAME}"))
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

def products_kb(cat_id):
    prods = db.get_products(cat_id)
    kb = InlineKeyboardBuilder()
    row_btns = []
    for p in prods:
        txt = f"{p['name']} — {fmt(p['price'])}"
        if p.get("bonus", 0) > 0:
            txt += f" (+{fmt(p['bonus'])})"
        row_btns.append(InlineKeyboardButton(text=txt, callback_data=f"order_{p['id']}"))
        if len(row_btns) == 2:
            kb.row(*row_btns)
            row_btns = []
    if row_btns:
        kb.row(*row_btns)
    kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💰 Wallet Balance", callback_data="pay_wallet"))
    kb.row(InlineKeyboardButton(text="💖 bKash", callback_data="pay_bkash"), InlineKeyboardButton(text="🟠 Nagad", callback_data="pay_nagad"))
    kb.row(InlineKeyboardButton(text="🚀 Rocket", callback_data="pay_rocket"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"), InlineKeyboardButton(text="📦 Orders", callback_data="admin_orders"))
    kb.row(InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"), InlineKeyboardButton(text="📦 Deliver", callback_data="admin_deliver"))
    kb.row(InlineKeyboardButton(text="📂 Categories", callback_data="admin_cats"), InlineKeyboardButton(text="📦 Products", callback_data="admin_prods"))
    kb.row(InlineKeyboardButton(text="🔑 Stock", callback_data="admin_stock"), InlineKeyboardButton(text="✏️ Edit Product", callback_data="admin_editprod"))
    kb.row(InlineKeyboardButton(text="⛔ Ban User", callback_data="admin_ban"), InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban"))
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ Pending", callback_data="orders_pending"), InlineKeyboardButton(text="✅ Delivered", callback_data="orders_delivered"))
    kb.row(InlineKeyboardButton(text="📋 All Orders", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_cats_kb():
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        kb.row(InlineKeyboardButton(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"admincat_{cat['id']}"))
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
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="stock_status"), InlineKeyboardButton(text="➕ Add Stock", callback_data="stock_add"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Stock", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def delivery_kb(oid):
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"), InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}"))
    return kb.as_markup()

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
        await call.message.edit_text(f"📦 *{title}*\n\nনিচের তালিকা থেকে একটি প্রোডাক্ট নির্বাচন করুন:", reply_markup=products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ এই ক্যাটাগরিতে বর্তমানে কোনো প্রোডাক্ট নেই", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    cat_id = prod["category_id"]
    await state.update_data(order_pid=pid, order_prod=prod)
    
    if cat_id in ["vpn", "proxy"]:
        # VPN/Proxy: Auto deliver, no admin needed
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 মূল্য: {fmt(prod['price'])}",
            f"⏰ মেয়াদ: {prod.get('expiry_days', 30)} দিন",
            "",
            "🌍 আপনার কাঙ্ক্ষিত সার্ভার/লোকেশন লিখুন:",
            "*(অথবা Auto নিতে নিচের বাটন চাপুন)*",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="⚡ Auto Location", callback_data="vpn_auto"))
        kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(Order.input)
    elif cat_id in ["youtube", "netflix"]:
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 মূল্য: {fmt(prod['price'])}",
            f"⏰ মেয়াদ: {prod.get('expiry_days', 30)} দিন",
            "",
            "📧 আপনার জিমেইল ঠিকানাটি লিখুন:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(Order.input)
    elif cat_id == "crunchyroll":
        lines = [
            f"📦 *{prod['name']}*",
            f"💰 মূল্য: {fmt(prod['price'])}",
            f"⏰ মেয়াদ: {prod.get('expiry_days', 30)} দিন",
            "",
            "প্রথমে পেমেন্ট কনফার্ম করুন। পেমেন্ট মেথড সিলেক্ট করুন:",
        ]
        await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
        await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    prod = data["order_prod"]
    lines = [
        f"📦 *{prod['name']}*",
        f"🌍 Server: Auto",
        f"💰 মূল্য: {fmt(prod['price'])}",
        "",
        "পেমেন্ট মেথড সিলেক্ট করুন:",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ সঠিক তথ্য প্রদান করুন")
    await state.update_data(user_input=text)
    data = await state.get_data()
    prod = data["order_prod"]
    cat_id = prod["category_id"]
    
    if cat_id == "crunchyroll":
        lines = [
            f"📦 *{prod['name']}*",
            "📧 ইমেইল দেওয়া হয়েছে।",
            "",
            "📱 এখন আপনার WhatsApp নাম্বারটি লিখুন:\n*(আপনার সাথে যোগাযোগের জন্য)*",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
        await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(Order.extra_input)
        return
    
    lines = [
        f"📦 *{prod['name']}*",
        f"📧/📍 তথ্য: {text}",
        f"💰 মূল্য: {fmt(prod['price'])}",
        "",
        "পেমেন্ট মেথড সিলেক্ট করুন:",
    ]
    await msg.answer("\n".join(lines), reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.message(Order.extra_input)
async def get_extra_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 5:
        return await msg.answer("❌ সঠিক WhatsApp নাম্বার দিন")
    data = await state.get_data()
    existing_input = data.get("user_input", "")
    await state.update_data(user_input=f"{existing_input} | WhatsApp: {text}")
    prod = data["order_prod"]
    lines = [
        f"📦 *{prod['name']}*",
        f"📧 ইমেইল: {existing_input}",
        f"📱 WhatsApp: {text}",
        f"💰 মূল্য: {fmt(prod['price'])}",
        "",
        "পেমেন্ট মেথড সিলেক্ট করুন:",
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
                "❌ *পর্যাপ্ত ব্যালেন্স নেই!*",
                "",
                f"প্রয়োজন: {fmt(price)}",
                f"আপনার আছে: {fmt(bal)}",
                "",
                "💳 টপআপ করতে নিচের বাটনে ক্লিক করুন:",
            ]
            kb = InlineKeyboardBuilder()
            kb.row(InlineKeyboardButton(text="💳 Add Balance", callback_data="my_wallet"))
            kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
            await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
            return
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    else:
        nums = {"bkash": "01742958563", "nagad": "01748506069", "rocket": "01742958563"}
        lines = [
            "💳 *পেমেন্ট নির্দেশিকা*",
            "",
            f"💰 পরিমাণ: {fmt(price)}",
            f"📱 মেথড: {method.upper()}",
            f"🔢 নম্বর: `{nums.get(method, '')}` (Send Money)",
            "",
            "টাকা পাঠানোর পর ট্রানজেকশন আইডি (TrxID) সেন্ড করুন:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="❌ Cancel Payment", callback_data="main_menu"))
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
    
    ##############################################
    # VPN/PROXY: AUTO DELIVER – NO ADMIN NOTIFY  #
    ##############################################
    if cat_id in ["vpn", "proxy"]:
        stock = db.get_available_stock(prod["id"])
        if stock:
            # Use stock's expiry_days (7 days if you set that)
            stock_expiry = stock.get("expiry_days", prod.get("expiry_days", 30))
            delivery_data = {}
            
            if stock["stock_type"] == "key_only":
                delivery_data["key"] = stock["key_data"]
                cred_part = f"🔑 Key: {stock['key_data']}"
            else:
                delivery_data["email"] = stock["email"]
                delivery_data["password"] = stock["password"]
                cred_part = f"📧 Email: {stock['email']}\n🔐 Pass: {stock['password']}"
            
            delivery_data["server"] = uinput or "Auto"
            delivery_data["expires"] = f"{stock_expiry} days"
            
            db.update_order(oid, "delivered", delivery_data)
            
            now = datetime.now()
            expiry_date = now + timedelta(days=stock_expiry)
            
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
                f"🙏 Thank you! @{SUPPORT_USERNAME}"
            ]
            msg_text = generate_box("✅ DELIVERY SUCCESSFUL", box_body)
            
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text(msg_text, reply_markup=main_menu(uid), parse_mode="Markdown")
            else:
                await call_or_msg.answer(msg_text, reply_markup=main_menu(uid), parse_mode="Markdown")
        else:
            # No stock – still no admin notify; just pending
            db.update_order(oid, "pending")
            lines = [
                "⏳ *No stock available!*",
                "",
                f"🆔 Order ID: #{oid}",
                "স্টক না থাকায় অর্ডার পেন্ডিং রাখা হয়েছে। অ্যাডমিন শীঘ্রই যুক্ত করবে।",
            ]
            if isinstance(call_or_msg, CallbackQuery):
                await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
            else:
                await call_or_msg.answer("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
        
        # ⛔ NO ADMIN NOTIFICATION FOR VPN/PROXY
        await state.clear()
        return
    
    ##############################################
    # YOUTUBE / NETFLIX / CRUNCHYROLL: PENDING   #
    ##############################################
    db.update_order(oid, "pending")
    lines = [
        "✅ *আপনার অর্ডারটি সফলভাবে এডমিনের কাছে পৌঁছে গেছে!*",
        "",
        f"🆔 Order ID: #{oid}",
        "⏳ কিছুক্ষণ ওয়েট করুন... আপনার অর্ডারটি কনফার্ম করে দেওয়া হবে।",
    ]
    if isinstance(call_or_msg, CallbackQuery):
        await call_or_msg.message.edit_text("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        await call_or_msg.answer("\n".join(lines), reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify Admin for these categories only
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

@dp.message(Order.trxid)
async def get_trx(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx:
        return
    data = await state.get_data()
    method = data.get("pay_method", "Manual")
    mn = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}.get(method, method)
    await process_payment(msg, state, mn, trx)

@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    uid = call.from_user.id
    bal = db.get_balance(uid)
    lines = [
        "💳 *ডিপোজিট পেমেন্ট ও ডিরেক্ট টপআপ*",
        "─────────────────────────────",
        f"💰 আপনার বর্তমান ব্যালেন্স: *{fmt(bal)}*",
        "─────────────────────────────",
        "📌 *টাকা যুক্ত করার উপায়:*",
        "১. নিচের যেকোনো নম্বরে (Send Money) করুন:",
        "   • 💖 *bKash:* `01742958563`",
        "   • 🟠 *Nagad:* `01748506069`",
        "   • 🚀 *Rocket:* `01742958563`",
        "",
        "২. টাকা পাঠানোর পর নিচে *টাকার পরিমাণ* এবং *TrxID* লিখুন:",
        "   *(যেমন: 500 TRX1234567)*",
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
        "",
        "অ্যাডমিন প্যানেল থেকে আইডি সার্চ করে ব্যালেন্স যুক্ত করুন।"
    ]
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_text), parse_mode="Markdown")
        except:
            pass
    await msg.answer("✅ আপনার ডিপোজিট রিকোয়েস্টটি এডমিনের কাছে পাঠানো হয়েছে! শীঘ্রই ভেরিফাই করে ব্যালেন্স যুক্ত করা হবে।", reply_markup=main_menu(uid))
    await state.clear()

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    user_orders = db.get_user_orders(uid, 10)
    if not user_orders:
        lines = ["📦 *Your Orders*", "", "আপনার কোনো অর্ডার হিস্ট্রি পাওয়া যায়নি।"]
    else:
        lines = ["📜 *আপনার সাম্প্রতিক অর্ডারসমূহ:*", ""]
        for o in user_orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name']}")
            lines.append(f"   মূল্য: {fmt(o['amount'])} - Status: {o['status']}")
            if o.get("delivery_data"):
                dd = o["delivery_data"]
                if dd.get("key"):
                    lines.append(f"   🔑 Key: `{dd['key']}`")
                if dd.get("email"):
                    lines.append(f"   📧 Email: `{dd['email']}`")
                if dd.get("password"):
                    lines.append(f"   🔐 Pass: `{dd['password']}`")
                if dd.get("expires"):
                    lines.append(f"   ⏰ {dd['expires']}")
            lines.append("")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back to Main Menu", callback_data="main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

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
        "🔑 *বর্তমান স্টক:*",
    ]
    if stock:
        for s in stock:
            lines.append(f"• `{s['product_id']}`: {s['cnt']} টি")
    else:
        lines.append("কোনো স্টক খালি নেই")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    await call.answer("✅ Approving...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    
    prod = db.get_product(order["product_id"])
    expiry_days = prod.get("expiry_days", 30) if prod else 30
    now = datetime.now()
    expiry_date = now + timedelta(days=expiry_days)
    
    # For YouTube / Netflix / Crunchyroll – manual approval
    db.update_order(oid, "delivered", {"approved_at": now.strftime("%d %B %Y %I:%M %p"), "expiry_days": expiry_days})
    
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
    
    lines = [f"✅ *Order #{oid} Approved & Delivered!*"]
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
        await bot.send_message(order["user_id"], f"❌ *অর্ডার #{oid} বাতিল করা হয়েছে।*", parse_mode="Markdown")
    except:
        pass
    lines = [f"❌ *Order #{oid} Rejected!*"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_orders")
async def all_orders_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Order Management*", reply_markup=admin_orders_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("orders_"))
async def orders_by_status(call: CallbackQuery):
    await call.answer()
    status = call.data.split("_")[1]
    if status == "all":
        all_orders = db.get_all_orders(limit=20)
        title = "All Orders"
    else:
        all_orders = db.get_all_orders(status, limit=20)
        title = f"{status.capitalize()} Orders"
    if not all_orders:
        lines = [f"📦 *{title}*", "", "কোনো অর্ডার পাওয়া যায়নি।"]
    else:
        lines = [f"📦 *{title}*", ""]
        for o in all_orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name'][:20]}")
            lines.append(f"   {fmt(o['amount'])} | User: `{o['user_id']}`")
            lines.append("")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_orders_kb(), parse_mode="Markdown")

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
            return await msg.answer("❌ কোনো ইউজার পাওয়া যায়নি।")
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
        await msg.answer("❌ ইউজার আইডি সঠিক নয়।")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        data = await state.get_data()
        uid = data["uid"]
        
        # Also try to get user's mobile – if available from orders
        orders = db.get_user_orders(uid, 1)
        user_info = orders[0].get("user_input", "") if orders else ""
        
        db.update_balance(uid, amt)
        trx_id = f"ADMIN_{datetime.now():%Y%m%d%H%M%S}"
        db.add_transaction(uid, amt, "admin_add", "Admin", trx_id)
        new_bal = db.get_balance(uid)
        
        # Detailed user notification with box
        now = datetime.now()
        box_body = [
            f"💳 Balance Added!",
            f"👤 User ID: {uid}",
            f"💰 Amount: {fmt(amt)}",
            f"💵 New Balance: {fmt(new_bal)}",
            f"🔢 TrxID: {trx_id}",
            f"📅 Date: {now.strftime('%d %b %Y %I:%M %p')}",
            f"📱 Info: {user_info[:20] if user_info else 'N/A'}",
            "",
            f"🙏 @{SUPPORT_USERNAME}"
        ]
        user_msg = generate_box("💰 BALANCE ADDED", box_body)
        
        try:
            await bot.send_message(uid, user_msg, parse_mode="Markdown")
        except:
            pass
        
        lines = [
            "✅ *ব্যালেন্স যুক্ত করা সফল হয়েছে!*",
            "",
            f"পরিমাণ: {fmt(amt)}",
            f"TrxID: {trx_id}",
            f"নতুন ব্যালেন্স: {fmt(new_bal)}",
        ]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ টাকার পরিমাণ সঠিক নয়।")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📦 *Deliver Order Manually*", "", "Order ID লিখুন:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text.strip())
        order = db.get_order(oid)
        if not order:
            return await msg.answer("❌ অর্ডার পাওয়া যায়নি।")
        await state.update_data(oid=oid)
        lines = [
            f"📦 *Order #{oid}*",
            f"Product: {order['product_name']}",
            f"User ID: {order['user_id']}",
            "",
            "ডেলিভারির তথ্য লিখুন (Email:Password বা Key):",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.deliver_file)
    except:
        await msg.answer("❌ ভুল Order ID")

@dp.message(Admin.deliver_file)
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
    now = datetime.now()
    expiry_date = now + timedelta(days=expiry_days)
    
    db.update_order(oid, "delivered", delivery_data)
    
    cred_part = ""
    if "key" in delivery_data:
        cred_part = f"🔑 Key: {delivery_data['key']}"
    else:
        cred_part = f"📧 Email: {delivery_data['email']}\n🔐 Pass: {delivery_data['password']}"
    
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
    
    lines = [f"✅ *Order #{oid} Delivered Successfully!*"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📨 *Broadcast Message*", "", "সকল ইউজারকে পাঠানো বার্তার টেক্সট লিখুন:"]
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
    lines = [f"✅ *ব্রডকাস্ট সম্পন্ন!*", "", f"মোট {sent}/{len(users)} ইউজারকে বার্তা পাঠানো হয়েছে।"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

# ─── CATEGORY MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_cats")
async def admin_cats(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📂 *Category Management*", reply_markup=admin_cats_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("admincat_"))
async def admin_cat_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    lines = [
        f"📂 *{cat.get('icon', '')} {cat['name']}*",
        f"ID: `{cat_id}`",
        f"প্রোডাক্ট সংখ্যা: {len(prods)}",
    ]
    if cat.get("description"):
        lines.append(f"বর্ণনা: {cat['description']}")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product Here", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="✏️ Edit Category", callback_data=f"editcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Category", callback_data=f"delcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addcat_"))
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = call.data[7:]
    await state.update_data(addcat_parent=None if parent_id == "root" else parent_id)
    lines = ["➕ *Add New Category*", "", "ক্যাটাগরি আইডি লিখুন (স্পেস ছাড়া):", "উদাহরণ: `spotify_prem`"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addcat_id)

@dp.message(Admin.addcat_id)
async def addcat_id(msg: Message, state: FSMContext):
    cid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addcat_id=cid)
    lines = ["ক্যাটাগরির নাম লিখুন (ইমোজি সহ):", "উদাহরণ: 🎵 Spotify Premium"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addcat_name)

@dp.message(Admin.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    lines = ["ক্যাটাগরির সংক্ষিপ্ত বিবরণ লিখুন (অথবা 'skip' লিখুন):"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addcat_desc)

@dp.message(Admin.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    data = await state.get_data()
    db.add_category(data["addcat_id"], data.get("addcat_parent"), data["addcat_name"], desc)
    lines = ["✅ *Category Created Successfully!*", "", f"ID: `{data['addcat_id']}`", f"Name: {data['addcat_name']}"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_id=cat_id)
    lines = ["✏️ *Edit Category*", "", "নতুন নাম লিখুন (পরিবর্তন না করতে চাইলে 'skip' লিখুন):"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"admincat_{cat_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.editcat_name)

@dp.message(Admin.editcat_name)
async def editcat_name_msg(msg: Message, state: FSMContext):
    name = msg.text.strip()
    data = await state.get_data()
    cat_id = data["editcat_id"]
    if name.lower() != "skip":
        db.update_category(cat_id, name=name)
    lines = ["নতুন বিবরণ লিখুন (পরিবর্তন না করতে চাইলে 'skip' লিখুন):"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.editcat_desc)

@dp.message(Admin.editcat_desc)
async def editcat_desc_msg(msg: Message, state: FSMContext):
    desc = msg.text.strip()
    data = await state.get_data()
    cat_id = data["editcat_id"]
    if desc.lower() != "skip":
        db.update_category(cat_id, description=desc)
    lines = ["✅ *Category Updated Successfully!*"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    cid = call.data[7:]
    db.delete_category(cid)
    lines = [f"🗑️ *Category Deleted: {cid}*"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_cats_kb(), parse_mode="Markdown")

# ─── PRODUCT MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_prods")
async def admin_prods(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Product Management*", reply_markup=admin_prods_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("adminprods_"))
async def admin_prods_view(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[11:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    lines = [f"📂 *{cat.get('icon', '')} {cat['name']}*", f"মোট প্রোডাক্ট: {len(prods)}", ""]
    for p in prods[:10]:
        exp = f" ({p.get('expiry_days', 30)}d)" if p.get('expiry_days') else ""
        lines.append(f"• {p['name']}: {fmt(p['price'])}{exp}")
    if not prods:
        lines.append("কোনো প্রোডাক্ট নেই।")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_prods"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addprod_"))
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:] if "_" in call.data else "select"
    if cat_id == "select":
        kb = InlineKeyboardBuilder()
        for cat in db.get_categories():
            kb.row(InlineKeyboardButton(text=f"{cat.get('icon', '📦')} {cat['name']}", callback_data=f"addprodsel_{cat['id']}"))
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_prods"))
        await call.message.edit_text("প্রোডাক্ট যোগ করতে একটি ক্যাটাগরি সিলেক্ট করুন:", reply_markup=kb.as_markup())
        return
    await state.update_data(addprod_cat=cat_id)
    lines = ["➕ *Add Product*", "", "প্রোডাক্ট এর ID দিন (স্পেস ছাড়া):", "উদাহরণ: `vpn_nord_1m`"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"adminprods_{cat_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addprod_id)

@dp.callback_query(lambda c: c.data.startswith("addprodsel_"))
async def addprod_select_cat(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[11:]
    await state.update_data(addprod_cat=cat_id)
    lines = ["➕ *Add Product*", "", "প্রোডাক্ট এর ID দিন (স্পেস ছাড়া):", "উদাহরণ: `vpn_nord_1m`"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data=f"adminprods_{cat_id}"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.addprod_id)

@dp.message(Admin.addprod_id)
async def addprod_id(msg: Message, state: FSMContext):
    pid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addprod_id=pid)
    lines = ["প্রোডাক্ট এর নাম লিখুন:", "উদাহরণ: 🔑 NordVPN Premium (1 Month)"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addprod_name)

@dp.message(Admin.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    lines = ["দাম লিখুন (শুধু সংখ্যা):", "উদাহরণ: 350"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(Admin.addprod_price)

@dp.message(Admin.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        lines = ["বোনাস পয়েন্ট (না থাকলে 0 দিন):"]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.addprod_bonus)
    except:
        await msg.answer("❌ সঠিক মূল্য প্রদান করুন।")

@dp.message(Admin.addprod_bonus)
async def addprod_bonus(msg: Message, state: FSMContext):
    try:
        bonus = float(msg.text.strip())
        await state.update_data(addprod_bonus=bonus)
        lines = ["মেয়াদ/মেয়াদকাল (দিনে লিখুন, যেমন: 30 বা 365):"]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(Admin.addprod_expiry)
    except:
        await msg.answer("❌ সঠিক তথ্য দিন।")

@dp.message(Admin.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        await state.update_data(addprod_expiry=expiry)
        data = await state.get_data()
        cat_id = data["addprod_cat"]
        if cat_id in ["vpn", "proxy"]:
            lines = ["স্টক টাইপ সিলেক্ট করুন:", "• `email_pass` = Email + Password", "• `key_only` = Only Key/Code"]
            await msg.answer("\n".join(lines), parse_mode="Markdown")
            await state.set_state(Admin.addprod_stocktype)
        else:
            stock_type = "manual"
            db.add_product(data["addprod_id"], cat_id, data["addprod_name"], data["addprod_price"], data["addprod_bonus"], stock_type, expiry)
            lines = ["✅ *Product Added Successfully!*"]
            await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
            await state.clear()
    except:
        await msg.answer("❌ সঠিক দিনের সংখ্যা লিখুন।")

@dp.message(Admin.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ["email_pass", "key_only"]:
        return await msg.answer("❌ শুধুমাত্র `email_pass` অথবা `key_only` লিখুন।")
    data = await state.get_data()
    db.add_product(data["addprod_id"], data["addprod_cat"], data["addprod_name"], data["addprod_price"], data["addprod_bonus"], stype, data["addprod_expiry"])
    lines = ["✅ *Product Added Successfully!*"]
    await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_editprod")
async def editprod_list(call: CallbackQuery):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        lines = ["এডিট করার মতো কোনো প্রোডাক্ট নেই।"]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    kb = InlineKeyboardBuilder()
    for p in prods[:20]:
        kb.row(InlineKeyboardButton(text=f"✏️ {p['name']} — {fmt(p['price'])}", callback_data=f"editprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    lines = ["এডিট করতে প্রোডাক্ট নির্বাচন করুন:"]
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod:
        return
    lines = [f"📦 *{prod['name']}*", f"ID: `{pid}`", f"💰 মূল্য: {fmt(prod['price'])}", f"⏰ মেয়াদ: {prod.get('expiry_days', 30)} Days", "", "কোন ফিল্ডটি এডিট করতে চান?"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Name", callback_data=f"editprod_field_{pid}_name"))
    kb.row(InlineKeyboardButton(text="💰 Price", callback_data=f"editprod_field_{pid}_price"))
    kb.row(InlineKeyboardButton(text="⏰ Expiry Days", callback_data=f"editprod_field_{pid}_expiry"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Product", callback_data=f"delprod_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"))
async def editprod_field(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_")
    pid = parts[3]
    field = parts[4]
    await state.update_data(editprod_pid=pid, editprod_field=field)
    lines = [f"✏️ *Edit {field.capitalize()}*", f"Product ID: `{pid}`", "", "নতুন মানটি লিখে পাঠান:"]
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
        elif field == "expiry":
            db.update_product(pid, expiry_days=int(value))
        lines = ["✅ *Product Updated Successfully!*"]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    pid = call.data[8:]
    db.delete_product(pid)
    lines = [f"🗑️ *Product Deleted: {pid}*"]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

# ─── STOCK MANAGEMENT ───
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
        lines = ["🔑 *স্টক স্ট্যাটাস:*", ""]
        for s in counts:
            lines.append(f"📦 Product: `{s['product_id']}`")
            lines.append(f"   टाइপ: {s['stock_type']}")
            lines.append(f"   অবশিষ্ট: {s['cnt']} টি")
            lines.append("")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["➕ *Add Stock*", "", "Product ID লিখুন:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.stock_pid)

@dp.message(Admin.stock_pid)
async def stock_pid(msg: Message, state: FSMContext):
    pid = msg.text.strip()
    prod = db.get_product(pid)
    if not prod:
        return await msg.answer("❌ কোনো প্রোডাক্ট পাওয়া যায়নি।")
    await state.update_data(stock_pid=pid, stock_type=prod.get("stock_type", "key_only"))
    if prod.get("stock_type") == "key_only":
        lines = ["প্রতি লাইনে ১টি করে Key/Code সেন্ড করুন:"]
    else:
        lines = ["প্রতি লাইনে `email:password` ফরম্যাটে অ্যাকাউন্ট পাঠান:"]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
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
    lines_msg = [f"✅ *{added} টি স্টক যুক্ত করা হয়েছে!*"]
    await msg.answer("\n".join(lines_msg), reply_markup=admin_stock_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del(call: CallbackQuery):
    await call.answer()
    all_stock = db.get_all_stock()
    if not all_stock:
        lines = ["মুছে ফেলার মতো কোনো স্টক নেই।"]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    kb = InlineKeyboardBuilder()
    for s in all_stock[:15]:
        status = "✅" if s['is_used'] else "📦"
        display = s['key_data'] or s['email'] or "N/A"
        kb.row(InlineKeyboardButton(text=f"{status} #{s['id']} {display[:20]}...", callback_data=f"delstock_{s['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    lines = ["🗑️ *যে স্টকটি মুছে ফেলতে চান সিলেক্ট করুন:*"]
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del(call)

@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["⛔ *Ban User*", "", "যাকে ব্যান করতে চান তার User ID দিন:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, True)
        await msg.answer(f"⛔ User `{uid}` টির এক্সেস ব্যান করা হয়েছে।", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ ভুল আইডি।")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["✅ *Unban User*", "", "যাকে আনব্যান করতে চান তার User ID দিন:"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, False)
        await msg.answer(f"✅ User `{uid}` সফলভাবে আনব্যান করা হয়েছে।", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ ভুল আইডি।")
    await state.clear()

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
