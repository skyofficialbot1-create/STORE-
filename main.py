#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║            🌟 TopUp Store BD — Premium Bot v4.0             ║
║     🔥 Free Fire | Netflix | YouTube | VPN Plus & More      ║
║             ✅ Colored Buttons | Full Admin Panel           ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio, json, os, sys, sqlite3, random, string, hashlib, re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from uuid import uuid4

try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command, CommandStart
    from aiogram.types import (Message, CallbackQuery, InlineKeyboardMarkup,
        InlineKeyboardButton, FSInputFile)
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
except ImportError:
    print("❌ aiogram not installed!\n📦 pip install aiogram")
    sys.exit(1)

# ==================== CONFIG ====================
BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
NAGAD_NUMBER = "01748506069"
BKASH_NUMBER = "01742958563"
ROCKET_NUMBER = "01742958563"
BOT_USERNAME = "@SKY_STOR_BOT"
SUPPORT_USERNAME = "FBSKYSUPPORT"

# ==================== PRODUCTS ====================
PRODUCTS = {
    "categories": [
        {
            "id": "freefire",
            "name": "🔥 Free Fire Diamonds",
            "btn": "🔥 Free Fire Diamonds",
            "input": "🎮 Enter your Free Fire Player ID:",
            "ph": "Example: 1234567890",
            "prods": [
                ("ff_25d", "💎 25 Diamond", 20),
                ("ff_50d", "💎 50 Diamond", 35),
                ("ff_115d", "💎 115 Diamond", 79),
                ("ff_240d", "💎 240 Diamond 🔥", 156),
                ("ff_355d", "💎 355 Diamond", 237),
                ("ff_505d", "💎 505 Diamond", 336),
                ("ff_610d", "💎 610 Diamond", 390),
                ("ff_850d", "💎 850 Diamond", 558),
                ("ff_1090d", "💎 1090 Diamond 🔥", 716),
                ("ff_1240d", "💎 1240 Diamond", 795),
                ("ff_2530d", "💎 2530 Diamond", 1580),
                ("ff_5060d", "💎 5060 Diamond", 3160),
                ("ff_7590d", "💎 7590 Diamond", 4800),
                ("ff_10120d", "💎 10120 Diamond", 6400),
            ]
        },
        {
            "id": "ff_weekly",
            "name": "📆 FF Weekly/Monthly",
            "btn": "📆 FF Weekly & Monthly",
            "input": "🎮 Enter Free Fire Player ID:",
            "ph": "Player ID",
            "prods": [
                ("ffw_1", "📆 1x Weekly", 155),
                ("ffw_2", "📆 2x Weekly", 310),
                ("ffw_3", "📆 3x Weekly", 465),
                ("ffw_5", "📆 5x Weekly", 775),
                ("ffw_m", "📆 Monthly 🔥", 765),
                ("ffw_2m", "📆 2x Monthly", 1540),
                ("ffw_3m", "📆 3x Monthly", 2295),
                ("ffw_5m", "📆 5x Monthly", 3825),
                ("ffw_1w1m", "📆 1Week+1Month", 930),
                ("ffw_4w1m", "📆 4Week+1Month", 1395),
            ]
        },
        {
            "id": "ff_lite",
            "name": "⭐ Weekly Lite",
            "btn": "⭐ Weekly Lite",
            "input": "🎮 Enter Free Fire Player ID:",
            "ph": "Player ID",
            "prods": [
                ("ffl_1", "⭐ 1x Weekly Lite 🔥", 40),
                ("ffl_2", "⭐ 2x Weekly Lite", 80),
                ("ffl_3", "⭐ 3x Weekly Lite", 120),
                ("ffl_5", "⭐ 5x Weekly Lite", 200),
            ]
        },
        {
            "id": "ff_like",
            "name": "❤️ FF Like Service",
            "btn": "❤️ FF Like",
            "input": "🎮 Enter Free Fire Player ID:",
            "ph": "Player ID",
            "prods": [
                ("fflk_200", "❤️ 200 Likes", 20),
                ("fflk_1000", "❤️ 1000 Likes", 100),
                ("fflk_2000", "❤️ 2000 Likes", 200),
                ("fflk_3000", "❤️ 3000 Likes", 300),
                ("fflk_5000", "❤️ 5000 Likes 🔥", 500),
                ("fflk_6000", "❤️ 6000 Likes", 600),
                ("fflk_12000", "❤️ 12000 Likes", 1200),
                ("fflk_24000", "❤️ 24000 Likes", 2400),
                ("fflk_48000", "❤️ 48000 Likes", 4800),
            ]
        },
        {
            "id": "netflix",
            "name": "🎬 Netflix Premium",
            "btn": "🎬 Netflix Premium",
            "input": "📧 Enter your WhatsApp/Email:",
            "ph": "Phone or Email",
            "prods": [
                ("nf_single", "🎬 Netflix Single 1Month 🔥", 400),
                ("nf_full", "🎬 Netflix Full 1Month", 1830),
            ]
        },
        {
            "id": "youtube",
            "name": "▶️ YouTube Premium",
            "btn": "▶️ YouTube Premium",
            "input": "📧 Enter your Email:",
            "ph": "your@email.com",
            "prods": [
                ("yt_1m", "▶️ 1 Month 🔥", 100),
                ("yt_3m", "▶️ 3 Months", 200),
                ("yt_6m", "▶️ 6 Months", 300),
                ("yt_1y", "▶️ 1 Year", 490),
            ]
        },
        {
            "id": "crunchyroll",
            "name": "🍿 Crunchyroll Premium",
            "btn": "🍿 Crunchyroll Premium",
            "input": "📧 Enter your WhatsApp/Telegram:",
            "ph": "Username or Phone",
            "prods": [
                ("cr_shared", "🍿 Crunchyroll Shared 1M", 200),
                ("cr_full1", "🍿 Crunchyroll Full 1M 🔥", 450),
                ("cr_full12", "🍿 Crunchyroll Full 12M", 1840),
            ]
        },
        {
            "id": "vpn",
            "name": "🌐 VPN Premium",
            "btn": "🌐 VPN Premium (Auto-Delivery)",
            "input": "🌍 Preferred Server (Singapore/USA/UK):",
            "ph": "e.g. Singapore",
            "prods": [
                ("vpn_express", "🔑 ExpressVPN 1Month 🔥", 350),
                ("vpn_hma", "🔑 HMA VPN 1Month 🔥", 250),
                ("vpn_ip", "🔑 VPN IP Service 1M", 300),
                ("vpn_vanish", "🔑 Vanish VPN 1M", 280),
                ("vpn_proton", "🔑 Proton VPN Plus 1M 🔥", 320),
                ("proxy_dedi", "🌐 Dedicated Proxy 1M", 200),
                ("vps_basic", "🖥️ Basic VPS 1M", 800),
                ("vps_premium", "🖥️ Premium VPS 1M", 1500),
            ]
        },
        {
            "id": "topup",
            "name": "💰 Wallet Top-Up",
            "btn": "💰 Wallet Top-Up",
            "input": "",
            "ph": "",
            "prods": [
                ("bal_100", "💰 100 Tk Balance", 100),
                ("bal_200", "💰 200 Tk [+5 Bonus]", 200),
                ("bal_500", "💰 500 Tk [+20 Bonus] 🔥", 500),
                ("bal_1000", "💰 1000 Tk [+50 Bonus]", 1000),
                ("bal_2000", "💰 2000 Tk [+120 Bonus]", 2000),
                ("bal_5000", "💰 5000 Tk [+350 Bonus]", 5000),
            ]
        }
    ]
}

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path="topup_store.db"):
        self.db_path = db_path
        Path("data").mkdir(exist_ok=True)
        self.db_path = f"data/{db_path}"
        self._init()

    def _get(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self):
        c = self._get()
        c.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY,first_name TEXT,username TEXT,balance REAL DEFAULT 0,is_banned INTEGER DEFAULT 0,joined_at TEXT,last_active TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,product_name TEXT,category TEXT,amount REAL,qty INTEGER DEFAULT 1,user_input TEXT,pay_method TEXT,trx_id TEXT,status TEXT DEFAULT 'pending',delivery_photo TEXT,note TEXT,created_at TEXT,updated_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,amount REAL,type TEXT,method TEXT,trx_id TEXT,note TEXT,created_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS vpn_configs(id INTEGER PRIMARY KEY AUTOINCREMENT,order_id INTEGER,user_id INTEGER,config_type TEXT,config_data TEXT,server_location TEXT,expiry_days INTEGER DEFAULT 30,created_at TEXT,expires_at TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT,key_data TEXT,is_used INTEGER DEFAULT 0,expiry_days INTEGER DEFAULT 30,created_at TEXT)")
        c.commit(); c.close()

    def add_user(self, uid, name, uname=None):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT OR IGNORE INTO users(user_id,first_name,username,joined_at,last_active)VALUES(?,?,?,?,?)",
                  (uid, name, uname, now, now))
        c.commit(); c.close()

    def get_user(self, uid):
        c = self._get()
        r = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        c.close(); return dict(r) if r else None

    def upd_activity(self, uid):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE users SET last_active=? WHERE user_id=?", (now, uid))
        c.commit(); c.close()

    def get_bal(self, uid):
        c = self._get()
        r = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        c.close(); return r["balance"] if r else 0

    def add_bal(self, uid, amt):
        c = self._get()
        c.execute("UPDATE users SET balance=COALESCE(balance,0)+? WHERE user_id=?", (amt, uid))
        c.commit(); c.close()

    def deduct_bal(self, uid, amt):
        c = self._get()
        r = c.execute("UPDATE users SET balance=COALESCE(balance,0)-? WHERE user_id=? AND COALESCE(balance,0)>=?", (amt, uid, amt))
        aff = r.rowcount; c.commit(); c.close(); return aff > 0

    def set_ban(self, uid, ban=True):
        c = self._get()
        c.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if ban else 0, uid))
        c.commit(); c.close()

    def get_all_users(self):
        c = self._get()
        r = c.execute("SELECT * FROM users ORDER BY joined_at DESC").fetchall()
        c.close(); return [dict(x) for x in r]

    def add_order(self, uid, pname, cat, amt, qty=1, inp="", pm="", trx=""):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = c.execute("INSERT INTO orders(user_id,product_name,category,amount,qty,user_input,pay_method,trx_id,created_at,updated_at)VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (uid, pname, cat, amt, qty, inp, pm, trx, now, now))
        oid = cur.lastrowid; c.commit(); c.close(); return oid

    def upd_order(self, oid, status, photo="", note=""):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE orders SET status=?,delivery_photo=?,note=?,updated_at=? WHERE id=?", (status, photo, note, now, oid))
        c.commit(); c.close()

    def get_order(self, oid):
        c = self._get()
        r = c.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        c.close(); return dict(r) if r else None

    def get_orders(self, uid=None, status=None, limit=50):
        c = self._get()
        if uid: r = c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()
        elif status: r = c.execute("SELECT * FROM orders WHERE status=? ORDER BY id DESC LIMIT ?", (status, limit)).fetchall()
        else: r = c.execute("SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        c.close(); return [dict(x) for x in r]

    def add_trx(self, uid, amt, typ, method, trx, note=""):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO transactions(user_id,amount,type,method,trx_id,note,created_at)VALUES(?,?,?,?,?,?,?)",
                  (uid, amt, typ, method, trx, note, now))
        c.commit(); c.close()

    def add_vpn(self, oid, uid, ctype, data, loc, days=30):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        exp = (datetime.now()+timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO vpn_configs(order_id,user_id,config_type,config_data,server_location,expiry_days,created_at,expires_at)VALUES(?,?,?,?,?,?,?,?)",
                  (oid, uid, ctype, data, loc, days, now, exp))
        c.commit(); c.close()

    def get_vpn(self, oid):
        c = self._get()
        r = c.execute("SELECT * FROM vpn_configs WHERE order_id=? ORDER BY id DESC LIMIT 1", (oid,)).fetchone()
        c.close(); return dict(r) if r else None

    def add_stock(self, cat, key, days=30):
        c = self._get()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO stock(category,key_data,expiry_days,created_at)VALUES(?,?,?,?)", (cat, key, days, now))
        c.commit(); c.close()

    def add_stock_bulk(self, cat, keys, days=30):
        count = 0
        for k in keys:
            if k.strip(): self.add_stock(cat, k.strip(), days); count += 1
        return count

    def get_stock(self, cat=None):
        c = self._get()
        if cat: r = c.execute("SELECT * FROM stock WHERE category=? AND is_used=0 ORDER BY id ASC", (cat,)).fetchall()
        else: r = c.execute("SELECT category,COUNT(*) as cnt FROM stock WHERE is_used=0 GROUP BY category").fetchall()
        c.close(); return [dict(x) for x in r]

    def take_stock(self, cat):
        c = self._get()
        r = c.execute("SELECT * FROM stock WHERE category=? AND is_used=0 ORDER BY id ASC LIMIT 1", (cat,)).fetchone()
        if r:
            c.execute("UPDATE stock SET is_used=1 WHERE id=?", (r["id"],))
            c.commit(); c.close(); return dict(r)
        c.close(); return None

    def get_all_stock(self):
        c = self._get()
        r = c.execute("SELECT * FROM stock ORDER BY category,id DESC LIMIT 100").fetchall()
        c.close(); return [dict(x) for x in r]

    def del_stock(self, kid):
        c = self._get()
        c.execute("DELETE FROM stock WHERE id=?", (kid,))
        aff = c.rowcount; c.commit(); c.close(); return aff > 0

    def get_stats(self):
        c = self._get()
        u = c.execute("SELECT COUNT(*) as c,COALESCE(SUM(balance),0) as b FROM users").fetchone()
        o = c.execute("SELECT COUNT(*) as c,COALESCE(SUM(amount),0) as r FROM orders").fetchone()
        p = c.execute("SELECT COUNT(*) as c FROM orders WHERE status='pending'").fetchone()
        d = c.execute("SELECT COUNT(*) as c FROM orders WHERE status='delivered'").fetchone()
        s = c.execute("SELECT category,COUNT(*) as c FROM stock WHERE is_used=0 GROUP BY category").fetchall()
        c.close()
        return {"users": u["c"], "wallets": u["b"], "orders": o["c"], "revenue": o["r"],
                "pending": p["c"], "delivered": d["c"], "stock": [dict(x) for x in s]}

db = Database()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== FSM ====================
class OrderStates(StatesGroup):
    inputting = State()
    paying = State()
    trx = State()

class AdminStates(StatesGroup):
    cat_select = State()
    bal_user = State()
    bal_amt = State()
    del_oid = State()
    del_file = State()
    bc_msg = State()
    bc_confirm = State()
    vpn_oid = State()
    vpn_data = State()
    vpn_loc = State()
    ban_uid = State()
    unban_uid = State()
    stock_cat = State()
    stock_keys = State()

# ==================== HELPERS ====================
def gp(cid, pid):
    cat = None
    for c in PRODUCTS["categories"]:
        if c["id"] == cid: cat = c; break
    if not cat: return None, None
    for p in cat["prods"]:
        if p[0] == pid: return cat, p
    return None, None

def fmt(n):
    return f"৳{n:,.0f}"

# ==================== KEYBOARDS ====================
def main_kb(uid=None):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔥 Free Fire Diamonds", callback_data="cat_freefire"),
          InlineKeyboardButton(text="📆 FF Weekly", callback_data="cat_ff_weekly"))
    b.row(InlineKeyboardButton(text="⭐ Weekly Lite", callback_data="cat_ff_lite"),
          InlineKeyboardButton(text="❤️ FF Like", callback_data="cat_ff_like"))
    b.row(InlineKeyboardButton(text="🎬 Netflix", callback_data="cat_netflix"),
          InlineKeyboardButton(text="▶️ YouTube", callback_data="cat_youtube"),
          InlineKeyboardButton(text="🍿 Crunchyroll", callback_data="cat_crunchyroll"))
    b.row(InlineKeyboardButton(text="🌐 VPN Premium (Auto-Delivery)", callback_data="cat_vpn"))
    b.row(InlineKeyboardButton(text="💰 Wallet", callback_data="my_wallet"),
          InlineKeyboardButton(text="📦 Orders", callback_data="my_orders"))
    if uid and uid in ADMIN_IDS:
        b.row(InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin"))
    return b.as_markup()

def cat_kb():
    b = InlineKeyboardBuilder()
    for c in PRODUCTS["categories"]:
        if c["id"] == "topup": continue
        b.row(InlineKeyboardButton(text=c["btn"], callback_data=f"cat_{c['id']}"))
    b.row(InlineKeyboardButton(text="💰 Wallet Top-Up", callback_data="cat_topup"))
    b.row(InlineKeyboardButton(text="🔙 Main Menu", callback_data="main"))
    return b.as_markup()

def prod_kb(cid):
    cat = None
    for c in PRODUCTS["categories"]:
        if c["id"] == cid: cat = c; break
    if not cat: return main_kb()
    b = InlineKeyboardBuilder()
    for p in cat["prods"]:
        b.row(InlineKeyboardButton(text=f"{p[1]} — {fmt(p[2])}", callback_data=f"prod_{cid}|{p[0]}"))
    b.row(InlineKeyboardButton(text="🔙 Categories", callback_data="cats"),
          InlineKeyboardButton(text="🏠 Main Menu", callback_data="main"))
    return b.as_markup()

def pay_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="💳 Wallet Balance", callback_data="pay_wallet"))
    b.row(InlineKeyboardButton(text="💳 bKash", callback_data="pay_bkash"),
          InlineKeyboardButton(text="💳 Nagad", callback_data="pay_nagad"),
          InlineKeyboardButton(text="💳 Rocket", callback_data="pay_rocket"))
    b.row(InlineKeyboardButton(text="🔙 Back", callback_data="pay_back"))
    return b.as_markup()

