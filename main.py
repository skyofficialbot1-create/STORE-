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

# ─── PRODUCT STRUCTURE (Hierarchical) ───
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
    "ff_diamonds":[ {"id":"ff_25d","name":"💎 25 Diamond","price":20}, {"id":"ff_50d","name":"💎 50 Diamond","price":35}, {"id":"ff_115d","name":"💎 115 Diamond","price":79}, {"id":"ff_240d","name":"💎 240 Diamond","price":156}, {"id":"ff_355d","name":"💎 355 Diamond","price":237}, {"id":"ff_505d","name":"💎 505 Diamond","price":336}, {"id":"ff_610d","name":"💎 610 Diamond","price":390}, {"id":"ff_850d","name":"💎 850 Diamond","price":558}, {"id":"ff_1090d","name":"💎 1090 Diamond","price":716}, {"id":"ff_1240d","name":"💎 1240 Diamond","price":795}, {"id":"ff_2530d","name":"💎 2530 Diamond","price":1580}, {"id":"ff_5060d","name":"💎 5060 Diamond","price":3160}, {"id":"ff_7590d","name":"💎 7590 Diamond","price":4800}, {"id":"ff_10120d","name":"💎 10120 Diamond","price":6400} ],
    "ff_weekly":[ {"id":"ffw_1","name":"📆 1x Weekly","price":155},{"id":"ffw_2","name":"📆 2x Weekly","price":310},{"id":"ffw_3","name":"📆 3x Weekly","price":465},{"id":"ffw_5","name":"📆 5x Weekly","price":775},{"id":"ffw_m","name":"📆 Monthly","price":765},{"id":"ffw_2m","name":"📆 2x Monthly","price":1540},{"id":"ffw_3m","name":"📆 3x Monthly","price":2295},{"id":"ffw_5m","name":"📆 5x Monthly","price":3825},{"id":"ffw_1w1m","name":"📆 1Week+1Month","price":930},{"id":"ffw_4w1m","name":"📆 4Week+1Month","price":1395} ],
    "ff_lite":[ {"id":"ffl_1","name":"⭐ 1x Weekly Lite","price":40},{"id":"ffl_2","name":"⭐ 2x Weekly Lite","price":80},{"id":"ffl_3","name":"⭐ 3x Weekly Lite","price":120},{"id":"ffl_5","name":"⭐ 5x Weekly Lite","price":200} ],
    "ff_like":[ {"id":"fflk_200","name":"❤️ 200 Likes","price":20},{"id":"fflk_1000","name":"❤️ 1000 Likes","price":100},{"id":"fflk_2000","name":"❤️ 2000 Likes","price":200},{"id":"fflk_3000","name":"❤️ 3000 Likes","price":300},{"id":"fflk_4000","name":"❤️ 4000 Likes","price":400},{"id":"fflk_5000","name":"❤️ 5000 Likes","price":500},{"id":"fflk_6000","name":"❤️ 6000 Likes","price":600},{"id":"fflk_12000","name":"❤️ 12000 Likes","price":1200},{"id":"fflk_24000","name":"❤️ 24000 Likes","price":2400},{"id":"fflk_48000","name":"❤️ 48000 Likes","price":4800} ],
    "netflix":[ {"id":"nf_single","name":"Single Profile (1M)","price":400},{"id":"nf_full","name":"Full Account (1M)","price":1830} ],
    "youtube":[ {"id":"yt_1m","name":"1 Month","price":100},{"id":"yt_3m","name":"3 Months","price":200},{"id":"yt_6m","name":"6 Months","price":300},{"id":"yt_1y","name":"1 Year","price":490} ],
    "crunchyroll":[ {"id":"cr_shared","name":"Shared (1M)","price":200},{"id":"cr_full1","name":"Full (1M)","price":450},{"id":"cr_full12","name":"Full (12M)","price":1840} ],
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
        if p["id"] == prod_id: return p
    return None

def fmt(amount): return f"৳{amount:,.0f}"

