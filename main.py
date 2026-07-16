#!/usr/bin/env python3
"""
████████╗ ██████╗ ██████╗ ██╗   ██╗██████╗     ███████╗████████╗ ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔═══██╗██╔══██╗██║   ██║██╔══██╗    ██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝
   ██║   ██║   ██║██████╔╝██║   ██║██████╔╝    ███████╗   ██║   ██║   ██║██████╔╝█████╗  
   ██║   ██║   ██║██╔═══╝ ██║   ██║██╔══██╗    ╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝  
   ██║   ╚██████╔╝██║     ╚██████╔╝██║  ██║    ███████║   ██║   ╚██████╔╝██║  ██║███████╗
   ╚═╝    ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝

   ╔══════════════════════════════════════════════════════════════════════════════════╗
   ║               🚀 TopUp Store BD — Premium Telegram Bot v3.0                      ║
   ║          🔥 Free Fire | Weekly | Monthly | Netflix | YouTube | More            ║
   ║                    🌐 NEW! VPN Plus — Premium VPN & IP Service                  ║
   ║                   ⚡ Instant Auto-Delivery | Colored Buttons                     ║
   ╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import os
import sys
import sqlite3
import random
import string
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path
from uuid import uuid4

# ==================== CORE IMPORTS ====================
try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command, CommandStart, CommandObject
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
        ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
        FSInputFile, BufferedInputFile, ChatAdministratorRights
    )
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State, StatesGroup
    from aiogram.fsm.storage.memory import MemoryStorage
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
except ImportError:
    print("""
    ❌ aiogram not installed!
    
    📦 Install with:
    pip install aiogram
    
    📱 On Termux:
    pkg install python python-pip
    pip install aiogram
    """)
    sys.exit(1)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"
ADMIN_IDS = [7689218221]
NAGAD_NUMBER = "01748506069"
BKASH_NUMBER = "01742958563"
ROCKET_NUMBER = "01742958563"
UPI_ID = "example@upi"
BOT_USERNAME = "@SKY_STOR_BOT"
BOT_NAME = "🌟 SKY STORE BD"
SUPPORT_USERNAME = "FBSKYSUPPORT"

# Inline Keyboard Button Colors (using HTML emoji markers)
BTN_HOME = "🏠"
BTN_BACK = "🔙"
BTN_ADMIN = "🔐"
BTN_CART = "🛒"
BTN_WALLET = "💰"
BTN_ORDERS = "📦"
BTN_PROFILE = "👤"
BTN_VPN = "🌐"
BTN_GAMES = "🎮"
BTN_SUB = "🎬"
BTN_SOCIAL = "📱"

# Stock categories for auto-delivery system
STOCK_CATEGORIES = {
    "expressvpn": {"name": "ExpressVPN", "type": "key"},
    "hma": {"name": "HMA VPN", "type": "key"},
    "vpnip": {"name": "VPN IP", "type": "key"},
    "vanish": {"name": "Vanish VPN", "type": "key"},
    "protonvpn": {"name": "Proton VPN", "type": "key"},
    "proxy": {"name": "Proxy IP", "type": "proxy"},
    "vps": {"name": "VPS Box", "type": "vps"},
}

# ==================== EMOJI STYLE MAP ====================
CAT_EMOJIS = {
    "freefire": "🔥", "ff_weekly": "📆", "ff_lite": "⭐", "ff_offer": "🎯",
    "ff_like": "❤️", "ff_indonesia": "🌏", "ff_levelup": "⬆️",
    "netflix": "🎬", "youtube": "▶️", "crunchyroll": "🍿",
    "vpn": "🌐", "vpn_plus": "🔒", "bals": "💰",
    "admin": "🔐", "home": "🏠", "back": "🔙",
}

EMOJIS = {
    "verified": "✅", "cross": "❌", "warning": "⚠️", "info": "ℹ️",
    "lightning": "⚡", "rocket": "🚀", "sparkle": "✨", "fire": "🔥",
    "diamond": "💎", "crown": "👑", "star": "⭐", "shield": "🛡️",
    "cart": "🛒", "wallet": "💳", "package": "📦", "clock": "⏰",
    "money": "💰", "cash": "💸", "phone": "📱", "game": "🎮",
    "tv": "📺", "movie": "🎥", "music": "🎶", "server": "🖥️",
    "wifi": "📶", "config": "🔗", "key": "🔑", "lock": "🔒",
    "unlock": "🔓", "back": "🔙", "home": "🏠", "admin": "🔐",
    "speed": "🚀", "expire": "⏳", "bell": "🔔", "heart": "❤️",
    "globe": "🌍", "data": "📊", "list": "📋", "book": "📚",
    "pen": "✏️", "gift": "🎁", "medal": "🥇", "trophy": "🏆",
}

# ==================== BD PRICES FROM TOPUPPAPA.COM ====================
PRODUCTS_CONFIG = {
    "categories": [
        # ============= FREE FIRE MAIN BD =============
        {
            "id": "freefire",
            "name": "🔥 Free Fire Diamonds (BD)",
            "emoji": "🔥",
            "color": "#FF6B35",
            "desc": "⚡ Best BD price! Instant Diamond delivery",
            "input_label": "🎮 Enter your Free Fire Player ID:",
            "input_placeholder": "Example: 1234567890",
            "products": [
                {"id": "ff_25d",  "name": "💎 25 Diamond",       "price": 20,   "popular": False},
                {"id": "ff_50d",  "name": "💎 50 Diamond",       "price": 35,   "popular": False},
                {"id": "ff_115d", "name": "💎 115 Diamond",      "price": 79,   "popular": False},
                {"id": "ff_240d", "name": "💎 240 Diamond",      "price": 156,  "popular": True},
                {"id": "ff_355d", "name": "💎 355 Diamond",      "price": 237,  "popular": False},
                {"id": "ff_505d", "name": "💎 505 Diamond",      "price": 336,  "popular": False},
                {"id": "ff_610d", "name": "💎 610 Diamond",      "price": 390,  "popular": False},
                {"id": "ff_850d", "name": "💎 850 Diamond",      "price": 558,  "popular": False},
                {"id": "ff_1090d","name": "💎 1090 Diamond",     "price": 716,  "popular": True},
                {"id": "ff_1240d","name": "💎 1240 Diamond",     "price": 795,  "popular": False},
                {"id": "ff_2530d","name": "💎 2530 Diamond",     "price": 1580, "popular": False},
                {"id": "ff_5060d","name": "💎 5060 Diamond",     "price": 3160, "popular": False},
                {"id": "ff_7590d","name": "💎 7590 Diamond",     "price": 4800, "popular": False},
                {"id": "ff_10120d","name":"💎 10120 Diamond",    "price": 6400, "popular": False},
            ]
        },
        # ============= FF WEEKLY =============
        {
            "id": "ff_weekly",
            "name": "📆 FF Weekly (BD Server)",
            "emoji": "📆",
            "color": "#FFD700",
            "desc": "Weekly Membership for BD Server",
            "input_label": "🎮 Enter Free Fire Player ID:",
            "input_placeholder": "Player ID",
            "products": [
                {"id": "ffw_1",  "name": "📆 1x Weekly",      "price": 155,  "popular": True},
                {"id": "ffw_2",  "name": "📆 2x Weekly",      "price": 310,  "popular": False},
                {"id": "ffw_3",  "name": "📆 3x Weekly",      "price": 465,  "popular": False},
                {"id": "ffw_5",  "name": "📆 5x Weekly",      "price": 775,  "popular": False},
                {"id": "ffw_m",  "name": "📆 Monthly",        "price": 765,  "popular": True},
                {"id": "ffw_2m", "name": "📆 2x Monthly",     "price": 1540, "popular": False},
                {"id": "ffw_3m", "name": "📆 3x Monthly",     "price": 2295, "popular": False},
                {"id": "ffw_5m", "name": "📆 5x Monthly",     "price": 3825, "popular": False},
                {"id": "ffw_1w1m","name":"📆 1Week+1Month",   "price": 930,  "popular": False},
                {"id": "ffw_4w1m","name":"📆 4Week+1Month",   "price": 1395, "popular": False},
            ]
        },
        # ============= FF WEEKLY LITE =============
        {
            "id": "ff_lite",
            "name": "⭐ Weekly Lite (BD)",
            "emoji": "⭐",
            "color": "#00CED1",
            "desc": "Budget Weekly Lite for BD Server",
            "input_label": "🎮 Enter Free Fire Player ID:",
            "input_placeholder": "Player ID",
            "products": [
                {"id": "ffl_1",  "name": "⭐ 1x Weekly Lite",  "price": 40,   "popular": True},
                {"id": "ffl_2",  "name": "⭐ 2x Weekly Lite",  "price": 80,   "popular": False},
                {"id": "ffl_3",  "name": "⭐ 3x Weekly Lite",  "price": 120,  "popular": False},
                {"id": "ffl_5",  "name": "⭐ 5x Weekly Lite",  "price": 200,  "popular": False},
            ]
        },
        # ============= FF LIKE =============
        {
            "id": "ff_like",
            "name": "❤️ FF Like Service",
            "emoji": "❤️",
            "color": "#FF1493",
            "desc": "Increase FF Like count! Daily delivery",
            "input_label": "🎮 Enter Free Fire Player ID:",
            "input_placeholder": "Player ID",
            "products": [
                {"id": "fflk_200",   "name": "❤️ 200 FF Likes",    "price": 20,   "popular": False},
                {"id": "fflk_1000",  "name": "❤️ 1000 FF Likes",   "price": 100,  "popular": False},
                {"id": "fflk_2000",  "name": "❤️ 2000 FF Likes",   "price": 200,  "popular": False},
                {"id": "fflk_3000",  "name": "❤️ 3000 FF Likes",   "price": 300,  "popular": False},
                {"id": "fflk_4000",  "name": "❤️ 4000 FF Likes",   "price": 400,  "popular": False},
                {"id": "fflk_5000",  "name": "❤️ 5000 FF Likes",   "price": 500,  "popular": False},
                {"id": "fflk_6000",  "name": "❤️ 6000 FF Likes",   "price": 600,  "popular": True},
                {"id": "fflk_12000", "name": "❤️ 12000 FF Likes",  "price": 1200, "popular": False},
                {"id": "fflk_24000", "name": "❤️ 24000 FF Likes",  "price": 2400, "popular": False},
                {"id": "fflk_48000", "name": "❤️ 48000 FF Likes",  "price": 4800, "popular": False},
            ]
        },
        # ============= SUBSCRIPTIONS =============
        {
            "id": "netflix",
            "name": "🎬 Netflix Premium",
            "emoji": "🎬",
            "color": "#E50914",
            "desc": "Netflix subscription at best price in BD",
            "input_label": "📧 Enter your Email or WhatsApp number:",
            "input_placeholder": "Email or Phone",
            "products": [
                {"id": "nf_single", "name": "🎬 Netflix Single Profile (1 Month)", "price": 400, "popular": True},
                {"id": "nf_full",   "name": "🎬 Netflix Full Account (1 Month)",  "price": 1830, "popular": False},
            ]
        },
        {
            "id": "youtube",
            "name": "▶️ YouTube Premium",
            "emoji": "▶️",
            "color": "#FF0000",
            "desc": "YouTube Premium — Ad-free, Background play",
            "input_label": "📧 Enter your Email address:",
            "input_placeholder": "your@email.com",
            "products": [
                {"id": "yt_1m",   "name": "▶️ YT Premium 1 Month",   "price": 100, "popular": True},
                {"id": "yt_3m",   "name": "▶️ YT Premium 3 Months",  "price": 200, "popular": False},
                {"id": "yt_6m",   "name": "▶️ YT Premium 6 Months",  "price": 300, "popular": False},
                {"id": "yt_1y",   "name": "▶️ YT Premium 1 Year",    "price": 490, "popular": False},
            ]
        },
        {
            "id": "crunchyroll",
            "name": "🍿 Crunchyroll Premium",
            "emoji": "🍿",
            "color": "#F47521",
            "desc": "Crunchyroll — Anime & Drama Premium",
            "input_label": "📧 Enter your Telegram/WhatsApp:",
            "input_placeholder": "Username or Phone",
            "products": [
                {"id": "cr_shared", "name": "🍿 Crunchyroll Shared (1 Month)",  "price": 200, "popular": False},
                {"id": "cr_full1",  "name": "🍿 Crunchyroll Full (1 Month)",    "price": 450, "popular": True},
                {"id": "cr_full12", "name": "🍿 Crunchyroll Full (12 Months)",  "price": 1840, "popular": False},
            ]
        },
        # ============= VPN PLUS CATEGORY =============
        {
            "id": "vpn_plus",
            "name": "🌐 VPN Plus — Premium IP",
            "emoji": "🌐",
            "color": "#00FF88",
            "desc": "🔒 ExpressVPN | HMA | VPN IP | Vanish | ProtonVPN | Proxy | VPS\n⚡ Auto-delivery with activation keys & configs",
            "input_label": "🌍 Enter your preferred server location (e.g., Singapore, USA, UK):",
            "input_placeholder": "Server location e.g. Singapore",
            "products": [
                # Stock-based auto-delivery products
                {"id": "vpn_express",   "name": "🔑 ExpressVPN (1 Month Key)",        "price": 350,  "popular": True, "stock_type": "key"},
                {"id": "vpn_hma",       "name": "🔑 HMA VPN (1 Month Key)",           "price": 250,  "popular": True, "stock_type": "key"},
                {"id": "vpn_vpnip",     "name": "🔑 VPN IP Service (1 Month)",        "price": 300,  "popular": False, "stock_type": "key"},
                {"id": "vpn_vanish",    "name": "🔑 Vanish VPN (1 Month)",            "price": 280,  "popular": False, "stock_type": "key"},
                {"id": "vpn_proton",    "name": "🔑 Proton VPN Plus (1 Month)",       "price": 320,  "popular": True, "stock_type": "key"},
                {"id": "proxy_dedicated","name":"🌐 Dedicated Proxy IP (1 Month)",    "price": 200,  "popular": False, "stock_type": "proxy"},
                {"id": "vps_basic",     "name": "🖥️ Basic VPS Box (1 Month)",        "price": 800,  "popular": False, "stock_type": "vps"},
                {"id": "vps_premium",   "name": "🖥️ Premium VPS Box (1 Month)",      "price": 1500, "popular": False, "stock_type": "vps"},
            ]
        },
        # ============= WALLET TOPUP CATEGORY =============
        {
            "id": "topup",
            "name": "💰 Balance Top-Up",
            "emoji": "💰",
            "color": "#FFD700",
            "desc": "Add balance to your wallet for easy payments",
            "input_label": "Send anything:",
            "input_placeholder": "",
            "products": [
                {"id": "bal_100",   "name": "💰 100 Tk Balance",    "price": 100,  "discount": 0, "popular": False},
                {"id": "bal_200",   "name": "💰 200 Tk Balance",    "price": 200,  "discount": 5, "popular": False},
                {"id": "bal_500",   "name": "💰 500 Tk Balance",    "price": 500,  "discount": 20, "popular": True},
                {"id": "bal_1000",  "name": "💰 1000 Tk Balance",   "price": 1000, "discount": 50, "popular": False},
                {"id": "bal_2000",  "name": "💰 2000 Tk Balance",   "price": 2000, "discount": 120, "popular": False},
                {"id": "bal_5000",  "name": "💰 5000 Tk Balance",   "price": 5000, "discount": 350, "popular": False},
            ]
        }
    ]
}


# ==================== DATABASE CLASS ====================
class Database:
    def __init__(self, db_path="topup_store.db"):
        self.db_path = db_path
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                balance REAL DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT (datetime('now', '+6 hours')),
                last_active TEXT DEFAULT (datetime('now', '+6 hours'))
            )
        """)
        
        # Orders table
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_name TEXT,
                category_name TEXT,
                amount REAL,
                quantity INTEGER DEFAULT 1,
                user_input TEXT,
                payment_method TEXT,
                transaction_id TEXT,
                status TEXT DEFAULT 'pending',
                delivery_photo TEXT,
                note TEXT,
                created_at TEXT DEFAULT (datetime('now', '+6 hours')),
                updated_at TEXT DEFAULT (datetime('now', '+6 hours'))
            )
        """)
        
        # Transactions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                method TEXT,
                trx_id TEXT,
                note TEXT,
                created_at TEXT DEFAULT (datetime('now', '+6 hours'))
            )
        """)
        
        # VPN Configs table
        c.execute("""
            CREATE TABLE IF NOT EXISTS vpn_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                user_id INTEGER,
                config_type TEXT,
                config_data TEXT,
                server_location TEXT,
                expiry_days INTEGER DEFAULT 30,
                created_at TEXT DEFAULT (datetime('now', '+6 hours')),
                expires_at TEXT
            )
        """)
        
        # Stock/Keys table for auto-delivery
        c.execute("""
            CREATE TABLE IF NOT EXISTS stock_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                key_data TEXT,
                is_used INTEGER DEFAULT 0,
                expiry_days INTEGER DEFAULT 30,
                created_at TEXT DEFAULT (datetime('now', '+6 hours'))
            )
        """)
        
        conn.commit()
        conn.close()

    # ==================== USER METHODS ====================
    def get_user(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def create_user(self, user_id, first_name, username=None):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT OR IGNORE INTO users (user_id, first_name, username)
            VALUES (?, ?, ?)
        """, (user_id, first_name, username))
        conn.commit()
        conn.close()

    def update_user_activity(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET last_active = datetime('now', '+6 hours')
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY joined_at DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_user_count(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users")
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    def get_active_user_count(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users WHERE is_banned = 0")
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    # ==================== BALANCE METHODS ====================
    def get_balance(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return row["balance"] if row else 0

    def update_balance(self, user_id, amount):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET balance = COALESCE(balance, 0) + ? WHERE user_id = ?
        """, (amount, user_id))
        conn.commit()
        conn.close()

    def deduct_balance(self, user_id, amount):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            UPDATE users SET balance = COALESCE(balance, 0) - ? WHERE user_id = ? AND COALESCE(balance, 0) >= ?
        """, (amount, user_id, amount))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    # ==================== BAN METHODS ====================
    def set_ban(self, user_id, banned=True):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))
        conn.commit()
        conn.close()

    # ==================== ORDER METHODS ====================
    def add_order(self, user_id, product_name, category_name, amount, quantity=1,
                  user_input="", payment_method="", transaction_id=""):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO orders (user_id, product_name, category_name, amount, quantity,
                                user_input, payment_method, transaction_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, product_name, category_name, amount, quantity,
              user_input, payment_method, transaction_id))
        order_id = c.lastrowid
        conn.commit()
        conn.close()
        return order_id

    def update_order_status(self, order_id, status, delivery_photo="", note=""):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            UPDATE orders SET status = ?, delivery_photo = ?, note = ?,
                              updated_at = datetime('now', '+6 hours')
            WHERE id = ?
        """, (status, delivery_photo, note, order_id))
        conn.commit()
        conn.close()

    def get_order(self, order_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_orders(self, user_id, limit=20):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM orders WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_all_orders(self, status=None, limit=50):
        conn = self._get_conn()
        c = conn.cursor()
        if status:
            c.execute("""
                SELECT * FROM orders WHERE status = ?
                ORDER BY created_at DESC LIMIT ?
            """, (status, limit))
        else:
            c.execute("""
                SELECT * FROM orders ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_pending_orders_count(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM orders WHERE status = 'pending'")
        row = c.fetchone()
        conn.close()
        return row["cnt"] if row else 0

    # ==================== TRANSACTION METHODS ====================
    def add_transaction(self, user_id, amount, trx_type, method, trx_id, note=""):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO transactions (user_id, amount, type, method, trx_id, note)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, amount, trx_type, method, trx_id, note))
        conn.commit()
        conn.close()

    def get_transactions(self, user_id, limit=10):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM transactions WHERE user_id = ?
            ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ==================== VPN CONFIG METHODS ====================
    def add_vpn_config(self, order_id, user_id, config_type, config_data,
                       server_location="", expiry_days=30):
        conn = self._get_conn()
        c = conn.cursor()
        expires_at = (datetime.now() + timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""
            INSERT INTO vpn_configs (order_id, user_id, config_type, config_data,
                                     server_location, expiry_days, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (order_id, user_id, config_type, config_data, server_location, expiry_days, expires_at))
        conn.commit()
        conn.close()

    def get_vpn_config(self, order_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM vpn_configs WHERE order_id = ? ORDER BY id DESC LIMIT 1", (order_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_user_vpn_configs(self, user_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM vpn_configs WHERE user_id = ?
            ORDER BY created_at DESC LIMIT 20
        """, (user_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ==================== STOCK KEYS METHODS ====================
    def add_stock_key(self, category, key_data, expiry_days=30):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            INSERT INTO stock_keys (category, key_data, expiry_days)
            VALUES (?, ?, ?)
        """, (category, key_data, expiry_days))
        key_id = c.lastrowid
        conn.commit()
        conn.close()
        return key_id

    def add_stock_keys_bulk(self, category, keys_list, expiry_days=30):
        """Add multiple keys at once. keys_list is a list of strings."""
        conn = self._get_conn()
        c = conn.cursor()
        added = 0
        for key_data in keys_list:
            if key_data.strip():
                c.execute("""
                    INSERT INTO stock_keys (category, key_data, expiry_days)
                    VALUES (?, ?, ?)
                """, (category, key_data.strip(), expiry_days))
                added += 1
        conn.commit()
        conn.close()
        return added

    def get_available_key(self, category):
        """Get one unused key from stock. Returns key data or None."""
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""
            SELECT * FROM stock_keys 
            WHERE category = ? AND is_used = 0 
            ORDER BY id ASC LIMIT 1
        """, (category,))
        row = c.fetchone()
        if row:
            c.execute("UPDATE stock_keys SET is_used = 1 WHERE id = ?", (row["id"],))
            conn.commit()
            conn.close()
            return dict(row)
        conn.close()
        return None

    def get_stock_count(self, category=None):
        conn = self._get_conn()
        c = conn.cursor()
        if category:
            c.execute("""
                SELECT COUNT(*) as cnt FROM stock_keys 
                WHERE category = ? AND is_used = 0
            """, (category,))
        else:
            c.execute("""
                SELECT category, COUNT(*) as cnt FROM stock_keys 
                WHERE is_used = 0 GROUP BY category
            """)
        rows = c.fetchall()
        conn.close()
        if category:
            row = rows[0] if rows else {"cnt": 0}
            return row["cnt"] if isinstance(row, dict) else 0
        return [dict(r) for r in rows]

    def get_all_stock(self, category=None):
        conn = self._get_conn()
        c = conn.cursor()
        if category:
            c.execute("""
                SELECT * FROM stock_keys WHERE category = ?
                ORDER BY id DESC LIMIT 100
            """, (category,))
        else:
            c.execute("""
                SELECT * FROM stock_keys ORDER BY category, id DESC LIMIT 200
            """)
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_stock_key(self, key_id):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("DELETE FROM stock_keys WHERE id = ?", (key_id,))
        affected = c.rowcount
        conn.commit()
        conn.close()
        return affected > 0


# ==================== INITIALIZE DATABASE ====================
db = Database()


# ==================== BOT SETUP ====================
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)


# ==================== FSM STATES ====================
class OrderStates(StatesGroup):
    selecting_category = State()
    selecting_product = State()
    entering_input = State()
    selecting_payment = State()
    entering_trx_id = State()

class AdminStates(StatesGroup):
    restoring_db = State()
    adding_balance_user = State()
    adding_balance_amount = State()
    delivering_order = State()
    delivering_file = State()
    broadcasting_msg = State()
    broadcasting_confirm = State()
    vpn_adding_config = State()
    vpn_config_data = State()
    vpn_config_expiry = State()
    banning_user = State()
    unbanning_user = State()
    editing_product_name = State()
    editing_product_price = State()
    adding_stock_category = State()
    adding_stock_keys = State()


# ==================== HELPER FUNCTIONS ====================
def get_categories():
    return PRODUCTS_CONFIG["categories"]

def get_category(cat_id):
    for cat in get_categories():
        if cat["id"] == cat_id:
            return cat
    return None

def get_product(cat_id, prod_id):
    cat = get_category(cat_id)
    if cat:
        for prod in cat["products"]:
            if prod["id"] == prod_id:
                return prod
    return None

def format_price(amount):
    return f"৳{amount:,.0f}"

def generate_trx_id():
    return f"TRX{datetime.now():%Y%m%d%H%M%S}{random.randint(100,999)}"


# ==================== STYLISH BUTTON BUILDERS ====================
def make_btn(text, callback_data, color=None):
    """Create a styled inline button. Color is visual hint only."""
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def row_btn(text, callback_data, color=None):
    return [make_btn(text, callback_data, color)]

# ==================== KEYBOARD BUILDERS ====================
def main_menu_kb(user_id=None):
    """Main menu with colored category buttons"""
    kb = InlineKeyboardBuilder()
    
    # Game buttons row
    kb.row(
        make_btn("🔥 Free Fire Diamonds", "cat_freefire"),
        make_btn("📆 FF Weekly", "cat_ff_weekly"),
    )
    kb.row(
        make_btn("⭐ Weekly Lite", "cat_ff_lite"),
        make_btn("❤️ FF Like", "cat_ff_like"),
    )
    
    # Subscription buttons row
    kb.row(
        make_btn("🎬 Netflix", "cat_netflix"),
        make_btn("▶️ YouTube", "cat_youtube"),
        make_btn("🍿 Crunchyroll", "cat_crunchyroll"),
    )
    
    # VPN Plus button
    kb.row(make_btn("🌐 VPN Plus — Premium IP Service", "cat_vpn_plus"))
    
    # Bottom row
    kb.row(
        make_btn("💰 Wallet", "my_wallet"),
        make_btn("📦 Orders", "my_orders"),
        make_btn("👤 Profile", "my_profile"),
    )
    
    if user_id and user_id in ADMIN_IDS:
        kb.row(make_btn("🔐 Admin Panel", "admin_menu"))
    
    return kb.as_markup()

def home_button():
    """Simple home button"""
    kb = InlineKeyboardBuilder()
    kb.row(make_btn(f"{EMOJIS['home']} Main Menu", "main_menu"))
    return kb.as_markup()

def back_button(callback_data="main_menu"):
    kb = InlineKeyboardBuilder()
    kb.row(make_btn(f"{EMOJIS['back']} Back", callback_data))
    return kb.as_markup()

def categories_kb():
    """Show all categories in a nice grid"""
    kb = InlineKeyboardBuilder()
    cats = get_categories()
    # First show game categories
    game_cats = [c for c in cats if c["id"] in ["freefire", "ff_weekly", "ff_lite", "ff_like"]]
    for cat in game_cats:
        kb.row(make_btn(f"{cat['emoji']} {cat['name']}", f"cat_{cat['id']}"))
    
    # Subscription categories
    sub_cats = [c for c in cats if c["id"] in ["netflix", "youtube", "crunchyroll"]]
    kb.row(
        make_btn(f"{sub_cats[0]['emoji']} {sub_cats[0]['name']}", f"cat_{sub_cats[0]['id']}"),
        make_btn(f"{sub_cats[1]['emoji']} {sub_cats[1]['name']}", f"cat_{sub_cats[1]['id']}"),
    )
    if len(sub_cats) > 2:
        kb.row(make_btn(f"{sub_cats[2]['emoji']} {sub_cats[2]['name']}", f"cat_{sub_cats[2]['id']}"))
    
    # VPN Plus - standout
    vpn_cat = [c for c in cats if c["id"] == "vpn_plus"]
    if vpn_cat:
        kb.row(make_btn(f"🔒 {vpn_cat[0]['name']} 🔒", f"cat_{vpn_cat[0]['id']}"))
    
    # Bottom
    kb.row(make_btn("💰 Wallet Top-Up", "cat_topup"))
    kb.row(make_btn(f"{EMOJIS['home']} Main Menu", "main_menu"))
    
    return kb.as_markup()

def products_kb(cat_id):
    """Show products for a category"""
    cat = get_category(cat_id)
    if not cat:
        return home_button()
    
    kb = InlineKeyboardBuilder()
    products = cat["products"]
    
    for prod in products:
        price = prod.get("price", 0)
        label = prod.get("name", "")
        
        # Add price info
        if cat_id == "topup":
            bonus = prod.get("discount", 0)
            if bonus > 0:
                label = f"{label} [+{format_price(bonus)} Bonus]"
            else:
                label = f"{label}"
        else:
            label = f"{label} — {format_price(price)}"
        
        kb.row(make_btn(label, f"prod_{cat_id}|{prod['id']}"))
    
    kb.row(make_btn(f"{EMOJIS['back']} Categories", "show_categories"))
    kb.row(make_btn(f"{EMOJIS['home']} Main Menu", "main_menu"))
    
    return kb.as_markup()

def payment_kb():
    """Payment method selection"""
    kb = InlineKeyboardBuilder()
    kb.row(make_btn(f"{EMOJIS['wallet']} Wallet Balance", "pay_wallet"))
    kb.row(make_btn("💳 bKash", "pay_bkash"))
    kb.row(make_btn("💳 Nagad", "pay_nagad"))
    kb.row(make_btn("💳 Rocket", "pay_rocket"))
    kb.row(make_btn(f"{EMOJIS['back']} Back to Products", "back_to_products"))
    return kb.as_markup()

def admin_kb():
    """Admin panel with colored buttons"""
    kb = InlineKeyboardBuilder()
    kb.row(make_btn("📊 Dashboard", "admin_dashboard"))
    kb.row(make_btn("📦 Pending Orders", "admin_orders_pending"))
    kb.row(make_btn("👥 All Users", "admin_users"))
    kb.row(make_btn("💰 Add Balance", "admin_add_balance"))
    kb.row(make_btn("📦 Deliver Order", "admin_deliver"))
    kb.row(make_btn("📨 Broadcast", "admin_broadcast"))
    kb.row(make_btn("🌐 VPN Configs", "admin_vpn"))
    kb.row(make_btn("🔑 Stock Keys", "admin_stock"))
    kb.row(make_btn("⛔ Ban User", "admin_ban"))
    kb.row(make_btn("✅ Unban User", "admin_unban"))
    kb.row(make_btn("💾 Restore DB", "admin_restore"))
    kb.row(make_btn(f"{EMOJIS['home']} Main Menu", "main_menu"))
    return kb.as_markup()

def admin_vpn_kb():
    kb = InlineKeyboardBuilder()
    kb.row(make_btn("📋 All VPN Orders", "admin_vpn_orders"))
    kb.row(make_btn("➕ Add VPN Config", "admin_vpn_add"))
    kb.row(make_btn("📊 Stock Status", "admin_stock_status"))
    kb.row(make_btn(f"{EMOJIS['back']} Admin Panel", "admin_menu"))
    return kb.as_markup()

def admin_stock_kb():
    kb = InlineKeyboardBuilder()
    kb.row(make_btn("📋 View All Stock", "admin_stock_view"))
    kb.row(make_btn("➕ Add Keys", "admin_stock_add"))
    kb.row(make_btn("🗑️ Delete Key", "admin_stock_delete"))
    kb.row(make_btn(f"{EMOJIS['back']} Admin Panel", "admin_menu"))
    return kb.as_markup()


# ==================== VPN KEY AUTO-GENERATOR ====================
def generate_vpn_key(category, user_id):
    """Generate a demo VPN key. In production, integrate with real API."""
    prefix = {
        "expressvpn": "EXVPN", "hma": "HMA", "vpnip": "VPNIP",
        "vanish": "VANISH", "protonvpn": "PROTON", "proxy": "PROXY",
        "vps": "VPS"
    }.get(category, "VPN")
    
    key = f"{prefix}-{uuid4().hex[:12].upper()}-{uuid4().hex[:8].upper()}"
    config_template = f"""[Interface]
PrivateKey = {uuid4().hex[:44]}
Address = 10.0.0.{random.randint(2,254)}/32
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {uuid4().hex[:44]}
PresharedKey = {uuid4().hex[:44]}
Endpoint = sg-{category}.vpnserver.com:{random.randint(1024,65535)}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return {
        "activation_key": key,
        "config_data": config_template,
        "category": category
    }

def get_vpn_expiry_days(product_name):
    """Extract expiry days from product name"""
    name_lower = product_name.lower()
    if "year" in name_lower or "12 month" in name_lower:
        return 365
    elif "6 month" in name_lower:
        return 180
    elif "3 month" in name_lower:
        return 90
    else:
        return 30  # Default 1 month


# ==================== WELCOME MESSAGE ====================
WELCOME_MSG = f"""
🌟 **Welcome to {BOT_NAME}!** 🌟

━━━━━━━━━━━━━━━━━━━━━
🔥 **Bangladesh's Premium Digital Store!**
━━━━━━━━━━━━━━━━━━━━━

**📌 What we offer:**
🔥 Free Fire Diamonds — Best BD Price!
📆 Weekly/Monthly Membership
⭐ Weekly Lite
❤️ FF Like Service
🎬 Netflix Premium
▶️ YouTube Premium
🍿 Crunchyroll Premium
🌐 **VPN Plus** — ExpressVPN, HMA, VPN IP, Vanish, ProtonVPN, Proxy, VPS
💰 Wallet Top-Up with Bonus

━━━━━━━━━━━━━━━━━━━━━
**⚡ Features:**
✅ Instant Auto-Delivery
✅ 24/7 Support
✅ Best Price in BD
✅ Secure Payment
━━━━━━━━━━━━━━━━━━━━━

📞 **Support:** @{SUPPORT_USERNAME}
💳 **Payment:** bKash / Nagad / Rocket / Wallet

👇 **Select a category to get started!**
"""


# ==================== COMMAND HANDLERS ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    username = message.from_user.username
    
    db.create_user(user_id, first_name, username)
    db.update_user_activity(user_id)
    
    await message.answer(
        WELCOME_MSG,
        reply_markup=main_menu_kb(user_id),
        parse_mode="Markdown"
    )

@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    user_id = message.from_user.id
    db.update_user_activity(user_id)
    await message.answer(
        f"{EMOJIS['home']} **Main Menu**",
        reply_markup=main_menu_kb(user_id),
        parse_mode="Markdown"
    )

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        return await message.answer(f"{EMOJIS['cross']} Unauthorized!")
    await message.answer(
        f"{EMOJIS['admin']} **Admin Panel**",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )


# ==================== CALLBACK: MAIN MENU ====================
@dp.callback_query(lambda c: c.data == "main_menu")
async def back_main_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = call.from_user.id
    await call.message.edit_text(
        f"{EMOJIS['home']} **Main Menu**\n\nWelcome back, {call.from_user.first_name}!",
        reply_markup=main_menu_kb(user_id),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "show_categories")
async def show_categories_handler(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text(
        "📂 **Select Category:**",
        reply_markup=categories_kb(),
        parse_mode="Markdown"
    )


# ==================== CALLBACK: CATEGORY SELECTION ====================
@dp.callback_query(lambda c: c.data.startswith("cat_") and not c.data.startswith("cat_vpn_"))
async def select_category(call: CallbackQuery, state: FSMContext):
    cat_id = call.data.replace("cat_", "")
    cat = get_category(cat_id)
    if not cat:
        return await call.answer("Category not found!", show_alert=True)
    
    await state.update_data(category=cat)
    await state.set_state(OrderStates.selecting_category)
    
    msg = f"{cat['emoji']} **{cat['name']}**\n\n{cat.get('desc', '')}\n\n📦 **Available Products:**"
    
    await call.message.edit_text(
        msg,
        reply_markup=products_kb(cat_id),
        parse_mode="Markdown"
    )


# ==================== CALLBACK: VPN PLUS CATEGORY ====================
@dp.callback_query(lambda c: c.data == "cat_vpn_plus")
async def select_vpn_category(call: CallbackQuery, state: FSMContext):
    cat = get_category("vpn_plus")
    if not cat:
        return await call.answer("Category not found!", show_alert=True)
    
    await state.update_data(category=cat)
    await state.set_state(OrderStates.selecting_category)
    
    # Show stock info
    stock_info = db.get_stock_count()
    stock_text = ""
    if stock_info:
        stock_text = "\n\n📊 **Available Stock:**\n"
        for s in stock_info:
            emoji = {"key": "🔑", "proxy": "🌐", "vps": "🖥️"}.get(
                s["category"], "📦")
            stock_text += f"{emoji} {s['category'].upper()}: {s['cnt']} keys\n"
    
    msg = f"""🌐 **VPN Plus — Premium IP Service** 🌐

━━━━━━━━━━━━━━━━━━━━━
🔒 **Available Services:**
• 🔑 ExpressVPN — 1 Month Key
• 🔑 HMA VPN — 1 Month Key
• 🔑 VPN IP Service — 1 Month
• 🔑 Vanish VPN — 1 Month
• 🔑 Proton VPN Plus — 1 Month
• 🌐 Dedicated Proxy IP — 1 Month
• 🖥️ Basic/ Premium VPS Box — 1 Month
━━━━━━━━━━━━━━━━━━━━━

⚡ **Auto-Delivery!** 
After payment, activation key & config will be delivered instantly!{stock_text}

📦 **Select your VPN plan:**"""
    
    await call.message.edit_text(
        msg,
        reply_markup=products_kb("vpn_plus"),
        parse_mode="Markdown"
    )


# ==================== CALLBACK: PRODUCT SELECTION ====================
@dp.callback_query(lambda c: c.data.startswith("prod_"))
async def select_product(call: CallbackQuery, state: FSMContext):
    parts = call.data.replace("prod_", "").split("|")
    if len(parts) != 2:
        return await call.answer("Invalid product!", show_alert=True)
    
    cat_id, prod_id = parts
    cat = get_category(cat_id)
    product = get_product(cat_id, prod_id)
    
    if not cat or not product:
        return await call.answer("Product not found!", show_alert=True)
    
    await state.update_data(product=product, category=cat)
    await state.set_state(OrderStates.selecting_product)
    
    price = product.get("price", 0)
    msg = f"""📦 **{product['name']}**

━━━━━━━━━━━━━━━━━━━━━
💰 **Price:** {format_price(price)}
📂 **Category:** {cat['name']}
━━━━━━━━━━━━━━━━━━━━━

{cat.get('input_label', '📝 Please enter your details:')}"""

    if cat_id == "topup":
        bonus = product.get("discount", 0)
        if bonus > 0:
            msg += f"\n\n🎁 **Bonus:** +{format_price(bonus)} Free!"
    
    await call.message.edit_text(
        msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['verified']} Proceed to Order", callback_data=f"order_{cat_id}|{prod_id}")],
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data=f"cat_{cat_id}")],
            [InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")],
        ]),
        parse_mode="Markdown"
    )


# ==================== ORDER FLOW: START ====================
@dp.callback_query(lambda c: c.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    parts = call.data.replace("order_", "").split("|")
    if len(parts) != 2:
        return await call.answer("Invalid!", show_alert=True)
    
    cat_id, prod_id = parts
    cat = get_category(cat_id)
    product = get_product(cat_id, prod_id)
    
    if not cat or not product:
        return await call.answer("Product not found!", show_alert=True)
    
    await state.update_data(product=product, category=cat, cat_id=cat_id, prod_id=prod_id)
    
    user_id = call.from_user.id
    
    # For VPN + topup categories, no input needed
    if cat_id in ["topup"]:
        await state.update_data(user_input="Wallet TopUp")
        # Go directly to payment
        price = product.get("price", 0)
        balance = db.get_balance(user_id)
        
        msg = f"""💳 **Payment Method**

📦 **Product:** {product['name']}
💰 **Price:** {format_price(price)}
💼 **Wallet Balance:** {format_price(balance)}

Select payment method:"""
        await call.message.edit_text(
            msg,
            reply_markup=payment_kb(),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.selecting_payment)
    elif cat_id == "vpn_plus":
        # For VPN, we need server location
        await call.message.edit_text(
            f"🌍 **Enter Server Location**\n\nPlease type your preferred server location:\n\n"
            f"Examples: `Singapore`, `USA`, `UK`, `Germany`, `Japan`, `India`\n\n"
            f"Or type `auto` for best available server.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['lightning']} Auto Select", callback_data="vpn_auto_location")],
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data=f"prod_{cat_id}|{prod_id}")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_input)
    else:
        # Normal products - ask for user input (Player ID, Email, etc.)
        await call.message.edit_text(
            f"{cat.get('input_label', '📝 Enter your details:')}\n\n"
            f"Example: `{cat.get('input_placeholder', 'Your ID/Email')}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data=f"prod_{cat_id}|{prod_id}")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_input)


# ==================== VPN AUTO LOCATION ====================
@dp.callback_query(lambda c: c.data == "vpn_auto_location")
async def vpn_auto_location(call: CallbackQuery, state: FSMContext):
    await state.update_data(user_input="Auto")
    user_id = call.from_user.id
    state_data = await state.get_data()
    product = state_data.get("product", {})
    price = product.get("price", 0)
    balance = db.get_balance(user_id)
    
    msg = f"""💳 **Payment Method**

📦 **Product:** {product.get('name', '')}
🌍 **Server:** Auto Select
💰 **Price:** {format_price(price)}
💼 **Wallet Balance:** {format_price(balance)}

Select payment method:"""
    await call.message.edit_text(
        msg,
        reply_markup=payment_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.selecting_payment)


# ==================== PROCESS USER INPUT ====================
@dp.message(OrderStates.entering_input)
async def process_user_input(message: Message, state: FSMContext):
    user_input = message.text.strip()
    if not user_input or len(user_input) < 2:
        return await message.answer(f"{EMOJIS['cross']} Please enter valid details! (min 2 characters)")
    
    await state.update_data(user_input=user_input)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    price = product.get("price", 0)
    user_id = message.from_user.id
    balance = db.get_balance(user_id)
    
    await message.answer(
        f"💳 **Payment Method**\n\n"
        f"📦 **Product:** {product.get('name', '')}\n"
        f"💰 **Price:** {format_price(price)}\n"
        f"💼 **Wallet Balance:** {format_price(balance)}\n\n"
        f"Select payment method:",
        reply_markup=payment_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.selecting_payment)


# ==================== PAYMENT SELECTION ====================
@dp.callback_query(lambda c: c.data.startswith("pay_"))
async def select_payment(call: CallbackQuery, state: FSMContext):
    payment_method = call.data.replace("pay_", "")
    await state.update_data(payment_method=payment_method)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    cat_id = state_data.get("cat_id", cat.get("id", ""))
    price = product.get("price", 0)
    user_id = call.from_user.id
    
    if payment_method == "wallet":
        # Check balance
        balance = db.get_balance(user_id)
        if balance < price:
            return await call.message.edit_text(
                f"{EMOJIS['cross']} **Insufficient Balance!**\n\n"
                f"💰 Balance: {format_price(balance)}\n"
                f"💵 Required: {format_price(price)}\n"
                f"📉 Short: {format_price(price - balance)}\n\n"
                f"Add balance via Wallet Top-Up first!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{EMOJIS['money']} Top-Up Now", callback_data="cat_topup")],
                    [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="back_to_products")],
                ]),
                parse_mode="Markdown"
            )
        
        # Process wallet payment
        trx_id = generate_trx_id()
        await process_wallet_payment(call, state, bot, trx_id)
        
    elif payment_method == "bkash":
        msg = f"""💳 **bKash Payment**

📞 **Send money to:** `{BKASH_NUMBER}`
💰 **Amount:** {format_price(price)}

📝 **Instructions:**
1️⃣ Send the exact amount to the bKash number above
2️⃣ Copy the Transaction ID (TrxID) from SMS
3️⃣ Send the TrxID here

⚠️ **After sending payment, type your Transaction ID below:**"""
        await call.message.edit_text(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back to Payment", callback_data="back_to_payment")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_trx_id)
        
    elif payment_method == "nagad":
        msg = f"""💳 **Nagad Payment**

📞 **Send money to:** `{NAGAD_NUMBER}`
💰 **Amount:** {format_price(price)}

📝 **Instructions:**
1️⃣ Send the exact amount to the Nagad number above
2️⃣ Copy the Transaction ID (TrxID) from SMS
3️⃣ Send the TrxID here

⚠️ **After sending payment, type your Transaction ID below:**"""
        await call.message.edit_text(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back to Payment", callback_data="back_to_payment")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_trx_id)
        
    elif payment_method == "rocket":
        msg = f"""💳 **Rocket Payment**

📞 **Send money to:** `{ROCKET_NUMBER}`
💰 **Amount:** {format_price(price)}

📝 **Instructions:**
1️⃣ Send the exact amount to the Rocket number above
2️⃣ Copy the Transaction ID (TrxID) from SMS
3️⃣ Send the TrxID here

⚠️ **After sending payment, type your Transaction ID below:**"""
        await call.message.edit_text(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back to Payment", callback_data="back_to_payment")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_trx_id)
        
    elif payment_method == "upi":
        msg = f"""💳 **UPI Payment**

📞 **UPI ID:** `{UPI_ID}`
💰 **Amount:** {format_price(price)}

📝 **Instructions:**
1️⃣ Send payment to UPI ID above
2️⃣ Copy the Transaction ID / UTR number
3️⃣ Send it here

⚠️ **Type your Transaction ID below:**"""
        await call.message.edit_text(
            msg,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back to Payment", callback_data="back_to_payment")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_trx_id)


# ==================== WALLET PAYMENT PROCESSING ====================
async def process_wallet_payment(call: CallbackQuery, state: FSMContext, bot: Bot, trx_id):
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    cat_id = state_data.get("cat_id", cat.get("id", ""))
    user_input = state_data.get("user_input", "")
    user_id = call.from_user.id
    price = product.get("price", 0)
    
    # Deduct balance
    success = db.deduct_balance(user_id, price)
    if not success:
        return await call.message.edit_text(
            f"{EMOJIS['cross']} Payment failed! Insufficient balance.",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    
    # Create order
    order_id = db.add_order(user_id, product.get("name", ""), cat.get("name", ""),
                            price, 1, user_input, "Wallet Balance", trx_id)
    
    # Handle VPN Plus auto-delivery
    if cat_id == "vpn_plus":
        stock_type = product.get("stock_type", "key")
        # Try to get from stock first
        stock_key = db.get_available_key(stock_type)
        
        if stock_key:
            key_data = stock_key["key_data"]
            expiry_days = stock_key.get("expiry_days", 30)
        else:
            # Auto-generate demo key
            vpn_data = generate_vpn_key(stock_type, user_id)
            key_data = vpn_data["activation_key"]
            expiry_days = 30
        
        server_location = user_input if user_input and user_input != "Wallet TopUp" else "Auto"
        
        db.add_vpn_config(order_id, user_id, stock_type, key_data, server_location, expiry_days)
        db.update_order_status(order_id, "delivered", note=f"VPN Auto-delivered. Server: {server_location}")
        
        await call.message.edit_text(
            f"{EMOJIS['verified']} **VPN Order Successful!**\n\n"
            f"🆔 Order #`{order_id}`\n"
            f"📦 Product: **{product['name']}**\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"💳 Paid via: **Wallet Balance**\n"
            f"🌍 Server: **{server_location}**\n\n"
            f"{EMOJIS['rocket']} **Auto-Delivered!**\n\n"
            f"🔑 **Your Activation Key:**\n`{key_data}`\n\n"
            f"📅 Expires: **{expiry_days} days**\n\n"
            f"{EMOJIS['info']} Use this key to activate your VPN.\n"
            f"📞 Contact @{SUPPORT_USERNAME} if you need help!",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    elif cat_id == "topup":
        # Topup - add balance
        bonus = product.get("discount", 0)
        total = price + bonus
        db.update_balance(user_id, total)
        db.add_transaction(user_id, total, "topup", "Wallet Balance", trx_id, f"Wallet TopUp +{format_price(bonus)} bonus")
        
        await call.message.edit_text(
            f"{EMOJIS['verified']} **Balance Added!**\n\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"🎁 Bonus: **+{format_price(bonus)}**\n"
            f"💵 Total Added: **{format_price(total)}**\n\n"
            f"✅ Your wallet has been updated!",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    else:
        # Normal product - mark as delivered
        db.update_order_status(order_id, "delivered", note="Auto-delivered via wallet payment")
        
        await call.message.edit_text(
            f"{EMOJIS['verified']} **Order Successful!**\n\n"
            f"🆔 Order #`{order_id}`\n"
            f"📦 Product: **{product['name']}**\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"💳 Paid via: **Wallet Balance**\n\n"
            f"{EMOJIS['rocket']} **Auto-Delivered!**\n"
            f"✅ Order processed instantly!\n\n"
            f"{EMOJIS['sparkle']} Thank you for your purchase!",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"{EMOJIS['lightning']} **Auto-Delivered (Wallet)**\n\n"
                f"🆔 Order #`{order_id}`\n"
                f"👤 User: [{call.from_user.first_name}](tg://user?id={user_id})\n"
                f"📦 {product['name']}\n"
                f"💰 {format_price(price)}\n"
                f"💳 Wallet Balance\n"
                f"📝 Input: `{user_input}`",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await state.clear()


# ==================== PROCESS TRANSACTION ID ====================
@dp.message(OrderStates.entering_trx_id)
async def process_trx_id(message: Message, state: FSMContext, bot: Bot):
    trx_id = message.text.strip()
    if not trx_id or len(trx_id) < 3:
        return await message.answer(f"{EMOJIS['cross']} Please enter a valid Transaction ID!")
    
    await state.update_data(transaction_id=trx_id)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    cat_id = state_data.get("cat_id", cat.get("id", ""))
    user_input = state_data.get("user_input", "")
    payment_method = state_data.get("payment_method", "")
    user_id = message.from_user.id
    price = product.get("price", 0)
    
    method_names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket", "upi": "UPI"}
    method_name = method_names.get(payment_method, payment_method)
    
    # Create order
    order_id = db.add_order(user_id, product.get("name", ""), cat.get("name", ""),
                            price, 1, user_input, method_name, trx_id)
    
    if cat_id == "topup":
        bonus = product.get("discount", 0)
        total = price + bonus
        db.update_balance(user_id, total)
        db.add_transaction(user_id, total, "topup", method_name, trx_id, f"Top-up via {method_name}")
        
        await message.answer(
            f"{EMOJIS['verified']} **Balance Added Successfully!**\n\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"🎁 Bonus: **+{format_price(bonus)}**\n"
            f"💵 Total Added: **{format_price(total)}**\n\n"
            f"{EMOJIS['sparkle']} Thank you! Your balance has been updated.",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
        
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"{EMOJIS['money']} **Balance Top-Up**\n\n"
                    f"👤 [{message.from_user.first_name}](tg://user?id={user_id})\n"
                    f"💰 {format_price(price)} + {format_price(bonus)} bonus\n"
                    f"💳 {method_name}\n"
                    f"🔢 TrxID: `{trx_id}`\n"
                    f"✅ **Auto-Credited**",
                    parse_mode="Markdown"
                )
            except:
                pass
        await state.clear()
        return
    
    # Handle VPN Plus with manual payment
    if cat_id == "vpn_plus":
        stock_type = product.get("stock_type", "key")
        server_location = user_input if user_input and user_input != "Wallet TopUp" else "Auto"
        
        # Try stock first
        stock_key = db.get_available_key(stock_type)
        if stock_key:
            key_data = stock_key["key_data"]
            expiry_days = stock_key.get("expiry_days", 30)
        else:
            vpn_data = generate_vpn_key(stock_type, user_id)
            key_data = vpn_data["activation_key"]
            expiry_days = 30
        
        db.add_vpn_config(order_id, user_id, stock_type, key_data, server_location, expiry_days)
        db.update_order_status(order_id, "delivered", note=f"VPN Auto-generated. Server: {server_location}")
        
        await message.answer(
            f"{EMOJIS['verified']} **VPN Order Placed!**\n\n"
            f"🆔 Order #`{order_id}`\n"
            f"📦 Product: **{product.get('name', '')}**\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"💳 Payment: **{method_name}**\n"
            f"🔢 TrxID: `{trx_id}`\n"
            f"🌍 Location: **{server_location}**\n\n"
            f"{EMOJIS['rocket']} **Auto-Generated!**\n\n"
            f"🔑 **Your Key:**\n`{key_data}`\n\n"
            f"📅 Valid for: **{expiry_days} days**\n\n"
            f"{EMOJIS['info']} Admin will verify shortly.\n"
            f"📞 @{SUPPORT_USERNAME} for help.",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"{EMOJIS['verified']} **Order Placed!**\n\n"
            f"🆔 Order #`{order_id}`\n"
            f"📦 Product: **{product.get('name', '')}**\n"
            f"💰 Amount: **{format_price(price)}**\n"
            f"💳 Payment: **{method_name}**\n"
            f"🔢 TrxID: `{trx_id}`\n\n"
            f"{EMOJIS['clock']} **Status: Pending Verification**\n\n"
            f"⏳ We will notify you once verified & delivered!\n"
            f"📞 @{SUPPORT_USERNAME} for any issues.",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    
    # Notify admin
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"{EMOJIS['bell']} **New Order!**\n\n"
                f"🆔 #`{order_id}`\n"
                f"👤 [{message.from_user.first_name}](tg://user?id={user_id})\n"
                f"📂 {cat.get('name', '')}\n"
                f"📦 {product.get('name', '')}\n"
                f"💰 {format_price(price)}\n"
                f"📝 Input: `{user_input}`\n"
                f"💳 {method_name}\n"
                f"🔢 TrxID: `{trx_id}`",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await state.clear()


# ==================== BACK TO PAYMENT / PRODUCTS ====================
@dp.callback_query(lambda c: c.data == "back_to_payment")
async def back_to_payment(call: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    product = state_data.get("product", {})
    price = product.get("price", 0)
    user_id = call.from_user.id
    balance = db.get_balance(user_id)
    
    await call.message.edit_text(
        f"💳 **Payment Method**\n\n"
        f"📦 **Product:** {product.get('name', '')}\n"
        f"💰 **Price:** {format_price(price)}\n"
        f"💼 **Wallet Balance:** {format_price(balance)}\n\n"
        f"Select payment method:",
        reply_markup=payment_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.selecting_payment)

@dp.callback_query(lambda c: c.data == "back_to_products")
async def back_to_products(call: CallbackQuery, state: FSMContext):
    state_data = await state.get_data()
    cat = state_data.get("category", {})
    cat_id = state_data.get("cat_id", cat.get("id", ""))
    if cat_id:
        await call.message.edit_text(
            f"{cat.get('emoji', '📦')} **{cat.get('name', 'Products')}**\n\nSelect a product:",
            reply_markup=products_kb(cat_id),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.selecting_category)
    else:
        await call.message.edit_text(
            f"{EMOJIS['home']} **Main Menu**",
            reply_markup=main_menu_kb(call.from_user.id),
            parse_mode="Markdown"
        )
        await state.clear()


# ==================== USER INFO HANDLERS ====================
@dp.callback_query(lambda c: c.data == "my_wallet")
async def my_wallet(call: CallbackQuery):
    user_id = call.from_user.id
    balance = db.get_balance(user_id)
    user = db.get_user(user_id)
    total_spent = sum(o["amount"] for o in db.get_user_orders(user_id, 50))
    
    await call.message.edit_text(
        f"{EMOJIS['wallet']} **My Wallet**\n\n"
        f"👤 **User:** {call.from_user.first_name}\n"
        f"💰 **Balance:** {format_price(balance)}\n"
        f"📦 **Total Spent:** {format_price(total_spent)}\n"
        f"📊 **Orders:** {len(db.get_user_orders(user_id, 50))}\n\n"
        f"{EMOJIS['info']} Use wallet balance for instant purchases!\n"
        f"Top up via {EMOJIS['money']} **Balance Top-Up** category.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['money']} Top-Up Now", callback_data="cat_topup")],
            [InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")],
        ]),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "my_orders")
async def my_orders(call: CallbackQuery):
    user_id = call.from_user.id
    orders = db.get_user_orders(user_id, 10)
    
    if not orders:
        return await call.message.edit_text(
            f"{EMOJIS['cart']} **My Orders**\n\nYou have no orders yet!\n\nStart shopping from the main menu!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")],
            ]),
            parse_mode="Markdown"
        )
    
    msg = f"{EMOJIS['cart']} **My Recent Orders**\n\n"
    for o in orders[:10]:
        status_emoji = {
            "pending": "⏳", "delivered": "✅", "cancelled": "❌"
        }.get(o["status"], "❓")
        msg += f"`#{o['id']}` {status_emoji} **{o['product_name']}**\n"
        msg += f"   💰 {format_price(o['amount'])} — {o['status'].title()}\n"
        msg += f"   📅 {o['created_at'][:16]}\n\n"
    
    msg += f"{EMOJIS['info']} Contact @{SUPPORT_USERNAME} for order support."
    
    await call.message.edit_text(
        msg,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")],
        ]),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "my_profile")
async def my_profile(call: CallbackQuery):
    user_id = call.from_user.id
    user = db.get_user(user_id)
    balance = db.get_balance(user_id) if user else 0
    order_count = len(db.get_user_orders(user_id, 100))
    total_spent = sum(o["amount"] for o in db.get_user_orders(user_id, 100))
    joined = user["joined_at"][:16] if user else "Unknown"
    
    await call.message.edit_text(
        f"{EMOJIS['crown']} **My Profile**\n\n"
        f"👤 **Name:** {call.from_user.first_name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📅 **Joined:** {joined}\n"
        f"💰 **Balance:** {format_price(balance)}\n"
        f"📦 **Orders:** {order_count}\n"
        f"💵 **Total Spent:** {format_price(total_spent)}\n\n"
        f"{EMOJIS['star']} Thank you for being a valued customer!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")],
        ]),
        parse_mode="Markdown"
    )


# ==================== ADMIN HANDLERS ====================
@dp.callback_query(lambda c: c.data == "admin_menu")
async def admin_menu_handler(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await state.clear()
    await call.message.edit_text(
        f"{EMOJIS['admin']} **Admin Panel**\n\nWelcome, {call.from_user.first_name}!",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_dashboard")
async def admin_dashboard(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    users = db.get_all_users()
    total_users = len(users)
    active_users = sum(1 for u in users if not u["is_banned"])
    banned_users = total_users - active_users
    pending_orders = db.get_pending_orders_count()
    total_orders = len(db.get_all_orders(status=None, limit=10000))
    stock_counts = db.get_stock_count()
    
    stock_msg = ""
    if stock_counts:
        for s in stock_counts:
            stock_msg += f"{s['category'].upper()}: {s['cnt']} keys\n"
    
    # Total revenue
    all_orders = db.get_all_orders(status="delivered", limit=10000)
    total_revenue = sum(o["amount"] for o in all_orders)
    
    await call.message.edit_text(
        f"{EMOJIS['chart']} **Admin Dashboard**\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 **Users:** `{total_users}` total | `{active_users}` active | `{banned_users}` banned\n"
        f"📦 **Orders:** `{total_orders}` total | `{pending_orders}` pending\n"
        f"💰 **Revenue:** {format_price(total_revenue)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔑 **Stock Status:**\n{stock_msg or 'No stock data'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_orders_pending")
async def admin_orders_pending(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    orders = db.get_all_orders(status="pending", limit=20)
    if not orders:
        return await call.message.edit_text(
            f"{EMOJIS['verified']} No pending orders!",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    
    msg = f"{EMOJIS['list']} **Pending Orders ({len(orders)}):**\n\n"
    for o in orders[:20]:
        msg += f"`#{o['id']}` 👤 `{o['user_id']}`\n"
        msg += f"   📦 {o['product_name']} — {format_price(o['amount'])}\n"
        msg += f"   💳 {o['payment_method']} | `{o['transaction_id'] or 'N/A'}`\n"
        msg += f"   📝 {o['user_input'][:30] or 'N/A'}\n"
        msg += f"   📅 {o['created_at'][:16]}\n\n"
    
    await call.message.edit_text(
        msg,
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    users = db.get_all_users()
    msg = f"{EMOJIS['users']} **All Users ({len(users)}):**\n\n"
    for u in users[:30]:
        badge = "👑" if u["user_id"] in ADMIN_IDS else ("🔒" if u["is_banned"] else "👤")
        msg += f"{badge} `{u['user_id']}` — {u['first_name'] or 'N/A'}\n"
        msg += f"   💰 {format_price(u['balance'])} | 📅 {u['joined_at'][:10]}\n"
    
    await call.message.edit_text(
        msg,
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )

# ==================== ADMIN: ADD BALANCE ====================
@dp.callback_query(lambda c: c.data == "admin_add_balance")
async def admin_add_balance_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['money']} **Add Balance**\n\nSend the User ID to add balance to:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.adding_balance_user)

@dp.message(AdminStates.adding_balance_user)
async def admin_balance_user_id(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        await state.update_data(target_user=target_id)
        user = db.get_user(target_id)
        if user:
            await message.answer(
                f"👤 **User Found:** `{target_id}`\n"
                f"Name: {user['first_name'] or 'Unknown'}\n"
                f"Current Balance: {format_price(user['balance'])}\n\n"
                f"Send the amount to add:",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"⚠️ User `{target_id}` not found in database.\n"
                f"Send amount anyway?",
                parse_mode="Markdown"
            )
        await state.set_state(AdminStates.adding_balance_amount)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid User ID. Send a numeric ID.")

@dp.message(AdminStates.adding_balance_amount)
async def admin_balance_amount_proc(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0 or amount > 1000000:
            return await message.answer(f"{EMOJIS['cross']} Invalid amount (1-1000000). Try again:")
        
        state_data = await state.get_data()
        target_id = state_data.get("target_user")
        
        db.update_balance(target_id, amount)
        db.add_transaction(target_id, amount, "admin_add", "Admin",
                          f"ADMIN_{datetime.now():%Y%m%d%H%M%S}",
                          f"Added by @{message.from_user.username or 'admin'}")
        
        await message.answer(
            f"{EMOJIS['verified']} **Balance Added!**\n\n"
            f"👤 User: `{target_id}`\n"
            f"💰 Amount: **+{format_price(amount)}**",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        
        try:
            await bot.send_message(
                target_id,
                f"{EMOJIS['money']} **Balance Added!**\n\n+**{format_price(amount)}** added to your wallet!",
                parse_mode="Markdown"
            )
        except:
            pass
        
        await state.clear()
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid amount. Send a number:")

# ==================== ADMIN: DELIVER ORDER ====================
@dp.callback_query(lambda c: c.data == "admin_deliver")
async def admin_deliver_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['package']} **Deliver Order**\n\nSend the Order ID to deliver:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.delivering_order)

@dp.message(AdminStates.delivering_order)
async def admin_deliver_order_id(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
        order = db.get_order(order_id)
        if not order:
            return await message.answer(f"{EMOJIS['cross']} Order not found!")
        
        await state.update_data(deliver_order_id=order_id)
        
        await message.answer(
            f"📦 **Order #`{order_id}`**\n\n"
            f"Product: {order['product_name']}\n"
            f"User: `{order['user_id']}`\n"
            f"Amount: {format_price(order['amount'])}\n"
            f"Status: **{order['status'].upper()}**\n"
            f"Input: {order['user_input']}\n\n"
            f"Send delivery photo 📷 or note ✏️:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['lightning']} Deliver Without Photo", callback_data="deliver_no_photo")],
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.delivering_file)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid Order ID. Send a number:")

@dp.callback_query(lambda c: c.data == "deliver_no_photo")
async def deliver_no_photo(call: CallbackQuery, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
    if not order_id:
        return await call.answer("No order selected!", show_alert=True)
    
    db.update_order_status(order_id, "delivered", note="Delivered ✅")
    order = db.get_order(order_id)
    
    await call.message.edit_text(
        f"{EMOJIS['verified']} **Order #`{order_id}` Delivered! ✅**",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    if order:
        try:
            await bot.send_message(
                order["user_id"],
                f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                f"🆔 #`{order_id}`\n"
                f"📦 {order['product_name']}\n"
                f"✅ Thank you for your purchase!",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await state.clear()

@dp.message(AdminStates.delivering_file)
async def admin_deliver_file_proc(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
    if not order_id:
        return await message.answer(f"{EMOJIS['cross']} Session expired!")
    
    file_id = ""
    note = "Delivered ✅"
    
    if message.photo:
        file_id = message.photo[-1].file_id
        note = message.caption or "Delivered with proof ✅"
    elif message.document:
        file_id = message.document.file_id
        note = message.caption or "Delivered with file ✅"
    else:
        note = message.text or "Delivered ✅"
    
    db.update_order_status(order_id, "delivered", file_id, note)
    order = db.get_order(order_id)
    
    await message.answer(
        f"{EMOJIS['verified']} **Order #`{order_id}` Delivered!**\n\n"
        f"📝 Note: {note}",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    if order:
        try:
            if file_id:
                await bot.send_photo(
                    order["user_id"],
                    file_id,
                    caption=f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                            f"🆔 #`{order_id}`\n📦 {order['product_name']}\n{note}\n\n"
                            f"{EMOJIS['sparkle']} Thank you!",
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    order["user_id"],
                    f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                    f"🆔 #`{order_id}`\n📦 {order['product_name']}\n{note}\n\n"
                    f"{EMOJIS['sparkle']} Thank you!",
                    parse_mode="Markdown"
                )
        except:
            pass
    
    await state.clear()

# ==================== ADMIN: BROADCAST ====================
@dp.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['message']} **Broadcast Message**\n\nSend the message to broadcast to all users:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.broadcasting_msg)

@dp.message(AdminStates.broadcasting_msg)
async def admin_broadcast_preview(message: Message, state: FSMContext):
    msg_text = message.text or message.caption or "📢 Broadcast"
    await state.update_data(broadcast_text=msg_text)
    
    users = db.get_all_users()
    total = len(users)
    active = sum(1 for u in users if not u["is_banned"])
    
    await message.answer(
        f"{EMOJIS['message']} **Broadcast Preview**\n\n"
        f"`{msg_text[:300]}`{'...' if len(msg_text) > 300 else ''}\n\n"
        f"👥 Total: `{total}`\n"
        f"📨 Will receive: `{active}`\n\n"
        f"Confirm broadcast?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['verified']} Send Broadcast!", callback_data="broadcast_confirm")],
            [InlineKeyboardButton(text=f"{EMOJIS['cross']} Cancel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.broadcasting_confirm)

@dp.callback_query(lambda c: c.data == "broadcast_confirm")
async def admin_broadcast_send(call: CallbackQuery, state: FSMContext, bot: Bot):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    state_data = await state.get_data()
    msg_text = state_data.get("broadcast_text", "📢")
    
    await call.message.edit_text(f"{EMOJIS['message']} Broadcasting...", parse_mode="Markdown")
    
    users = db.get_all_users()
    sent = 0
    failed = 0
    
    for user in users:
        if user["is_banned"]:
            continue
        try:
            await bot.send_message(user["user_id"], msg_text, parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.03)
        except:
            failed += 1
    
    await call.message.edit_text(
        f"{EMOJIS['verified']} **Broadcast Complete!**\n\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    await state.clear()

# ==================== ADMIN: VPN MANAGEMENT ====================
@dp.callback_query(lambda c: c.data == "admin_vpn")
async def admin_vpn_menu(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['vpn']} **VPN Config Management**",
        reply_markup=admin_vpn_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_vpn_orders")
async def admin_vpn_orders(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    orders = db.get_all_orders(status="delivered", limit=50)
    vpn_orders = [o for o in orders if "vpn" in o["category_name"].lower() or "vpn" in o["product_name"].lower()]
    
    if not vpn_orders:
        return await call.message.edit_text(
            f"{EMOJIS['info']} No VPN orders found.",
            reply_markup=admin_vpn_kb(),
            parse_mode="Markdown"
        )
    
    msg = f"{EMOJIS['list']} **VPN Orders ({len(vpn_orders)}):**\n\n"
    for o in vpn_orders[:20]:
        config = db.get_vpn_config(o["id"])
        has_config = "✅" if config else "❌"
        msg += f"`#{o['id']}` {has_config} 👤 `{o['user_id']}`\n"
        msg += f"   📦 {o['product_name'][:30]} — {o['user_input'][:20]}\n"
        msg += f"   💰 {format_price(o['amount'])} | 📅 {o['created_at'][:10]}\n\n"
    
    await call.message.edit_text(
        msg,
        reply_markup=admin_vpn_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_vpn_add")
async def admin_vpn_add_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['vpn']} **Add VPN Config**\n\nSend the Order ID:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.vpn_adding_config)

@dp.message(AdminStates.vpn_adding_config)
async def admin_vpn_order_proc(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
        order = db.get_order(order_id)
        if not order:
            return await message.answer(f"{EMOJIS['cross']} Order not found!")
        
        await state.update_data(vpn_order_id=order_id)
        await message.answer(
            f"📦 **Order #`{order_id}`**\n"
            f"Product: {order['product_name']}\n"
            f"User: `{order['user_id']}`\n\n"
            f"📋 Send the VPN config/key data:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")],
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.vpn_config_data)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid Order ID!")

@dp.message(AdminStates.vpn_config_data)
async def admin_vpn_data_proc(message: Message, state: FSMContext):
    config_data = message.text.strip()
    if not config_data or len(config_data) < 5:
        return await message.answer(f"{EMOJIS['cross']} Config too short!")
    
    await state.update_data(vpn_config_data=config_data)
    await message.answer(
        f"{EMOJIS['verified']} Config received!\n\nSend the server location (e.g., Singapore, USA, UK):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.vpn_config_expiry)

@dp.message(AdminStates.vpn_config_expiry)
async def admin_vpn_expiry_proc(message: Message, state: FSMContext, bot: Bot):
    server_location = message.text.strip()
    if not server_location:
        return await message.answer(f"{EMOJIS['cross']} Enter a valid location!")
    
    state_data = await state.get_data()
    order_id = state_data.get("vpn_order_id")
    config_data = state_data.get("vpn_config_data")
    order = db.get_order(order_id)
    
    if not order:
        return await message.answer(f"{EMOJIS['cross']} Order not found!")
    
    db.add_vpn_config(order_id, order["user_id"], "Manual Config",
                     config_data, server_location, 30)
    db.update_order_status(order_id, "delivered", note=f"VPN Config delivered. Server: {server_location}")
    
    await message.answer(
        f"{EMOJIS['verified']} **VPN Config Added!**\n\n"
        f"🆔 Order #`{order_id}`\n"
        f"👤 User: `{order['user_id']}`\n"
        f"🌍 Location: {server_location}",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    try:
        await bot.send_message(
            order["user_id"],
            f"{EMOJIS['vpn']} **VPN Config Ready!** 🌐\n\n"
            f"🌍 **Server:** {server_location}\n"
            f"📋 **Your Config:**\n`{config_data[:500]}`\n\n"
            f"📞 Need help? @{SUPPORT_USERNAME}",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await state.clear()

# ==================== ADMIN: STOCK MANAGEMENT ====================
@dp.callback_query(lambda c: c.data == "admin_stock")
async def admin_stock_menu(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['key']} **Stock Keys Management**\n\n"
        f"Manage auto-delivery stock for VPN/Proxy/VPS products.",
        reply_markup=admin_stock_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_stock_view")
async def admin_stock_view(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    stock = db.get_all_stock()
    if not stock:
        return await call.message.edit_text(
            f"{EMOJIS['info']} No stock found.\n\nUse 'Add Keys' to add stock.",
            reply_markup=admin_stock_kb(),
            parse_mode="Markdown"
        )
    
    # Group by category
    by_cat = {}
    for s in stock:
        cat = s["category"]
        if cat not in by_cat:
            by_cat[cat] = {"total": 0, "used": 0, "available": 0}
        by_cat[cat]["total"] += 1
        if s["is_used"]:
            by_cat[cat]["used"] += 1
        else:
            by_cat[cat]["available"] += 1
    
    msg = f"{EMOJIS['key']} **Stock Overview**\n\n"
    for cat, data in by_cat.items():
        emoji = {"key": "🔑", "proxy": "🌐", "vps": "🖥️"}.get(cat, "📦")
        msg += f"{emoji} **{cat.upper()}**\n"
        msg += f"   Total: {data['total']} | ✅ Available: {data['available']} | ❌ Used: {data['used']}\n\n"
    
    # Show recent 10
    msg += f"**Recent Keys:**\n"
    for s in stock[:10]:
        status = "✅" if s["is_used"] else "📦"
        msg += f"{status} `{s['key_data'][:40]}...` ({s['category']})\n"
    
    await call.message.edit_text(
        msg,
        reply_markup=admin_stock_kb(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_stock_add")
async def admin_stock_add_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    # Show available categories
    kb = InlineKeyboardBuilder()
    for cat_name, cat_info in STOCK_CATEGORIES.items():
        kb.row(make_btn(f"{cat_info['name']} ({cat_info['type']})", f"stock_cat_{cat_name}"))
    kb.row(make_btn(f"{EMOJIS['back']} Stock Menu", "admin_stock"))
    
    await call.message.edit_text(
        f"{EMOJIS['plus']} **Add Stock Keys**\n\nSelect the stock category:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.adding_stock_category)

@dp.callback_query(lambda c: c.data.startswith("stock_cat_"))
async def admin_stock_cat_select(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    cat_name = call.data.replace("stock_cat_", "")
    cat_info = STOCK_CATEGORIES.get(cat_name)
    if not cat_info:
        return await call.answer("Invalid category!", show_alert=True)
    
    await state.update_data(stock_category=cat_name, stock_cat_info=cat_info)
    
    await call.message.edit_text(
        f"{EMOJIS['pen']} **Add {cat_info['name']} Keys**\n\n"
        f"Send the keys (one per line):\n\n"
        f"Example:\n"
        f"`KEY-XXXX-XXXX-XXXX`\n"
        f"`KEY-YYYY-YYYY-YYYY`\n"
        f"`KEY-ZZZZ-ZZZZ-ZZZZ`\n\n"
        f"You can send multiple keys at once!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="admin_stock_add")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.adding_stock_keys)

@dp.message(AdminStates.adding_stock_keys)
async def admin_stock_keys_proc(message: Message, state: FSMContext):
    state_data = await state.get_data()
    cat_name = state_data.get("stock_category", "")
    cat_info = state_data.get("stock_cat_info", {})
    
    raw_keys = message.text.strip()
    keys_list = [k.strip() for k in raw_keys.split("\n") if k.strip()]
    
    if not keys_list:
        return await message.answer(f"{EMOJIS['cross']} No valid keys found!")
    
    added = db.add_stock_keys_bulk(cat_name, keys_list, 30)
    
    await message.answer(
        f"{EMOJIS['verified']} **Keys Added!**\n\n"
        f"📂 Category: **{cat_info.get('name', cat_name)}**\n"
        f"🔑 Keys added: **{added}**\n"
        f"✅ Total available: **{db.get_stock_count(cat_name)}**",
        reply_markup=admin_stock_kb(),
        parse_mode="Markdown"
    )
    await state.clear()

@dp.callback_query(lambda c: c.data == "admin_stock_delete")
async def admin_stock_delete_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    stock = db.get_all_stock()
    if not stock:
        return await call.message.edit_text(
            f"{EMOJIS['info']} No stock to delete.",
            reply_markup=admin_stock_kb(),
            parse_mode="Markdown"
        )
    
    kb = InlineKeyboardBuilder()
    for s in stock[:20]:
        status = "✅" if s["is_used"] else "📦"
        kb.row(make_btn(
            f"{status} #{s['id']} {s['key_data'][:25]}... ({s['category']})",
            f"stock_del_{s['id']}"
        ))
    kb.row(make_btn(f"{EMOJIS['back']} Stock Menu", "admin_stock"))
    
    await call.message.edit_text(
        f"{EMOJIS['trash']} **Delete Stock Key**\n\nSelect key to delete:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("stock_del_"))
async def admin_stock_delete_confirm(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    key_id = int(call.data.replace("stock_del_", ""))
    success = db.delete_stock_key(key_id)
    
    if success:
        await call.answer("Key deleted!", show_alert=True)
    else:
        await call.answer("Key not found!", show_alert=True)
    
    # Refresh
    stock = db.get_all_stock()
    kb = InlineKeyboardBuilder()
    for s in stock[:20]:
        status = "✅" if s["is_used"] else "📦"
        kb.row(make_btn(
            f"{status} #{s['id']} {s['key_data'][:25]}... ({s['category']})",
            f"stock_del_{s['id']}"
        ))
    kb.row(make_btn(f"{EMOJIS['back']} Stock Menu", "admin_stock"))
    
    await call.message.edit_text(
        f"{EMOJIS['trash']} **Delete Stock Key**\n\nSelect key to delete:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data == "admin_stock_status")
async def admin_stock_status(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    
    stock_counts = db.get_stock_count()
    msg = f"{EMOJIS['data']} **Stock Status**\n\n"
    if stock_counts:
        for s in stock_counts:
            emoji = {"key": "🔑", "proxy": "🌐", "vps": "🖥️"}.get(s["category"], "📦")
            cat_name = STOCK_CATEGORIES.get(s["category"], {}).get("name", s["category"].upper())
            msg += f"{emoji} **{cat_name}**: {s['cnt']} available\n"
    else:
        msg += "No stock available.\n"
    
    msg += f"\n{EMOJIS['info']} Add stock via Stock Management."
    
    await call.message.edit_text(
        msg,
        reply_markup=admin_vpn_kb(),
        parse_mode="Markdown"
    )

# ==================== ADMIN: BAN/UNBAN ====================
@dp.callback_query(lambda c: c.data == "admin_ban")
async def admin_ban_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['lock']} **Ban User**\n\nSend the User ID to ban:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.banning_user)

@dp.message(AdminStates.banning_user)
async def admin_ban_proc(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = int(message.text.strip())
        if user_id in ADMIN_IDS:
            return await message.answer(f"{EMOJIS['cross']} Cannot ban admin!")
        db.set_ban(user_id, True)
        await message.answer(
            f"{EMOJIS['lock']} **User Banned**\n\n👤 `{user_id}`",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        await state.clear()
        try:
            await bot.send_message(user_id, f"{EMOJIS['cross']} You have been banned from the bot.")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")

@dp.callback_query(lambda c: c.data == "admin_unban")
async def admin_unban_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['unlock']} **Unban User**\n\nSend the User ID to unban:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.unbanning_user)

@dp.message(AdminStates.unbanning_user)
async def admin_unban_proc(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = int(message.text.strip())
        db.set_ban(user_id, False)
        await message.answer(
            f"{EMOJIS['unlock']} **User Unbanned**\n\n👤 `{user_id}`",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        await state.clear()
        try:
            await bot.send_message(user_id, f"{EMOJIS['verified']} You have been unbanned!")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")

# ==================== ADMIN: RESTORE DB ====================
@dp.callback_query(lambda c: c.data == "admin_restore")
async def admin_restore_start(call: CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer("Unauthorized!", show_alert=True)
    await call.message.edit_text(
        f"{EMOJIS['warning']} **Restore Database**\n\n"
        f"Send a `.db` file to restore the database.\n\n"
        f"⚠️ This will REPLACE the current database!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")],
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.restoring_db)

@dp.message(AdminStates.restoring_db, F.document)
async def admin_restore_db_handler(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return
    document = message.document
    if not document.file_name.endswith('.db'):
        return await message.answer(f"{EMOJIS['cross']} Invalid file! Send a `.db` file.")
    
    await message.answer(f"{EMOJIS['clock']} Downloading and restoring database...")
    try:
        os.makedirs(os.path.dirname(db.db_path), exist_ok=True)
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, db.db_path)
        db._init_tables()
        await message.answer(
            f"{EMOJIS['verified']} **Database Restored Successfully!**",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"{EMOJIS['cross']} Error: {e}")
    await state.clear()


# ==================== CATCH ALL: UNKNOWN CALLBACKS ====================
@dp.callback_query()
async def catch_all_callbacks(call: CallbackQuery):
    """Catch all unhandled callbacks"""
    data = call.data
    
    # If it's a category callback that wasn't caught
    if data.startswith("cat_"):
        cat_id = data.replace("cat_", "")
        cat = get_category(cat_id)
        if cat:
            await select_category(call, None)
            return
    
    # If it's a product callback
    if data.startswith("prod_"):
        parts = data.replace("prod_", "").split("|")
        if len(parts) == 2:
            cat_id, prod_id = parts
            cat = get_category(cat_id)
            product = get_product(cat_id, prod_id)
            if cat and product:
                await select_product(call, None)
                return
    
    # Fallback
    await call.answer("Processing...", show_alert=False)


# ==================== MAIN FUNCTION ====================
async def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║         🚀 TOPUP STORE BD — BOT v3.0 FULL FIXED            ║
    ║                                                            ║
    ║   🤖 Bot: """ + BOT_USERNAME + f"""                               
    ║   👤 Admins: {len(ADMIN_IDS)} configured                             
    ║   📦 Products: {sum(len(c['products']) for c in get_categories())} items                 
    ║   📂 Categories: {len(get_categories())}                                 
    ║   🌐 VPN Plus — ExpressVPN | HMA | VPN IP | Vanish | ProtonVPN
    ║   🔑 Auto-Delivery Stock System Active                     
    ║   💾 Database: SQLite                                       
    ║   🎨 Style: Premium Colored Buttons                         
    ║   🟢 BOT IS RUNNING...                                      
    ║                                                            ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