def admin_kb():
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 Dashboard", callback_data="adm_dash"))
    b.row(InlineKeyboardButton(text="📦 Pending Orders", callback_data="adm_pending"))
    b.row(InlineKeyboardButton(text="💰 Add Balance", callback_data="adm_bal"))
    b.row(InlineKeyboardButton(text="📦 Deliver Order", callback_data="adm_del"))
    b.row(InlineKeyboardButton(text="📨 Broadcast", callback_data="adm_bc"))
    b.row(InlineKeyboardButton(text="🌐 VPN Configs", callback_data="adm_vpn"))
    b.row(InlineKeyboardButton(text="🔑 Stock Keys", callback_data="adm_stock"))
    b.row(InlineKeyboardButton(text="⛔ Ban User", callback_data="adm_ban"))
    b.row(InlineKeyboardButton(text="✅ Unban User", callback_data="adm_unban"))
    b.row(InlineKeyboardButton(text="💾 Restore DB", callback_data="adm_restore"))
    b.row(InlineKeyboardButton(text="🏠 Main Menu", callback_data="main"))
    return b.as_markup()

def back_kb(cb="main"):
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🔙 Back", callback_data=cb))
    return b.as_markup()

# ==================== START ====================
@dp.message(CommandStart())
async def start(m: Message):
    db.add_user(m.from_user.id, m.from_user.first_name or "", m.from_user.username)
    db.upd_activity(m.from_user.id)
    txt = (
        f"🌟 **Welcome to SKY STORE BD!** 🌟\n\n"
        f"👋 Hello, **{m.from_user.first_name}**!\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔥 Free Fire Diamonds — Best BD Price\n"
        f"📆 Weekly / Monthly Membership\n"
        f"⭐ Weekly Lite\n"
        f"❤️ FF Like Service\n"
        f"🎬 Netflix Premium\n"
        f"▶️ YouTube Premium\n"
        f"🍿 Crunchyroll Premium\n"
        f"🌐 VPN Premium (Auto-Delivery)\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"✅ Instant Delivery • 💳 bKash/Nagad/Rocket/Wallet\n"
        f"📞 Support: @{SUPPORT_USERNAME}\n\n"
        f"👇 **Select a category below:**"
    )
    await m.answer(txt, reply_markup=main_kb(m.from_user.id), parse_mode="Markdown")