# ─── DATABASE ───
class DB:
    def __init__(self, path="store.db"):
        self.path = path
        self._init()
    def _conn(self):
        conn = sqlite3.connect(self.path); conn.row_factory = sqlite3.Row; return conn
    def _init(self):
        with self._conn() as c:
            c.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT, balance REAL DEFAULT 0, is_banned INTEGER DEFAULT 0, joined_at TEXT DEFAULT (datetime('now','+6 hours')))")
            c.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product_name TEXT, category_name TEXT, amount REAL, user_input TEXT, payment_method TEXT, transaction_id TEXT, status TEXT DEFAULT 'pending', delivery_photo TEXT, note TEXT, created_at TEXT DEFAULT (datetime('now','+6 hours')))")
            c.execute("CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL, type TEXT, method TEXT, trx_id TEXT, note TEXT, created_at TEXT DEFAULT (datetime('now','+6 hours')))")
            c.execute("CREATE TABLE IF NOT EXISTS vpn_configs(id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, user_id INTEGER, config_type TEXT, config_data TEXT, server_location TEXT, expiry_days INTEGER, created_at TEXT DEFAULT (datetime('now','+6 hours')))")
            c.execute("CREATE TABLE IF NOT EXISTS stock_keys(id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, key_data TEXT, is_used INTEGER DEFAULT 0, expiry_days INTEGER DEFAULT 30, created_at TEXT DEFAULT (datetime('now','+6 hours')))")
    def get_user(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM users WHERE user_id=?",(uid,)).fetchone()
        return dict(r) if r else None
    def create_user(self, uid, fn, un):
        with self._conn() as c:
            c.execute("INSERT OR IGNORE INTO users(user_id,first_name,username) VALUES(?,?,?)",(uid,fn,un))
    def get_balance(self, uid):
        with self._conn() as c:
            r = c.execute("SELECT balance FROM users WHERE user_id=?",(uid,)).fetchone()
        return r["balance"] if r else 0
    def update_balance(self, uid, amt):
        with self._conn() as c:
            c.execute("UPDATE users SET balance=balance+? WHERE user_id=?",(amt,uid))
    def deduct_balance(self, uid, amt):
        with self._conn() as c:
            cur = c.execute("UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",(amt,uid,amt))
            if cur.rowcount==0: return False
            return True
    def set_ban(self, uid, ban=True):
        with self._conn() as c:
            c.execute("UPDATE users SET is_banned=? WHERE user_id=?",(1 if ban else 0,uid))
    def add_order(self, uid, pname, cat, amt, uinput, pmethod, trid):
        with self._conn() as c:
            cur = c.execute("INSERT INTO orders(user_id,product_name,category_name,amount,user_input,payment_method,transaction_id) VALUES(?,?,?,?,?,?,?)",
                            (uid,pname,cat,amt,uinput,pmethod,trid))
            return cur.lastrowid
    def update_order(self, oid, status, photo="", note=""):
        with self._conn() as c:
            c.execute("UPDATE orders SET status=?,delivery_photo=?,note=? WHERE id=?",(status,photo,note,oid))
    def get_order(self, oid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM orders WHERE id=?",(oid,)).fetchone()
        return dict(r) if r else None
    def get_user_orders(self, uid, limit=10):
        with self._conn() as c:
            rows = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",(uid,limit)).fetchall()
        return [dict(r) for r in rows]
    def get_all_orders(self, status=None, limit=50):
        with self._conn() as c:
            if status: rows = c.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC LIMIT ?",(status,limit)).fetchall()
            else: rows = c.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
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
            c.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note) VALUES(?,?,?,?,?,?)",(uid,amt,typ,method,trid,note))
    def add_vpn_config(self, oid, uid, ctype, cdata, loc, days=30):
        with self._conn() as c:
            c.execute("INSERT INTO vpn_configs(order_id,user_id,config_type,config_data,server_location,expiry_days) VALUES(?,?,?,?,?,?)",(oid,uid,ctype,cdata,loc,days))
    def get_vpn_config(self, oid):
        with self._conn() as c:
            r = c.execute("SELECT * FROM vpn_configs WHERE order_id=? ORDER BY id DESC LIMIT 1",(oid,)).fetchone()
        return dict(r) if r else None
    def add_stock_keys_bulk(self, cat, keys, days=30):
        with self._conn() as c:
            added = 0
            for k in keys:
                if k.strip():
                    c.execute("INSERT INTO stock_keys(category,key_data,expiry_days) VALUES(?,?,?)",(cat,k.strip(),days))
                    added+=1
            return added
    def get_available_key(self, cat):
        with self._conn() as c:
            r = c.execute("SELECT * FROM stock_keys WHERE category=? AND is_used=0 ORDER BY id LIMIT 1",(cat,)).fetchone()
            if r:
                c.execute("UPDATE stock_keys SET is_used=1 WHERE id=?",(r["id"],))
                return dict(r)
            return None
    def get_stock_counts(self):
        with self._conn() as c:
            rows = c.execute("SELECT category, COUNT(*) as cnt FROM stock_keys WHERE is_used=0 GROUP BY category").fetchall()
        return [dict(r) for r in rows]
    def get_all_stock(self, cat=None):
        with self._conn() as c:
            if cat: rows = c.execute("SELECT * FROM stock_keys WHERE category=? ORDER BY id DESC LIMIT 100",(cat,)).fetchall()
            else: rows = c.execute("SELECT * FROM stock_keys ORDER BY category, id DESC LIMIT 200").fetchall()
        return [dict(r) for r in rows]
    def delete_stock_key(self, kid):
        with self._conn() as c:
            cur = c.execute("DELETE FROM stock_keys WHERE id=?",(kid,))
            return cur.rowcount>0

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
    kb.row(InlineKeyboardButton(text="📦 My Orders", callback_data="my_orders"),
           InlineKeyboardButton(text="💰 My Wallet", callback_data="my_wallet"))
    if uid in ADMIN_IDS:
        kb.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

def subcategory_kb(main_cat):
    subs = SUBCATEGORIES.get(main_cat)
    if not subs: # direct products
        return products_kb(main_cat)
    kb = InlineKeyboardBuilder()
    for s in subs:
        kb.row(InlineKeyboardButton(text=s["name"], callback_data=f"sub_{main_cat}|{s['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def products_kb(subcat):
    prods = PRODUCTS.get(subcat, [])
    kb = InlineKeyboardBuilder()
    for p in prods:
        if "bonus" in p and p["bonus"]>0:
            txt = f"{p['name']} (+{fmt(p['bonus'])}) — {fmt(p['price'])}"
        else:
            txt = f"{p['name']} — {fmt(p['price'])}"
        kb.row(InlineKeyboardButton(text=txt, callback_data=f"order_{subcat}|{p['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back to Categories", callback_data="show_main"),
           InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def payment_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💰 Wallet Balance", callback_data="pay_wallet"))
    kb.row(InlineKeyboardButton(text="💳 bKash", callback_data="pay_bkash"),
           InlineKeyboardButton(text="💳 Nagad", callback_data="pay_nagad"))
    kb.row(InlineKeyboardButton(text="💳 Rocket", callback_data="pay_rocket"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products"))
    return kb.as_markup()

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="admin_dash"))
    kb.row(InlineKeyboardButton(text="📦 Pending Orders", callback_data="admin_orders"),
           InlineKeyboardButton(text="👥 Users", callback_data="admin_users"))
    kb.row(InlineKeyboardButton(text="💰 Add Balance", callback_data="admin_addbal"),
           InlineKeyboardButton(text="📦 Deliver", callback_data="admin_deliver"))
    kb.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🌐 VPN Manage", callback_data="admin_vpn"),
           InlineKeyboardButton(text="🔑 Stock Manage", callback_data="admin_stock"))
    kb.row(InlineKeyboardButton(text="⛔ Ban", callback_data="admin_ban"),
           InlineKeyboardButton(text="✅ Unban", callback_data="admin_unban"))
    kb.row(InlineKeyboardButton(text="💾 Restore DB", callback_data="admin_restore"))
    kb.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"))
    return kb.as_markup()

def admin_vpn_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 VPN Orders", callback_data="vpn_orders"),
           InlineKeyboardButton(text="➕ Add VPN Config", callback_data="vpn_add"))
    kb.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="vpn_stock_status"))
    kb.row(InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📋 View Stock", callback_data="stock_view"),
           InlineKeyboardButton(text="➕ Add Keys", callback_data="stock_add"))
    kb.row(InlineKeyboardButton(text="🗑️ Delete Key", callback_data="stock_del"))
    kb.row(InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_menu"))
    return kb.as_markup()

# ─── WELCOME MESSAGE (NEW BEAUTIFUL DESIGN) ───
WELCOME = f"""🌟 *Welcome to SKY STORE BD!* 🌟

🛍️ *Your Ultimate Digital Store*
━━━━━━━━━━━━━━━━━━━━━
🎮 *Game Top-Ups:* Free Fire, Weekly/Monthly
🎬 *Subscriptions:* Netflix, YouTube Premium
🌐 *VPN & Proxy:* ExpressVPN, HMA, VPS
💰 *Wallet:* Add balance for instant purchases
━━━━━━━━━━━━━━━━━━━━━
⚡ _Instant delivery | Best price in BD_
📞 Support: @{SUPPORT_USERNAME}

👇 *Select a category below to start:*"""

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
    await call.message.edit_text(WELCOME, reply_markup=main_menu(call.from_user.id), parse_mode="Markdown")

# Main category -> subcategory or products
@dp.callback_query(lambda c: c.data.startswith("main_"))
async def main_cat(call: CallbackQuery, state: FSMContext):
    main_id = call.data.split("_")[1]
    await state.update_data(main_cat=main_id)
    await call.message.edit_text(f"📂 *Select subcategory:*", reply_markup=subcategory_kb(main_id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("sub_"))
async def sub_cat(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_",1)
    main, sub = rest.split("|")
    await state.update_data(subcat_id=sub)
    await call.message.edit_text(f"📦 *Select product:*", reply_markup=products_kb(sub), parse_mode="Markdown")

# Product order start
@dp.callback_query(lambda c: c.data.startswith("order_"))
async def order_start(call: CallbackQuery, state: FSMContext):
    _, rest = call.data.split("_",1)
    sub, pid = rest.split("|")
    prod = get_product(sub, pid)
    if not prod: return await call.answer("Invalid")
    await state.update_data(subcat_id=sub, prod=prod)
    # VPN / Topup special handling
    if sub == "vpn_plus":
        await call.message.edit_text("🌍 Enter server location (or type auto):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Auto", callback_data="vpn_auto")]
        ]))
        await state.set_state(Order.input)
    elif sub == "topup":
        await state.update_data(user_input="Wallet TopUp")
        await call.message.edit_text(f"💳 *Payment*\nProduct: {prod['name']}\nPrice: {fmt(prod['price'])}", reply_markup=payment_kb(), parse_mode="Markdown")
        await state.set_state(Order.payment)
    else:
        prompt = "🎮 Enter your Player ID:" if "ff_" in sub else "📧 Enter your Email/Info:"
        await call.message.edit_text(f"📝 {prompt}", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_products")]
        ]))
        await state.set_state(Order.input)

