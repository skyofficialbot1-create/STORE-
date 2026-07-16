#!/usr/bin/env python3
import asyncio, os, sys, sqlite3, json, re
from datetime import datetime, timedelta
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, F, BaseMiddleware
    from aiogram.filters import Command, CommandStart, StateFilter
    from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, TelegramObject, ContentType
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
except ImportError as e:
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
            # Add whatsapp column if not exists
            try:
                conn.execute("ALTER TABLE orders ADD COLUMN whatsapp TEXT")
            except:
                pass

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
            ("yt_3m", "youtube", "▶️ YouTube Premium 3 Months", 200, 0, "email_pass", 90),
            ("nf_1m", "netflix", "🎬 Netflix Premium 1 Month", 150, 0, "email_pass", 30),
            ("cr_1m", "crunchyroll", "🍿 Crunchyroll 1 Month", 200, 0, "email_pass", 30),
            ("vpn_express", "vpn", "🚀 ExpressVPN 1 Month", 350, 0, "email_pass", 30),
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
    def add_order(self, uid, pid, pname, catid, amt, uinput, pmethod, trid, whatsapp=None):
        with self._get_conn() as conn:
            cur = conn.execute("""INSERT INTO orders(user_id,product_id,product_name,category_id,amount,user_input,payment_method,transaction_id,whatsapp)
                                 VALUES(?,?,?,?,?,?,?,?,?)""",
                              (uid, pid, pname, catid, amt, uinput, pmethod, trid, whatsapp))
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
class Order(StatesGroup):
    input = State()
    whatsapp = State()          # for Crunchyroll
    server = State()            # for VPN/Proxy

class DepositState(StatesGroup):
    amount = State()
    trxid = State()
    screenshot = State()

class Admin(StatesGroup):
    addbal_uid = State()
    addbal_amt = State()
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
    stock_data = State()
    deliver_details = State()   # for manual delivery after approve

# ─── HELPERS ───
def fmt(amount):
    return f"৳{amount:,.0f}"

def expiry_date(days):
    dt = datetime.now() + timedelta(days=days)
    return dt.strftime("%d %b %Y, %I:%M %p")

def delivery_message(prod_name, details, expiry_days):
    """Beautiful delivery message for user"""
    lines = [
        "✅ *অর্ডার ডেলিভারি সফল!*",
        "──────────────────────",
        f"📦 *পণ্য:* {prod_name}",
        f"⏰ *মেয়াদ:* {expiry_days} দিন",
    ]
    if details.get("email"):
        lines.append(f"📧 *ইমেইল:* `{details['email']}`")
    if details.get("password"):
        lines.append(f"🔐 *পাসওয়ার্ড:* `{details['password']}`")
    if details.get("key"):
        lines.append(f"🔑 *কী:* `{details['key']}`")
    if details.get("server"):
        lines.append(f"🌍 *সার্ভার:* {details['server']}")

    lines.append("")
    lines.append("📅 *সক্রিয় হয়েছে:* এখন")
    lines.append(f"📅 *মেয়াদ শেষ:* {expiry_date(expiry_days)}")
    lines.append("🟢 *স্ট্যাটাস:* সক্রিয়")
    lines.append("")
    lines.append(f"💬 সমস্যা হলে সাপোর্ট: @{SUPPORT_USERNAME}")
    return "\n".join(lines)

# ─── WELCOME MESSAGE ───
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