@dp.message(Command("admin"))
async def adm_cmd(m: Message):
    if m.from_user.id not in ADMIN_IDS: return
    await m.answer("🔐 **Admin Panel**", reply_markup=admin_kb(), parse_mode="Markdown")

# ==================== MAIN NAV ====================
@dp.callback_query(lambda c: c.data == "main")
async def go_main(c: CallbackQuery, s: FSMContext):
    await s.clear()
    await c.message.edit_text(f"🏠 **Main Menu**\n\nWelcome back, {c.from_user.first_name}!", reply_markup=main_kb(c.from_user.id), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "cats")
async def go_cats(c: CallbackQuery, s: FSMContext):
    await s.clear()
    await c.message.edit_text("📂 **Categories:**", reply_markup=cat_kb(), parse_mode="Markdown")

# ==================== CATEGORY ====================
@dp.callback_query(lambda c: c.data.startswith("cat_"))
async def sel_cat(c: CallbackQuery, s: FSMContext):
    cid = c.data[4:]
    cat = None
    for x in PRODUCTS["categories"]:
        if x["id"] == cid: cat = x; break
    if not cat: return await c.answer("Not found!")
    await s.update_data(cat=cat, cid=cid)
    await c.message.edit_text(f"{cat['name']}\n\nSelect your package:", reply_markup=prod_kb(cid), parse_mode="Markdown")