@dp.callback_query(lambda c: c.data == "vpn_auto")
async def vpn_auto(call: CallbackQuery, state: FSMContext):
    await state.update_data(user_input="Auto")
    data = await state.get_data()
    await call.message.edit_text(f"💳 *Payment*\nProduct: {data['prod']['name']}\nServer: Auto\nPrice: {fmt(data['prod']['price'])}", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.message(Order.input)
async def get_input(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if len(text)<2: return await msg.answer("❌ Please enter valid details")
    await state.update_data(user_input=text)
    data = await state.get_data()
    await msg.answer(f"💳 *Payment*\nProduct: {data['prod']['name']}\nPrice: {fmt(data['prod']['price'])}", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

# Payment selection
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
            return await call.message.edit_text(f"❌ Insufficient balance. Need {fmt(price)}, have {fmt(bal)}.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💰 Top Up", callback_data="main_topup")]
            ]))
        trx = f"WAL{datetime.now():%Y%m%d%H%M%S}"
        await process_payment(call, state, "Wallet Balance", trx)
    else:
        nums = {"bkash":"01742958563","nagad":"01748506069","rocket":"01742958563","upi":"example@upi"}
        await call.message.edit_text(f"💳 Send {fmt(price)} to {method.upper()} `{nums.get(method,'')}`\nThen type TrxID:", parse_mode="Markdown",
                                     reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="back_to_payment")]]))
        await state.set_state(Order.trxid)

