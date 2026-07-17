#!/usr/bin/env python3
"""
SKY STORE BD — Premium Digital Store Telegram Bot
Version 3.7 — Complete fix: syntax error, callbacks, DB sync, expiry, deposit
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
TIMEZONE_OFFSET = 6  # Bangladesh (BST)
DB_PATH = "store.db"
BACKUP_DIR = "backups"
BKASH_NUMBER = "01302940879"
NAGAD_NUMBER = "01302940879"
ROCKET_NUMBER = "01302940879"

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
            conn.execute("""CREATE TABLE IF NOT EXISTS promo_codes(
                code TEXT PRIMARY KEY,
                amount REAL DEFAULT 0,
                discount_pct REAL DEFAULT 0,
                max_uses INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                created_at TEXT DEFAULT (datetime('now','+6 hours'))
            )""")

    # ── Category Operations ──
    def add_category(self, cat_id, name, parent_id=None, description=""):
        with self._get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO categories (id, parent_id, name, description, is_active) VALUES (?,?,?,?,1)",
                         (cat_id, parent_id, name, description))

    def get_categories(self, parent_id=None, active_only=True):
        with self._get_conn() as conn:
            if parent_id is None:
                if active_only:
                    cur = conn.execute("SELECT * FROM categories WHERE parent_id IS NULL AND is_active=1 ORDER BY sort_order, name")
                else:
                    cur = conn.execute("SELECT * FROM categories WHERE parent_id IS NULL ORDER BY sort_order, name")
            else:
                if active_only:
                    cur = conn.execute("SELECT * FROM categories WHERE parent_id=? AND is_active=1 ORDER BY sort_order, name", (parent_id,))
                else:
                    cur = conn.execute("SELECT * FROM categories WHERE parent_id=? ORDER BY sort_order, name", (parent_id,))
            return [dict(r) for r in cur.fetchall()]

    def get_all_categories(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order, name")
            return [dict(r) for r in cur.fetchall()]

    def get_category(self, cat_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM categories WHERE id=?", (cat_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def update_category(self, cat_id, name=None, description=None, is_active=None):
        with self._get_conn() as conn:
            sets = []
            vals = []
            if name:
                sets.append("name=?")
                vals.append(name)
            if description is not None:
                sets.append("description=?")
                vals.append(description)
            if is_active is not None:
                sets.append("is_active=?")
                vals.append(is_active)
            if sets:
                vals.append(cat_id)
                conn.execute(f"UPDATE categories SET {','.join(sets)} WHERE id=?", vals)

    def delete_category(self, cat_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
            conn.execute("DELETE FROM categories WHERE parent_id=?", (cat_id,))

    def category_has_products(self, cat_id):
        """Recursively check if a category or any subcategory has active products with stock."""
        with self._get_conn() as conn:
            cur = conn.execute("""
                SELECT COUNT(*) FROM products p
                WHERE p.category_id=? AND p.is_active=1
                AND EXISTS (SELECT 1 FROM stock s WHERE s.product_id=p.id AND s.is_used=0)
            """, (cat_id,))
            if cur.fetchone()[0] > 0:
                return True
            cur = conn.execute("SELECT id FROM categories WHERE parent_id=? AND is_active=1", (cat_id,))
            rows = cur.fetchall()
            for r in rows:
                if self.category_has_products(r["id"]):
                    return True
            return False

    # ── Product Operations ──
    def add_product(self, prod_id, cat_id, name, price, bonus=0, stock_type="key_only", expiry_days=30):
        with self._get_conn() as conn:
            conn.execute("""INSERT OR REPLACE INTO products 
                (id, category_id, name, price, bonus, stock_type, expiry_days, is_active)
                VALUES (?,?,?,?,?,?,?,1)""",
                (prod_id, cat_id, name, price, bonus, stock_type, expiry_days))

    def get_product(self, prod_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products WHERE id=?", (prod_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_products(self, cat_id=None, active_only=True):
        with self._get_conn() as conn:
            if cat_id:
                if active_only:
                    cur = conn.execute("SELECT * FROM products WHERE category_id=? AND is_active=1 AND EXISTS (SELECT 1 FROM stock s WHERE s.product_id=products.id AND s.is_used=0) ORDER BY sort_order, name", (cat_id,))
                else:
                    cur = conn.execute("SELECT * FROM products WHERE category_id=? ORDER BY sort_order, name", (cat_id,))
            else:
                if active_only:
                    cur = conn.execute("SELECT * FROM products WHERE is_active=1 ORDER BY sort_order, name")
                else:
                    cur = conn.execute("SELECT * FROM products ORDER BY sort_order, name")
            return [dict(r) for r in cur.fetchall()]

    def get_all_products(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM products ORDER BY sort_order, name")
            return [dict(r) for r in cur.fetchall()]

    def get_products_for_admin(self, cat_id=None):
        with self._get_conn() as conn:
            if cat_id:
                cur = conn.execute("SELECT p.*, (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.is_used=0) as stock_count FROM products p WHERE p.category_id=? ORDER BY p.sort_order, p.name", (cat_id,))
            else:
                cur = conn.execute("SELECT p.*, (SELECT COUNT(*) FROM stock s WHERE s.product_id=p.id AND s.is_used=0) as stock_count FROM products p ORDER BY p.sort_order, p.name")
            return [dict(r) for r in cur.fetchall()]

    def update_product(self, prod_id, name=None, price=None, bonus=None, stock_type=None, expiry_days=None, is_active=None):
        with self._get_conn() as conn:
            sets = []
            vals = []
            if name:
                sets.append("name=?")
                vals.append(name)
            if price is not None:
                sets.append("price=?")
                vals.append(price)
            if bonus is not None:
                sets.append("bonus=?")
                vals.append(bonus)
            if stock_type:
                sets.append("stock_type=?")
                vals.append(stock_type)
            if expiry_days is not None:
                sets.append("expiry_days=?")
                vals.append(expiry_days)
            if is_active is not None:
                sets.append("is_active=?")
                vals.append(is_active)
            if sets:
                vals.append(prod_id)
                conn.execute(f"UPDATE products SET {','.join(sets)} WHERE id=?", vals)

    def delete_product(self, prod_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM products WHERE id=?", (prod_id,))
            conn.execute("DELETE FROM stock WHERE product_id=?", (prod_id,))

    # ── Stock Operations ──
    def add_stock(self, product_id, stock_type, email="", password="", key_data="", expiry_days=None):
        with self._get_conn() as conn:
            if expiry_days is None:
                cur = conn.execute("SELECT expiry_days FROM products WHERE id=?", (product_id,))
                r = cur.fetchone()
                expiry_days = r["expiry_days"] if r else 30
            conn.execute("""INSERT INTO stock (product_id, stock_type, email, password, key_data, expiry_days)
                VALUES (?,?,?,?,?,?)""",
                (product_id, stock_type, email, password, key_data, expiry_days))

    def get_stock_counts(self):
        with self._get_conn() as conn:
            cur = conn.execute("""
                SELECT s.product_id, p.name, p.stock_type,
                       COUNT(*) as cnt,
                       MIN(s.expiry_days) as min_expiry
                FROM stock s
                JOIN products p ON p.id = s.product_id
                WHERE s.is_used=0
                GROUP BY s.product_id
                ORDER BY cnt DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    def get_available_stock(self, product_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM stock WHERE product_id=? AND is_used=0 ORDER BY id ASC LIMIT 1", (product_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_all_stock(self, product_id=None):
        with self._get_conn() as conn:
            if product_id:
                cur = conn.execute("SELECT * FROM stock WHERE product_id=? ORDER BY id DESC", (product_id,))
            else:
                cur = conn.execute("SELECT s.*, p.name as product_name FROM stock s JOIN products p ON p.id=s.product_id ORDER BY s.id DESC")
            return [dict(r) for r in cur.fetchall()]

    def mark_stock_used(self, stock_id):
        with self._get_conn() as conn:
            conn.execute("UPDATE stock SET is_used=1 WHERE id=?", (stock_id,))

    def delete_stock(self, stock_id):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM stock WHERE id=?", (stock_id,))

    def get_stock_count(self, product_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM stock WHERE product_id=? AND is_used=0", (product_id,))
            return cur.fetchone()[0]

    # ── User Operations ──
    def add_user(self, user_id, first_name="", username=""):
        with self._get_conn() as conn:
            conn.execute("""INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?,?,?)""",
                         (user_id, first_name, username))

    def get_user(self, user_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_all_users(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM users ORDER BY joined_at DESC")
            return [dict(r) for r in cur.fetchall()]

    def user_count(self):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM users")
            return cur.fetchone()[0]

    def set_ban(self, user_id, banned=True):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (1 if banned else 0, user_id))

    # ── Balance Operations ──
    def add_balance(self, user_id, amount):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET balance=COALESCE(balance,0)+? WHERE user_id=?", (amount, user_id))

    def deduct_balance(self, user_id, amount):
        with self._get_conn() as conn:
            conn.execute("UPDATE users SET balance=COALESCE(balance,0)-? WHERE user_id=? AND COALESCE(balance,0)>=?", (amount, user_id, amount))

    def get_balance(self, user_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT COALESCE(balance,0) as balance FROM users WHERE user_id=?", (user_id,))
            r = cur.fetchone()
            return r["balance"] if r else 0

    # ── Order Operations ──
    def add_order(self, user_id, product_id, product_name, category_id, amount, user_input="", payment_method="", transaction_id=""):
        with self._get_conn() as conn:
            cur = conn.execute("""INSERT INTO orders 
                (user_id, product_id, product_name, category_id, amount, user_input, payment_method, transaction_id)
                VALUES (?,?,?,?,?,?,?,?)""",
                (user_id, product_id, product_name, category_id, amount, user_input, payment_method, transaction_id))
            return cur.lastrowid

    def get_order(self, order_id):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,))
            r = cur.fetchone()
            return dict(r) if r else None

    def get_orders(self, user_id=None, status=None):
        with self._get_conn() as conn:
            if user_id and status:
                cur = conn.execute("SELECT * FROM orders WHERE user_id=? AND status=? ORDER BY id DESC", (user_id, status))
            elif user_id:
                cur = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user_id,))
            elif status:
                cur = conn.execute("SELECT * FROM orders WHERE status=? ORDER BY id DESC", (status,))
            else:
                cur = conn.execute("SELECT * FROM orders ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def get_pending_orders(self):
        with self._get_conn() as conn:
            cur = conn.execute("""
                SELECT o.*, u.first_name, u.username 
                FROM orders o 
                JOIN users u ON u.user_id=o.user_id 
                WHERE o.status='pending' 
                ORDER BY o.id DESC
            """)
            return [dict(r) for r in cur.fetchall()]

    def update_order(self, order_id, status, delivery_data=None):
        with self._get_conn() as conn:
            if delivery_data:
                conn.execute("UPDATE orders SET status=?, delivery_data=? WHERE id=?",
                            (status, json.dumps(delivery_data), order_id))
            else:
                conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))

    # ── Transaction Operations ──
    def add_transaction(self, user_id, amount, trx_type, method="", trx_id="", note=""):
        with self._get_conn() as conn:
            conn.execute("""INSERT INTO transactions (user_id, amount, type, method, trx_id, note)
                VALUES (?,?,?,?,?,?)""",
                (user_id, amount, trx_type, method, trx_id, note))

    # ── Promo Code Operations ──
    def add_promo(self, code, amount, discount_pct=0, max_uses=0):
        with self._get_conn() as conn:
            conn.execute("""INSERT OR REPLACE INTO promo_codes (code, amount, discount_pct, max_uses)
                VALUES (?,?,?,?)""", (code, amount, discount_pct, max_uses))

    def get_promo(self, code):
        with self._get_conn() as conn:
            cur = conn.execute("SELECT * FROM promo_codes WHERE code=?", (code,))
            r = cur.fetchone()
            return dict(r) if r else None

    def use_promo(self, code):
        with self._get_conn() as conn:
            conn.execute("UPDATE promo_codes SET used_count=used_count+1 WHERE code=?", (code,))

    # ── Backup & Restore ──
    def backup(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = now_local().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{BACKUP_DIR}/store_backup_{timestamp}.db"
        shutil.copy2(self.path, backup_path)
        return backup_path

    def restore(self, backup_path):
        if not os.path.exists(backup_path):
            return False
        try:
            test_conn = sqlite3.connect(backup_path)
            test_conn.execute("SELECT COUNT(*) FROM categories")
            test_conn.close()
            shutil.copy2(backup_path, self.path)
            return True
        except:
            return False


# ─── INITIALIZE ──────────────────────────────────────────────────────────────
db = Database()
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# ─── HELPER: Get Product Expiry Days ─────────────────────────────────────────
def get_product_expiry_days(prod, stock=None):
    """Get expiry days for a product: stock record → product → fallback 30"""
    if stock and stock.get("expiry_days") is not None:
        return int(stock["expiry_days"])
    if prod and prod.get("expiry_days") is not None:
        return int(prod["expiry_days"])
    return 30


# ─── MIDDLEWARE ──────────────────────────────────────────────────────────────
class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = None
        if hasattr(event, "from_user") and event.from_user:
            user = event.from_user
        elif hasattr(event, "message") and event.message and event.message.from_user:
            user = event.message.from_user

        if user and user.id in ADMIN_IDS:
            return await handler(event, data)

        if user:
            u = db.get_user(user.id)
            if u and u["is_banned"]:
                return
        return await handler(event, data)


# ─── STATES ──────────────────────────────────────────────────────────────────
class OrderFlow(StatesGroup):
    category = State()
    product = State()
    quantity = State()
    user_input = State()
    payment_confirm = State()

class DepositFlow(StatesGroup):
    amount = State()
    method = State()
    trx_id = State()

class AdminFlow(StatesGroup):
    menu = State()
    # Category management
    addcat_name = State()
    addcat_parent = State()
    delcat_confirm = State()
    editcat_select = State()
    editcat_field = State()
    # Product management
    addprod_cat = State()
    addprod_name = State()
    addprod_price = State()
    addprod_expiry = State()
    addprod_stocktype_pending = State()
    editprod_select = State()
    editprod_cat = State()
    editprod_field = State()
    # Stock management
    stock_target = State()
    stock_type_choice = State()
    stock_input = State()
    # Orders & Delivery
    deliver_oid = State()
    deliver_file = State()
    # Other
    broadcast_msg = State()
    ban_uid = State()
    unban_uid = State()
    restore_file = State()
    promo_code = State()
    promo_amount = State()
    # Add Balance
    addbal_uid = State()
    addbal_amt = State()


# ─── KEYBOARD BUILDERS ──────────────────────────────────────────────────────
def btn(text, callback_data, style=None):
    kwargs = {"text": text, "callback_data": callback_data}
    if style:
        kwargs["style"] = style.value if hasattr(style, 'value') else style
    return InlineKeyboardButton(**kwargs)

def admin_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Dashboard", "admin_dash"))
    kb.row(btn("📁 Categories", "admin_cat"), btn("📦 Products", "admin_prod"))
    kb.row(btn("🔑 Stock", "admin_stock"), btn("📋 Orders", "admin_orders"))
    kb.row(btn("💰 Add Balance", "admin_addbal"), btn("📨 Broadcast", "admin_broadcast"))
    kb.row(btn("💰 Promo", "admin_promo"))
    kb.row(btn("⛔ Ban User", "admin_ban"), btn("✅ Unban", "admin_unban"))
    kb.row(btn("💾 Backup", "admin_backup"), btn("🔄 Restore", "admin_restore"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("📊 Status", "stock_status"), btn("➕ Add Stock", "stock_add"))
    kb.row(btn("🗑️ Delete Stock", "stock_del"))
    kb.row(btn("🔙 Back to Admin", "admin_menu"))
    return kb.as_markup()

def admin_cat_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("➕ Add Main Category", "cat_add_main"))
    kb.row(btn("➕ Add Sub-Category", "cat_add_sub"))
    kb.row(btn("📋 List Categories", "cat_list"))
    kb.row(btn("✏️ Edit Category", "cat_edit"))
    kb.row(btn("🗑️ Delete Category", "cat_del"))
    kb.row(btn("🔙 Back to Admin", "admin_menu"))
    return kb.as_markup()

def admin_prod_kb():
    kb = InlineKeyboardBuilder()
    kb.row(btn("➕ Add Product", "prod_add"))
    kb.row(btn("✏️ Edit Product", "prod_edit"))
    kb.row(btn("🗑️ Delete Product", "prod_del"))
    kb.row(btn("🔙 Back to Admin", "admin_menu"))
    return kb.as_markup()

def back_btn(callback_data="admin_menu"):
    return btn("🔙 Back", callback_data)

# ── MAIN MENU (User) ─────────────────────────────────────────────────────────
def main_menu_kb():
    kb = InlineKeyboardBuilder()
    cats = db.get_categories(parent_id=None, active_only=True)
    for cat in cats:
        if db.category_has_products(cat["id"]):
            icon = cat.get("icon", "📁")
            kb.button(text=f"{icon} {cat['name']}", callback_data=f"cat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("👤 My Account", "my_account"))
    kb.row(btn("📞 Support", "support"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════════════════════════════
#  USER HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = msg.from_user
    db.add_user(user.id, user.first_name, user.username)
    u = db.get_user(user.id)
    bal = u["balance"] if u else 0
    lines = [
        f"🌟 *Welcome to SKY STORE BD!* 🌟",
        "",
        f"👋 Hello, {user.first_name}!",
        f"💰 Balance: {fmt(bal)}",
        "",
        "👇 Choose a category to browse products:",
    ]
    await msg.answer("\n".join(lines), reply_markup=main_menu_kb(), parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    await msg.answer("🔐 *Admin Panel*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu_back(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔐 *Admin Panel*", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "support")
async def support_handler(call: CallbackQuery):
    await call.answer()
    lines = [
        "📞 *Support*",
        "",
        f"👤 Username: @{SUPPORT_USERNAME}",
        "",
        "Contact us for any issues or inquiries.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("💬 Contact Support", f"https://t.me/{SUPPORT_USERNAME}"))
    kb.row(back_btn())
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "my_account")
async def my_account(call: CallbackQuery):
    await call.answer()
    user = call.from_user
    u = db.get_user(user.id)
    bal = u["balance"] if u else 0
    orders = db.get_orders(user.id)
    total_orders = len(orders)
    lines = [
        "👤 *My Account*",
        "",
        f"🆔 ID: `{user.id}`",
        f"💰 Balance: {fmt(bal)}",
        f"📦 Total Orders: {total_orders}",
        "",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("💰 Deposit", "deposit_start"))
    kb.row(btn("📦 My Orders", "my_orders"))
    kb.row(back_btn())
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ── CATEGORY VIEW (USER) ─────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("cat_") and not c.data.startswith("cat_add") and not c.data.startswith("cat_li") and not c.data.startswith("cat_de") and not c.data.startswith("cat_ed"))
async def view_category(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[4:]
    cat = db.get_category(cat_id)
    if not cat:
        return

    subcats = db.get_categories(parent_id=cat_id, active_only=True)
    products = db.get_products(cat_id, active_only=True)

    kb = InlineKeyboardBuilder()

    for sc in subcats:
        if db.category_has_products(sc["id"]):
            icon = sc.get("icon", "📂")
            kb.button(text=f"{icon} {sc['name']}", callback_data=f"cat_{sc['id']}")

    for p in products:
        stock_count = db.get_stock_count(p["id"])
        if stock_count > 0:
            kb.button(text=f"🔑 {p['name']} — {fmt(p['price'])}", callback_data=f"buy_{p['id']}")

    kb.adjust(1)
    kb.row(back_btn())

    if not subcats and not products:
        lines = [
            f"📁 *{cat['name']}*",
            "",
            "😔 No products available in this category yet.",
        ]
    else:
        lines = [
            f"📁 *{cat['name']}*",
            cat.get("description", ""),
            "",
            "👇 Select a product to purchase:",
        ]

    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ── BUY FLOW ──────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prod_id = call.data[4:]
    prod = db.get_product(prod_id)
    if not prod:
        return

    stock_count = db.get_stock_count(prod_id)
    if stock_count == 0:
        return await call.answer("❌ Out of stock!", show_alert=True)

    await state.update_data(buy_prod_id=prod_id)
    lines = [
        f"🔑 *{prod['name']}*",
        f"💰 Price: {fmt(prod['price'])}",
        f"📦 Stock: {stock_count} available",
        f"⏰ Validity: {prod.get('expiry_days', 30)} days",
        "",
        "Do you want to purchase this product?",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✅ Buy Now", f"confirm_buy_{prod_id}"))
    kb.row(back_btn())
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("confirm_buy_"))
async def confirm_buy(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prod_id = call.data[12:]
    prod = db.get_product(prod_id)
    if not prod:
        return
    user = call.from_user
    u = db.get_user(user.id)
    bal = u["balance"] if u else 0

    price = prod["price"]
    if bal < price:
        await call.message.edit_text(
            f"❌ *Insufficient Balance!*\n\n"
            f"Required: {fmt(price)}\n"
            f"Your Balance: {fmt(bal)}\n\n"
            f"Please deposit first.",
            reply_markup=InlineKeyboardBuilder().row(btn("💰 Deposit", "deposit_start"), btn("🔙 Back", "my_account")).as_markup(),
            parse_mode="Markdown"
        )
        await state.clear()
        return

    stock_item = db.get_available_stock(prod_id)
    if not stock_item:
        return await call.answer("❌ Sorry, this product just went out of stock!", show_alert=True)

    db.deduct_balance(user.id, price)
    db.mark_stock_used(stock_item["id"])

    order_id = db.add_order(
        user_id=user.id,
        product_id=prod_id,
        product_name=prod["name"],
        category_id=prod["category_id"],
        amount=price,
        user_input="",
        payment_method="balance",
        transaction_id=""
    )

    # ★ FIX 4: Dynamic expiry days from DB
    expiry_days = get_product_expiry_days(prod, stock_item)
    now = now_local()
    expiry_date = now + timedelta(days=expiry_days)

    delivery_info = {
        "key": stock_item.get("key_data", ""),
        "email": stock_item.get("email", ""),
        "password": stock_item.get("password", ""),
        "expiry_days": expiry_days,
        "expires": expiry_date.strftime("%d %B %Y")
    }
    db.update_order(order_id, "delivered", delivery_info)

    cred_lines = []
    if prod["stock_type"] == "key_only" and stock_item.get("key_data"):
        cred_lines.append(f"🔑 *Key:* `{stock_item['key_data']}`")
    elif stock_item.get("email") and stock_item.get("password"):
        cred_lines.append(f"📧 *Email:* `{stock_item['email']}`")
        cred_lines.append(f"🔐 *Password:* `{stock_item['password']}`")
    elif stock_item.get("key_data"):
        cred_lines.append(f"🔑 *Key:* `{stock_item['key_data']}`")

    box_body = [
        f"📦 *{prod['name']}*",
        f"🆔 Order ID: #{order_id}",
        "",
    ] + cred_lines + [
        "",
        f"✅ Purchased: {now.strftime('%d %b %Y %I:%M %p')}",
        f"⏰ Validity: {expiry_days} days",
        f"📅 Expires: {expiry_date.strftime('%d %B %Y')}",
        f"✅ Status: Active",
        "",
        f"🙏 Thank you! @{SUPPORT_USERNAME}"
    ]
    deliver_text = generate_box("✅ PURCHASE CONFIRMED", box_body)

    await call.message.edit_text(deliver_text, parse_mode="Markdown")
    await state.clear()

# ── MY ORDERS ─────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "my_orders")
async def my_orders(call: CallbackQuery):
    await call.answer()
    orders = db.get_orders(call.from_user.id)
    if not orders:
        lines = ["📦 *My Orders*", "", "No orders yet."]
        kb = InlineKeyboardBuilder()
        kb.row(back_btn("my_account"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

    lines = ["📦 *My Orders*", ""]
    kb = InlineKeyboardBuilder()
    for o in orders[:10]:
        status_icon = "✅" if o["status"] == "delivered" else "⏳" if o["status"] == "pending" else "❌"
        kb.button(text=f"{status_icon} #{o['id']} {o['product_name']}", callback_data=f"view_order_{o['id']}")
    kb.adjust(1)
    kb.row(back_btn("my_account"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("view_order_"))
async def view_order(call: CallbackQuery):
    await call.answer()
    oid = int(call.data.split("_")[2])
    order = db.get_order(oid)
    if not order or order["user_id"] != call.from_user.id:
        return

    status_icon = "✅" if order["status"] == "delivered" else "⏳" if order["status"] == "pending" else "❌"
    lines = [
        f"📦 *Order #{oid}*",
        f"Product: {order['product_name']}",
        f"Amount: {fmt(order['amount'])}",
        f"Status: {status_icon} {order['status'].upper()}",
        f"Date: {order.get('created_at', 'N/A')}",
        "",
    ]
    if order["delivery_data"]:
        dd = json.loads(order["delivery_data"])
        if dd.get("key"):
            lines.append(f"🔑 Key: `{dd['key']}`")
        if dd.get("email"):
            lines.append(f"📧 Email: `{dd['email']}`")
        if dd.get("password"):
            lines.append(f"🔐 Password: `{dd['password']}`")
        if dd.get("expiry_days"):
            lines.append(f"⏰ Validity: {dd['expiry_days']} days")

    kb = InlineKeyboardBuilder()
    kb.row(back_btn("my_orders"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ── DEPOSIT FLOW ─────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "deposit_start")
async def deposit_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💰 *Deposit Funds*",
        "",
        "Enter the amount you want to deposit (BDT):",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "my_account"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositFlow.amount)

@dp.message(DepositFlow.amount)
async def deposit_amount(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.strip())
        if amount < 10:
            return await msg.answer("❌ Minimum deposit is ৳10.")
        await state.update_data(dep_amount=amount)
        lines = [
            f"💰 Deposit: {fmt(amount)}",
            "",
            "Select payment method:",
        ]
        kb = InlineKeyboardBuilder()
        kb.row(btn("💳 bkash", "dep_method_bkash"))
        kb.row(btn("💳 Nagad", "dep_method_nagad"))
        kb.row(btn("💳 Rocket", "dep_method_rocket"))
        kb.row(btn("🔙 Back", "deposit_start"))
        await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
        await state.set_state(DepositFlow.method)
    except:
        await msg.answer("❌ Enter a valid number.")

@dp.callback_query(lambda c: c.data.startswith("dep_method_"), DepositFlow.method)
async def deposit_method(call: CallbackQuery, state: FSMContext):
    await call.answer()
    method = call.data[11:]
    await state.update_data(dep_method=method)
    data = await state.get_data()
    amount = data["dep_amount"]
    
    number_map = {"bkash": BKASH_NUMBER, "nagad": NAGAD_NUMBER, "rocket": ROCKET_NUMBER}
    number = number_map.get(method, BKASH_NUMBER)
    
    lines = [
        f"💰 *Deposit {fmt(amount)} via {method.upper()}*",
        "",
        f"📱 Send exactly *{fmt(amount)}* to: `{number}`",
        "",
        "After sending, enter your Transaction ID (TrxID):",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "my_account"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(DepositFlow.trx_id)

@dp.message(DepositFlow.trx_id)
async def deposit_trx(msg: Message, state: FSMContext):
    trx_id = msg.text.strip()
    if not trx_id or len(trx_id) < 3:
        return await msg.answer("❌ Please enter a valid Transaction ID.")
    
    data = await state.get_data()
    amount = data["dep_amount"]
    method = data.get("dep_method", "bkash")
    user = msg.from_user

    # ★ FIX 5: Proper deposit with saving transaction
    db.add_balance(user.id, amount)
    db.add_transaction(user.id, amount, "deposit", method, trx_id, f"Deposit via {method}")

    new_bal = db.get_balance(user.id)
    lines = [
        f"✅ *Deposit Successful!*",
        f"Amount: {fmt(amount)}",
        f"Method: {method.upper()}",
        f"TrxID: `{trx_id}`",
        f"New Balance: {fmt(new_bal)}",
        "",
        "Your balance has been updated.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("👤 My Account", "my_account"))
    kb.row(btn("🛍️ Browse Store", "back_to_store"))
    await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    
    # Notify admins
    for aid in ADMIN_IDS:
        try:
            await bot.send_message(aid, 
                f"💰 *New Deposit*\n\n"
                f"User: `{user.id}` (@{user.username or 'N/A'})\n"
                f"Amount: {fmt(amount)}\n"
                f"Method: {method.upper()}\n"
                f"TrxID: `{trx_id}`\n"
                f"New Balance: {fmt(new_bal)}",
                parse_mode="Markdown")
        except:
            pass
    await state.clear()

@dp.callback_query(lambda c: c.data == "back_to_store")
async def back_to_store(call: CallbackQuery):
    await call.answer()
    await cmd_start(call.message)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

# ── DASHBOARD ─────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_dash")
async def admin_dash(call: CallbackQuery):
    await call.answer()
    users = db.user_count()
    prods = len(db.get_all_products())
    pend = len(db.get_pending_orders())
    stock = db.get_stock_counts()
    total_stock = sum(s["cnt"] for s in stock)
    lines = [
        "📊 *Dashboard*",
        "",
        f"👥 Users: {users}",
        f"📦 Products: {prods}",
        f"📋 Pending Orders: {pend}",
        f"🔑 Total Stock: {total_stock}",
    ]
    await call.message.edit_text("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")

# ── ADD BALANCE ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_addbal")
async def addbal_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "💰 *Add Balance*",
        "",
        "Enter the user's Telegram *User ID* (numeric) or *@username*:",
        "",
        "📌 Example: `123456789` or `@username`",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addbal_uid)

@dp.message(AdminFlow.addbal_uid)
async def addbal_uid_received(msg: Message, state: FSMContext):
    text = msg.text.strip()
    user = None
    uid = None

    if text.startswith("@") or (not text.isdigit() and not text.lstrip('-').isdigit()):
        clean_username = text.lstrip("@")
        users = db.get_all_users()
        for u in users:
            if u.get("username", "").lower() == clean_username.lower():
                user = u
                uid = u["user_id"]
                break
        if not uid:
            return await msg.answer("❌ User not found by username!", reply_markup=admin_kb())
    else:
        try:
            uid = int(text)
            user = db.get_user(uid)
            if not user:
                return await msg.answer(f"❌ User `{uid}` not found!", reply_markup=admin_kb(), parse_mode="Markdown")
        except:
            return await msg.answer("❌ Invalid User ID.", reply_markup=admin_kb())

    await state.update_data(addbal_uid=uid)
    lines = [
        "💰 *Add Balance*",
        "",
        f"👤 User: {user['first_name']} (@{user.get('username', 'N/A')})",
        f"🆔 ID: `{uid}`",
        f"💳 Current Balance: {fmt(user['balance'])}",
        "",
        "Enter amount to add (BDT):",
    ]
    await msg.answer("\n".join(lines), parse_mode="Markdown")
    await state.set_state(AdminFlow.addbal_amt)

@dp.message(AdminFlow.addbal_amt)
async def addbal_amount_received(msg: Message, state: FSMContext):
    try:
        amt = float(msg.text.strip())
        if amt <= 0:
            return await msg.answer("❌ Amount must be positive.")
        data = await state.get_data()
        uid = data["addbal_uid"]

        db.add_balance(uid, amt)
        trx_id = f"ADMIN_{now_local():%Y%m%d%H%M%S}"
        db.add_transaction(uid, amt, "admin_add", "Admin", trx_id)
        new_bal = db.get_balance(uid)

        box_body = [
            f"💰 Balance Added!",
            f"Amount: +{fmt(amt)}",
            f"New Balance: {fmt(new_bal)}",
            f"Date: {now_local().strftime('%d %b %Y %I:%M %p')}",
            "",
            f"🙏 @{SUPPORT_USERNAME}"
        ]
        user_msg = generate_box("💰 BALANCE UPDATED", box_body)
        try:
            await bot.send_message(uid, user_msg, parse_mode="Markdown")
        except:
            pass

        lines = [
            "✅ *Balance added successfully!*",
            "",
            f"Amount: +{fmt(amt)}",
            f"User ID: `{uid}`",
            f"Old Balance: {fmt(new_bal - amt)}",
            f"New Balance: {fmt(new_bal)}",
            f"TrxID: {trx_id}",
            "",
            "User has been notified ✅",
        ]
        await msg.answer("\n".join(lines), reply_markup=admin_kb(), parse_mode="Markdown")
    except ValueError:
        await msg.answer("❌ Invalid amount. Enter a number (e.g., `500`).")
    except Exception as e:
        await msg.answer(f"❌ Error: {e}")
    await state.clear()

# ── ADMIN CATEGORIES ─────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_cat")
async def admin_cat(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📁 *Category Management*", reply_markup=admin_cat_kb(), parse_mode="Markdown")

# ── ADD MAIN CATEGORY ────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "cat_add_main")
async def cat_add_main(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(cat_parent=None)
    lines = ["📁 *Add Main Category*", "", "Enter category name:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_name)

# ── ADD SUB-CATEGORY ─────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "cat_add_sub")
async def cat_add_sub(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parents = db.get_categories(parent_id=None, active_only=True)
    if not parents:
        return await call.answer("❌ No main categories exist. Create one first.", show_alert=True)

    lines = ["📁 *Add Sub-Category*", "", "Select parent category:"]
    kb = InlineKeyboardBuilder()
    for p in parents:
        kb.button(text=f"📁 {p['name']}", callback_data=f"cat_parent_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_parent)

@dp.callback_query(lambda c: c.data.startswith("cat_parent_"), AdminFlow.addcat_parent)
async def cat_parent_selected(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parent_id = call.data[11:]
    parent = db.get_category(parent_id)
    await state.update_data(cat_parent=parent_id)
    lines = ["📁 *Add Sub-Category*", f"Parent: {parent['name']}", "", "Enter sub-category name:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "cat_add_sub"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addcat_name)

@dp.message(AdminFlow.addcat_name)
async def cat_add_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    data = await state.get_data()
    parent_id = data.get("cat_parent")
    cat_id = generate_id("cat_")
    db.add_category(cat_id, name, parent_id=parent_id)
    await msg.answer(f"✅ Category '{name}' created!", reply_markup=admin_cat_kb())
    await state.clear()

# ── LIST CATEGORIES (Admin) ──────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "cat_list")
async def cat_list(call: CallbackQuery):
    await call.answer()
    cats = db.get_categories(parent_id=None, active_only=False)
    if not cats:
        return await call.message.edit_text("❌ No categories.", reply_markup=admin_cat_kb())

    lines = ["📋 *All Categories*", ""]
    kb = InlineKeyboardBuilder()
    for cat in cats:
        subcats = db.get_categories(parent_id=cat["id"], active_only=False)
        status = "🟢" if cat["is_active"] else "🔴"
        label = f"{status} {cat['name']} ({len(subcats)} sub)"
        kb.button(text=label, callback_data=f"list_sub_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("list_sub_"))
async def list_sub(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[8:]
    cat = db.get_category(cat_id)
    subcats = db.get_categories(parent_id=cat_id, active_only=False)
    prods = db.get_products_for_admin(cat_id)
    lines = [f"📋 *{cat['name']}*", ""]
    if subcats:
        lines.append(f"📂 Sub-categories ({len(subcats)}):")
        for sc in subcats:
            sc_status = "🟢" if sc["is_active"] else "🔴"
            lines.append(f"  {sc_status} {sc['name']} ({sc['id']})")
    else:
        lines.append("📂 No sub-categories.")
    if prods:
        lines.append(f"\n📦 Products ({len(prods)}):")
        for p in prods:
            lines.append(f"  🔑 {p['name']} — {fmt(p['price'])} [{p.get('stock_count', 0)} stock]")
    else:
        lines.append("\n📦 No products.")
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "cat_list"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

# ── EDIT CATEGORY ────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "cat_edit")
async def cat_edit_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cats = db.get_categories(parent_id=None, active_only=False)
    if not cats:
        return await call.answer("❌ No categories.", show_alert=True)
    lines = ["✏️ *Edit Category*", "", "Select category:"]
    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=f"📁 {cat['name']}", callback_data=f"editcat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editcat_select)

@dp.callback_query(lambda c: c.data.startswith("editcat_"), AdminFlow.editcat_select)
async def cat_edit_selected(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[8:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    await state.update_data(editcat_id=cat_id)
    lines = [
        f"✏️ *Edit Category: {cat['name']}*",
        f"ID: `{cat_id}`",
        "",
        "What do you want to edit?",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Name", "editcat_field_name"))
    kb.row(btn("📝 Description", "editcat_field_desc"))
    kb.row(btn("🟢 Active", "editcat_field_active_on"), btn("🔴 Inactive", "editcat_field_active_off"))
    kb.row(btn("🔙 Back", "cat_edit"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editcat_field)

@dp.callback_query(lambda c: c.data.startswith("editcat_field_"), AdminFlow.editcat_field)
async def cat_edit_field(call: CallbackQuery, state: FSMContext):
    await call.answer()
    field = call.data[13:]
    data = await state.get_data()
    cat_id = data["editcat_id"]
    cat = db.get_category(cat_id)

    if field == "name":
        await call.message.edit_text(f"✏️ Enter new name for '{cat['name']}':", parse_mode="Markdown")
        await state.set_state(AdminFlow.addcat_name)
        await state.update_data(editcat_doing="name")
    elif field == "desc":
        await call.message.edit_text(f"📝 Enter new description for '{cat['name']}':", parse_mode="Markdown")
        await state.update_data(editcat_doing="description")
    elif field == "active_on":
        db.update_category(cat_id, is_active=1)
        await call.message.edit_text(f"✅ '{cat['name']}' activated!", reply_markup=admin_cat_kb())
        await state.clear()
    elif field == "active_off":
        db.update_category(cat_id, is_active=0)
        await call.message.edit_text(f"✅ '{cat['name']}' deactivated!", reply_markup=admin_cat_kb())
        await state.clear()

# ── DELETE CATEGORY ──────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "cat_del")
async def cat_del_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cats = db.get_categories(parent_id=None, active_only=False)
    if not cats:
        return await call.answer("❌ No categories.", show_alert=True)
    lines = ["🗑️ *Delete Category*", "", "⚠️ This will also delete all sub-categories and products!", "", "Select category:"]
    kb = InlineKeyboardBuilder()
    for cat in cats:
        kb.button(text=f"🗑️ {cat['name']}", callback_data=f"delcat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.delcat_confirm)

@dp.callback_query(lambda c: c.data.startswith("delcat_"), AdminFlow.delcat_confirm)
async def cat_del_confirm(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[7:]
    cat = db.get_category(cat_id)
    lines = [
        f"🗑️ *Delete '{cat['name']}'?*",
        "",
        "⚠️ This action cannot be undone!",
        "All sub-categories and products will be deleted.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✅ Yes, Delete", f"delcat_do_{cat_id}"), btn("❌ No", "admin_cat"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delcat_do_"))
async def cat_del_do(call: CallbackQuery):
    await call.answer()
    cat_id = call.data[9:]
    db.delete_category(cat_id)
    await call.message.edit_text("✅ Category deleted!", reply_markup=admin_cat_kb())


# ── ADMIN PRODUCTS ───────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_prod")
async def admin_prod(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("📦 *Product Management*", reply_markup=admin_prod_kb(), parse_mode="Markdown")

# ── ADD PRODUCT ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "prod_add")
async def prod_add_cat_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    all_cats = []
    main_cats = db.get_categories(parent_id=None, active_only=True)
    for mc in main_cats:
        all_cats.append(mc)
        subs = db.get_categories(parent_id=mc["id"], active_only=True)
        all_cats.extend(subs)

    if not all_cats:
        return await call.answer("❌ No categories available. Create one first.", show_alert=True)

    lines = ["📦 *Add Product*", "", "Select category for the product:"]
    kb = InlineKeyboardBuilder()
    for cat in all_cats:
        label = f"📁 {cat['name']}"
        if cat.get("parent_id"):
            label = f"  📂 {cat['name']}"
        kb.button(text=label, callback_data=f"addprod_cat_{cat['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_prod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addprod_cat)

@dp.callback_query(lambda c: c.data.startswith("addprod_cat_"), AdminFlow.addprod_cat)
async def prod_add_name(call: CallbackQuery, state: FSMContext):
    await call.answer()
    cat_id = call.data[12:]
    cat = db.get_category(cat_id)
    if not cat:
        return
    await state.update_data(addprod_cat=cat_id)
    await call.message.edit_text(
        f"📦 *Add Product in '{cat['name']}'\n\nEnter product name:",
        parse_mode="Markdown"
    )
    await state.set_state(AdminFlow.addprod_name)

@dp.message(AdminFlow.addprod_name)
async def prod_add_name_input(msg: Message, state: FSMContext):
    name = msg.text.strip()
    await state.update_data(addprod_name=name)
    await msg.answer("💰 Enter price (BDT):")
    await state.set_state(AdminFlow.addprod_price)

@dp.message(AdminFlow.addprod_price)
async def prod_add_price(msg: Message, state: FSMContext):
    try:
        price = float(msg.text.strip())
        await state.update_data(addprod_price=price)
        await msg.answer("⏰ Enter expiry days (default 30):")
        await state.set_state(AdminFlow.addprod_expiry)
    except:
        await msg.answer("❌ Enter a valid number.")

@dp.message(AdminFlow.addprod_expiry)
async def prod_add_expiry(msg: Message, state: FSMContext):
    try:
        expiry = int(msg.text.strip())
        if expiry < 1:
            return await msg.answer("❌ Minimum 1 day.")
    except:
        expiry = 30

    await state.update_data(addprod_expiry=expiry)
    data = await state.get_data()

    lines = [
        f"📦 *New Product Summary*",
        f"Name: {data['addprod_name']}",
        f"Price: {fmt(data['addprod_price'])}",
        f"Expiry: {expiry} days",
        "",
        "Select stock type:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(
        btn("🔑 Key Only", "addprod_stktype_keyonly"),
        btn("📧 Email & Pass", "addprod_stktype_emailpass")
    )
    kb.row(btn("🔙 Back", "admin_prod"))
    await msg.answer("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.addprod_stocktype_pending)

# ★ FIX 2: No StateFilter — catches from ANY state globally
@dp.callback_query(lambda c: c.data.startswith("addprod_stktype_"))
async def addprod_stocktype_btn(call: CallbackQuery, state: FSMContext):
    await call.answer()
    chosen_type = call.data.split("_")[2]
    stock_type = "key_only" if chosen_type == "keyonly" else "email_pass"

    data = await state.get_data()
    cat_id = data["addprod_cat"]
    auto_id = generate_id("prod_")

    db.add_product(
        auto_id,
        cat_id,
        data["addprod_name"],
        data["addprod_price"],
        0,
        stock_type,
        data["addprod_expiry"]
    )

    await call.message.edit_text(
        f"✅ *Product Added!*\n\n"
        f"Name: {data['addprod_name']}\n"
        f"ID: `{auto_id}`\n"
        f"Price: {fmt(data['addprod_price'])}\n"
        f"Expiry: {data['addprod_expiry']} days\n"
        f"Stock Type: {stock_type}",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    await state.clear()

# ── EDIT PRODUCT ─────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "prod_edit")
async def prod_edit_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        return await call.answer("❌ No products.", show_alert=True)
    lines = ["✏️ *Edit Product*", "", "Select product:"]
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"🔑 {p['name']} — {fmt(p['price'])}", callback_data=f"editprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_prod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_select)

@dp.callback_query(lambda c: c.data.startswith("editprod_"), AdminFlow.editprod_select)
async def prod_edit_selected(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prod_id = call.data[9:]
    prod = db.get_product(prod_id)
    if not prod:
        return
    await state.update_data(editprod_id=prod_id)
    lines = [
        f"✏️ *Edit Product: {prod['name']}*",
        f"ID: `{prod_id}`",
        f"Price: {fmt(prod['price'])}",
        f"Expiry: {prod.get('expiry_days', 30)} days",
        f"Stock Type: {prod['stock_type']}",
        "",
        "What do you want to edit?",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✏️ Name", "editprod_field_name"))
    kb.row(btn("💰 Price", "editprod_field_price"))
    kb.row(btn("⏰ Expiry", "editprod_field_expiry"))
    kb.row(btn("🟢 Active", "editprod_field_active_on"), btn("🔴 Inactive", "editprod_field_active_off"))
    kb.row(btn("🔙 Back", "prod_edit"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.editprod_field)

@dp.callback_query(lambda c: c.data.startswith("editprod_field_"), AdminFlow.editprod_field)
async def prod_edit_field(call: CallbackQuery, state: FSMContext):
    await call.answer()
    field = call.data[15:]
    data = await state.get_data()
    prod_id = data["editprod_id"]
    prod = db.get_product(prod_id)

    if field == "name":
        await call.message.edit_text(f"✏️ Enter new name for '{prod['name']}':", parse_mode="Markdown")
        await state.update_data(editprod_target="name")
    elif field == "price":
        await call.message.edit_text(f"💰 Enter new price (current: {fmt(prod['price'])}):", parse_mode="Markdown")
        await state.update_data(editprod_target="price")
    elif field == "expiry":
        await call.message.edit_text(f"⏰ Enter new expiry days (current: {prod.get('expiry_days', 30)}):", parse_mode="Markdown")
        await state.update_data(editprod_target="expiry")
    elif field == "active_on":
        db.update_product(prod_id, is_active=1)
        await call.message.edit_text(f"✅ '{prod['name']}' activated!", reply_markup=admin_prod_kb())
        await state.clear()
    elif field == "active_off":
        db.update_product(prod_id, is_active=0)
        await call.message.edit_text(f"✅ '{prod['name']}' deactivated!", reply_markup=admin_prod_kb())
        await state.clear()

@dp.message(lambda msg: msg.text, StateFilter(AdminFlow.editprod_field))
async def prod_edit_input(msg: Message, state: FSMContext):
    data = await state.get_data()
    prod_id = data["editprod_id"]
    target = data.get("editprod_target")

    if target == "name":
        db.update_product(prod_id, name=msg.text.strip())
        await msg.answer(f"✅ Name updated!", reply_markup=admin_prod_kb())
        await state.clear()
    elif target == "price":
        try:
            price = float(msg.text.strip())
            db.update_product(prod_id, price=price)
            await msg.answer(f"✅ Price updated to {fmt(price)}!", reply_markup=admin_prod_kb())
            await state.clear()
        except:
            await msg.answer("❌ Invalid price.")
    elif target == "expiry":
        try:
            expiry = int(msg.text.strip())
            db.update_product(prod_id, expiry_days=expiry)
            await msg.answer(f"✅ Expiry updated to {expiry} days!", reply_markup=admin_prod_kb())
            await state.clear()
        except:
            await msg.answer("❌ Invalid number.")

# ── DELETE PRODUCT ───────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "prod_del")
async def prod_del_select(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        return await call.answer("❌ No products.", show_alert=True)
    lines = ["🗑️ *Delete Product*", ""]
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"🗑️ {p['name']}", callback_data=f"delprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_prod"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delprod_"))
async def prod_del_do(call: CallbackQuery):
    await call.answer()
    prod_id = call.data[8:]
    prod = db.get_product(prod_id)
    db.delete_product(prod_id)
    await call.message.edit_text(f"✅ Product '{prod['name']}' deleted!", reply_markup=admin_prod_kb())


# ── STOCK MANAGEMENT ─────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock_menu(call: CallbackQuery):
    await call.answer()
    await call.message.edit_text("🔑 *Stock Management*", reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_status")
async def stock_status(call: CallbackQuery):
    await call.answer()
    counts = db.get_stock_counts()
    lines = ["🔑 *Stock Status*", ""]
    if counts:
        for s in counts:
            lines.append(f"📦 `{s['product_id']}` ({s['stock_type']}): {s['cnt']} available")
    else:
        lines.append("No stock available.")
    await call.message.edit_text("\n".join(lines), reply_markup=admin_stock_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "stock_add")
async def stock_add_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    prods = db.get_all_products()
    if not prods:
        return await call.answer("❌ No products. Add a product first.", show_alert=True)
    kb = InlineKeyboardBuilder()
    for p in prods:
        kb.button(text=f"📦 {p['name']} [{p['stock_type']}]", callback_data=f"stkprod_{p['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🔑 *Add Stock*\nSelect a product:", reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_target)

@dp.callback_query(lambda c: c.data.startswith("stkprod_"))
async def stock_target_set(call: CallbackQuery, state: FSMContext):
    await call.answer()
    pid = call.data[8:]
    prod = db.get_product(pid)
    if not prod:
        return
    await state.update_data(stock_target=pid)

    lines = [
        f"🔑 *Add Stock to: {prod['name']}*",
        f"Product ID: `{pid}`",
        f"Default Expiry: {prod.get('expiry_days', 30)} days",
        "",
        "📌 Select the type of data you want to add:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(
        btn("🔑 Key Only", f"stktype_keyonly_{pid}"),
        btn("📧 Email & Password", f"stktype_emailpass_{pid}")
    )
    kb.row(btn("🔙 Back", "stock_add"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_type_choice)

# ★ FIX 2: No StateFilter — catches from ANY state globally
@dp.callback_query(lambda c: c.data.startswith("stktype_"))
async def stock_type_chosen(call: CallbackQuery, state: FSMContext):
    await call.answer()
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        return
    chosen_type = parts[1]
    pid = parts[2]
    prod = db.get_product(pid)
    if not prod:
        return

    stock_type = "key_only" if chosen_type == "keyonly" else "email_pass"
    await state.update_data(stock_target=pid, stock_type=stock_type)

    lines = [
        f"🔑 *Add Stock to: {prod['name']}*",
        f"Stock Type: *{stock_type}*",
        f"Expiry: {prod.get('expiry_days', 30)} days",
        "",
        "📤 Now send your data (one per line) or upload a `.txt` file.",
        "",
    ]
    if stock_type == "key_only":
        lines.append("🔑 Send Key(s) — one per line:")
        lines.append("Example: `ABC123XYZ`")
    else:
        lines.append("📧 Send email:password pairs — one per line:")
        lines.append("Example: `email@example.com:password123`")

    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Change Type", f"stkprod_{pid}"))
    kb.row(btn("🔙 Back to Menu", "admin_stock"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.stock_input)

@dp.message(AdminFlow.stock_input, F.text)
async def stock_input_text(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    lines_input = [l.strip() for l in msg.text.split("\n") if l.strip()]
    added = 0
    for line in lines_input:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip())
                added += 1
    await msg.answer(f"✅ {added} stock items added!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.message(AdminFlow.stock_input, F.document)
async def stock_file_upload(msg: Message, state: FSMContext):
    data = await state.get_data()
    pid = data["stock_target"]
    stype = data["stock_type"]
    doc = msg.document
    if not doc.file_name.endswith(".txt"):
        return await msg.answer("❌ Please upload a `.txt` file.")
    file = await bot.get_file(doc.file_id)
    file_path = f"/tmp/{doc.file_id}.txt"
    await bot.download_file(file.file_path, destination=file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        lines_input = [l.strip() for l in content.split("\n") if l.strip()]
    except:
        return await msg.answer("❌ Could not read file.")
    os.remove(file_path)
    added = 0
    for line in lines_input:
        if stype == "key_only":
            db.add_stock(pid, "key_only", key_data=line)
            added += 1
        else:
            parts = re.split(r'[:|]', line, maxsplit=1)
            if len(parts) == 2:
                db.add_stock(pid, "email_pass", email=parts[0].strip(), password=parts[1].strip())
                added += 1
    await msg.answer(f"✅ {added} stock items added from file!", reply_markup=admin_stock_kb())
    await state.clear()

@dp.callback_query(lambda c: c.data == "stock_del")
async def stock_del_list(call: CallbackQuery):
    await call.answer()
    all_stock = db.get_all_stock()
    if not all_stock:
        return await call.answer("❌ No stock items.", show_alert=True)
    kb = InlineKeyboardBuilder()
    for s in all_stock[:20]:
        status = "✅" if s['is_used'] else "📦"
        display = s.get('key_data') or s.get('email') or f"ID:{s['id']}"
        text = f"{status} #{s['id']} {display[:25]}"
        kb.button(text=text, callback_data=f"delstock_{s['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_stock"))
    await call.message.edit_text("🗑️ *Select stock to delete:*", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("delstock_"))
async def del_stock(call: CallbackQuery):
    await call.answer("🗑️ Deleting...")
    sid = int(call.data.split("_")[1])
    db.delete_stock(sid)
    await stock_del_list(call)


# ── ORDERS ────────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_orders")
async def admin_orders(call: CallbackQuery):
    await call.answer()
    pending = db.get_pending_orders()
    lines = ["📋 *Pending Orders*", ""]
    if not pending:
        lines.append("✅ No pending orders.")
        kb = InlineKeyboardBuilder()
        kb.row(btn("🔙 Back", "admin_menu"))
        return await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

    kb = InlineKeyboardBuilder()
    for o in pending:
        label = f"⏳ #{o['id']} {o['product_name']} — {fmt(o['amount'])} ({o.get('first_name', '?')})"
        kb.button(text=label, callback_data=f"review_{o['id']}")
    kb.adjust(1)
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("review_"))
async def review_order(call: CallbackQuery):
    await call.answer()
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    user = db.get_user(order["user_id"])
    prod = db.get_product(order["product_id"])
    expiry_days = get_product_expiry_days(prod)
    lines = [
        f"📋 *Order #{oid}*",
        f"Product: {order['product_name']}",
        f"Amount: {fmt(order['amount'])}",
        f"User: {user.get('first_name', '?')} (@{user.get('username', '?')})",
        f"User ID: `{order['user_id']}`",
        f"Date: {order.get('created_at', 'N/A')}",
        f"Expiry: {expiry_days} days",
        "",
        "Actions:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("✅ Approve", f"approve_{oid}"), btn("❌ Reject", f"reject_{oid}"))
    kb.row(btn("📦 Manual Deliver", f"manual_deliver_{oid}"))
    kb.row(btn("🔙 Back", "admin_orders"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_order(call: CallbackQuery):
    await call.answer("✅ Approving...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    prod = db.get_product(order["product_id"])
    # ★ FIX 4: Dynamic expiry days
    expiry_days = get_product_expiry_days(prod)
    now = now_local()
    expiry_date = now + timedelta(days=expiry_days)
    db.update_order(oid, "delivered", {
        "approved_at": now.strftime("%d %B %Y %I:%M %p"),
        "expires": expiry_date.strftime("%d %B %Y"),
        "expiry_days": expiry_days,
        "info": order.get("user_input", "N/A")
    })
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
    await call.message.edit_text(f"✅ Order #{oid} Approved & Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    await call.answer("❌ Rejecting...")
    oid = int(call.data.split("_")[1])
    order = db.get_order(oid)
    if not order:
        return
    db.update_order(oid, "cancelled")
    try:
        await bot.send_message(order["user_id"], f"❌ Order #{oid} has been cancelled.\nContact @{SUPPORT_USERNAME} for details.", parse_mode="Markdown")
    except:
        pass
    await call.message.edit_text(f"❌ Order #{oid} Rejected.", reply_markup=admin_kb(), parse_mode="Markdown")

# ── MANUAL DELIVER ───────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data.startswith("manual_deliver_"))
async def manual_deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    oid = int(call.data.split("_")[2])
    order = db.get_order(oid)
    if not order:
        return
    await state.update_data(oid=oid)
    lines = [
        f"📦 *Manual Delivery - Order #{oid}*",
        f"Product: {order['product_name']}",
        f"User ID: {order['user_id']}",
        f"Info: {order.get('user_input', 'N/A')}",
        "",
        "Enter delivery details:",
        "• For Key only: `KEY123`",
        "• For Email:Password: `email:password`",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_orders"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.deliver_file)

@dp.callback_query(lambda c: c.data == "admin_deliver")
async def deliver_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["📦 *Manual Delivery*", "", "Enter Order ID:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.deliver_oid)

@dp.message(AdminFlow.deliver_oid)
async def deliver_oid(msg: Message, state: FSMContext):
    try:
        oid = int(msg.text.strip())
        order = db.get_order(oid)
        if not order:
            return await msg.answer("❌ Order not found.")
        await state.update_data(oid=oid)
        lines = [
            f"📦 *Order #{oid}*",
            f"Product: {order['product_name']}",
            f"User ID: {order['user_id']}",
            f"Info: {order.get('user_input', 'N/A')}",
            "",
            "Enter delivery details:",
            "• For Key only: `KEY123`",
            "• For Email:Password: `email:password`",
        ]
        await msg.answer("\n".join(lines), parse_mode="Markdown")
        await state.set_state(AdminFlow.deliver_file)
    except:
        await msg.answer("❌ Invalid Order ID.")

@dp.message(AdminFlow.deliver_file)
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
    # ★ FIX 4: Dynamic expiry days
    expiry_days = get_product_expiry_days(prod)
    now = now_local()
    expiry_date = now + timedelta(days=expiry_days)
    delivery_data["expiry_days"] = expiry_days
    delivery_data["expires"] = expiry_date.strftime("%d %B %Y")
    db.update_order(oid, "delivered", delivery_data)
    cred_part = ""
    if "key" in delivery_data:
        cred_part = f"🔑 Key: `{delivery_data['key']}`"
    else:
        cred_part = f"📧 Email: `{delivery_data['email']}`\n🔐 Pass: `{delivery_data['password']}`"
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
    await msg.answer(f"✅ Order #{oid} Delivered!", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()


# ── BACKUP ────────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_backup")
async def admin_backup(call: CallbackQuery):
    await call.answer("💾 Creating backup...")
    try:
        backup_path = db.backup()
        file_size = os.path.getsize(backup_path)
        await call.message.edit_text(
            f"💾 *Backup Created!*\n\n"
            f"📁 File: `{os.path.basename(backup_path)}`\n"
            f"📏 Size: {file_size/1024:.1f} KB\n\n"
            f"Sending file...",
            parse_mode="Markdown"
        )
        doc = FSInputFile(backup_path)
        await bot.send_document(
            call.from_user.id,
            doc,
            caption=f"📦 *SKY STORE BD - Database Backup*\n📅 {now_local().strftime('%d %B %Y %I:%M %p')}\n📏 {file_size/1024:.1f} KB",
            parse_mode="Markdown"
        )
        await call.message.edit_text(
            "✅ *Backup sent successfully!*\n\nThe backup file has been sent as a document above.",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await call.message.edit_text(
            f"❌ Backup failed: {e}",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )

# ── RESTORE ───────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_restore")
async def admin_restore_prompt(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "🔄 *Restore Database*",
        "",
        "⚠️ *WARNING:* This will OVERWRITE the current database!",
        "",
        "Send the backup `.db` file to restore.",
        "The file should be a valid SQLite database.",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Cancel", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.restore_file)

@dp.message(AdminFlow.restore_file, F.document)
async def admin_restore_file(msg: Message, state: FSMContext):
    doc = msg.document
    if not doc.file_name.endswith(".db"):
        return await msg.answer("❌ Please upload a `.db` file (SQLite database backup).")

    await msg.answer("🔄 Downloading and restoring database...")

    file = await bot.get_file(doc.file_id)
    restore_path = f"/tmp/restore_{doc.file_id}.db"
    await bot.download_file(file.file_path, destination=restore_path)

    try:
        success = db.restore(restore_path)
        if success:
            await msg.answer(
                "✅ *Database restored successfully!*\n\nThe bot is now using the restored data.",
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
        else:
            await msg.answer(
                "❌ Failed to restore database. The file may be corrupted or invalid.",
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
    except Exception as e:
        await msg.answer(
            f"❌ Restore error: {e}",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    finally:
        if os.path.exists(restore_path):
            os.remove(restore_path)
    await state.clear()


# ── BROADCAST ─────────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def broadcast_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = [
        "📨 *Broadcast Message*",
        "",
        "Send the text or video with caption to broadcast to all users:",
    ]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.broadcast_msg)

@dp.message(AdminFlow.broadcast_msg, F.text)
async def broadcast_text(msg: Message, state: FSMContext):
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

@dp.message(AdminFlow.broadcast_msg, F.video)
async def broadcast_video(msg: Message, state: FSMContext):
    video = msg.video.file_id
    caption = msg.caption or ""
    users = db.get_all_users()
    sent = 0
    for u in users:
        if not u["is_banned"]:
            try:
                await bot.send_video(u["user_id"], video, caption=caption)
                sent += 1
            except:
                pass
    await msg.answer(f"✅ Video broadcast sent to {sent}/{len(users)} users.", reply_markup=admin_kb())
    await state.clear()


# ── BAN / UNBAN ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_ban")
async def ban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["⛔ *Ban User*", "", "Enter User ID to ban:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.ban_uid)

@dp.message(AdminFlow.ban_uid)
async def ban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, True)
        await msg.answer(f"⛔ User `{uid}` banned.", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ Invalid ID.")
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_unban")
async def unban_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["✅ *Unban User*", "", "Enter User ID to unban:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.unban_uid)

@dp.message(AdminFlow.unban_uid)
async def unban_do(msg: Message, state: FSMContext):
    try:
        uid = int(msg.text.strip())
        db.set_ban(uid, False)
        await msg.answer(f"✅ User `{uid}` unbanned.", reply_markup=admin_kb(), parse_mode="Markdown")
    except:
        await msg.answer("❌ Invalid ID.")
    await state.clear()


# ── PROMO CODES ──────────────────────────────────────────────────────────────
@dp.callback_query(lambda c: c.data == "admin_promo")
async def promo_start(call: CallbackQuery, state: FSMContext):
    await call.answer()
    lines = ["💰 *Promo Code Management*", "", "Enter promo code:"]
    kb = InlineKeyboardBuilder()
    kb.row(btn("🔙 Back", "admin_menu"))
    await call.message.edit_text("\n".join(lines), reply_markup=kb.as_markup(), parse_mode="Markdown")
    await state.set_state(AdminFlow.promo_code)

@dp.message(AdminFlow.promo_code)
async def promo_code_input(msg: Message, state: FSMContext):
    code = msg.text.strip().upper()
    await state.update_data(promo_code=code)
    await msg.answer(f"💰 Enter amount for promo `{code}`:", parse_mode="Markdown")
    await state.set_state(AdminFlow.promo_amount)

@dp.message(AdminFlow.promo_amount)
async def promo_amount_input(msg: Message, state: FSMContext):
    try:
        amount = float(msg.text.strip())
        data = await state.get_data()
        code = data["promo_code"]
        db.add_promo(code, amount=amount)
        await msg.answer(f"✅ Promo `{code}` created worth {fmt(amount)}!", reply_markup=admin_kb(), parse_mode="Markdown")
        await state.clear()
    except:
        await msg.answer("❌ Invalid amount.")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    print("🚀 SKY STORE BD Bot v3.7 starting...")
    dp.message.outer_middleware(BanCheckMiddleware())
    dp.callback_query.outer_middleware(BanCheckMiddleware())
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