# ==================== PRODUCT ====================
@dp.callback_query(lambda c: c.data.startswith("prod_"))
async def sel_prod(c: CallbackQuery, s: FSMContext):
    _, rest = c.data.split("_", 1)
    cid, pid = rest.split("|")
    cat, prod = gp(cid, pid)
    if not prod: return await c.answer("Product not found!")
    await s.update_data(cat=cat, cid=cid, prod=prod, pid=pid)
    if cid == "topup":
        bal = db.get_bal(c.from_user.id)
        await c.message.edit_text(f"💰 **{prod[1]}**\nPrice: {fmt(prod[2])}\nBalance: {fmt(bal)}\n\nChoose payment:", reply_markup=pay_kb(), parse_mode="Markdown")
        await s.set_state(OrderStates.paying)
    else:
        inp = cat["input"]
        await c.message.edit_text(f"📦 **{prod[1]}**\n💰 Price: {fmt(prod[2])}\n\n{inp}\n`{cat['ph']}`", reply_markup=back_kb(f"cat_{cid}"), parse_mode="Markdown")
        await s.set_state(OrderStates.inputting)

# ==================== INPUT ====================
@dp.message(OrderStates.inputting)
async def inp_handler(m: Message, s: FSMContext):
    val = m.text.strip()
    if len(val) < 2: return await m.answer("❌ Please enter valid details!")
    await s.update_data(inp=val)
    sd = await s.get_data()
    prod = sd.get("prod")
    bal = db.get_bal(m.from_user.id)
    await m.answer(f"✅ Input: `{val}`\n📦 **{prod[1]}**\n💰 Price: {fmt(prod[2])}\n💳 Balance: {fmt(bal)}\n\nSelect payment:", reply_markup=pay_kb(), parse_mode="Markdown")
    await s.set_state(OrderStates.paying)