async def notify_admin_order(uid, oid, prod, sub, price, pmethod, trx, uinput):
    user_info = db.get_user(uid)
    username_txt = f"@{user_info['username']}" if user_info and user_info.get('username') else str(uid)
    first_name = user_info['first_name'] if user_info else "Unknown"
    
    # Beautiful Box Format for Admin
    order_details = f"""📦 *NEW ORDER RECEIVED* 📦
━━━━━━━━━━━━━━━━━━━━━
👤 *Ordered By:* {first_name} ({username_txt})
🆔 *User ID:* `{uid}`
🛒 *Order ID:* `#{oid}`
🛍️ *Product:* {prod['name']}
🏷️ *Category:* {sub}
💵 *Price:* {fmt(price)}
💳 *Payment Method:* {pmethod}
🧾 *TrxID:* `{trx}`
📝 *User Input:* `{uinput}`
🕒 *Time:* {datetime.now().strftime('%Y-%m-%d %I:%M %p')}
━━━━━━━━━━━━━━━━━━━━━"""

    admin_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Deliver / Approve", callback_data=f"admin_fast_deliver_{oid}")]
    ])
    
    for aid in ADMIN_IDS:
        try: await bot.send_message(aid, order_details, parse_mode="Markdown", reply_markup=admin_kb)
        except: pass

