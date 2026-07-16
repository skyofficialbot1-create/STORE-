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

# ─── EMOJIS ───
E = {
    "ok":"✅","no":"❌","back":"🔙","home":"🏠",
    "wallet":"💰","admin":"🔐","light":"⚡","rocket":"🚀",
    "star":"✨","money":"💸","box":"📦","clock":"⏰",
    "bell":"🔔","lock":"🔒","unlock":"🔓","key":"🔑",
    "globe":"🌍","chart":"📊","users":"👥","msg":"📨",
    "vpn":"🌐","stock":"🔑","ban":"⛔","unban":"✅"
}

# ─── PRODUCT STRUCTURE ───
MAIN_CATEGORIES = [
    {"id":"freefire","name":"🔥 Free Fire BD","desc":"Diamonds, Weekly, Lite, Likes"},
    {"id":"subscriptions","name":"🎬 Premium Subscriptions","desc":"Netflix, YouTube, Crunchyroll"},
    {"id":"vpn_plus","name":"🌐 VPN Plus","desc":"ExpressVPN, HMA, Proxy, VPS"},
    {"id":"topup","name":"💰 Wallet Top-Up","desc":"Add balance instantly"}
]

SUBCATEGORIES = {
    "freefire":[
        {"id":"ff_diamonds","name":"💎 Diamonds"},
        {"id":"ff_weekly","name":"📆 Weekly"},
        {"id":"ff_lite","name":"⭐ Weekly Lite"},
        {"id":"ff_like","name":"❤️ Like Service"}
    ],
    "subscriptions":[
        {"id":"netflix","name":"🎬 Netflix Premium"},
        {"id":"youtube","name":"▶️ YouTube Premium"},
        {"id":"crunchyroll","name":"🍿 Crunchyroll"}
    ]
}

PRODUCTS = {
    "ff_diamonds":[
        {"id":"ff_25d","name":"💎 25 Diamond","price":20},
        {"id":"ff_50d","name":"💎 50 Diamond","price":35},
        {"id":"ff_115d","name":"💎 115 Diamond","price":79},
        {"id":"ff_240d","name":"💎 240 Diamond","price":156},
        {"id":"ff_355d","name":"💎 355 Diamond","price":237},
        {"id":"ff_505d","name":"💎 505 Diamond","price":336},
        {"id":"ff_610d","name":"💎 610 Diamond","price":390},
        {"id":"ff_850d","name":"💎 850 Diamond","price":558},
        {"id":"ff_1090d","name":"💎 1090 Diamond","price":716},
        {"id":"ff_1240d","name":"💎 1240 Diamond","price":795},
        {"id":"ff_2530d","name":"💎 2530 Diamond","price":1580},
        {"id":"ff_5060d","name":"💎 5060 Diamond","price":3160},
        {"id":"ff_7590d","name":"💎 7590 Diamond","price":4800},
        {"id":"ff_10120d","name":"💎 10120 Diamond","price":6400}
    ],
    "ff_weekly":[
        {"id":"ffw_1","name":"📆 1x Weekly","price":155},
        {"id":"ffw_2","name":"📆 2x Weekly","price":310},
        {"id":"ffw_3","name":"📆 3x Weekly","price":465},
        {"id":"ffw_5","name":"📆 5x Weekly","price":775},
        {"id":"ffw_m","name":"📆 Monthly","price":765},
        {"id":"ffw_2m","name":"📆 2x Monthly","price":1540},
        {"id":"ffw_3m","name":"📆 3x Monthly","price":2295},
        {"id":"ffw_5m","name":"📆 5x Monthly","price":3825},
        {"id":"ffw_1w1m","name":"📆 1Week+1Month","price":930},
        {"id":"ffw_4w1m","name":"📆 4Week+1Month","price":1395}
    ],
    "ff_lite":[
        {"id":"ffl_1","name":"⭐ 1x Weekly Lite","price":40},
        {"id":"ffl_2","name":"⭐ 2x Weekly Lite","price":80},
        {"id":"ffl_3","name":"⭐ 3x Weekly Lite","price":120},
        {"id":"ffl_5","name":"⭐ 5x Weekly Lite","price":200}
    ],
    "ff_like":[
        {"id":"fflk_200","name":"❤️ 200 Likes","price":20},
        {"id":"fflk_1000","name":"❤️ 1000 Likes","price":100},
        {"id":"fflk_2000","name":"❤️ 2000 Likes","price":200},
        {"id":"fflk_3000","name":"❤️ 3000 Likes","price":300},
        {"id":"fflk_4000","name":"❤️ 4000 Likes","price":400},
        {"id":"fflk_5000","name":"❤️ 5000 Likes","price":500},
        {"id":"fflk_6000","name":"❤️ 6000 Likes","price":600},
        {"id":"fflk_12000","name":"❤️ 12000 Likes","price":1200},
        {"id":"fflk_24000","name":"❤️ 24000 Likes","price":2400},
        {"id":"fflk_48000","name":"❤️ 48000 Likes","price":4800}
    ],
    "netflix":[
        {"id":"nf_single","name":"🎬 Single Profile (1M)","price":400},
        {"id":"nf_full","name":"🎬 Full Account (1M)","price":1830}
    ],
    "youtube":[
        {"id":"yt_1m","name":"▶️ 1 Month","price":100},
        {"id":"yt_3m","name":"▶️ 3 Months","price":200},
        {"id":"yt_6m","name":"▶️ 6 Months","price":300},
        {"id":"yt_1y","name":"▶️ 1 Year","price":490}
    ],
    "crunchyroll":[
        {"id":"cr_shared","name":"🍿 Shared (1M)","price":200},
        {"id":"cr_full1","name":"🍿 Full (1M)","price":450},
        {"id":"cr_full12","name":"🍿 Full (12M)","price":1840}
    ],
    "vpn_plus":[
        {"id":"vpn_express","name":"🔑 ExpressVPN (1M)","price":350,"stock_type":"key"},
        {"id":"vpn_hma","name":"🔑 HMA VPN (1M)","price":250,"stock_type":"key"},
        {"id":"vpn_vpnip","name":"🔑 VPN IP (1M)","price":300,"stock_type":"key"},
        {"id":"vpn_vanish","name":"🔑 Vanish VPN (1M)","price":280,"stock_type":"key"},
        {"id":"vpn_proton","name":"🔑 Proton VPN (1M)","price":320,"stock_type":"key"},
        {"id":"proxy_dedicated","name":"🌐 Dedicated Proxy IP (1M)","price":200,"stock_type":"proxy"},
        {"id":"vps_basic","name":"🖥️ Basic VPS (1M)","price":800,"stock_type":"vps"},
        {"id":"vps_premium","name":"🖥️ Premium VPS (1M)","price":1500,"stock_type":"vps"}
    ],
    "topup":[
        {"id":"bal_100","name":"💰 100 Tk","price":100,"bonus":0},
        {"id":"bal_200","name":"💰 200 Tk (+5 Bonus)","price":200,"bonus":5},
        {"id":"bal_500","name":"💰 500 Tk (+20 Bonus)","price":500,"bonus":20},
        {"id":"bal_1000","name":"💰 1000 Tk (+50 Bonus)","price":1000,"bonus":50},
        {"id":"bal_2000","name":"💰 2000 Tk (+120 Bonus)","price":2000,"bonus":120},
        {"id":"bal_5000","name":"💰 5000 Tk (+350 Bonus)","price":5000,"bonus":350}
    ]
}