# ==================== PAYMENT ====================
@dp.callback_query(lambda c: c.data.startswith("pay_"), OrderStates.paying)
async def pay_sel(c: CallbackQuery, s: FSMContext, bot: Bot):
    pm = c.data[4:]
    sd = await s.get_data()
    prod = sd.get("prod"); cat = sd.get("cat"); cid = sd.get("cid"); inp = sd.get("inp", "")
    amt = prod[2]; uid = c.from_user.id

    if pm == "back":
        if cid == "topup": await c.message.edit_text("📂 Categories:", reply_markup=cat_kb())
        else: await c.message.edit_text(f"{cat['name']}\n\nSelect:", reply_markup=prod_kb(cid))
        await s.clear(); return

    if pm == "wallet":
        bal = db.get_bal(uid)
        if bal < amt: return await c.message.edit_text(f"❌ **Insufficient Balance!**\nNeed: {fmt(amt)}\nHave: {fmt(bal)}\n\nTop-up first!", reply_markup=back_kb("cat_topup"), parse_mode="Markdown")
        trx = f"WALLET{datetime.now():%Y%m%d%H%M%S}{random.randint(100,999)}"
        db.deduct_bal(uid, amt)
        await process_order(c, s, bot, uid, prod, cat, cid, inp, "Wallet", trx, amt)
        return

    nums = {"bkash": BKASH_NUMBER, "nagad": NAGAD_NUMBER, "rocket": ROCKET_NUMBER}
    num = nums.get(pm, "Contact admin")
    names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}
    name = names.get(pm, pm)
    await s.update_data(pm=pm)
    await c.message.edit_text(f"💳 **{name} Payment**\n\n📞 Send to: `{num}`\n💰 Amount: `{fmt(amt)}`\n\n📝 Send your Transaction ID after payment:", reply_markup=back_kb("pay_back"), parse_mode="Markdown")
    await s.set_state(OrderStates.trx)

@dp.callback_query(lambda c: c.data == "pay_back", OrderStates.trx)
async def pay_back(c: CallbackQuery, s: FSMContext):
    sd = await s.get_data()
    bal = db.get_bal(c.from_user.id)
    prod = sd.get("prod")
    await c.message.edit_text(f"💳 Payment Method\n📦 {prod[1]}\n💰 {fmt(prod[2])}\n💳 Balance: {fmt(bal)}", reply_markup=pay_kb(), parse_mode="Markdown")
    await s.set_state(OrderStates.paying)

# ==================== TRX ====================
@dp.message(OrderStates.trx)
async def trx_handler(m: Message, s: FSMContext, bot: Bot):
    trx = m.text.strip()
    if len(trx) < 3: return await m.answer("❌ Invalid Transaction ID!")
    sd = await s.get_data()
    prod = sd.get("prod"); cat = sd.get("cat"); cid = sd.get("cid"); inp = sd.get("inp", "")
    pm = sd.get("pm"); amt = prod[2]; uid = m.from_user.id
    names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket"}
    pname = names.get(pm, pm)
    await process_order(m, s, bot, uid, prod, cat, cid, inp, pname, trx, amt)

async def process_order(msg_or_call, s, bot, uid, prod, cat, cid, inp, pm, trx, amt):
    oid = db.add_order(uid, prod[1], cat["name"], amt, 1, inp, pm, trx)

    if cid == "topup":
        bonus = 0
        pname = prod[1]
        if "+" in pname:
            try: bonus = int(re.search(r'\+(\d+)', pname).group(1))
            except: pass
        total = amt + bonus
        db.add_bal(uid, total)
        db.add_trx(uid, total, "topup", pm, trx, f"TopUp +{fmt(bonus)} bonus")
        txt = f"✅ **Balance Added!**\nAmount: {fmt(amt)}\nBonus: +{fmt(bonus)}\nTotal: {fmt(total)}"
        if isinstance(msg_or_call, CallbackQuery):
            await msg_or_call.message.edit_text(txt, reply_markup=main_kb(uid), parse_mode="Markdown")
        else:
            await msg_or_call.answer(txt, reply_markup=main_kb(uid), parse_mode="Markdown")
        for a in ADMIN_IDS:
            try: await bot.send_message(a, f"💰 TopUp\n👤 {uid}\n💵 {fmt(amt)}+{fmt(bonus)}\n💳 {pm}\n🔢 `{trx}`", parse_mode="Markdown")
            except: pass
        await s.clear(); return

    if cid == "vpn":
        loc = inp if inp and inp != "Wallet TopUp" else "Auto"
        stock = db.take_stock(prod[0].split("_")[0] if "_" in prod[0] else prod[0])
        if stock:
            key_data = stock["key_data"]; days = stock.get("expiry_days", 30)
        else:
            key_data = f"VPN-{uuid4().hex[:12].upper()}-{uuid4().hex[:8].upper()}"
            days = 30
        db.add_vpn(oid, uid, prod[0], key_data, loc, days)
        db.upd_order(oid, "delivered", note=f"VPN Auto: {loc}")
        txt = f"✅ **VPN Order Success!**\n\n📦 **{prod[1]}**\n🔑 Key: `{key_data}`\n🌍 Server: {loc}\n📅 Expires: {days}d"
    else:
        db.upd_order(oid, "delivered", note="Auto-delivered")
        txt = f"✅ **Order Success!**\n\n📦 **{prod[1]}**\n💰 {fmt(amt)}\n💳 {pm}\n🔢 `{trx}`\n\n✅ Delivered!"

    if isinstance(msg_or_call, CallbackQuery):
        await msg_or_call.message.edit_text(txt, reply_markup=main_kb(uid), parse_mode="Markdown")
    else:
        await msg_or_call.answer(txt, reply_markup=main_kb(uid), parse_mode="Markdown")

    for a in ADMIN_IDS:
        try:
            await bot.send_message(a, f"📦 New Order #{oid}\n👤 {uid}\n📂 {prod[1]}\n💵 {fmt(amt)}\n💳 {pm}\n🔢 `{trx}`\n📝 `{inp}`", parse_mode="Markdown")
        except: pass
    await s.clear()

# ==================== WALLET / ORDERS ====================
@dp.callback_query(lambda c: c.data == "my_wallet")
async def wallet_handler(c: CallbackQuery):
    uid = c.from_user.id; bal = db.get_bal(uid)
    await c.message.edit_text(f"💰 **My Wallet**\n\nBalance: {fmt(bal)}\n\nTop-up via Wallet Top-Up category!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💰 Top-Up", callback_data="cat_topup")],[InlineKeyboardButton(text="🏠 Main Menu", callback_data="main")]]), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "my_orders")
async def orders_handler(c: CallbackQuery):
    uid = c.from_user.id; orders = db.get_orders(uid=uid, limit=10)
    if not orders:
        return await c.message.edit_text("📦 **No orders yet!**", reply_markup=back_kb("main"), parse_mode="Markdown")
    txt = "📦 **My Orders:**\n\n"
    for o in orders:
        em = {"pending": "⏳", "delivered": "✅", "processing": "🔄"}.get(o["status"], "❓")
        txt += f"`#{o['id']}` {em} **{o['product_name'][:25]}**\n   {fmt(o['amount'])} — {o['status'].upper()}\n\n"
    await c.message.edit_text(txt, reply_markup=back_kb("main"), parse_mode="Markdown")