# ─── 2-COLUMN MAIN MENU ───
def main_menu(uid):
    kb = InlineKeyboardBuilder()
    cats = db.get_categories()
    # Pair categories into rows of 2 buttons
    pairs = []
    for i in range(0, len(cats), 2):
        pair = cats[i:i+2]
        pairs.append(pair)
    for pair in pairs:
        row = []
        for cat in pair:
            row.append(InlineKeyboardButton(
                text=f"{cat.get('icon', '📦')} {cat['name']}",
                callback_data=f"cat_{cat['id']}"
            ))
        kb.row(*row)
    kb.row(
        InlineKeyboardButton(text="📜 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💳 Deposit", callback_data="deposit_start")
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
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"),
           InlineKeyboardButton(text="📦 Orders", callback_data="admin_orders"))
    kb.row(InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"),
           InlineKeyboardButton(text="📂 Categories", callback_data="admin_cats"))
    kb.row(InlineKeyboardButton(text="📦 Products", callback_data="admin_prods"),
           InlineKeyboardButton(text="🔑 Stock", callback_data="admin_stock"))
    kb.row(InlineKeyboardButton(text="✏️ Edit Product", callback_data="admin_editprod"),
           InlineKeyboardButton(text="⛔ Ban", callback_data="admin_ban"))
    kb.row(InlineKeyboardButton(text="✅ Unban", callback_data="admin_unban"),
           InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ Pending", callback_data="orders_pending"),
           InlineKeyboardButton(text="✅ Delivered", callback_data="orders_delivered"))
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
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="stock_status"),
           InlineKeyboardButton(text="➕ Add Stock", callback_data="stock_add"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Stock", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
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
        await call.message.edit_text(f"📦 *{title}*\n\nনিচের তালিকা থেকে একটি প্রোডাক্ট নির্বাচন করুন:",
                                    reply_markup=products_kb(cat_id), parse_mode="Markdown")
    else:
        await call.answer("❌ এই ক্যাটাগরিতে বর্তমানে কোনো প্রোডাক্ট নেই", show_alert=True)

# ─── ORDER FLOW (BALANCE CHECK & DEDUCTION) ───
@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[6:]
    prod = db.get_product(pid)
    if not prod:
        return
    uid = call.from_user.id
    price = prod["price"]
    bal = db.get_balance(uid)
    if bal < price:
        lines = [
            "❌ *পর্যাপ্ত ব্যালেন্স নেই!*",
            "",
            f"প্রয়োজন: {fmt(price)}",
            f"আপনার ব্যালেন্স: {fmt(bal)}",
            "",
            "অনুগ্রহ করে ব্যালেন্স টপ-আপ করুন।"
        ]
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text="💳 টপ-আপ করুন", callback_data="deposit_start"))
        kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
        await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        return

    # Deduct balance
    success = db.deduct_balance(uid, price)
    if not success:
        await call.answer("❌ ব্যালেন্স কাটা যায়নি! আবার চেষ্টা করুন।", show_alert=True)
        return

    await state.update_data(order_pid=pid, order_prod=prod, deducted=True)

    cat_id = prod["category_id"]
    if cat_id in ["vpn", "proxy"]:
        await call.message.edit_text(
            "🌍 *আপনার পছন্দের সার্ভার/লোকেশন লিখুন:*\n(অথবা Auto-তে বাটন ক্লিক করুন)",
            reply_markup=InlineKeyboardBuilder()
                .row(InlineKeyboardButton(text="⚡ Auto Location", callback_data="vpn_auto"))
                .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
                .as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(Order.server)
    else:
        # YouTube, Netflix, Crunchyroll etc. -> ask email
        prompt = "📧 *আপনার জিমেইল অ্যাড্রেস দিন:*"
        if cat_id == "crunchyroll":
            prompt = "📧 *আপনার জিমেইল অ্যাড্রেস দিন (Crunchyroll):*"
        await call.message.edit_text(prompt, reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
            .as_markup(), parse_mode="Markdown")
        await state.set_state(Order.input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    await process_vpn_order(call.message, call.from_user.id, data, state)

@dp.message(Order.server)
async def vpn_server_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if not text:
        return
    await state.update_data(user_input=text)
    data = await state.get_data()
    await process_vpn_order(msg, msg.from_user.id, data, state)

async def process_vpn_order(message, uid, data, state: FSMContext):
    """Auto deliver from stock for VPN/Proxy"""
    prod = data["order_prod"]
    stock = db.get_available_stock(prod["id"])
    if stock:
        details = {}
        if stock["stock_type"] == "key_only":
            details["key"] = stock["key_data"]
        else:
            details["email"] = stock["email"]
            details["password"] = stock["password"]
        details["server"] = data.get("user_input", "Auto")
        expiry = stock.get("expiry_days", prod.get("expiry_days", 30))
        # create order as delivered
        oid = db.add_order(uid, prod["id"], prod["name"], prod["category_id"],
                           prod["price"], details["server"], "Wallet", "WAL" + uuid4().hex[:10].upper())
        db.update_order(oid, "delivered", details)
        user_text = delivery_message(prod["name"], details, expiry)
        await message.answer(user_text, reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        # No stock -> pending
        oid = db.add_order(uid, prod["id"], prod["name"], prod["category_id"],
                           prod["price"], data.get("user_input", ""), "Wallet", "WAL" + uuid4().hex[:10].upper())
        pending_msg = (
            "⏳ *আপনার অর্ডারটি গৃহীত হয়েছে!*\n"
            f"Order ID: #{oid}\n"
            "স্টক শেষ থাকায় এটি অ্যাডমিনের কাছে পেন্ডিং আছে। শীঘ্রই ডেলিভারি দেয়া হবে।\n"
            f"সাপোর্ট: @{SUPPORT_USERNAME}"
        )
        await message.answer(pending_msg, reply_markup=main_menu(uid), parse_mode="Markdown")
        await notify_admin_new_order(oid, uid, prod["name"], prod["price"], data.get("user_input", ""))
    await state.clear()

# ─── ORDER INPUT FOR MANUAL PRODUCTS ───
@dp.message(Order.input)
async def manual_email_input(msg: Message, state: FSMContext):
    email = msg.text.strip()
    if "@" not in email:  # basic check
        return await msg.answer("❌ সঠিক জিমেইল অ্যাড্রেস দিন।")
    data = await state.get_data()
    prod = data["order_prod"]
    cat_id = prod["category_id"]
    await state.update_data(user_input=email)

    if cat_id == "crunchyroll":
        await msg.answer("📱 *আপনার WhatsApp নম্বর দিন:*\n(দেশের কোড সহ, যেমন: +8801XXXXXXXXX)",
                         reply_markup=InlineKeyboardBuilder()
                             .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
                             .as_markup(),
                         parse_mode="Markdown")
        await state.set_state(Order.whatsapp)
    else:
        # YouTube, Netflix etc. -> confirm and finish
        await finish_manual_order(msg.from_user.id, msg, state)

@dp.message(Order.whatsapp)
async def manual_whatsapp_input(msg: Message, state: FSMContext):
    whatsapp = msg.text.strip()
    if not whatsapp:
        return
    await state.update_data(whatsapp=whatsapp)
    await finish_manual_order(msg.from_user.id, msg, state)

async def finish_manual_order(uid, message, state: FSMContext):
    data = await state.get_data()
    prod = data["order_prod"]
    email = data.get("user_input", "")
    whatsapp = data.get("whatsapp", "")
    price = prod["price"]

    # create pending order
    oid = db.add_order(uid, prod["id"], prod["name"], prod["category_id"],
                       price, email, "Wallet", "WAL" + uuid4().hex[:10].upper(), whatsapp=whatsapp)
    confirmation = (
        "✅ *আপনার অর্ডার সফলভাবে এডমিনের কাছে পৌঁছেছে!*\n\n"
        f"🆔 Order ID: #{oid}\n"
        f"📦 Product: {prod['name']}\n"
        "📧 ইমেইল: " + email + "\n"
        + (f"📱 WhatsApp: {whatsapp}\n" if whatsapp else "") +
        "\n⏳ কিছুক্ষণ অপেক্ষা করুন, আপনার অর্ডারটি কনফার্ম করা হবে।\n"
        f"🚀 দ্রুত কনফার্মেশনের জন্য এডমিনের সাথে যোগাযোগ করুন @{SUPPORT_USERNAME}"
    )
    await message.answer(confirmation, reply_markup=main_menu(uid), parse_mode="Markdown")
    await notify_admin_new_order(oid, uid, prod["name"], price, email, whatsapp)
    await state.clear()

async def notify_admin_new_order(oid, uid, pname, price, email, whatsapp=None):
    user = db.get_user(uid)
    admin_lines = [
        "📦 *নতুন অর্ডার এসেছে!*",
        f"🆔 Order ID: #{oid}",
        f"👤 User: [{user['first_name']}](tg://user?id={uid})" if user else str(uid),
        f"📦 Product: {pname}",
        f"💰 Price: {fmt(price)}",
        f"📧 Email: `{email}`",
    ]
    if whatsapp:
        admin_lines.append(f"📱 WhatsApp: `{whatsapp}`")
    admin_lines.append("")
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, "\n".join(admin_lines),
                                   reply_markup=InlineKeyboardBuilder()
                                       .row(InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
                                            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}"))
                                       .as_markup(),
                                   parse_mode="Markdown")
        except:
            pass

# ─── DEPOSIT SYSTEM (AMOUNT → TRXID → SCREENSHOT) ───
@dp.callback_query(lambda c: c.data == "deposit_start")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.clear()
    await call.message.edit_text(
        "💰 *টপ-আপ এর পরিমাণ লিখুন:*\n\n"
        "টাকার অংক (শুধু সংখ্যা) দিন।",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
            .as_markup()
    )
    await state.set_state(DepositState.amount)

@dp.message(DepositState.amount)
async def deposit_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.strip())
        if amount <= 0:
            raise ValueError
    except:
        return await msg.answer("❌ সঠিক পরিমাণ লিখুন (শুধু সংখ্যা)।")
    await state.update_data(amount=amount)
    await msg.answer(
        "🔢 *ট্রানজেকশন আইডি (TrxID) দিন:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
            .as_markup()
    )
    await state.set_state(DepositState.trxid)

@dp.message(DepositState.trxid)
async def deposit_trxid(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx:
        return
    await state.update_data(trxid=trx)
    await msg.answer(
        "📸 *পেমেন্টের স্ক্রিনশট পাঠান:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="🔙 Cancel", callback_data="main_menu"))
            .as_markup()
    )
    await state.set_state(DepositState.screenshot)

@dp.message(DepositState.screenshot, F.photo)
async def deposit_screenshot(msg: Message, state: FSMContext):
    data = await state.get_data()
    amount = data["amount"]
    trxid = data["trxid"]
    uid = msg.from_user.id
    user = msg.from_user
    photo = msg.photo[-1].file_id

    for aid in ADMIN_IDS:
        try:
            caption = (
                "💰 *নতুন ডিপোজিট রিকোয়েস্ট!*\n\n"
                f"👤 User: [{user.first_name}](tg://user?id={uid})\n"
                f"💵 Amount: {fmt(amount)}\n"
                f"🔢 TrxID: `{trxid}`\n"
                f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            await bot.send_photo(aid, photo, caption=caption, parse_mode="Markdown")
        except:
            pass

    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    await msg.answer(
        "✅ *আপনার ডিপোজিট রিকোয়েস্ট সফলভাবে পাঠানো হয়েছে!*\n\n"
        f"পরিমাণ: {fmt(amount)}\n"
        f"TrxID: `{trxid}`\n\n"
        "কিছুক্ষণের মধ্যে এডমিন চেক করে ব্যালেন্স যুক্ত করে দিবে।\n"
        f"দ্রুত যোগাযোগ: @{SUPPORT_USERNAME}",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await state.clear()

@dp.message(DepositState.screenshot)
async def deposit_no_photo(msg: Message, state: FSMContext):
    await msg.answer("❌ দয়া করে একটি স্ক্রিনশট (ছবি) পাঠান।")

# ─── MY ORDERS ───
@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    await call.answer()
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    if not orders:
        lines = ["📦 *Your Orders*", "", "আপনার কোনো অর্ডার হিস্ট্রি পাওয়া যায়নি।"]
    else:
        lines = ["📜 *সাম্প্রতিক অর্ডারসমূহ:*", ""]
        for o in orders:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name']}")
            lines.append(f"   {fmt(o['amount'])} | Status: {o['status']}")
            if o.get("delivery_data"):
                dd = o["delivery_data"]
                if dd.get("key"): lines.append(f"   🔑 Key: `{dd['key']}`")
                if dd.get("email"): lines.append(f"   📧 Email: `{dd['email']}`")
                if dd.get("password"): lines.append(f"   🔐 Pass: `{dd['password']}`")
            lines.append("")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ─── ADMIN PANEL ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    await call.answer()
    if call.from_user.id not in ADMIN_IDS:
        return
    await state.clear()
    await call.message.edit_text("⚡ *Admin Panel*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    await call.answer()
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    lines = ["📊 *Dashboard*", f"👥 Users: {len(users)}", f"⏳ Pending: {pending}", "", "🔑 *Stock:*"]
    if stock:
        for s in stock:
            lines.append(f"• `{s['product_id']}`: {s['cnt']}")
    else:
        lines.append("No stock")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_orders")
async def admin_orders_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Order Management*", reply_markup=admin_orders_kb(), parse_mode="Markdown")

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
        lines = [f"📦 *{title}*", "", "কোনো অর্ডার নেই।"]
    else:
        lines = [f"📦 *{title}*", ""]
        for o in orders[:10]:
            emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            lines.append(f"{emoji} *#{o['id']}* - {o['product_name'][:20]}")
            lines.append(f"   {fmt(o['amount'])} | User: `{o['user_id']}`")
            lines.append("")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_orders_kb(), parse_mode="Markdown")

# ─── APPROVE/REJECT WITH MANUAL DETAILS ───
@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    await state.update_data(approve_oid=oid)
    await call.message.edit_text(
        f"📦 *Order #{oid}*\n\nঅনুগ্রহ করে ডেলিভারির তথ্য দিন:\n"
        "`email:password` অথবা `key` ফরম্যাটে পাঠান।",
        reply_markup=InlineKeyboardBuilder()
            .row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_orders"))
            .as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(Admin.deliver_details)

@dp.message(Admin.deliver_details)
async def deliver_details_input(msg: Message, state: FSMContext):
    data = await state.get_data()
    oid = data["approve_oid"]
    order = db.get_order(oid)
    text = msg.text.strip()
    if ":" in text:
        email, password = text.split(":", 1)
        delivery = {"email": email.strip(), "password": password.strip()}
    else:
        delivery = {"key": text}

    prod = db.get_product(order["product_id"])
    expiry_days = prod["expiry_days"] if prod else 30
    db.update_order(oid, "delivered", delivery)

    # Notify user
    try:
        user_msg = delivery_message(order["product_name"], delivery, expiry_days)
        await bot.send_message(order["user_id"], user_msg, parse_mode="Markdown")
    except:
        pass

    await msg.answer(f"✅ Order #{oid} delivered.", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer()
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if order:
        db.update_order(oid, "cancelled")
        try:
            await bot.send_message(order["user_id"], f"❌ অর্ডার #{oid} বাতিল করা হয়েছে।")
        except:
            pass
    await call.message.edit_text(f"❌ Order #{oid} rejected.", reply_markup=admin_kb())

# ─── ADD BALANCE ───
@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("User ID দিন:", reply_markup=InlineKeyboardBuilder()
        .row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")).as_markup())
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        user = db.get_user(uid)
        if not user:
            return await msg.answer("❌ ইউজার খুঁজে পাওয়া যায়নি।")
        await state.update_data(uid=uid)
        await msg.answer(f"User: {user['first_name']}\nBalance: {fmt(user['balance'])}\nকত টাকা যোগ করবেন?")
        await state.set_state(Admin.addbal_amt)
    except:
        await msg.answer("ভুল ID")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        data = await state.get_data()
        uid = data["uid"]
        db.update_balance(uid, amt)
        db.add_transaction(uid, amt, "admin_add", "Admin", f"ADMIN_{datetime.now():%Y%m%d%H%M%S}")
        new_bal = db.get_balance(uid)
        await msg.answer(f"✅ {fmt(amt)} যুক্ত হয়েছে। বর্তমান ব্যালেন্স: {fmt(new_bal)}", reply_markup=admin_kb())
        try:
            await bot.send_message(uid, f"🎉 আপনার ব্যালেন্সে {fmt(amt)} যোগ হয়েছে!\nবর্তমান: {fmt(new_bal)}")
        except:
            pass
    except:
        await msg.answer("❌ সঠিক পরিমাণ দিন।")
    await state.clear()

# ─── CATEGORIES ───
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
    lines = [f"📂 {cat.get('icon','')} {cat['name']}", f"ID: `{cat_id}`", f"Products: {len(prods)}"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="✏️ Edit", callback_data=f"editcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delcat_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addcat_"))
async def addcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = call.data[7:] if call.data[7:] != "root" else None
    await state.update_data(addcat_parent=parent_id)
    await call.message.edit_text("➕ নতুন ক্যাটাগরির আইডি দিন (spaces ছাড়া):", reply_markup=InlineKeyboardBuilder()
        .row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_cats")).as_markup())
    await state.set_state(Admin.addcat_id)

@dp.message(Admin.addcat_id)
async def addcat_id(msg: Message, state: FSMContext):
    cid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addcat_id=cid)
    await msg.answer("নাম দিন (ইমোজি সহ):")
    await state.set_state(Admin.addcat_name)

@dp.message(Admin.addcat_name)
async def addcat_name(msg: Message, state: FSMContext):
    await state.update_data(addcat_name=msg.text.strip())
    await msg.answer("সংক্ষিপ্ত বিবরণ (skip করলে ফাঁকা):")
    await state.set_state(Admin.addcat_desc)

@dp.message(Admin.addcat_desc)
async def addcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip() if msg.text.strip().lower() != "skip" else ""
    data = await state.get_data()
    db.add_category(data["addcat_id"], data.get("addcat_parent"), data["addcat_name"], desc)
    await msg.answer("✅ Category created!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("editcat_"))
async def editcat_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(editcat_id=cat_id)
    await call.message.edit_text("নতুন নাম (skip for no change):")
    await state.set_state(Admin.editcat_name)

@dp.message(Admin.editcat_name)
async def editcat_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    data = await state.get_data()
    if name.lower() != "skip":
        with db._get_conn() as conn:
            conn.execute("UPDATE categories SET name=? WHERE id=?", (name, data["editcat_id"]))
            conn.commit()
    await msg.answer("নতুন বিবরণ (skip):")
    await state.set_state(Admin.editcat_desc)

@dp.message(Admin.editcat_desc)
async def editcat_desc(msg: Message, state: FSMContext):
    desc = msg.text.strip()
    data = await state.get_data()
    if desc.lower() != "skip":
        with db._get_conn() as conn:
            conn.execute("UPDATE categories SET description=? WHERE id=?", (desc, data["editcat_id"]))
            conn.commit()
    await msg.answer("✅ Category updated.", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delcat_"))
async def delcat(call: CallbackQuery):
    await call.answer()
    cid = call.data[7:]
    db.delete_category(cid)
    await call.message.edit_text(f"🗑️ Category {cid} deleted.", reply_markup=admin_cats_kb())

# ─── PRODUCTS ───
@dp.callback_query(lambda c: c.data == "admin_prods")
async def admin_prods(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Product Management*", reply_markup=admin_prods_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("adminprods_"))
async def admin_prods_view(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[11:]
    cat = db.get_category(cat_id)
    prods = db.get_products(cat_id)
    lines = [f"📂 {cat['name']} ({len(prods)} products)", ""]
    for p in prods[:10]:
        lines.append(f"• {p['name']} - {fmt(p['price'])} ({p.get('expiry_days', 30)}d)")
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Add Product", callback_data=f"addprod_{cat_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_prods"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("addprod_") and c.data != "addprod_select")
async def addprod_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    await state.update_data(addprod_cat=cat_id)
    await call.message.edit_text("প্রোডাক্ট আইডি (spaces ছাড়া):", reply_markup=InlineKeyboardBuilder()
        .row(InlineKeyboardButton(text="🔙 Back", callback_data=f"adminprods_{cat_id}")).as_markup())
    await state.set_state(Admin.addprod_id)

@dp.callback_query(lambda c: c.data == "addprod_select")
async def addprod_select_cat(call: CallbackQuery, state: FSMContext):
    await call.answer()
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        kb.row(InlineKeyboardButton(text=f"{cat['icon']} {cat['name']}", callback_data=f"addprodsel_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_prods"))
    await call.message.edit_text("ক্যাটাগরি নির্বাচন করুন:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("addprodsel_"))
async def addprodsel(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[11:]
    await state.update_data(addprod_cat=cat_id)
    await call.message.edit_text("প্রোডাক্ট আইডি:")
    await state.set_state(Admin.addprod_id)

@dp.message(Admin.addprod_id)
async def addprod_id(msg: Message, state: FSMContext):
    pid = msg.text.strip().lower().replace(" ", "_")
    await state.update_data(addprod_id=pid)
    await msg.answer("প্রোডাক্ট নাম:")
    await state.set_state(Admin.addprod_name)

@dp.message(Admin.addprod_name)
async def addprod_name(msg: Message, state: FSMContext):
    await state.update_data(addprod_name=msg.text.strip())
    await msg.answer("দাম:")
    await state.set_state(Admin.addprod_price)

@dp.message(Admin.addprod_price)
async def addprod_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        await msg.answer("বোনাস (0 দিলে কিছু না):")
        await state.set_state(Admin.addprod_bonus)
    except:
        await msg.answer("সঠিক সংখ্যা দিন")

@dp.message(Admin.addprod_bonus)
async def addprod_bonus(msg: Message, state: FSMContext):
    try:
        bonus = float(msg.text.strip())
        await state.update_data(addprod_bonus=bonus)
        await msg.answer("মেয়াদ (দিনে):")
        await state.set_state(Admin.addprod_expiry)
    except:
        await msg.answer("সংখ্যা দিন")

@dp.message(Admin.addprod_expiry)
async def addprod_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        await state.update_data(addprod_expiry=expiry)
        data = await state.get_data()
        cat_id = data["addprod_cat"]
        if cat_id in ["vpn", "proxy"]:
            await msg.answer("স্টক টাইপ লিখুন: `email_pass` বা `key_only`")
            await state.set_state(Admin.addprod_stocktype)
        else:
            db.add_product(data["addprod_id"], cat_id, data["addprod_name"],
                          data["addprod_price"], data["addprod_bonus"], None, expiry)
            await msg.answer("✅ Product added!", reply_markup=admin_kb())
            await state.clear()
    except:
        await msg.answer("সংখ্যা দিন")

@dp.message(Admin.addprod_stocktype)
async def addprod_stocktype(msg: Message, state: FSMContext):
    stype = msg.text.strip().lower()
    if stype not in ["email_pass", "key_only"]:
        return await msg.answer("শুধু email_pass বা key_only")
    data = await state.get_data()
    db.add_product(data["addprod_id"], data["addprod_cat"], data["addprod_name"],
                  data["addprod_price"], data["addprod_bonus"], stype, data["addprod_expiry"])
    await msg.answer("✅ Product added!", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_editprod")
async def editprod_list(call: CallbackQuery):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        kb = InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
        await call.message.edit_text("No products.", reply_markup=kb.as_markup())
        return
    kb = InlineKeyboardBuilder()
    for p in prods[:20]:
        kb.row(InlineKeyboardButton(text=f"{p['name']} ({fmt(p['price'])})", callback_data=f"editprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    await call.message.edit_text("Edit product:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("editprod_"))
async def editprod_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    if not prod: return
    lines = [f"📦 {prod['name']} (ID: {pid})", f"Price: {fmt(prod['price'])}", f"Expiry: {prod.get('expiry_days',30)}d"]
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ Name", callback_data=f"editfield_{pid}_name"))
    kb.row(InlineKeyboardButton(text="💰 Price", callback_data=f"editfield_{pid}_price"))
    kb.row(InlineKeyboardButton(text="⏰ Expiry", callback_data=f"editfield_{pid}_expiry"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete", callback_data=f"delprod_{pid}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_editprod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("editfield_"))
async def editfield(call: CallbackQuery, state: FSMContext):
    await call.answer()
    _, pid, field = call.data.split("_")
    await state.update_data(editprod_pid=pid, editprod_field=field)
    await call.message.edit_text(f"New {field}:", reply_markup=InlineKeyboardBuilder()
        .row(InlineKeyboardButton(text="🔙 Back", callback_data=f"editprod_{pid}")).as_markup())
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
        await msg.answer("✅ Updated.", reply_markup=admin_kb())
    except Exception as e:
        await msg.answer(f"Error: {e}")
    await state.clear()

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def delprod(call: CallbackQuery):
    await call.answer()
    pid = call.data[8:]
    db.delete_product(pid)
    await call.message.edit_text(f"🗑️ Product {pid} deleted.", reply_markup=admin_kb())

# ─── STOCK (CATEGORY → PRODUCT SELECTION) ───
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    if not counts:
        await call.message.edit_text("No stock available.", reply_markup=admin_stock_kb())
    else:
        lines = ["🔑 *Stock Status:*", ""]
        for s in counts:
            lines.append(f"• {s['product_id']}: {s['cnt']}")
        await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_category_select(call: CallbackQuery):
    await call.answer()
    kb = InlineKeyboardBuilder()
    for cat in db.get_categories():
        kb.row(InlineKeyboardButton(text=f"{cat['icon']} {cat['name']}", callback_data=f"stockcat_{cat['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("ক্যাটাগরি বাছাই করুন:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("stockcat_"))
async def stock_product_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[9:]
    prods = db.get_products(cat_id)
    if not prods:
        await call.answer("এই ক্যাটাগরিতে কোনো প্রোডাক্ট নেই", show_alert=True)
        return
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.row(InlineKeyboardButton(text=f"{p['name']} ({fmt(p['price'])})", callback_data=f"stockprod_{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="stock_add"))
    await call.message.edit_text("প্রোডাক্ট নির্বাচন করুন:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("stockprod_"))
async def stock_add_data_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[9:]
    prod = db.get_product(pid)
    await state.update_data(stock_pid=pid, stock_type=prod.get("stock_type", "key_only"))
    if prod.get("stock_type") == "key_only":
        prompt = "প্রতি লাইনে একটি কী লিখুন:"
    else:
        prompt = "প্রতি লাইনে `email:password` ফরম্যাটে দিন:"
    await call.message.edit_text(prompt, reply_markup=InlineKeyboardBuilder()
        .row(InlineKeyboardButton(text="🔙 Back", callback_data=f"stockcat_{prod['category_id']}")).as_markup())
    await state.set_state(Admin.stock_data)

@dp.message(Admin.stock_data)
async def stock_data_receive(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_pid"]
    stype = data["stock_type"]
    lines = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    for line in lines:
        if stype == "key_only":
            db.add_stock(pid, stype, key_data=line)
            added += 1
        else:
            if ":" in line:
                email, password = line.split(":", 1)
                db.add_stock(pid, stype, email=email.strip(), password=password.strip())
                added += 1
    await msg.answer(f"✅ {added} stock added.", reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del_list(call: CallbackQuery):
    await call.answer()
    stock = db.get_all_stock()
    if not stock:
        await call.message.edit_text("No stock to delete.", reply_markup=admin_stock_kb())
        return
    kb = InlineKeyboardBuilder()
    for s in stock[:15]:
        display = s['key_data'] or s['email'] or "N/A"
        kb.row(InlineKeyboardButton(text=f"#{s['id']} {display[:20]}", callback_data=f"delstock_{s['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("Select stock to delete:", reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def delstock(call: CallbackQuery):
    await call.answer()
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del_list(call)

# ─── BAN/UNBAN ───
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("⛔ Ban user ID:", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")).as_markup())
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, True)
        await msg.answer(f"⛔ Banned {uid}", reply_markup=admin_kb())
    except:
        await msg.answer("Invalid ID")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("✅ Unban user ID:", reply_markup=InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")).as_markup())
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, False)
        await msg.answer(f"✅ Unbanned {uid}", reply_markup=admin_kb())
    except:
        await msg.answer("Invalid ID")
    await state.clear()

# ─── BROADCAST ───
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.edit_text("📨 Broadcast message:")
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
    await msg.answer(f"✅ Broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

# ─── MAIN ───
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