def get_product(subcat_id, prod_id):
    for p in PRODUCTS.get(subcat_id, []):
        if p["id"] == prod_id:
            return p
    return None

def fmt(amount):
    return f"৳{amount:,.0f}"

def box_text(title, content):
    """Create a beautiful box design"""
    lines = content.strip().split('\n')
    max_len = max(len(line) for line in lines) if lines else 0
    max_len = max(max_len, len(title) + 4)
    
    box = f"╔{'═' * (max_len + 2)}╗\n"
    box += f"║ {title:^{max_len}} ║\n"
    box += f"╠{'═' * (max_len + 2)}╣\n"
    for line in lines:
        box += f"║ {line:<{max_len}} ║\n"
    box += f"╚{'═' * (max_len + 2)}╝"
    return box

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
            c.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                balance REAL DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
            
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
            
            c.execute("""CREATE TABLE IF NOT EXISTS stock_keys(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key_data TEXT,
                is_used INTEGER DEFAULT 0,
                expiry_days INTEGER DEFAULT 30,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")
    
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
    
    def add_vpn_config(self, oid, uid, ctype, cdata, loc, days=30):
        with self._conn() as c:
            c.execute("INSERT INTO vpn_configs(order_id, user_id, config_type, config_data, server_location, expiry_days) VALUES(?,?,?,?,?,?)", 
                     (oid, uid, ctype, cdata, loc, days))
    
    def get_vpn_config(self, oid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM vpn_configs WHERE order_id=? ORDER BY id DESC LIMIT 1", (oid,)).fetchone()
        return dict(r) if r else None
    
    def add_stock_keys_bulk(self, cat, keys, days=30):
        with self._conn() as c:
            added = 0
            for k in keys:
                if k.strip():
                    c.execute("INSERT INTO stock_keys(category, key_data, expiry_days) VALUES(?,?,?)", (cat, k.strip(), days))
                    added += 1
            return added
    
    def get_available_key(self, cat):
        with self._conn() as c:
            r = c.execute("SELECT * FROM stock_keys WHERE category=? AND is_used=0 ORDER BY id LIMIT 1", (cat,)).fetchone()
            if r:
                c.execute("UPDATE stock_keys SET is_used=1 WHERE id=?", (r["id"],))
                return dict(r)
            return None
    
    def get_stock_counts(self):
        with self._conn() as c:
            rows = c.execute("SELECT category, COUNT(*) as cnt FROM stock_keys WHERE is_used=0 GROUP BY category").fetchall()
        return [dict(r) for r in rows]
    
    def get_all_stock(self, cat=None):
        with self._conn() as c:
            if cat:
                rows = c.execute("SELECT * FROM stock_keys WHERE category=? ORDER BY id DESC LIMIT 100", (cat,)).fetchall()
            else:
                rows = c.execute("SELECT * FROM stock_keys ORDER BY category, id DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]
    
    def delete_stock_key(self, kid):
        with self._conn() as c:
            cur = c.execute("DELETE FROM stock_keys WHERE id=?", (kid,))
            return cur.rowcount > 0

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
    stock_cat = State()
    stock_keys = State()
    ban_uid = State()
    unban_uid = State()
    restore_db = State()

# ─── KEYBOARDS ───
def main_menu(uid):
    kb = InlineKeyboardBuilder()
    for cat in MAIN_CATEGORIES:
        kb.row(InlineKeyboardButton(text=cat["name"], callback_data=f"main_{cat['id']}"))
    kb.row(
        InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
        InlineKeyboardButton(text="💰 My Wallet", callback_data="my_wallet")
    )
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

def subcategory_kb(main_cat):
    subs = SUBCATEGORIES.get(main_cat)
    if not subs:
        return products_kb(main_cat)
    kb = InlineKeyboardBuilder()
    for s in subs:
        kb.row(InlineKeyboardButton(text=s["name"], callback_data=f"sub_{main_cat}|{s['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="main_menu"))
    return kb.as_markup()

def products_kb(subcat):
    prods = PRODUCTS.get(subcat, [])
    kb = InlineKeyboardBuilder()
    for p in prods:
        if "bonus" in p and p["bonus"] > 0:
            txt = f"{p['name']} (+{fmt(p['bonus'])}) — {fmt(p['price'])}"
        else:
            txt = f"{p['name']} — {fmt(p['price'])}"
        kb.row(InlineKeyboardButton(text=txt, callback_data=f"order_{subcat}|{p['id']}"))
    kb.row(
        InlineKeyboardButton(text="🔙 Back", callback_data="show_main"),
        InlineKeyboardButton(text="🏠 Home", callback_data="main_menu")
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
        InlineKeyboardButton(text="📦 Deliver", callback_data="admin_deliver")
    )
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(
        InlineKeyboardButton(text="🌐 VPN Manage", callback_data="admin_vpn"),
        InlineKeyboardButton(text="🔑 Stock Manage", callback_data="admin_stock")
    )
    kb.row(
        InlineKeyboardButton(text="⛔ Ban User", callback_data="admin_ban"),
        InlineKeyboardButton(text="✅ Unban User", callback_data="admin_unban")
    )
    kb.row(InlineKeyboardButton(text="💾 Restore DB", callback_data="admin_restore"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_orders_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⏳ Pending Orders", callback_data="orders_pending"))
    kb.row(InlineKeyboardButton(text="✅ Delivered Orders", callback_data="orders_delivered"))
    kb.row(InlineKeyboardButton(text="❌ Cancelled Orders", callback_data="orders_cancelled"))
    kb.row(InlineKeyboardButton(text="📋 All Orders", callback_data="orders_all"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def order_actions_kb(oid, status):
    kb = InlineKeyboardBuilder()
    if status == "pending":
        kb.row(
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
        )
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="orders_pending"))
    return kb.as_markup()

def admin_vpn_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 VPN Orders", callback_data="vpn_orders"),
        InlineKeyboardButton(text="➕ Add VPN Config", callback_data="vpn_add")
    )
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="vpn_stock_status"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📋 View Stock", callback_data="stock_view"),
        InlineKeyboardButton(text="➕ Add Keys", callback_data="stock_add")
    )
    kb.row(InlineKeyboardButton(text="🗑️ Delete Key", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu"))
    return kb.as_markup()

# ─── WELCOME MESSAGE ───
WELCOME = """╔═══════════════════════════════════╗
║   🌟 Welcome to SKY STORE BD! 🌟   ║
╠═══════════════════════════════════╣
║                                    ║
║  ⚡ Instant Delivery               ║
║  💎 Best Price in Bangladesh       ║
║  🛡️ 100% Trusted & Safe           ║
║                                    ║
╠═══════════════════════════════════╣
║  🔥 Free Fire (Diamonds/Weekly)   ║
║  🎬 Netflix | YouTube Premium     ║
║  🍿 Crunchyroll Premium           ║
║  🌐 VPN Plus (Express/HMA/VPS)    ║
║  💰 Wallet Top-Up with Bonus      ║
║                                    ║
╠═══════════════════════════════════╣
║  📞 Support: @FBSKYSUPPORT        ║
║  👇 Select a category below!      ║
║                                    ║
╚═══════════════════════════════════╝"""

# ─── COMMANDS ───
@dp.message(CommandStart())
async def start(msg: Message):
    user = msg.from_user
    db.create_user(user.id, user.first_name, user.username)
    await msg.answer(WELCOME, reply_markup=main_menu(user.id))

@dp.callback_query(lambda c: c.data == "main_menu")
async def go_main(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(WELCOME, reply_markup=main_menu(call.from_user.id))

@dp.callback_query(lambda c: c.data == "show_main")
async def show_main_cats(call: CallbackQuery, state: FSMContext):
    await state.clear()
    txt = "╔═══════════════════════════════════╗\n"
    txt += "║      📂 Select Category          ║\n"
    txt += "╚═══════════════════════════════════╝"
    await call.message.edit_text(txt, reply_markup=main_menu(call.from_user.id))

@dp.callback_query(lambda c: c.data.startswith("main_"))
async def main_cat(call: CallbackQuery, state: FSMContext):
    main_id = call.data.split("_")[1]
    await state.update_data(main_cat=main_id)
    
    cat_info = next((c for c in MAIN_CATEGORIES if c["id"] == main_id), None)
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  {cat_info['name']:^35}  ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  {cat_info['desc']:^35}  ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=subcategory_kb(main_id))

@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def sub_cat(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_", 1)
    main, sub = rest.split("|")
    await state.update_data(subcat_id=sub)
    
    sub_info = next((s for s in SUBCATEGORIES.get(main, []) if s["id"] == sub), None)
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  {sub_info['name']:^35}  ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=products_kb(sub))

@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_", 1)
    sub, pid = rest.split("|")
    prod = get_product(sub, pid)
    if not prod:
        return await call.answer("❌ Invalid product")
    
    await state.update_data(subcat_id=sub, prod=prod)
    
    if sub == "vpn_plus":
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  🌍 VPN Configuration             ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Product: {prod['name']:<25} ║\n"
        txt += f"║  Price: {fmt(prod['price']):<28} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  🌍 Enter server location         ║\n"
        txt += f"║  (or type 'auto')                 ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Auto", callback_data="vpn_auto")]
        ]))
        await state.set_state(Order.input)
    
    elif sub == "topup":
        await state.update_data(user_input="Wallet TopUp")
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  💳 Payment Details               ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Product: {prod['name']:<25} ║\n"
        txt += f"║  Price: {fmt(prod['price']):<28} ║\n"
        if prod.get("bonus", 0) > 0:
            txt += f"║  Bonus: +{fmt(prod['bonus']):<26} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=payment_kb())
        await state.set_state(Order.payment)
    
    else:
        prompt = "🎮 Enter your Player ID:" if "ff_" in sub else "📧 Enter your Email:"
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  📝 Order Information             ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Product: {prod['name']:<25} ║\n"
        txt += f"║  Price: {fmt(prod['price']):<28} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  {prompt:<35} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products")]
        ]))
        await state.set_state(Order.input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💳 Payment Details               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Product: {data['prod']['name']:<25} ║\n"
    txt += f"║  Server: Auto                     ║\n"
    txt += f"║  Price: {fmt(data['prod']['price']):<28} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=payment_kb())
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text) < 2:
        return await msg.answer("❌ Please enter valid details")
    
    await state.update_data(user_input=text)
    data = await state.get_data()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💳 Payment Details               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Product: {data['prod']['name']:<25} ║\n"
    txt += f"║  Price: {fmt(data['prod']['price']):<28} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt, reply_markup=payment_kb())
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
            txt = f"╔═══════════════════════════════════╗\n"
            txt += f"║  ❌ Insufficient Balance          ║\n"
            txt += f"╠═══════════════════════════════════╣\n"
            txt += f"║  Need: {fmt(price):<30} ║\n"
            txt += f"║  Have: {fmt(bal):<30} ║\n"
            txt += f"╚═══════════════════════════════════╝"
            
            return await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Top Up", callback_data="main_topup")]
            ]))
        
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    
    else:
        nums = {
            "bkash": "01742958563",
            "nagad": "01748506069",
            "rocket": "01742958563"
        }
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  💳 Send Payment                  ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Amount: {fmt(price):<28} ║\n"
        txt += f"║  Method: {method.upper():<28} ║\n"
        txt += f"║  Number: {nums.get(method, ''):<28} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  📝 Send payment & enter TrxID    ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment")]
        ]))
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
    
    if sub == "topup":
        bonus = prod.get("bonus", 0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        
        bal = db.get_balance(uid)
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Top-Up Successful!            ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Added: {fmt(total):<29} ║\n"
        if bonus > 0:
            txt += f"║  Bonus: +{fmt(bonus):<27} ║\n"
        txt += f"║  Balance: {fmt(bal):<27} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=main_menu(uid))
    
    elif sub == "vpn_plus":
        stype = prod.get("stock_type", "key")
        stock = db.get_available_key(stype)
        
        if stock:
            key = stock["key_data"]
            days = stock["expiry_days"]
        else:
            key = f"DEMO-{uuid4().hex[:12]}"
            days = 30
        
        db.add_vpn_config(oid, uid, stype, key, uinput or "Auto", days)
        db.update_order(oid, "delivered")
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ VPN Delivered!                ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Key: {key:<31} ║\n"
        txt += f"║  Server: {uinput or 'Auto':<28} ║\n"
        txt += f"║  Expires: {days} days{' ' * (25 - len(str(days)))} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=main_menu(uid))
    
    else:
        db.update_order(oid, "pending")
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Order Placed!                 ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Order ID: #{oid:<26} ║\n"
        txt += f"║  Status: Pending Verification     ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await call.message.edit_text(txt, reply_markup=main_menu(uid))
    
    # Notify admin with beautiful order details
    user = db.get_user(uid)
    order = db.get_order(oid)
    
    admin_txt = f"╔═══════════════════════════════════╗\n"
    admin_txt += f"║  📦 NEW ORDER RECEIVED            ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Order ID: #{oid:<26} ║\n"
    admin_txt += f"║  User ID: {uid:<27} ║\n"
    admin_txt += f"║  Name: {user['first_name']:<30} ║\n"
    admin_txt += f"║  Username: @{user['username'] or 'N/A':<24} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Product: {prod['name']:<27} ║\n"
    admin_txt += f"║  Category: {sub:<26} ║\n"
    admin_txt += f"║  Amount: {fmt(price):<28} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  User Input: {uinput:<24} ║\n"
    admin_txt += f"║  Payment: {pmethod:<27} ║\n"
    admin_txt += f"║  TrxID: {trx:<29} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Time: {order['created_at']:<30} ║\n"
    admin_txt += f"╚═══════════════════════════════════╝"
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_txt, reply_markup=kb.as_markup())
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
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Top-Up Successful!            ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Added: {fmt(total):<29} ║\n"
        if bonus > 0:
            txt += f"║  Bonus: +{fmt(bonus):<27} ║\n"
        txt += f"║  Balance: {fmt(bal):<27} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=main_menu(uid))
    
    elif sub == "vpn_plus":
        stype = prod.get("stock_type", "key")
        stock = db.get_available_key(stype)
        
        if stock:
            key = stock["key_data"]
            days = stock["expiry_days"]
        else:
            key = f"DEMO-{uuid4().hex[:12]}"
            days = 30
        
        db.add_vpn_config(oid, uid, stype, key, uinput or "Auto", days)
        db.update_order(oid, "delivered")
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ VPN Delivered!                ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Key: {key:<31} ║\n"
        txt += f"║  Server: {uinput or 'Auto':<28} ║\n"
        txt += f"║  Expires: {days} days{' ' * (25 - len(str(days)))} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=main_menu(uid))
    
    else:
        db.update_order(oid, "pending")
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Order Placed!                 ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Order ID: #{oid:<26} ║\n"
        txt += f"║  Status: Pending Verification     ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=main_menu(uid))
    
    # Notify admin
    user = db.get_user(uid)
    order = db.get_order(oid)
    
    admin_txt = f"╔═══════════════════════════════════╗\n"
    admin_txt += f"║  📦 NEW ORDER RECEIVED            ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Order ID: #{oid:<26} ║\n"
    admin_txt += f"║  User ID: {uid:<27} ║\n"
    admin_txt += f"║  Name: {user['first_name']:<30} ║\n"
    admin_txt += f"║  Username: @{user['username'] or 'N/A':<24} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Product: {prod['name']:<27} ║\n"
    admin_txt += f"║  Category: {sub:<26} ║\n"
    admin_txt += f"║  Amount: {fmt(price):<28} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  User Input: {uinput:<24} ║\n"
    admin_txt += f"║  Payment: {pmethod:<27} ║\n"
    admin_txt += f"║  TrxID: {trx:<29} ║\n"
    admin_txt += f"╠═══════════════════════════════════╣\n"
    admin_txt += f"║  Time: {order['created_at']:<30} ║\n"
    admin_txt += f"╚═══════════════════════════════════╝"
    
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{oid}"),
        InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{oid}")
    )
    
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, admin_txt, reply_markup=kb.as_markup())
        except:
            pass
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "back_to_payment")
async def back_pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💳 Payment Details               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Product: {data['prod']['name']:<25} ║\n"
    txt += f"║  Price: {fmt(data['prod']['price']):<28} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=payment_kb())
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
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💰 Your Wallet                   ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Balance: {fmt(bal):<27} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=main_menu(uid))

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 10)
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  📦 Your Orders                   ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    if orders:
        for o in orders[:5]:
            status_emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
            txt += f"║  {status_emoji} #{o['id']} {o['product_name'][:20]:<15} ║\n"
            txt += f"║     {fmt(o['amount'])} - {o['status']:<20} ║\n"
    else:
        txt += f"║  No orders yet.                   ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=main_menu(uid))

# ─── ADMIN PANEL ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("❌ Unauthorized")
    
    await state.clear()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🔐 Admin Panel                   ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Manage your store efficiently    ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    
    s = "\n".join(f"║  {c['category']}: {c['cnt']} available{' ' * (20 - len(c['category']) - len(str(c['cnt'])))} ║" for c in stock) or "║  No stock available{' ' * 18} ║\n"
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  📊 Dashboard                     ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  👥 Total Users: {len(users):<20} ║\n"
    txt += f"║  ⏳ Pending Orders: {pending:<17} ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  🔑 Stock Status                  ║\n"
    txt += f"{s}"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_kb())

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
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  📦 {title:<27} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  No orders found.                 ║\n"
        txt += f"╚═══════════════════════════════════╝"
        return await call.message.edit_text(txt, reply_markup=admin_orders_kb())
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  📦 {title:<27} ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    for o in orders[:10]:
        status_emoji = {"pending": "⏳", "delivered": "✅", "cancelled": "❌"}.get(o['status'], "⏳")
        txt += f"║  {status_emoji} #{o['id']} {o['product_name'][:18]:<16} ║\n"
        txt += f"║     {fmt(o['amount'])} by {o['user_id']:<15} ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_orders_kb())

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    
    if not order:
        return await call.answer("❌ Order not found")
    
    db.update_order(oid, "delivered")
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ Order Approved!               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Order #{oid:<26} ║\n"
    txt += f"║  Status: Delivered                ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_kb())
    
    try:
        user_txt = f"╔═══════════════════════════════════╗\n"
        user_txt += f"║  ✅ Order Delivered!              ║\n"
        user_txt += f"╠═══════════════════════════════════╣\n"
        user_txt += f"║  Order #{oid:<26} ║\n"
        user_txt += f"║  {order['product_name']:<35} ║\n"
        user_txt += f"╚═══════════════════════════════════╝"
        
        await bot.send_message(order["user_id"], user_txt)
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery, bot: Bot):
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    
    if not order:
        return await call.answer("❌ Order not found")
    
    db.update_order(oid, "cancelled")
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ❌ Order Rejected!               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Order #{oid:<26} ║\n"
    txt += f"║  Status: Cancelled                ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_kb())
    
    try:
        user_txt = f"╔═══════════════════════════════════╗\n"
        user_txt += f"║  ❌ Order Cancelled               ║\n"
        user_txt += f"╠═══════════════════════════════════╣\n"
        user_txt += f"║  Order #{oid:<26} ║\n"
        user_txt += f"║  {order['product_name']:<35} ║\n"
        user_txt += f"╚═══════════════════════════════════╝"
        
        await bot.send_message(order["user_id"], user_txt)
    except:
        pass

@dp.callback_query(lambda c: c.data == "admin_users")
async def users_list(call: CallbackQuery):
    users = db.get_all_users()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  👥 Users ({len(users)}){' ' * (25 - len(str(len(users))))} ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    for u in users[:15]:
        status = "🔒" if u['is_banned'] else "👤"
        txt += f"║  {status} {u['user_id']} {u['first_name'][:15]:<15} ║\n"
        txt += f"║     Balance: {fmt(u['balance']):<22} ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_kb())

@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💰 Add Balance                   ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send User ID:                 ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]))
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        user = db.get_user(uid)
        
        if not user:
            return await msg.answer("❌ User not found")
        
        await state.update_data(uid=uid)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  💰 Add Balance                   ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  User: {user['first_name']:<30} ║\n"
        txt += f"║  Current Balance: {fmt(user['balance']):<17} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  📝 Send amount to add:           ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt)
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
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Balance Added!                ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Amount: {fmt(amt):<28} ║\n"
        txt += f"║  New Balance: {fmt(new_bal):<23} ║\n"
        txt += f"║  Added by: Admin                  ║\n"
        txt += f"║  Time: {datetime.now():%Y-%m-%d %H:%M}{' ' * 15} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=admin_kb())
        
        try:
            user_txt = f"╔═══════════════════════════════════╗\n"
            user_txt += f"║  💰 Balance Added!                ║\n"
            user_txt += f"╠═══════════════════════════════════╣\n"
            user_txt += f"║  Amount: {fmt(amt):<28} ║\n"
            user_txt += f"║  New Balance: {fmt(new_bal):<23} ║\n"
            user_txt += f"║  Added by: Admin                  ║\n"
            user_txt += f"║  Time: {datetime.now():%Y-%m-%d %H:%M}{' ' * 15} ║\n"
            user_txt += f"╚═══════════════════════════════════╝"
            
            await bot.send_message(uid, user_txt)
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid amount")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  📦 Deliver Order                 ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send Order ID:                ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]))
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        
        if not order:
            return await msg.answer("❌ Order not found")
        
        await state.update_data(oid=oid)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  📦 Order #{oid:<26} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Product: {order['product_name']:<27} ║\n"
        txt += f"║  User: {order['user_id']:<30} ║\n"
        txt += f"║  Amount: {fmt(order['amount']):<28} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  📸 Send photo or type 'done'     ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt)
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
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ Order Delivered!              ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Order #{oid:<26} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt, reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  📨 Broadcast Message             ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send message to broadcast:    ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt)
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
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ Broadcast Sent!               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Sent: {sent}/{len(users)}{' ' * (28 - len(str(sent)) - len(str(len(users))))} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt, reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_vpn")
async def vpn_menu(call: CallbackQuery):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🌐 VPN Management                ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_vpn_kb())

@dp.callback_query(lambda c: c.data == "vpn_orders")
async def vpn_orders(call: CallbackQuery):
    orders = db.get_all_orders(limit=50)
    vpn_orders = [o for o in orders if "vpn" in o["category_name"].lower() or "vpn" in o["product_name"].lower()]
    
    if not vpn_orders:
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  🌐 VPN Orders                    ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  No VPN orders found.             ║\n"
        txt += f"╚═══════════════════════════════════╝"
        return await call.message.edit_text(txt, reply_markup=admin_vpn_kb())
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🌐 VPN Orders ({len(vpn_orders)}){' ' * (22 - len(str(len(vpn_orders))))} ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    for o in vpn_orders[:10]:
        txt += f"║  #{o['id']} {o['product_name'][:20]:<18} ║\n"
        txt += f"║     User: {o['user_id']:<28} ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_vpn_kb())

@dp.callback_query(lambda c: c.data == "vpn_add")
async def vpn_add_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ➕ Add VPN Config                ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send Order ID:                ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_vpn")]
    ]))
    await state.set_state(Admin.vpn_oid)

@dp.message(Admin.vpn_oid)
async def vpn_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        
        if not order:
            return await msg.answer("❌ Order not found")
        
        await state.update_data(vpn_oid=oid)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  🌐 VPN Config for #{oid:<20} ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  📝 Send config data:             ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt)
        await state.set_state(Admin.vpn_data)
    
    except:
        await msg.answer("❌ Invalid Order ID")

@dp.message(Admin.vpn_data)
async def vpn_data(msg: Message, state: FSMContext):
    config = msg.text.strip()
    await state.update_data(vpn_data=config)
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🌍 Server Location               ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Enter server location:        ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt)
    await state.set_state(Admin.vpn_loc)

@dp.message(Admin.vpn_loc)
async def vpn_loc(msg: Message, state: FSMContext, bot: Bot):
    loc = msg.text.strip()
    data = await state.get_data()
    oid = data["vpn_oid"]
    config = data["vpn_data"]
    order = db.get_order(oid)
    
    db.add_vpn_config(oid, order["user_id"], "Manual Config", config, loc, 30)
    db.update_order(oid, "delivered")
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ VPN Config Added!             ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Order #{oid:<26} ║\n"
    txt += f"║  Server: {loc:<28} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt, reply_markup=admin_kb())
    
    try:
        user_txt = f"╔═══════════════════════════════════╗\n"
        user_txt += f"║  🌐 VPN Ready!                    ║\n"
        user_txt += f"╠═══════════════════════════════════╣\n"
        user_txt += f"║  Server: {loc:<28} ║\n"
        user_txt += f"║  Config:\n`{config[:400]}`{' ' * (30 - min(len(config), 400))} ║\n"
        user_txt += f"╚═══════════════════════════════════╝"
        
        await bot.send_message(order["user_id"], user_txt, parse_mode="Markdown")
    except:
        pass
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "vpn_stock_status")
async def vpn_stock(call: CallbackQuery):
    counts = db.get_stock_counts()
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🔑 Stock Status                  ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    if counts:
        for c in counts:
            txt += f"║  {c['category']}: {c['cnt']} available{' ' * (20 - len(c['category']) - len(str(c['cnt'])))} ║\n"
    else:
        txt += f"║  No stock available.              ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_vpn_kb())

@dp.callback_query(lambda c: c.data == "admin_stock")
async def stock_menu(call: CallbackQuery):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🔑 Stock Management              ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_stock_kb())

@dp.callback_query(lambda c: c.data == "stock_view")
async def stock_view(call: CallbackQuery):
    stock = db.get_all_stock()
    
    if not stock:
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  🔑 Stock View                    ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  No stock available.              ║\n"
        txt += f"╚═══════════════════════════════════╝"
        return await call.message.edit_text(txt, reply_markup=admin_stock_kb())
    
    by_cat = {}
    for s in stock:
        c = s["category"]
        by_cat.setdefault(c, {"total": 0, "used": 0, "avail": 0})
        by_cat[c]["total"] += 1
        if s["is_used"]:
            by_cat[c]["used"] += 1
        else:
            by_cat[c]["avail"] += 1
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🔑 Stock Overview                ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    
    for c, v in by_cat.items():
        txt += f"║  {c.upper()}:                         ║\n"
        txt += f"║    Total: {v['total']:<27} ║\n"
        txt += f"║    Available: {v['avail']:<23} ║\n"
        txt += f"║    Used: {v['used']:<28} ║\n"
    
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=admin_stock_kb())

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add(call: CallbackQuery, state: FSMContext):
    cats = {"key": "🔑 Keys", "proxy": "🌐 Proxy", "vps": "🖥️ VPS"}
    
    kb = InlineKeyboardBuilder()
    for k, v in cats.items():
        kb.row(InlineKeyboardButton(text=v, callback_data=f"stockcat_{k}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ➕ Add Stock                     ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Select stock type:            ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=kb.as_markup())
    await state.set_state(Admin.stock_cat)

@dp.callback_query(lambda c: c.data.startswith("stockcat_"))
async def stock_cat_chosen(call: CallbackQuery, state: FSMContext):
    cat = call.data.split("_")[1]
    await state.update_data(stock_cat=cat)
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ➕ Add {cat.upper()} Keys{' ' * (25 - len(cat))} ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send keys (one per line):     ║\n"
    txt += f"║  📎 Or send a text file           ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="stock_add")]
    ]))
    await state.set_state(Admin.stock_keys)

@dp.message(Admin.stock_keys, F.text)
async def stock_keys_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    cat = data["stock_cat"]
    keys = [k.strip() for k in msg.text.split("\n") if k.strip()]
    
    if not keys:
        return await msg.answer("❌ No keys found")
    
    added = db.add_stock_keys_bulk(cat, keys)
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ Stock Added!                  ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  Category: {cat.upper():<26} ║\n"
    txt += f"║  Added: {added} keys{' ' * (27 - len(str(added)))} ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await msg.answer(txt, reply_markup=admin_stock_kb())
    await state.clear()

@dp.message(Admin.stock_keys, F.document)
async def stock_keys_file(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    cat = data["stock_cat"]
    
    try:
        file = await bot.get_file(msg.document.file_id)
        file_data = await bot.download_file(file.file_path)
        content = file_data.read().decode('utf-8')
        keys = [k.strip() for k in content.split("\n") if k.strip()]
        
        if not keys:
            return await msg.answer("❌ No keys found in file")
        
        added = db.add_stock_keys_bulk(cat, keys)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Stock Added from File!        ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  Category: {cat.upper():<26} ║\n"
        txt += f"║  Added: {added} keys{' ' * (27 - len(str(added)))} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=admin_stock_kb())
    
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del(call: CallbackQuery, state: FSMContext):
    stock = db.get_all_stock()
    
    if not stock:
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  🗑️ Delete Stock                  ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  No stock to delete.              ║\n"
        txt += f"╚═══════════════════════════════════╝"
        return await call.message.edit_text(txt, reply_markup=admin_stock_kb())
    
    kb = InlineKeyboardBuilder()
    for s in stock[:15]:
        status = "✅" if s['is_used'] else "📦"
        kb.row(InlineKeyboardButton(
            text=f"{status} #{s['id']} {s['key_data'][:20]}...",
            callback_data=f"delkey_{s['id']}"
        ))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  🗑️ Select Key to Delete          ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=kb.as_markup())

@dp.callback_query(lambda c: c.data.startswith("delkey_"))
async def del_key(call: CallbackQuery):
    kid = int(call.data.split("_")[1])
    ok = db.delete_stock_key(kid)
    
    await call.answer("✅ Deleted" if ok else "❌ Not found")
    await stock_del(call, None)

@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ⛔ Ban User                      ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send User ID to ban:          ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]))
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, True)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ⛔ User Banned!                  ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  User ID: {uid:<27} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=admin_kb())
        
        try:
            await bot.send_message(uid, "❌ You have been banned from using this bot.")
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid User ID")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  ✅ Unban User                    ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📝 Send User ID to unban:        ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]))
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, False)
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ User Unbanned!                ║\n"
        txt += f"╠═══════════════════════════════════╣\n"
        txt += f"║  User ID: {uid:<27} ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=admin_kb())
        
        try:
            await bot.send_message(uid, "✅ You have been unbanned! Welcome back!")
        except:
            pass
    
    except:
        await msg.answer("❌ Invalid User ID")
    
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_restore")
async def restore_start(call: CallbackQuery, state: FSMContext):
    txt = f"╔═══════════════════════════════════╗\n"
    txt += f"║  💾 Restore Database              ║\n"
    txt += f"╠═══════════════════════════════════╣\n"
    txt += f"║  📎 Send .db file to restore      ║\n"
    txt += f"╚═══════════════════════════════════╝"
    
    await call.message.edit_text(txt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_menu")]
    ]))
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
        
        txt = f"╔═══════════════════════════════════╗\n"
        txt += f"║  ✅ Database Restored!            ║\n"
        txt += f"╚═══════════════════════════════════╝"
        
        await msg.answer(txt, reply_markup=admin_kb())
    
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    
    await state.clear()

# ─── MAIN ───
async def main():
    print("🚀 Bot is running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