# ==================== ADMIN ====================
@dp.callback_query(lambda c: c.data == "admin")
async def admin_menu(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await s.clear()
    await c.message.edit_text("🔐 **Admin Panel**", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_dash")
async def adm_dash(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    st = db.get_stats()
    stk = ""
    for s in st["stock"]: stk += f"{s['category']}: {s['c']} keys\n"
    await c.message.edit_text(f"📊 **Dashboard**\n\n👥 Users: {st['users']}\n📦 Orders: {st['orders']}\n⏳ Pending: {st['pending']}\n💰 Revenue: {fmt(st['revenue'])}\n💳 Wallets: {fmt(st['wallets'])}\n🔑 Stock:\n{stk or 'None'}", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_pending")
async def adm_pending(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    orders = db.get_orders(status="pending", limit=20)
    if not orders: return await c.message.edit_text("✅ No pending orders!", reply_markup=admin_kb())
    txt = "⏳ **Pending Orders:**\n\n"
    for o in orders[:15]:
        txt += f"`#{o['id']}` 👤 `{o['user_id']}`\n   {o['product_name'][:20]} | {fmt(o['amount'])}\n   💳 {o['pay_method']} | `{o['trx_id'][:15]}`\n\n"
    await c.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_bal")
async def adm_bal_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("💰 **Add Balance**\n\nSend User ID:", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.bal_user)

@dp.message(AdminStates.bal_user)
async def adm_bal_user(m: Message, s: FSMContext):
    try: uid = int(m.text.strip()); await s.update_data(target=uid); await m.answer(f"👤 Target: `{uid}`\nCurrent: {fmt(db.get_bal(uid))}\n\nSend amount:"); await s.set_state(AdminStates.bal_amt)
    except: await m.answer("❌ Invalid ID!")

@dp.message(AdminStates.bal_amt)
async def adm_bal_amt(m: Message, s: FSMContext, bot: Bot):
    try:
        amt = float(m.text.strip()); sd = await s.get_data(); uid = sd.get("target")
        if amt <= 0 or amt > 1e6: return await m.answer("❌ Invalid amount!")
        db.add_bal(uid, amt); db.add_trx(uid, amt, "admin_add", "Admin", f"ADMIN{datetime.now():%Y%m%d%H%M%S}", f"By @{m.from_user.username}")
        await m.answer(f"✅ **Added!**\n👤 `{uid}`\n💰 +{fmt(amt)}", reply_markup=admin_kb(), parse_mode="Markdown")
        try: await bot.send_message(uid, f"💰 +{fmt(amt)} added to your wallet!")
        except: pass
        await s.clear()
    except: await m.answer("❌ Invalid amount!")

@dp.callback_query(lambda c: c.data == "adm_del")
async def adm_del_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("📦 **Deliver Order**\n\nSend Order ID:", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.del_oid)

@dp.message(AdminStates.del_oid)
async def adm_del_oid(m: Message, s: FSMContext):
    try:
        oid = int(m.text.strip()); o = db.get_order(oid)
        if not o: return await m.answer("❌ Order not found!")
        await s.update_data(del_oid=oid)
        await m.answer(f"📦 Order #{oid}\nProduct: {o['product_name']}\nUser: `{o['user_id']}`\nStatus: {o['status']}\n\nSend photo/note:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⚡ Deliver Now", callback_data="del_now")],[InlineKeyboardButton(text="🔙 Admin", callback_data="admin")]]), parse_mode="Markdown")
        await s.set_state(AdminStates.del_file)
    except: await m.answer("❌ Invalid ID!")

@dp.callback_query(lambda c: c.data == "del_now")
async def del_now(c: CallbackQuery, s: FSMContext, bot: Bot):
    sd = await s.get_data(); oid = sd.get("del_oid")
    db.upd_order(oid, "delivered", note="Delivered ✅")
    o = db.get_order(oid)
    await c.message.edit_text(f"✅ Order #{oid} Delivered!", reply_markup=admin_kb())
    if o:
        try: await bot.send_message(o["user_id"], f"✅ **Order Delivered!**\n\n#{oid}\n📦 {o['product_name']}\nThank you!", parse_mode="Markdown")
        except: pass
    await s.clear()

@dp.message(AdminStates.del_file)
async def adm_del_file(m: Message, s: FSMContext, bot: Bot):
    sd = await s.get_data(); oid = sd.get("del_oid")
    fid = ""; note = "Delivered ✅"
    if m.photo: fid = m.photo[-1].file_id; note = m.caption or "✅"
    elif m.document: fid = m.document.file_id; note = m.caption or "✅"
    else: note = m.text or "✅"
    db.upd_order(oid, "delivered", fid, note)
    o = db.get_order(oid)
    await m.answer(f"✅ Order #{oid} Delivered!\n📝 {note}", reply_markup=admin_kb())
    if o:
        try:
            if fid: await bot.send_photo(o["user_id"], fid, caption=f"✅ **Delivered!**\n#{oid}\n📦 {o['product_name']}", parse_mode="Markdown")
            else: await bot.send_message(o["user_id"], f"✅ **Delivered!**\n\n#{oid}\n📦 {o['product_name']}\n{note}", parse_mode="Markdown")
        except: pass
    await s.clear()

@dp.callback_query(lambda c: c.data == "adm_bc")
async def adm_bc_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("📨 **Broadcast**\n\nSend message:", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.bc_msg)

@dp.message(AdminStates.bc_msg)
async def adm_bc_preview(m: Message, s: FSMContext):
    txt = m.text or m.caption or "📢"
    await s.update_data(bc_txt=txt)
    users = db.get_all_users(); total = len(users); active = sum(1 for u in users if not u["is_banned"])
    await m.answer(f"📨 Preview:\n`{txt[:200]}`\n\n👥 Total: {total}\n📨 Will get: {active}\n\nSend?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ Send", callback_data="bc_send"),InlineKeyboardButton(text="❌ Cancel", callback_data="admin")]]), parse_mode="Markdown")
    await s.set_state(AdminStates.bc_confirm)