async def process_payment(call: CallbackQuery, state: FSMContext, pmethod, trx):
    data = await state.get_data()
    prod = data["prod"]
    sub = data["subcat_id"]
    uinput = data.get("user_input","")
    uid = call.from_user.id
    price = prod["price"]
    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price): return
    oid = db.add_order(uid, prod["name"], sub, price, uinput, pmethod, trx)
    
    # Auto-delivery logic
    if sub == "topup":
        bonus = prod.get("bonus",0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        await call.message.edit_text(f"✅ Added {fmt(total)} to wallet!", reply_markup=main_menu(uid), parse_mode="Markdown")
    elif sub == "vpn_plus":
        stype = prod.get("stock_type","key")
        stock = db.get_available_key(stype)
        if stock:
            key = stock["key_data"]; days = stock["expiry_days"]
        else:
            key = f"DEMO-{uuid4().hex[:12]}"; days = 30
        db.add_vpn_config(oid, uid, stype, key, uinput or "Auto", days)
        db.update_order(oid, "delivered")
        await call.message.edit_text(f"✅ VPN Key: `{key}`\nServer: {uinput}\nExpires: {days} days", reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        db.update_order(oid, "delivered")
        await call.message.edit_text(f"✅ Order `#{oid}` placed! Pending verification.", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify admin with beautiful format
    await notify_admin_order(uid, oid, prod, sub, price, pmethod, trx, uinput)
    await state.clear()

@dp.message(Order.trxid)
async def get_trx(msg: Message, state: FSMContext):
    trx = msg.text.strip()
    if not trx: return
    data = await state.get_data()
    method = data.get("pay_method","Manual")
    mn = {"bkash":"bKash","nagad":"Nagad","rocket":"Rocket","upi":"UPI"}.get(method, method)
    await process_payment_msg(msg, state, mn, trx)

async def process_payment_msg(msg: Message, state: FSMContext, pmethod, trx):
    data = await state.get_data()
    prod = data["prod"]
    sub = data["subcat_id"]
    uinput = data.get("user_input","")
    uid = msg.from_user.id
    price = prod["price"]
    if pmethod == "Wallet Balance":
        if not db.deduct_balance(uid, price): return
    oid = db.add_order(uid, prod["name"], sub, price, uinput, pmethod, trx)
    if sub == "topup":
        bonus = prod.get("bonus",0)
        total = price + bonus
        db.update_balance(uid, total)
        db.add_transaction(uid, total, "topup", pmethod, trx)
        db.update_order(oid, "delivered")
        await msg.answer(f"✅ Added {fmt(total)} to wallet!", reply_markup=main_menu(uid), parse_mode="Markdown")
    elif sub == "vpn_plus":
        stype = prod.get("stock_type","key")
        stock = db.get_available_key(stype)
        key = stock["key_data"] if stock else f"DEMO-{uuid4().hex[:12]}"
        days = stock["expiry_days"] if stock else 30
        db.add_vpn_config(oid, uid, stype, key, uinput or "Auto", days)
        db.update_order(oid, "delivered")
        await msg.answer(f"✅ VPN Key: `{key}`\nServer: {uinput}", reply_markup=main_menu(uid), parse_mode="Markdown")
    else:
        db.update_order(oid, "delivered")
        await msg.answer(f"✅ Order `#{oid}` placed! Pending verification.", reply_markup=main_menu(uid), parse_mode="Markdown")
    
    # Notify admin with beautiful format
    await notify_admin_order(uid, oid, prod, sub, price, pmethod, trx, uinput)
    await state.clear()

@dp.callback_query(lambda c: c.data == "back_to_payment")
async def back_pay(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.message.edit_text(f"💳 Payment:\nProduct: {data['prod']['name']}\nPrice: {fmt(data['prod']['price'])}", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(Order.payment)

@dp.callback_query(lambda c: c.data == "back_to_products")
async def back_prod(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    sub = data.get("subcat_id")
    if sub:
        await call.message.edit_text("📦 *Select product:*", reply_markup=products_kb(sub), parse_mode="Markdown")
        await state.set_state(None)

# User info
@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet(call: CallbackQuery):
    uid = call.from_user.id
    bal = db.get_balance(uid)
    await call.message.edit_text(f"💰 *Your Wallet Balance:*\n\n💵 Amount: {fmt(bal)}", reply_markup=main_menu(uid), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders(call: CallbackQuery):
    uid = call.from_user.id
    orders = db.get_user_orders(uid, 5)
    if not orders:
        txt = "❌ You have no previous orders."
    else:
        txt = "📦 *Your Recent Orders:*\n━━━━━━━━━━━━━━━━━━━━━\n"
        for o in orders:
            txt += f"🛒 *ID:* `#{o['id']}`\n🛍️ *Item:* {o['product_name']}\n📊 *Status:* {o['status'].upper()}\n━━━━━━━━━━━━━━━━━━━━━\n"
    await call.message.edit_text(txt, reply_markup=main_menu(uid), parse_mode="Markdown")

# ─── ADMIN PANEL ───
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("Unauthorized")
    await state.clear()
    await call.message.edit_text("🔐 *Admin Panel Dashboard*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_dash")
async def dash(call: CallbackQuery):
    users = db.get_all_users()
    pending = db.pending_count()
    stock = db.get_stock_counts()
    s = "\n".join(f"🔸 {c['category']}: {c['cnt']}" for c in stock) or "No stock available"
    
    txt = f"""📊 *SYSTEM DASHBOARD*
━━━━━━━━━━━━━━━━━━━━━
👥 *Total Users:* {len(users)}
📦 *Pending Orders:* {pending}

🔑 *Stock Status:*
{s}
━━━━━━━━━━━━━━━━━━━━━"""
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_orders")
async def pending_orders(call: CallbackQuery):
    orders = db.get_all_orders("pending", 15)
    if not orders: return await call.message.edit_text("✅ *No pending orders right now!*", reply_markup=admin_kb(), parse_mode="Markdown")
    
    txt = "📦 *PENDING ORDERS LIST*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for o in orders:
        txt += f"🛒 *Order ID:* `#{o['id']}` | 🛍️ {o['product_name']}\n👤 *User:* `{o['user_id']}` | 💵 {fmt(o['amount'])}\n📝 *Input:* `{o['user_input']}`\n━━━━━━━━━━━━━━━━━━━━━\n"
    
    await call.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

# Admin Fast Deliver (From Inline Button)
@dp.callback_query(lambda c: c.data.startswith("admin_fast_deliver_"))
async def fast_deliver(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS: return await call.answer("Unauthorized")
    oid = int(call.data.split("_")[-1])
    order = db.get_order(oid)
    if not order: return await call.answer("Order not found or already processed!")
    
    await state.update_data(oid=oid)
    await call.message.answer(f"📦 *Delivering Order `#{oid}`*\nProduct: {order['product_name']}\n\n📸 Send a screenshot/photo of delivery, OR type 'done' to deliver without photo:", parse_mode="Markdown")
    await state.set_state(Admin.deliver_file)
    await call.answer()

# Add Balance
@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("👤 *Send User ID to add balance:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin", callback_data="admin_menu")]]), parse_mode="Markdown")
    await state.set_state(Admin.addbal_uid)

@dp.message(Admin.addbal_uid)
async def addbal_uid(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text)
        await state.update_data(uid=uid)
        await msg.answer("💵 *Send amount to add:*", parse_mode="Markdown")
        await state.set_state(Admin.addbal_amt)
    except: await msg.answer("❌ Invalid ID format")

@dp.message(Admin.addbal_amt)
async def addbal_amt(msg: Message, state: FSMContext, bot: Bot):
    try:
        amt = float(msg.text)
        data = await state.get_data()
        uid = data["uid"]
        db.update_balance(uid, amt)
        db.add_transaction(uid, amt, "admin_add", "Admin", f"ADMIN_{datetime.now():%Y%m%d%H%M%S}")
        await msg.answer(f"✅ Successfully added *{fmt(amt)}* to user `{uid}`", reply_markup=admin_kb(), parse_mode="Markdown")
        
        # Beautiful notification for user
        try: 
            user_msg = f"🎉 *Congratulations!*\n\n💰 An Admin has added *{fmt(amt)}* to your wallet.\n🥳 Happy Shopping!"
            await bot.send_message(uid, user_msg, parse_mode="Markdown")
        except: pass
    except: await msg.answer("❌ Invalid amount format")
    await state.clear()

# Deliver Order (Manual ID entry)
@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📦 *Send Order ID to deliver:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin", callback_data="admin_menu")]]), parse_mode="Markdown")
    await state.set_state(Admin.deliver_oid)

@dp.message(Admin.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        if not order: return await msg.answer("❌ Order not found")
        await state.update_data(oid=oid)
        await msg.answer(f"📦 *Order `#{oid}`:* {order['product_name']}\n\n📸 Send delivery photo or type 'done':", parse_mode="Markdown")
        await state.set_state(Admin.deliver_file)
    except: await msg.answer("❌ Invalid ID format")

@dp.message(Admin.deliver_file)
async def deliver_file(msg: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    oid = data["oid"]
    if msg.photo:
        file_id = msg.photo[-1].file_id
        note = msg.caption or "Delivered successfully"
        db.update_order(oid, "delivered", file_id, note)
        order = db.get_order(oid)
        try: await bot.send_photo(order["user_id"], file_id, caption=f"✅ *Your order `#{oid}` has been delivered!*\n📝 Note: {note}", parse_mode="Markdown")
        except: pass
    else:
        db.update_order(oid, "delivered", note="Delivered successfully")
        order = db.get_order(oid)
        try: await bot.send_message(order["user_id"], f"✅ *Your order `#{oid}` has been delivered!*\nThank you for purchasing!", parse_mode="Markdown")
        except: pass
    await msg.answer(f"✅ Order `#{oid}` Marked as Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

# Broadcast
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("📨 *Send the message you want to broadcast:*", parse_mode="Markdown")
    await state.set_state(Admin.broadcast_msg)

@dp.message(Admin.broadcast_msg)
async def broadcast_do(msg: Message, state: FSMContext, bot: Bot):
    text = msg.text
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_message(u["user_id"], f"📢 *Announcement*\n━━━━━━━━━━━━━━━━━━━━━\n{text}", parse_mode="Markdown")
                sent += 1
            except: pass
    await msg.answer(f"✅ Broadcast complete! Sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()

# ─── ADMIN VPN MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_vpn")
async def vpn_menu(call: CallbackQuery):
    await call.message.edit_text("🌐 *VPN Management Panel*", reply_markup=admin_vpn_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "vpn_orders")
async def vpn_orders(call: CallbackQuery):
    orders = db.get_all_orders(limit=50)
    vpn_orders = [o for o in orders if "vpn" in o["category_name"].lower() or "vpn" in o["product_name"].lower()]
    if not vpn_orders: return await call.message.edit_text("❌ No VPN orders found", reply_markup=admin_vpn_kb())
    
    txt = "🌐 *RECENT VPN ORDERS*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for o in vpn_orders[:15]:
         txt += f"🛒 `#{o['id']}` | {o['product_name']}\n👤 User: `{o['user_id']}`\n━━━━━━━━━━━━━━━━━━━━━\n"
    await call.message.edit_text(txt, reply_markup=admin_vpn_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "vpn_add")
async def vpn_add_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("🛒 *Send Order ID to add VPN config:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="admin_vpn")]]), parse_mode="Markdown")
    await state.set_state(Admin.vpn_oid)

@dp.message(Admin.vpn_oid)
async def vpn_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text)
        order = db.get_order(oid)
        if not order: return await msg.answer("❌ Order not found")
        await state.update_data(vpn_oid=oid)
        await msg.answer("⚙️ *Send config data/Key:*", parse_mode="Markdown")
        await state.set_state(Admin.vpn_data)
    except: await msg.answer("❌ Invalid ID format")

@dp.message(Admin.vpn_data)
async def vpn_data(msg: Message, state: FSMContext):
    config = msg.text.strip()
    await state.update_data(vpn_data=config)
    await msg.answer("🌍 *Enter Server Location:*", parse_mode="Markdown")
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
    await msg.answer(f"✅ VPN Config added & delivered for order `#{oid}`", reply_markup=admin_kb(), parse_mode="Markdown")
    try: await bot.send_message(order["user_id"], f"🌐 *Your VPN is Ready!*\n━━━━━━━━━━━━━━━━━━━━━\n🌍 *Server:* {loc}\n⚙️ *Config/Key:*\n`{config[:500]}`\n━━━━━━━━━━━━━━━━━━━━━", parse_mode="Markdown")
    except: pass
    await state.clear()

@dp.callback_query(lambda c: c.data == "vpn_stock_status")
async def vpn_stock(call: CallbackQuery):
    counts = db.get_stock_counts()
    txt = "\n".join(f"🔸 {c['category']}: {c['cnt']} available" for c in counts) or "No stock available"
    await call.message.edit_text(f"🔑 *Current VPN/Proxy Stock:*\n━━━━━━━━━━━━━━━━━━━━━\n{txt}\n━━━━━━━━━━━━━━━━━━━━━", reply_markup=admin_vpn_kb(), parse_mode="Markdown")

# ─── ADMIN STOCK MANAGEMENT ───
@dp.callback_query(lambda c: c.data == "admin_stock")
async def stock_menu(call: CallbackQuery):
    await call.message.edit_text("🔑 *Stock Management Panel*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_view")
async def stock_view(call: CallbackQuery):
    stock = db.get_all_stock()
    if not stock: return await call.message.edit_text("❌ No stock available", reply_markup=admin_stock_kb())
    by_cat = {}
    for s in stock:
        c = s["category"]
        by_cat.setdefault(c, {"total":0,"used":0,"avail":0})
        by_cat[c]["total"]+=1
        if s["is_used"]: by_cat[c]["used"]+=1
        else: by_cat[c]["avail"]+=1
    txt = "📊 *STOCK OVERVIEW*\n━━━━━━━━━━━━━━━━━━━━━\n"
    for c,v in by_cat.items():
         txt += f"📁 *{c.upper()}*\nTotal: {v['total']} | Available: {v['avail']} | Used: {v['used']}\n━━━━━━━━━━━━━━━━━━━━━\n"
    await call.message.edit_text(txt, reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add(call: CallbackQuery, state: FSMContext):
    cats = {"key":"🔑 VPN Keys","proxy":"🌐 Proxy IPs","vps":"🖥️ VPS Logins"}
    kb = InlineKeyboardBuilder()
    for k,v in cats.items():
        kb.row(InlineKeyboardButton(text=v, callback_data=f"stockcat_{k}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("📁 *Select category to add stock into:*", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(Admin.stock_cat)

@dp.callback_query(lambda c: c.data.startswith("stockcat_"))
async def stock_cat_chosen(call: CallbackQuery, state: FSMContext):
    cat = call.data.split("_")[1]
    await state.update_data(stock_cat=cat)
    await call.message.edit_text(f"📝 *Send items for {cat.upper()}*\n(Send one item per line):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Back", callback_data="stock_add")]]), parse_mode="Markdown")
    await state.set_state(Admin.stock_keys)

@dp.message(Admin.stock_keys)
async def stock_keys_save(msg: Message, state: FSMContext):
    data = await state.get_data()
    cat = data["stock_cat"]
    keys = [k.strip() for k in msg.text.split("\n") if k.strip()]
    if not keys: return await msg.answer("❌ No valid items found")
    added = db.add_stock_keys_bulk(cat, keys)
    await msg.answer(f"✅ Successfully added *{added} items* to `{cat}` stock!", reply_markup=admin_stock_kb(), parse_mode="Markdown")
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del(call: CallbackQuery, state: FSMContext):
    stock = db.get_all_stock()
    if not stock: return await call.message.edit_text("❌ No stock available to delete", reply_markup=admin_stock_kb())
    kb = InlineKeyboardBuilder()
    for s in stock[:20]:
        kb.row(InlineKeyboardButton(text=f"{'✅' if s['is_used'] else '📦'} #{s['id']} {s['key_data'][:25]}...", callback_data=f"delkey_{s['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Back", callback_data="admin_stock"))
    await call.message.edit_text("🗑️ *Select a key to delete:*", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delkey_"))
async def del_key(call: CallbackQuery):
    kid = int(call.data.split("_")[1])
    ok = db.delete_stock_key(kid)
    await call.answer("✅ Item Deleted successfully!" if ok else "❌ Not found")
    # Refresh menu
    await stock_del(call, None)

# Ban / Unban
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("⛔ *Send user ID to BAN:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin", callback_data="admin_menu")]]), parse_mode="Markdown")
    await state.set_state(Admin.ban_uid)

@dp.message(Admin.ban_uid)
async def ban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, True)
        await msg.answer(f"⛔ User `{uid}` has been banned.", reply_markup=admin_kb(), parse_mode="Markdown")
        try: await bot.send_message(uid, "❌ You have been banned by the Administrator.")
        except: pass
    except: await msg.answer("❌ Invalid ID format")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("✅ *Send user ID to UNBAN:*", parse_mode="Markdown")
    await state.set_state(Admin.unban_uid)

@dp.message(Admin.unban_uid)
async def unban_do(msg: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(msg.text)
        db.set_ban(uid, False)
        await msg.answer(f"✅ User `{uid}` has been unbanned.", reply_markup=admin_kb(), parse_mode="Markdown")
        try: await bot.send_message(uid, "✅ Your account has been unbanned! You can now use the bot.")
        except: pass
    except: await msg.answer("❌ Invalid ID format")
    await state.clear()

# Restore DB
@dp.callback_query(lambda c: c.data == "admin_restore")
async def restore_start(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("💾 *Send .db file to restore database:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Admin", callback_data="admin_menu")]]), parse_mode="Markdown")
    await state.set_state(Admin.restore_db)

@dp.message(Admin.restore_db, F.document)
async def restore_db(msg: Message, state: FSMContext, bot: Bot):
    doc = msg.document
    if not doc.file_name.endswith('.db'): return await msg.answer("❌ Please upload a valid .db file.")
    await msg.answer("🔄 Restoring database...")
    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, db.path)
        db._init()
        await msg.answer("✅ Database restored successfully!", reply_markup=admin_kb())
    except Exception as e: await msg.answer(f"❌ Error: {e}")
    await state.clear()

# ─── MAIN ───
async def main():
    print("Bot running...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