@dp.callback_query(lambda c: c.data == "bc_send")
async def adm_bc_send(c: CallbackQuery, s: FSMContext, bot: Bot):
    if c.from_user.id not in ADMIN_IDS: return
    sd = await s.get_data(); txt = sd.get("bc_txt", "📢")
    await c.message.edit_text("📨 Broadcasting...")
    users = db.get_all_users(); sent = 0; failed = 0
    for u in users:
        if u["is_banned"]: continue
        try: await bot.send_message(u["user_id"], txt, parse_mode="Markdown"); sent += 1; await asyncio.sleep(0.03)
        except: failed += 1
    await c.message.edit_text(f"✅ Broadcast done!\n✅ Sent: {sent}\n❌ Failed: {failed}", reply_markup=admin_kb())
    await s.clear()

@dp.callback_query(lambda c: c.data == "adm_vpn")
async def adm_vpn(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📋 VPN Orders", callback_data="adm_vpn_orders"))
    b.row(InlineKeyboardButton(text="➕ Add Config", callback_data="adm_vpn_add"))
    b.row(InlineKeyboardButton(text="📊 Stock Status", callback_data="adm_stock_status"))
    b.row(InlineKeyboardButton(text="🔙 Admin", callback_data="admin"))
    await c.message.edit_text("🌐 **VPN Management**", reply_markup=b.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_vpn_orders")
async def adm_vpn_orders(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    orders = db.get_orders(status="delivered", limit=30)
    vpn_orders = [o for o in orders if "vpn" in o["category"].lower() or "vpn" in o["product_name"].lower()]
    if not vpn_orders: return await c.message.edit_text("No VPN orders.", reply_markup=admin_kb())
    txt = "🌐 **VPN Orders:**\n\n"
    for o in vpn_orders[:15]:
        cfg = db.get_vpn(o["id"])
        has = "✅" if cfg else "❌"
        txt += f"`#{o['id']}` {has} 👤 `{o['user_id']}`\n   {o['product_name'][:20]} | {fmt(o['amount'])} | {o['user_input'][:15]}\n\n"
    await c.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_vpn_add")
async def adm_vpn_add(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("➕ **Add VPN Config**\n\nSend Order ID:", reply_markup=back_kb("adm_vpn"), parse_mode="Markdown")
    await s.set_state(AdminStates.vpn_oid)

@dp.message(AdminStates.vpn_oid)
async def adm_vpn_oid(m: Message, s: FSMContext):
    try:
        oid = int(m.text.strip()); o = db.get_order(oid)
        if not o: return await m.answer("❌ Order not found!")
        await s.update_data(vpn_oid=oid)
        await m.answer(f"Order #{oid}\nProduct: {o['product_name']}\nUser: `{o['user_id']}`\n\nSend VPN config/key:", reply_markup=back_kb("adm_vpn"), parse_mode="Markdown")
        await s.set_state(AdminStates.vpn_data)
    except: await m.answer("❌ Invalid ID!")

@dp.message(AdminStates.vpn_data)
async def adm_vpn_data(m: Message, s: FSMContext):
    data = m.text.strip()
    if len(data) < 5: return await m.answer("❌ Too short!")
    await s.update_data(vpn_data=data)
    await m.answer("✅ Config received!\nSend server location (e.g., Singapore):", reply_markup=back_kb("adm_vpn"))
    await s.set_state(AdminStates.vpn_loc)

@dp.message(AdminStates.vpn_loc)
async def adm_vpn_loc(m: Message, s: FSMContext, bot: Bot):
    loc = m.text.strip()
    if not loc: return await m.answer("❌ Enter location!")
    sd = await s.get_data(); oid = sd.get("vpn_oid"); data = sd.get("vpn_data")
    o = db.get_order(oid)
    if not o: return await m.answer("❌ Order not found!")
    db.add_vpn(oid, o["user_id"], "Manual", data, loc, 30)
    db.upd_order(oid, "delivered", note=f"VPN Config: {loc}")
    await m.answer(f"✅ **VPN Config Added!**\nOrder #{oid}\n👤 `{o['user_id']}`\n🌍 {loc}", reply_markup=admin_kb(), parse_mode="Markdown")
    try: await bot.send_message(o["user_id"], f"🌐 **VPN Config Ready!**\n\n🌍 {loc}\n📋 `{data[:300]}`\n\n📞 @{SUPPORT_USERNAME}", parse_mode="Markdown")
    except: pass
    await s.clear()

@dp.callback_query(lambda c: c.data == "adm_stock")
async def adm_stock(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📋 View Stock", callback_data="adm_stock_view"))
    b.row(InlineKeyboardButton(text="➕ Add Keys", callback_data="adm_stock_add"))
    b.row(InlineKeyboardButton(text="🗑️ Delete Key", callback_data="adm_stock_del"))
    b.row(InlineKeyboardButton(text="🔙 Admin", callback_data="admin"))
    await c.message.edit_text("🔑 **Stock Keys**", reply_markup=b.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_stock_view")
async def adm_stock_view(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    stock = db.get_all_stock()
    if not stock: return await c.message.edit_text("No stock.", reply_markup=admin_kb())
    by_cat = {}
    for s in stock:
        cat = s["category"]
        if cat not in by_cat: by_cat[cat] = {"total": 0, "used": 0, "avail": 0}
        by_cat[cat]["total"] += 1
        if s["is_used"]: by_cat[cat]["used"] += 1
        else: by_cat[cat]["avail"] += 1
    txt = "🔑 **Stock Overview:**\n\n"
    for cat, data in by_cat.items():
        txt += f"**{cat.upper()}**: {data['avail']} avail / {data['total']} total\n"
    txt += "\n**Recent:**\n"
    for s in stock[:10]:
        st = "✅" if s["is_used"] else "📦"
        txt += f"{st} #{s['id']} `{s['key_data'][:30]}...` ({s['category']})\n"
    await c.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_stock_add")
async def adm_stock_add(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    b = InlineKeyboardBuilder()
    cats = ["expressvpn","hma","vpnip","vanish","protonvpn","proxy","vps"]
    names = {"expressvpn":"ExpressVPN","hma":"HMA","vpnip":"VPN IP","vanish":"Vanish","protonvpn":"ProtonVPN","proxy":"Proxy","vps":"VPS"}
    for cat in cats:
        b.row(InlineKeyboardButton(text=f"🔑 {names.get(cat,cat)}", callback_data=f"stk_cat_{cat}"))
    b.row(InlineKeyboardButton(text="🔙 Stock", callback_data="adm_stock"))
    await c.message.edit_text("➕ **Add Keys**\n\nSelect category:", reply_markup=b.as_markup(), parse_mode="Markdown")
    await s.set_state(AdminStates.stock_cat)

@dp.callback_query(lambda c: c.data.startswith("stk_cat_"))
async def stk_cat_sel(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    cat = c.data[8:]
    await s.update_data(stk_cat=cat)
    names = {"expressvpn":"ExpressVPN","hma":"HMA","vpnip":"VPN IP","vanish":"Vanish","protonvpn":"ProtonVPN","proxy":"Proxy","vps":"VPS"}
    await c.message.edit_text(f"➕ **{names.get(cat,cat)} Keys**\n\nSend keys (one per line):\n\nExample:\n`KEY-XXXX-XXXX`\n`KEY-YYYY-YYYY`", reply_markup=back_kb("adm_stock_add"), parse_mode="Markdown")
    await s.set_state(AdminStates.stock_keys)

@dp.message(AdminStates.stock_keys)
async def stk_keys_in(m: Message, s: FSMContext):
    sd = await s.get_data(); cat = sd.get("stk_cat","")
    keys = [k.strip() for k in m.text.strip().split("\n") if k.strip()]
    if not keys: return await m.answer("❌ No valid keys!")
    added = db.add_stock_bulk(cat, keys, 30)
    await m.answer(f"✅ **{added} keys added to {cat.upper()}!**", reply_markup=admin_kb())
    await s.clear()

@dp.callback_query(lambda c: c.data == "adm_stock_del")
async def adm_stock_del(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    stock = db.get_all_stock()
    if not stock: return await c.message.edit_text("No stock.", reply_markup=admin_kb())
    b = InlineKeyboardBuilder()
    for s in stock[:20]:
        st = "✅" if s["is_used"] else "📦"
        b.row(InlineKeyboardButton(text=f"{st} #{s['id']} {s['key_data'][:20]}... ({s['category']})", callback_data=f"delk_{s['id']}"))
    b.row(InlineKeyboardButton(text="🔙 Stock", callback_data="adm_stock"))
    await c.message.edit_text("🗑️ **Delete Key:**", reply_markup=b.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delk_"))
async def delk_go(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    kid = int(c.data[5:])
    if db.del_stock(kid): await c.answer("🗑️ Deleted!", show_alert=True)
    else: await c.answer("❌ Not found!", show_alert=True)

@dp.callback_query(lambda c: c.data == "adm_stock_status")
async def adm_stock_st(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS: return
    st = db.get_stock()
    txt = "📊 **Stock Status:**\n\n"
    if st:
        for s in st: txt += f"🔑 {s['category'].upper()}: {s['cnt']} keys\n"
    else: txt += "No stock.\n"
    await c.message.edit_text(txt, reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "adm_ban")
async def adm_ban_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("⛔ **Ban User**\nSend User ID:", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.ban_uid)

@dp.message(AdminStates.ban_uid)
async def adm_ban_go(m: Message, s: FSMContext, bot: Bot):
    try:
        uid = int(m.text.strip())
        if uid in ADMIN_IDS: return await m.answer("❌ Cannot ban admin!")
        db.set_ban(uid, True)
        await m.answer(f"⛔ Banned: `{uid}`", reply_markup=admin_kb())
        try: await bot.send_message(uid, "⛔ You have been banned.")
        except: pass
        await s.clear()
    except: await m.answer("❌ Invalid ID!")

@dp.callback_query(lambda c: c.data == "adm_unban")
async def adm_unban_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("✅ **Unban User**\nSend User ID:", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.unban_uid)

@dp.message(AdminStates.unban_uid)
async def adm_unban_go(m: Message, s: FSMContext, bot: Bot):
    try:
        uid = int(m.text.strip())
        db.set_ban(uid, False)
        await m.answer(f"✅ Unbanned: `{uid}`", reply_markup=admin_kb())
        try: await bot.send_message(uid, "✅ You have been unbanned.")
        except: pass
        await s.clear()
    except: await m.answer("❌ Invalid ID!")

@dp.callback_query(lambda c: c.data == "adm_restore")
async def adm_restore_start(c: CallbackQuery, s: FSMContext):
    if c.from_user.id not in ADMIN_IDS: return
    await c.message.edit_text("💾 **Restore DB**\nSend `.db` file:\n⚠️ This REPLACES current DB!", reply_markup=back_kb("admin"), parse_mode="Markdown")
    await s.set_state(AdminStates.bc_msg)
    await s.update_data(is_restore=True)

@dp.message(lambda m: m.document and m.document.file_name.endswith('.db'))
async def restore_db_handler(m: Message, bot: Bot):
    uid = m.from_user.id
    if uid not in ADMIN_IDS: return
    await m.answer("📥 Restoring...")
    try:
        file = await bot.get_file(m.document.file_id)
        path = db.db_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        await bot.download_file(file.file_path, path)
        db._init()
        await m.answer("✅ **Database Restored!**", reply_markup=admin_kb(), parse_mode="Markdown")
    except Exception as e: await m.answer(f"❌ Error: {e}")

# ==================== MAIN ====================
async def main():
    print(f"""
╔══════════════════════════════════════════╗
║     🌟 SKY STORE BD — v4.0              ║
║     🤖 {BOT_USERNAME}                   
║     👤 Admins: {len(ADMIN_IDS)}                     
║     📦 Products: {sum(len(c['prods']) for c in PRODUCTS['categories'])}            
║     🟢 BOT RUNNING...                    ║
╚══════════════════════════════════════════╝
    """)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
