#!/usr/bin/env python3
"""
████████╗ ██████╗ ██████╗ ██╗   ██╗██████╗     ███████╗████████╗ ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔═══██╗██╔══██╗██║   ██║██╔══██╗    ██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝
   ██║   ██║   ██║██████╔╝██║   ██║██████╔╝    ███████╗   ██║   ██║   ██║██████╔╝█████╗  
   ██║   ██║   ██║██╔═══╝ ██║   ██║██╔══██╗    ╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝  
   ██║   ╚██████╔╝██║     ╚██████╔╝██║  ██║    ███████║   ██║   ╚██████╔╝██║  ██║███████╗
   ╚═╝    ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝
                                                                                          
   ╔══════════════════════════════════════════════════════════════════════════════════╗
   ║               🚀 TopUp Store BD — Premium Telegram Bot v2.1                      ║
   ║          🔥 Free Fire | PUBG | MLBB | Netflix | YouTube | Crunchyroll          ║
   ║                    🌐 NEW! VPN Plus | Premium IP Service                        ║
   ║                    ⚡ Instant AI Auto-Delivery System                            ║
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
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from pathlib import Path

# ==================== CORE IMPORTS ====================
try:
    from aiogram import Bot, Dispatcher, types, F
    from aiogram.filters import Command, CommandStart, CommandObject
    from aiogram.types import (
        Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
        ReplyKeyboardMarkup, KeyboardButton, FSInputFile, BufferedInputFile,
        ChatAdministratorRights
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
    pip install aiogram aiofiles
    
    📱 On Termux:
    pkg install python
    pip install aiogram aiofiles
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
BOT_NAME = "SKY STORE"
SUPPORT_USERNAME = "FBSKYSUPPORT"

# ==================== EMOJI & STYLE CONSTANTS ====================
EMOJIS = {
    "freefire": "🔥", "pubg": "🎯", "mlbb": "🐉", "netflix": "🎬",
    "youtube": "▶️", "crunchyroll": "🍿", "spotify": "🎵", "vpn": "🌐",
    "balance": "💰", "crown": "👑", "star": "⭐", "lightning": "⚡",
    "shield": "🛡️", "cart": "🛒", "wallet": "💳", "package": "📦",
    "clock": "⏰", "verified": "✅", "cross": "❌", "warning": "⚠️",
    "info": "ℹ️", "settings": "⚙️", "admin": "🔐", "users": "👥",
    "chart": "📊", "message": "📨", "back": "🔙", "next": "➡️",
    "previous": "⬅️", "home": "🏠", "search": "🔍", "bell": "🔔",
    "gift": "🎁", "fire": "🔥", "diamond": "💎", "trophy": "🏆",
    "medal": "🥇", "rocket": "🚀", "sparkle": "✨", "rainbow": "🌈",
    "heart": "❤️", "thumb": "👍", "clap": "👏", "wave": "👋",
    "globe": "🌍", "lock": "🔒", "unlock": "🔓", "key": "🔑",
    "money": "💵", "cash": "💸", "bank": "🏦", "card": "💳",
    "phone": "📱", "computer": "💻", "game": "🎮", "headphone": "🎧",
    "music": "🎶", "movie": "🎥", "tv": "📺", "book": "📚",
    "pen": "✏️", "clip": "📎", "file": "📄", "folder": "📁",
    "trash": "🗑️", "plus": "➕", "minus": "➖", "check": "✔️",
    "bullet": "▸", "arrow": "→", "divider": "━━━━━━━━━━━━━━━━━━━━━",
    "speed": "🚀", "server": "🖥️", "wifi": "📶", "config": "🔗",
    "data": "📊", "expire": "⏳", "list": "📋"
}

# ==================== PRODUCTS DATABASE ====================
PRODUCTS_CONFIG = {
    "categories": [
        {
            "id": "freefire",
            "name": "Free Fire Diamonds",
            "emoji": "🔥",
            "color": "danger",
            "description": "⚡ Best price in Bangladesh!\nInstant delivery via AI auto-system",
            "input_label": "🎮 Enter your Free Fire Player ID:",
            "input_placeholder": "Example: 1234567890",
            "products": [
                {"id": "ff_70", "name": "70  💎  Diamond", "price": 7,  "popular": False, "discount": 0},
                {"id": "ff_100", "name": "100 💎  Diamond", "price": 10, "popular": False, "discount": 0},
                {"id": "ff_115", "name": "115 💎  Diamond", "price": 12, "popular": True,  "discount": 5},
                {"id": "ff_140", "name": "140 💎  Diamond", "price": 14, "popular": False, "discount": 0},
                {"id": "ff_210", "name": "210 💎  Diamond", "price": 21, "popular": False, "discount": 0},
                {"id": "ff_240", "name": "240 💎  Diamond", "price": 24, "popular": True,  "discount": 10},
                {"id": "ff_355", "name": "355 💎  Diamond", "price": 35, "popular": False, "discount": 0},
                {"id": "ff_425", "name": "425 💎  Diamond", "price": 42, "popular": False, "discount": 0},
                {"id": "ff_505", "name": "505 💎  Diamond", "price": 49, "popular": True,  "discount": 15},
                {"id": "ff_610", "name": "610 💎  Diamond", "price": 59, "popular": False, "discount": 0},
                {"id": "ff_720", "name": "720 💎  Diamond", "price": 69, "popular": False, "discount": 0},
                {"id": "ff_860", "name": "860 💎  Diamond", "price": 79, "popular": False, "discount": 0},
                {"id": "ff_1000", "name": "1000 💎 Diamond", "price": 89, "popular": True,  "discount": 25},
                {"id": "ff_1090", "name": "1090 💎 Diamond", "price": 99, "popular": False, "discount": 0},
                {"id": "ff_1250", "name": "1250 💎 Diamond", "price": 119, "popular": False, "discount": 0},
                {"id": "ff_1600", "name": "1600 💎 Diamond", "price": 149, "popular": False, "discount": 0},
                {"id": "ff_2000", "name": "2000 💎 Diamond", "price": 179, "popular": False, "discount": 0},
                {"id": "ff_2180", "name": "2180 💎 Diamond", "price": 199, "popular": True,  "discount": 50},
                {"id": "ff_3000", "name": "3000 💎 Diamond", "price": 269, "popular": False, "discount": 0},
                {"id": "ff_4000", "name": "4000 💎 Diamond", "price": 349, "popular": False, "discount": 0},
                {"id": "ff_5000", "name": "5000 💎 Diamond", "price": 429, "popular": False, "discount": 0},
                {"id": "ff_5600", "name": "5600 💎 Diamond", "price": 499, "popular": True,  "discount": 100},
                {"id": "ff_10000", "name": "10000 💎 Diamond", "price": 849, "popular": False, "discount": 0},
                {"id": "ff_membership", "name": "👑 Weekly Membersip", "price": 25, "popular": True, "discount": 5},
                {"id": "ff_monthly", "name": "📅 Monthly Membersip", "price": 89, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "pubg",
            "name": "PUBG Mobile UC",
            "emoji": "🎯",
            "color": "success",
            "description": "🔫 Best UC price in BD!\nAll server supported (BGMI/PUBG)",
            "input_label": "🎮 Enter your PUBG Player ID:",
            "input_placeholder": "Example: 1234567890",
            "products": [
                {"id": "pubg_60", "name": "60 UC", "price": 15, "popular": False, "discount": 0},
                {"id": "pubg_180", "name": "180+10 UC", "price": 35, "popular": True, "discount": 5},
                {"id": "pubg_325", "name": "325+20 UC", "price": 59, "popular": False, "discount": 0},
                {"id": "pubg_385", "name": "385 UC", "price": 69, "popular": False, "discount": 0},
                {"id": "pubg_505", "name": "505 UC", "price": 89, "popular": False, "discount": 0},
                {"id": "pubg_660", "name": "660+35 UC", "price": 119, "popular": True, "discount": 10},
                {"id": "pubg_1100", "name": "1100 UC", "price": 179, "popular": False, "discount": 0},
                {"id": "pubg_1500", "name": "1500 UC", "price": 249, "popular": False, "discount": 0},
                {"id": "pubg_1800", "name": "1800+150 UC", "price": 299, "popular": True, "discount": 20},
                {"id": "pubg_3000", "name": "3000 UC", "price": 499, "popular": False, "discount": 0},
                {"id": "pubg_3850", "name": "3850 UC", "price": 599, "popular": False, "discount": 0},
                {"id": "pubg_6000", "name": "6000 UC", "price": 899, "popular": False, "discount": 0},
                {"id": "pubg_8100", "name": "8100 UC", "price": 1199, "popular": False, "discount": 0},
                {"id": "pubg_15000", "name": "15000 UC", "price": 2199, "popular": False, "discount": 0},
                {"id": "pubg_royal", "name": "👑 Royale Pass", "price": 29, "popular": True, "discount": 0},
            ]
        },
        {
            "id": "mlbb",
            "name": "MLBB Diamonds",
            "emoji": "🐉",
            "color": "danger",
            "description": "🐉 Mobile Legends: Bang Bang\nCheapest diamonds in BD!",
            "input_label": "🎮 Enter your MLBB Game ID:",
            "input_placeholder": "Example: 1234567890(1234)",
            "products": [
                {"id": "mlbb_100", "name": "100 💎 Diamond", "price": 18, "popular": False, "discount": 0},
                {"id": "mlbb_250", "name": "250 💎 Diamond", "price": 39, "popular": False, "discount": 0},
                {"id": "mlbb_500", "name": "500 💎 Diamond (Best Seller)", "price": 79, "popular": True, "discount": 5},
                {"id": "mlbb_750", "name": "750 💎 Diamond", "price": 119, "popular": False, "discount": 0},
                {"id": "mlbb_1000", "name": "1000 💎 Diamond", "price": 149, "popular": True, "discount": 10},
                {"id": "mlbb_1500", "name": "1500 💎 Diamond", "price": 219, "popular": False, "discount": 0},
                {"id": "mlbb_2000", "name": "2000 💎 Diamond", "price": 289, "popular": False, "discount": 0},
                {"id": "mlbb_3000", "name": "3000 💎 Diamond", "price": 419, "popular": False, "discount": 0},
                {"id": "mlbb_5000", "name": "5000 💎 Diamond", "price": 699, "popular": True, "discount": 50},
                {"id": "mlbb_weekly", "name": "📅 Weekly Diamond Pass", "price": 39, "popular": True, "discount": 0},
                {"id": "mlbb_starlight", "name": "🌟 Starlight Membersip", "price": 49, "popular": True, "discount": 0},
            ]
        },
        {
            "id": "netflix",
            "name": "Netflix Premium",
            "emoji": "🎬",
            "color": "danger",
            "description": "🎬 Watch anywhere, anytime!\nFull HD & 4K available",
            "input_label": "📧 Enter your Netflix email:",
            "input_placeholder": "your.email@gmail.com",
            "products": [
                {"id": "nflx_mobile", "name": "📱 Mobile 1 Month", "price": 149, "popular": False, "discount": 0},
                {"id": "nflx_basic", "name": "💻 Basic 1 Month", "price": 249, "popular": False, "discount": 0},
                {"id": "nflx_standard", "name": "📺 Standard 1 Month", "price": 349, "popular": True, "discount": 50},
                {"id": "nflx_premium", "name": "👑 Premium 1 Month", "price": 499, "popular": True, "discount": 100},
                {"id": "nflx_3m", "name": "Premium 3 Months (🔥Save 30%)", "price": 1299, "popular": False, "discount": 0},
                {"id": "nflx_6m", "name": "Premium 6 Months (🔥Save 50%)", "price": 2499, "popular": False, "discount": 0},
                {"id": "nflx_12m", "name": "Premium 12 Months (🔥Save 60%)", "price": 4599, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "youtube",
            "name": "YouTube Premium",
            "emoji": "▶️",
            "color": "danger",
            "description": "▶️ No ads! Background play!\nYouTube Music included",
            "input_label": "📧 Enter your Google email:",
            "input_placeholder": "your.email@gmail.com",
            "products": [
                {"id": "yt_1m", "name": "1 Month Individual", "price": 199, "popular": True, "discount": 0},
                {"id": "yt_3m", "name": "3 Months Individual (🔥Save 15%)", "price": 549, "popular": False, "discount": 0},
                {"id": "yt_6m", "name": "6 Months Individual (🔥Save 25%)", "price": 999, "popular": False, "discount": 0},
                {"id": "yt_12m", "name": "12 Months Individual (🔥Save 40%)", "price": 1799, "popular": False, "discount": 0},
                {"id": "yt_family_1m", "name": "👨‍👩‍👧‍👦 Family 1 Month", "price": 349, "popular": True, "discount": 0},
                {"id": "yt_student_1m", "name": "🎓 Student 1 Month", "price": 129, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "crunchyroll",
            "name": "Crunchyroll Premium",
            "emoji": "🍿",
            "color": "success",
            "description": "🍿 Watch anime ad-free!\nSimulcast & HD streaming",
            "input_label": "📧 Enter your Crunchyroll email:",
            "input_placeholder": "your.email@gmail.com",
            "products": [
                {"id": "cr_1m", "name": "1 Month Fan", "price": 249, "popular": False, "discount": 0},
                {"id": "cr_3m", "name": "3 Months Fan (🔥Save 20%)", "price": 649, "popular": False, "discount": 0},
                {"id": "cr_12m", "name": "12 Months Fan (🔥Save 40%)", "price": 1999, "popular": False, "discount": 0},
                {"id": "cr_mega_1m", "name": "👑 Mega Fan 1 Month", "price": 349, "popular": False, "discount": 0},
                {"id": "cr_mega_12m", "name": "👑 Mega Fan 12 Months", "price": 2999, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "spotify",
            "name": "Spotify Premium",
            "emoji": "🎵",
            "color": "success",
            "description": "🎵 Ad-free music streaming!\nOffline downloads & HQ audio",
            "input_label": "📧 Enter your Spotify email:",
            "input_placeholder": "your.email@gmail.com",
            "products": [
                {"id": "sp_1m", "name": "1 Month Individual", "price": 149, "popular": True, "discount": 0},
                {"id": "sp_3m", "name": "3 Months (🔥Save 10%)", "price": 399, "popular": False, "discount": 0},
                {"id": "sp_6m", "name": "6 Months (🔥Save 20%)", "price": 749, "popular": False, "discount": 0},
                {"id": "sp_12m", "name": "12 Months (🔥Save 30%)", "price": 1299, "popular": False, "discount": 0},
                {"id": "sp_duo_1m", "name": "👫 Duo 1 Month", "price": 249, "popular": False, "discount": 0},
                {"id": "sp_family_1m", "name": "👨‍👩‍👧‍👦 Family 1 Month", "price": 299, "popular": True, "discount": 50},
                {"id": "sp_student_1m", "name": "🎓 Student 1 Month", "price": 79, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "valo",
            "name": "Valorant VP",
            "emoji": "🎯",
            "color": "danger",
            "description": "🎯 Buy Valorant Points!\nCheapest rate for Bangladeshi players",
            "input_label": "🎮 Enter your Riot ID:",
            "input_placeholder": "PlayerName#1234",
            "products": [
                {"id": "valo_475", "name": "475 VP", "price": 299, "popular": False, "discount": 0},
                {"id": "valo_1000", "name": "1000 VP (Best Seller)", "price": 599, "popular": True, "discount": 50},
                {"id": "valo_2050", "name": "2050 VP", "price": 1199, "popular": False, "discount": 0},
                {"id": "valo_3650", "name": "3650 VP (🔥Save 20%)", "price": 1999, "popular": False, "discount": 0},
                {"id": "valo_5350", "name": "5350 VP (🔥Save 30%)", "price": 2899, "popular": False, "discount": 0},
                {"id": "valo_11000", "name": "11000 VP (🔥Save 40%)", "price": 5499, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "social",
            "name": "Social Media Services",
            "emoji": "📱",
            "color": "primary",
            "description": "📱 Social media marketing\nFollowers, likes, views & more!",
            "input_label": "🔗 Enter your profile link or ID:",
            "input_placeholder": "instagram.com/username",
            "products": [
                {"id": "soc_ig_100", "name": "📸 100 IG Followers", "price": 29, "popular": False, "discount": 0},
                {"id": "soc_ig_500", "name": "📸 500 IG Followers", "price": 99, "popular": True, "discount": 0},
                {"id": "soc_ig_1000", "name": "📸 1K IG Followers", "price": 179, "popular": False, "discount": 0},
                {"id": "soc_fb_500", "name": "👍 500 FB Page Likes", "price": 79, "popular": True, "discount": 0},
                {"id": "soc_fb_1000", "name": "👍 1K FB Page Likes", "price": 149, "popular": False, "discount": 0},
                {"id": "soc_tg_100", "name": "✈️ 100 TG Members", "price": 49, "popular": False, "discount": 0},
                {"id": "soc_tg_500", "name": "✈️ 500 TG Members", "price": 199, "popular": True, "discount": 0},
                {"id": "soc_tg_1000", "name": "✈️ 1K TG Members", "price": 349, "popular": False, "discount": 0},
                {"id": "soc_tiktok_200", "name": "🎵 200 TikTok Followers", "price": 49, "popular": False, "discount": 0},
                {"id": "soc_tiktok_1000", "name": "🎵 1K TikTok Followers", "price": 199, "popular": True, "discount": 0},
                {"id": "soc_yt_100", "name": "▶️ 100 YT Subscribers", "price": 59, "popular": False, "discount": 0},
                {"id": "soc_yt_500", "name": "▶️ 500 YT Subscribers", "price": 249, "popular": False, "discount": 0},
                {"id": "soc_yt_1000", "name": "▶️ 1K YT Subscribers", "price": 449, "popular": True, "discount": 0},
            ]
        },
        {
            "id": "giftcard",
            "name": "🎁 Gift Cards & Vouchers",
            "emoji": "🎁",
            "color": "primary",
            "description": "🎁 Gift cards for all platforms!\nGoogle Play, Steam, PSN & more",
            "input_label": "📧 Enter your email to receive code:",
            "input_placeholder": "your.email@gmail.com",
            "products": [
                {"id": "gc_google_50", "name": "🅿️ Google Play $5", "price": 499, "popular": False, "discount": 0},
                {"id": "gc_google_100", "name": "🅿️ Google Play $10", "price": 949, "popular": True, "discount": 0},
                {"id": "gc_google_200", "name": "🅿️ Google Play $20", "price": 1899, "popular": False, "discount": 0},
                {"id": "gc_steam_5", "name": "🎮 Steam $5", "price": 549, "popular": False, "discount": 0},
                {"id": "gc_steam_10", "name": "🎮 Steam $10", "price": 999, "popular": True, "discount": 0},
                {"id": "gc_steam_20", "name": "🎮 Steam $20", "price": 1949, "popular": False, "discount": 0},
                {"id": "gc_psn_10", "name": "🎮 PSN $10", "price": 1099, "popular": False, "discount": 0},
                {"id": "gc_psn_20", "name": "🎮 PSN $20", "price": 2099, "popular": True, "discount": 0},
                {"id": "gc_xbox_10", "name": "🎮 Xbox $10", "price": 1049, "popular": False, "discount": 0},
                {"id": "gc_xbox_20", "name": "🎮 Xbox $20", "price": 1999, "popular": False, "discount": 0},
                {"id": "gc_apple_10", "name": "🍎 Apple $10", "price": 999, "popular": True, "discount": 0},
                {"id": "gc_apple_25", "name": "🍎 Apple $25", "price": 2399, "popular": False, "discount": 0},
                {"id": "gc_netflix_10", "name": "🎬 Netflix $10", "price": 949, "popular": False, "discount": 0},
                {"id": "gc_spotify_10", "name": "🎵 Spotify $10", "price": 899, "popular": False, "discount": 0},
            ]
        },
        # ==================== 🌐 VPN Plus CATEGORY ====================
        {
            "id": "vpn",
            "name": "VPN Plus — Premium IP",
            "emoji": "🌐",
            "color": "success",
            "description": (
                "🌐 **Premium VPN & IP Service**\n"
                "🔒 Secure, Fast & Anonymous\n"
                "📶 Unlimited Bandwidth\n"
                "🖥️ Dedicated IP Available\n"
                "🚀 1Gbps Speed Servers\n"
                "📱 All Devices Supported"
            ),
            "input_label": "📱 Send your device type & desired location:",
            "input_placeholder": "Example: Android, Singapore",
            "products": [
                {"id": "vpn_1m_basic", "name": "🌐 VPN Basic — 1 Month", "price": 149, "popular": True, "discount": 0},
                {"id": "vpn_3m_basic", "name": "🌐 VPN Basic — 3 Months (🔥Save 15%)", "price": 379, "popular": False, "discount": 0},
                {"id": "vpn_6m_basic", "name": "🌐 VPN Basic — 6 Months (🔥Save 25%)", "price": 649, "popular": False, "discount": 0},
                {"id": "vpn_12m_basic", "name": "🌐 VPN Basic — 12 Months (🔥Save 40%)", "price": 999, "popular": True, "discount": 0},
                {"id": "vpn_1m_premium", "name": "👑 VPN Premium — 1 Month", "price": 299, "popular": True, "discount": 0},
                {"id": "vpn_3m_premium", "name": "👑 VPN Premium — 3 Months (🔥Save 20%)", "price": 719, "popular": False, "discount": 0},
                {"id": "vpn_6m_premium", "name": "👑 VPN Premium — 6 Months (🔥Save 35%)", "price": 1199, "popular": False, "discount": 0},
                {"id": "vpn_12m_premium", "name": "👑 VPN Premium — 12 Months (🔥Save 50%)", "price": 1799, "popular": True, "discount": 0},
                {"id": "vpn_1m_dedip", "name": "🛡️ Dedicated IP — 1 Month", "price": 499, "popular": False, "discount": 0},
                {"id": "vpn_3m_dedip", "name": "🛡️ Dedicated IP — 3 Months (🔥Save 20%)", "price": 1199, "popular": False, "discount": 0},
                {"id": "vpn_6m_dedip", "name": "🛡️ Dedicated IP — 6 Months (🔥Save 30%)", "price": 2099, "popular": True, "discount": 0},
                {"id": "vpn_12m_dedip", "name": "🛡️ Dedicated IP — 12 Months (🔥Save 45%)", "price": 3299, "popular": False, "discount": 0},
                {"id": "vpn_1m_stream", "name": "🎬 Streaming VPN — 1 Month", "price": 399, "popular": True, "discount": 0},
                {"id": "vpn_1m_usa", "name": "🇺🇸 USA IP — 1 Month", "price": 349, "popular": False, "discount": 0},
                {"id": "vpn_1m_uk", "name": "🇬🇧 UK IP — 1 Month", "price": 349, "popular": False, "discount": 0},
                {"id": "vpn_1m_singapore", "name": "🇸🇬 Singapore IP — 1 Month", "price": 299, "popular": True, "discount": 0},
                {"id": "vpn_5dev", "name": "📱 5 Devices — 1 Month", "price": 599, "popular": False, "discount": 0},
                {"id": "vpn_unlimited_dev", "name": "📱 Unlimited Devices — 1 Month", "price": 999, "popular": False, "discount": 0},
                {"id": "vpn_trial", "name": "🧪 VPN Trial — 3 Days", "price": 29, "popular": True, "discount": 0},
                {"id": "vpn_trial_7", "name": "🧪 VPN Trial — 7 Days", "price": 49, "popular": False, "discount": 0},
            ]
        },
        {
            "id": "topup",
            "name": "💰 Wallet Top-Up",
            "emoji": "💰",
            "color": "success",
            "description": "💰 Add balance to your wallet\nInstant auto-credit system!",
            "input_label": "Amount will be auto-added",
            "input_placeholder": "",
            "products": [
                {"id": "bal_50", "name": "➕ 50 ৳ Add Balance", "price": 50, "popular": False, "discount": 0},
                {"id": "bal_100", "name": "➕ 100 ৳ Add Balance", "price": 100, "popular": False, "discount": 0},
                {"id": "bal_200", "name": "➕ 200 ৳ Add Balance", "price": 200, "popular": True, "discount": 0},
                {"id": "bal_500", "name": "➕ 500 ৳ Add Balance (🔥Free 25)", "price": 500, "popular": True, "discount": 25},
                {"id": "bal_1000", "name": "➕ 1000 ৳ Add Balance (🔥Free 75)", "price": 1000, "popular": False, "discount": 75},
                {"id": "bal_2000", "name": "➕ 2000 ৳ Add Balance (🔥Free 200)", "price": 2000, "popular": False, "discount": 200},
                {"id": "bal_5000", "name": "➕ 5000 ৳ Add Balance (🔥Free 750)", "price": 5000, "popular": False, "discount": 750},
            ]
        }
    ]
}

# ==================== DATABASE MANAGER ====================
class Database:
    def __init__(self, db_path: str = "data/topup_bot.db"):
        self.db_path = db_path
        Path("data").mkdir(exist_ok=True)
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY, username TEXT DEFAULT '', first_name TEXT DEFAULT '',
                balance REAL DEFAULT 0.0, total_spent REAL DEFAULT 0.0, total_orders INTEGER DEFAULT 0,
                join_date TEXT DEFAULT '', last_active TEXT DEFAULT '', is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0, referral_code TEXT DEFAULT '', referred_by INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                product_name TEXT DEFAULT '', category_name TEXT DEFAULT '', amount REAL DEFAULT 0.0,
                quantity INTEGER DEFAULT 1, user_input TEXT DEFAULT '', payment_method TEXT DEFAULT '',
                transaction_id TEXT DEFAULT '', status TEXT DEFAULT 'pending', order_date TEXT DEFAULT '',
                delivered_date TEXT DEFAULT '', delivery_file_id TEXT DEFAULT '', delivery_note TEXT DEFAULT '',
                admin_id INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, amount REAL DEFAULT 0.0,
                type TEXT DEFAULT '', method TEXT DEFAULT '', transaction_id TEXT DEFAULT '',
                status TEXT DEFAULT 'completed', note TEXT DEFAULT '', date TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL, reward_amount REAL DEFAULT 0.0, date TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT DEFAULT '',
                sent_count INTEGER DEFAULT 0, failed_count INTEGER DEFAULT 0, date TEXT DEFAULT '')""")
        c.execute("""CREATE TABLE IF NOT EXISTS vpn_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                config_type TEXT DEFAULT '', config_data TEXT DEFAULT '', server_location TEXT DEFAULT '',
                expiry_date TEXT DEFAULT '', status TEXT DEFAULT 'active', created_date TEXT DEFAULT '')""")
        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: str = "", first_name: str = ""):
        conn = self._get_conn()
        conn.execute("INSERT OR IGNORE INTO users (user_id, username, first_name, join_date, last_active) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, first_name, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_user(self, user_id: int):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user

    def update_user_activity(self, user_id: int):
        conn = self._get_conn()
        conn.execute("UPDATE users SET last_active = ? WHERE user_id = ?", (datetime.now().isoformat(), user_id))
        conn.commit()
        conn.close()

    def update_balance(self, user_id: int, amount: float):
        conn = self._get_conn()
        conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()

    def set_ban(self, user_id: int, ban: bool = True):
        conn = self._get_conn()
        conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if ban else 0, user_id))
        conn.commit()
        conn.close()

    def get_all_users(self):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM users ORDER BY join_date DESC")
        users = c.fetchall()
        conn.close()
        return users

    def add_order(self, user_id: int, product_name: str, category_name: str, amount: float, quantity: int, user_input: str, payment_method: str, transaction_id: str) -> int:
        conn = self._get_conn()
        c = conn.execute("INSERT INTO orders (user_id, product_name, category_name, amount, quantity, user_input, payment_method, transaction_id, order_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (user_id, product_name, category_name, amount, quantity, user_input, payment_method, transaction_id, datetime.now().isoformat()))
        order_id = c.lastrowid
        conn.execute("UPDATE users SET total_orders = total_orders + 1, total_spent = total_spent + ? WHERE user_id = ?", (amount, user_id))
        conn.commit()
        conn.close()
        return order_id

    def get_order(self, order_id: int):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order = c.fetchone()
        conn.close()
        return order

    def get_user_orders(self, user_id: int, limit: int = 20):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY order_date DESC LIMIT ?", (user_id, limit))
        orders = c.fetchall()
        conn.close()
        return orders

    def get_all_orders(self, status=None, limit=50):
        conn = self._get_conn()
        if status:
            c = conn.execute("SELECT * FROM orders WHERE status = ? ORDER BY order_date DESC LIMIT ?", (status, limit))
        else:
            c = conn.execute("SELECT * FROM orders ORDER BY order_date DESC LIMIT ?", (limit,))
        orders = c.fetchall()
        conn.close()
        return orders

    def update_order_status(self, order_id: int, status: str, file_id: str = "", note: str = ""):
        conn = self._get_conn()
        if status == "delivered":
            conn.execute("UPDATE orders SET status = ?, delivery_file_id = ?, delivery_note = ?, delivered_date = ? WHERE order_id = ?",
                        (status, file_id, note, datetime.now().isoformat(), order_id))
        else:
            conn.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
        conn.commit()
        conn.close()

    def add_vpn_config(self, order_id: int, user_id: int, config_type: str, config_data: str, server_location: str, expiry_days: int):
        conn = self._get_conn()
        expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        conn.execute("INSERT INTO vpn_configs (order_id, user_id, config_type, config_data, server_location, expiry_date, created_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (order_id, user_id, config_type, config_data, server_location, expiry, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_user_vpn_configs(self, user_id: int):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM vpn_configs WHERE user_id = ? AND status = 'active' ORDER BY created_date DESC", (user_id,))
        configs = c.fetchall()
        conn.close()
        return configs

    def get_vpn_config(self, config_id: int):
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM vpn_configs WHERE id = ?", (config_id,))
        config = c.fetchone()
        conn.close()
        return config

    def revoke_vpn_config(self, config_id: int):
        conn = self._get_conn()
        conn.execute("UPDATE vpn_configs SET status = 'revoked' WHERE id = ?", (config_id,))
        conn.commit()
        conn.close()

    def add_transaction(self, user_id: int, amount: float, type_: str, method: str, trx_id: str, note: str = ""):
        conn = self._get_conn()
        conn.execute("INSERT INTO transactions (user_id, amount, type, method, transaction_id, note, date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, amount, type_, method, trx_id, note, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = self._get_conn()
        stats = {}
        c = conn.execute("SELECT COUNT(*) as count, COALESCE(SUM(balance),0) as total FROM users")
        row = c.fetchone()
        stats['total_users'] = row[0]
        stats['total_wallet'] = row[1]
        c = conn.execute("SELECT COUNT(*) as count, COALESCE(SUM(amount),0) as total FROM orders")
        row = c.fetchone()
        stats['total_orders'] = row[0]
        stats['total_revenue'] = row[1]
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
        stats['pending_orders'] = c.fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='delivered'")
        stats['delivered_orders'] = c.fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='processing'")
        stats['processing_orders'] = c.fetchone()[0]
        c = conn.execute("SELECT COUNT(*) FROM vpn_configs WHERE status='active'")
        stats['active_vpn'] = c.fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        c = conn.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders WHERE order_date LIKE ?", (f"{today}%",))
        row = c.fetchone()
        stats['today_orders'] = row[0]
        stats['today_revenue'] = row[1]
        conn.close()
        return stats


# ==================== INITIALIZATION ====================
db = Database()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ==================== FSM STATES ====================
class OrderStates(StatesGroup):
    selecting_category = State()
    selecting_product = State()
    entering_input = State()
    selecting_payment = State()
    entering_trx_id = State()
    confirming = State()

class AdminStates(StatesGroup):
    main_menu = State()
    adding_balance_user = State()
    adding_balance_amount = State()
    delivering_order = State()
    delivering_file = State()
    broadcasting_msg = State()
    broadcasting_confirm = State()
    editing_product_cat = State()
    editing_product = State()
    editing_product_name = State()
    editing_product_price = State()
    banning_user = State()
    unbanning_user = State()
    restoring_db = State()
    vpn_adding_config = State()
    vpn_config_data = State()
    vpn_config_expiry = State()


# ==================== HELPER FUNCTIONS ====================
def get_categories():
    return PRODUCTS_CONFIG["categories"]

def get_category(cat_id: str):
    for cat in get_categories():
        if cat["id"] == cat_id:
            return cat
    return None

def get_product(cat_id: str, prod_id: str):
    cat = get_category(cat_id)
    if not cat:
        return None
    for prod in cat["products"]:
        if prod["id"] == prod_id:
            return {**prod, "category": cat}
    return None

def format_price(price: float) -> str:
    return f"৳{price:,.0f}"

def get_status_emoji(status: str) -> str:
    emojis = {"pending": "⏳", "processing": "🔄", "delivered": "✅", "cancelled": "❌", "refunded": "💰", "completed": "✅"}
    return emojis.get(status, "❓")

def generate_vpn_config(order_id: int, user_id: int, config_type: str, location: str) -> str:
    unique_seed = hashlib.sha256(f"{order_id}-{user_id}-{datetime.now().timestamp()}".encode()).hexdigest()
    private_key = f"wP{unique_seed[:42]}="
    public_key = f"bP{unique_seed[44:86]}="
    preshared_key = f"kP{unique_seed[88:130]}="
    endpoints = {"singapore": "sg1.vpn-topup-bd.com:51820", "usa": "us1.vpn-topup-bd.com:51820", "uk": "uk1.vpn-topup-bd.com:51820", "india": "in1.vpn-topup-bd.com:51820", "germany": "de1.vpn-topup-bd.com:51820", "default": "vpn-topup-bd.com:51820"}
    endpoint = endpoints.get(location.lower(), endpoints["default"])
    config = f"""[Interface]
PrivateKey = {private_key}
Address = 10.0.0.{order_id % 255}/24
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {public_key}
PresharedKey = {preshared_key}
Endpoint = {endpoint}
AllowedIPs = 0.0.0.0/0, ::/0
PersistentKeepalive = 25
"""
    return config

def get_vpn_expiry_days(product_name: str) -> int:
    if "12 Month" in product_name:
        return 365
    elif "6 Month" in product_name:
        return 180
    elif "3 Month" in product_name:
        return 90
    elif "7 Day" in product_name:
        return 7
    elif "3 Day" in product_name:
        return 3
    return 30


# ==================== KEYBOARD BUILDERS ====================
def main_menu_kb(user_id: int = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    is_admin = user_id in ADMIN_IDS if user_id else False
    builder.button(text=f"{EMOJIS['cart']} Buy TopUp", callback_data="categories")
    builder.button(text=f"{EMOJIS['wallet']} My Wallet", callback_data="my_wallet")
    builder.button(text=f"{EMOJIS['package']} My Orders", callback_data="my_orders")
    builder.button(text=f"{EMOJIS['gift']} Promotions", callback_data="promotions")
    builder.button(text=f"{EMOJIS['phone']} Support", callback_data="support")
    builder.button(text=f"{EMOJIS['star']} Rate Us", callback_data="rate")
    if is_admin:
        builder.button(text=f"{EMOJIS['admin']} Admin Panel", callback_data="admin_menu")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def categories_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in get_categories():
        if cat["id"] == "topup":
            continue
        builder.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"cat_{cat['id']}")
    builder.button(text=f"{EMOJIS['wallet']} {EMOJIS['plus']} Wallet Top-Up", callback_data="cat_topup")
    builder.button(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")
    builder.adjust(2, 2, 2, 2, 1)
    return builder.as_markup()

def products_kb(cat_id: str, page: int = 0) -> InlineKeyboardMarkup:
    cat = get_category(cat_id)
    if not cat:
        return main_menu_kb()
    builder = InlineKeyboardBuilder()
    products = cat["products"]
    per_page = 8
    total_pages = max(1, (len(products) + per_page - 1) // per_page)
    page = min(page, total_pages - 1)
    start = page * per_page
    end = start + per_page
    for prod in products[start:end]:
        price_text = format_price(prod["price"])
        if prod.get("discount", 0) > 0:
            price_text += f" 🔥-{format_price(prod['discount'])}"
        name = prod["name"]
        if prod.get("popular"):
            name = f"{EMOJIS['fire']} {name}"
        builder.button(text=f"{name} — {price_text}", callback_data=f"prod_{cat_id}_{prod['id']}")
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=f"{EMOJIS['previous']} Page {page}", callback_data=f"page_{cat_id}_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text=f"Page {page+2} {EMOJIS['next']}", callback_data=f"page_{cat_id}_{page+1}"))
    builder.row(*nav_buttons)
    builder.button(text=f"{EMOJIS['back']} Back to Categories", callback_data="categories")
    builder.button(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")
    builder.adjust(1, len(nav_buttons), 1)
    return builder.as_markup()

def payment_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=f"{EMOJIS['bank']} bKash", callback_data="pay_bkash")
    builder.button(text=f"{EMOJIS['bank']} Nagad", callback_data="pay_nagad")
    builder.button(text=f"{EMOJIS['rocket']} Rocket", callback_data="pay_rocket")
    builder.button(text=f"{EMOJIS['card']} UPI", callback_data="pay_upi")
    builder.button(text=f"{EMOJIS['wallet']} Wallet Balance", callback_data="pay_wallet")
    builder.button(text=f"{EMOJIS['back']} Change Product", callback_data="prod_back")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    stats = db.get_stats()
    builder.button(text=f"{EMOJIS['chart']} Dashboard", callback_data="admin_dashboard")
    builder.button(text=f"{EMOJIS['package']} Orders ({stats['total_orders']})", callback_data="admin_orders")
    builder.button(text=f"{EMOJIS['clock']} Pending ({stats['pending_orders']})", callback_data="admin_pending")
    builder.button(text=f"{EMOJIS['money']} Add Balance", callback_data="admin_add_balance")
    builder.button(text=f"{EMOJIS['rocket']} Deliver Order", callback_data="admin_deliver")
    builder.button(text=f"{EMOJIS['pen']} Edit Products", callback_data="admin_edit_products")
    builder.button(text=f"{EMOJIS['message']} Broadcast", callback_data="admin_broadcast")
    builder.button(text=f"{EMOJIS['users']} Users ({stats['total_users']})", callback_data="admin_users")
    builder.button(text=f"{EMOJIS['file']} Backup DB", callback_data="admin_backup")
    builder.button(text=f"{EMOJIS['folder']} Restore DB", callback_data="admin_restore")
    builder.button(text=f"{EMOJIS['chart']} Full Stats", callback_data="admin_stats")
    builder.button(text=f"{EMOJIS['vpn']} VPN Configs ({stats.get('active_vpn', 0)})", callback_data="admin_vpn")
    builder.button(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")
    builder.adjust(2, 2, 2, 2, 2, 2, 1)
    return builder.as_markup()


# ==================== START HANDLER ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    db.add_user(user.id, user.username or "", user.first_name or "")
    db.update_user_activity(user.id)
    welcome_text = (
        f"{EMOJIS['sparkle']}{EMOJIS['sparkle']}{EMOJIS['sparkle']}"
        f" **WELCOME TO TOPUP STORE BD!** "
        f"{EMOJIS['sparkle']}{EMOJIS['sparkle']}{EMOJIS['sparkle']}\n\n"
        f"{EMOJIS['wave']} Hello, **{user.first_name}**! Welcome to Bangladesh's #1\n"
        f"premium game top-up & digital services store.\n\n"
        f"{EMOJIS['rocket']} **What we offer:**\n"
        f"{EMOJIS['bullet']} {EMOJIS['freefire']} Free Fire Diamonds\n"
        f"{EMOJIS['bullet']} {EMOJIS['pubg']} PUBG Mobile UC\n"
        f"{EMOJIS['bullet']} {EMOJIS['mlbb']} MLBB Diamonds\n"
        f"{EMOJIS['bullet']} {EMOJIS['netflix']} Netflix, YouTube Premium, Crunchyroll\n"
        f"{EMOJIS['bullet']} {EMOJIS['gift']} Gift Cards & Social Media Services\n"
        f"{EMOJIS['bullet']} {EMOJIS['vpn']} **NEW! VPN Plus — Premium IP Service**\n\n"
        f"{EMOJIS['lightning']} **Key Features:**\n"
        f"{EMOJIS['bullet']} {EMOJIS['rocket']} **Instant AI Auto-Delivery**\n"
        f"{EMOJIS['bullet']} {EMOJIS['shield']} **100% Secure & Trusted**\n"
        f"{EMOJIS['bullet']} {EMOJIS['money']} **Best Prices in Bangladesh**\n"
        f"{EMOJIS['bullet']} {EMOJIS['phone']} **24/7 Customer Support**\n\n"
        f"{EMOJIS['arrow']} Use the buttons below to get started!"
    )
    await message.answer(text=welcome_text, reply_markup=main_menu_kb(user.id), parse_mode="Markdown")

@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer(f"{EMOJIS['cross']} Unauthorized access!")
    await message.answer(f"{EMOJIS['admin']} **Admin Panel**\n\nWelcome to the admin control center.\nManage orders, users, products, VPN configs & broadcast.",
                        reply_markup=admin_kb(), parse_mode="Markdown")


# ==================== CALLBACK QUERY HANDLER ====================
@dp.callback_query()
async def callback_handler(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = call.data
    user_id = call.from_user.id
    db.update_user_activity(user_id)
    user = db.get_user(user_id)
    if user and user["is_banned"] and user_id not in ADMIN_IDS:
        return await call.answer(f"{EMOJIS['cross']} You are banned!", show_alert=True)

    # ----- MAIN MENU -----
    if data == "main_menu":
        await state.clear()
        await call.message.edit_text(f"{EMOJIS['home']} **Main Menu**\n\nChoose an option:", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")
        return await call.answer()

    # ----- CATEGORIES -----
    if data == "categories":
        await state.clear()
        await call.message.edit_text(f"{EMOJIS['cart']} **Select Category**\n\nChoose what you want to purchase:", reply_markup=categories_kb(), parse_mode="Markdown")
        return await call.answer()

    # ----- CATEGORY SELECTED -----
    if data.startswith("cat_"):
        cat_id = data[4:]
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Category not found!", show_alert=True)
        await state.update_data(category=cat)
        desc_text = f"\n\n{cat['description']}\n" if cat.get("description") else ""
        await call.message.edit_text(f"{cat['emoji']} **{cat['name']}**{desc_text}\n\nSelect your package below:", reply_markup=products_kb(cat_id), parse_mode="Markdown")
        return await call.answer()

    # ----- PAGINATION -----
    if data.startswith("page_"):
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2])
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Error!", show_alert=True)
        await call.message.edit_text(f"{cat['emoji']} **{cat['name']}**\n\nSelect your package below:", reply_markup=products_kb(cat_id, page), parse_mode="Markdown")
        return await call.answer()

    # ----- PRODUCT SELECTED -----
    if data.startswith("prod_"):
        parts = data.split("_")
        cat_id = parts[1]
        prod_id = "_".join(parts[2:])
        product = get_product(cat_id, prod_id)
        if not product:
            return await call.answer(f"{EMOJIS['cross']} Product not found!", show_alert=True)
        cat = product["category"]

        # Wallet Top-Up direct payment
        if cat_id == "topup":
            await state.update_data(product=product, category=cat)
            await call.message.edit_text(f"{EMOJIS['wallet']} **{product['name']}**\n\nPrice: {format_price(product['price'])}\nBonus: +{format_price(product.get('discount', 0))} Free\n\nSelect payment method:", reply_markup=payment_kb(), parse_mode="Markdown")
            await state.set_state(OrderStates.selecting_payment)
            return await call.answer()

        await state.update_data(product=product, category=cat)
        discount_text = ""
        if product.get("discount", 0) > 0:
            discount_text = f"\n{EMOJIS['fire']} **Discount:** -{format_price(product['discount'])}"
        popular_text = ""
        if product.get("popular"):
            popular_text = f"\n{EMOJIS['fire']} **Popular Choice!**"
        await call.message.edit_text(f"{cat['emoji']} **{product['name']}**\n\n{EMOJIS['money']} Price: **{format_price(product['price'])}**{discount_text}{popular_text}\n\n{EMOJIS['info']} **{cat.get('input_label', 'Enter your details:')}**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Back to Products", callback_data=f"cat_{cat_id}")]]), parse_mode="Markdown")
        await state.set_state(OrderStates.entering_input)
        return await call.answer()

    # ----- PRODUCT BACK -----
    if data == "prod_back":
        state_data = await state.get_data()
        cat = state_data.get("category", {})
        if isinstance(cat, dict):
            cat_id = cat.get("id", "freefire")
        else:
            cat_id = "freefire"
        await call.message.edit_text("Select your package below:", reply_markup=products_kb(cat_id), parse_mode="Markdown")
        await state.set_state(OrderStates.selecting_product)
        return await call.answer()

    # ----- PAYMENT METHOD -----
    if data.startswith("pay_"):
        method = data[4:]
        state_data = await state.get_data()
        product = state_data.get("product", {})
        method_names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket", "upi": "UPI", "wallet": "Wallet Balance"}
        method_numbers = {"bkash": BKASH_NUMBER, "nagad": NAGAD_NUMBER, "rocket": ROCKET_NUMBER, "upi": UPI_ID}
        await state.update_data(payment_method=method)

        if method == "wallet":
            user_bal = db.get_user(user_id)
            price = product.get("price", 0)
            if not user_bal or user_bal["balance"] < price:
                return await call.answer(f"{EMOJIS['cross']} Insufficient balance!\nNeed: {format_price(price)}\nHave: {format_price(user_bal['balance'] if user_bal else 0)}", show_alert=True)
            return await process_wallet_payment(call, state, bot)
        else:
            price = product.get("price", 0)
            number = method_numbers.get(method, "Contact admin")
            await call.message.edit_text(f"{EMOJIS['money']} **Payment Instructions**\n\nProduct: **{product.get('name', 'N/A')}**\nAmount: **{format_price(price)}**\nMethod: **{method_names.get(method, method)}**\n\n{EMOJIS['phone']} Send to:\n`{number}`\n\n{EMOJIS['info']} After sending payment, enter your **Transaction ID (TrxID)** below:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Change Method", callback_data="prod_back")]]), parse_mode="Markdown")
            await state.set_state(OrderStates.entering_trx_id)
            return await call.answer()

    # ----- MY WALLET -----
    if data == "my_wallet":
        user_w = db.get_user(user_id)
        if not user_w:
            return await call.answer(f"{EMOJIS['cross']} User not found!")
        vpn_configs = db.get_user_vpn_configs(user_id)
        vpn_text = f"\n{EMOJIS['vpn']} Active VPN Configs: **{len(vpn_configs)}**\n" if vpn_configs else ""
        await call.message.edit_text(f"{EMOJIS['wallet']} **My Wallet**\n\nBalance: **{format_price(user_w['balance'])}**\nTotal Spent: **{format_price(user_w['total_spent'])}**\nTotal Orders: **{user_w['total_orders']}**{vpn_text}\n\n{EMOJIS['arrow']} Use Wallet Top-Up to add balance!\n{EMOJIS['arrow']} Pay with wallet for instant delivery!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['wallet']} {EMOJIS['plus']} Top-Up Wallet", callback_data="cat_topup")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    # ----- MY ORDERS -----
    if data == "my_orders":
        orders = db.get_user_orders(user_id)
        if not orders:
            await call.message.edit_text(f"{EMOJIS['package']} **My Orders**\n\nYou haven't placed any orders yet!\n\n{EMOJIS['arrow']} Start shopping from Categories!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['cart']} Browse Categories", callback_data="categories")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
            return await call.answer()
        order_text = f"{EMOJIS['package']} **My Orders**\n\n"
        for o in orders[:8]:
            order_text += f"`#{o['order_id']}` {get_status_emoji(o['status'])} {o['product_name'][:25]}\n   {format_price(o['amount'])} — {o['status'].upper()}\n\n"
        if len(orders) > 8:
            order_text += f"\n... and {len(orders)-8} more orders"
        await call.message.edit_text(order_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    # ----- MY VPN -----
    if data == "my_vpn":
        vpn_configs = db.get_user_vpn_configs(user_id)
        if not vpn_configs:
            await call.message.edit_text(f"{EMOJIS['vpn']} **My VPN Configs**\n\nYou don't have any active VPN configurations.\n\n{EMOJIS['arrow']} Buy a VPN plan from Categories!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['cart']} Browse VPN Plans", callback_data="cat_vpn")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
            return await call.answer()
        text = f"{EMOJIS['vpn']} **My Active VPN Configs**\n\n"
        for cfg in vpn_configs[:5]:
            expiry = datetime.fromisoformat(cfg["expiry_date"]) if cfg["expiry_date"] else datetime.now()
            days_left = (expiry - datetime.now()).days
            expiry_text = f"{days_left} days left" if days_left > 0 else "Expired"
            text += f"`#{cfg['id']}` {cfg['config_type']}\n   🌍 {cfg['server_location']} | {expiry_text}\n\n"
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    # ----- PROMOTIONS -----
    if data == "promotions":
        await call.message.edit_text(f"{EMOJIS['gift']} **Promotions & Offers**\n\n{EMOJIS['fire']} **New User Offer:**\nGet **10% extra** on first wallet top-up!\n\n{EMOJIS['fire']} **Referral Program:**\nInvite friends & earn **৳50** per referral!\n\n{EMOJIS['fire']} **Bulk Discount:**\nOrder over ৳1000 and get **5% cashback**!\n\n{EMOJIS['fire']} **VPN Plus Launch Offer:**\n**30% OFF** on all VPN plans this month!\n\n{EMOJIS['fire']} **Weekly Special:**\nEvery Friday — **Free 10 diamonds** with 115+ pack!\n\nFollow our channel for updates!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['bell']} Join Channel", url=f"https://t.me/{SUPPORT_USERNAME}")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    # ----- SUPPORT -----
    if data == "support":
        await call.message.edit_text(f"{EMOJIS['phone']} **24/7 Support**\n\nNeed help? Contact us anytime!\n\n{EMOJIS['arrow']} **Admin:** @{SUPPORT_USERNAME}\n{EMOJIS['arrow']} **Response:** Within 5 minutes\n{EMOJIS['arrow']} **Hours:** 24/7/365\n\nCommon issues:\n• Order not delivered → Contact with Order ID\n• Payment issue → Send payment screenshot\n• VPN config not working → We'll help setup\n• Account problem → We'll help resolve\n\n{EMOJIS['lightning']} We're here to help!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['message']} Message Admin", url=f"https://t.me/{SUPPORT_USERNAME}")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    # ----- RATE US -----
    if data == "rate":
        await call.message.edit_text(f"{EMOJIS['star']} **Rate Our Service**\n\nEnjoying our service? Leave a review!\n\nYour feedback helps us improve! {EMOJIS['heart']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['star']} 5 Stars — Excellent!", callback_data="rate_5")], [InlineKeyboardButton(text=f"{EMOJIS['star']} 4 Stars — Good", callback_data="rate_4")], [InlineKeyboardButton(text=f"{EMOJIS['star']} 3 Stars — Average", callback_data="rate_3")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return await call.answer()

    if data.startswith("rate_"):
        rating = data[5:]
        await call.answer(f"{EMOJIS['heart']} Thanks for rating us {rating}/5!", show_alert=True)
        await call.message.edit_text(f"{EMOJIS['heart']}{EMOJIS['heart']}{EMOJIS['heart']}\n\nThank you for your feedback!\nYour {rating}-star rating means a lot to us!\n\nCome back anytime! {EMOJIS['wave']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")]]), parse_mode="Markdown")
        return

    if data == "noop":
        return await call.answer()

    # ----- ADMIN CALLBACKS -----
    if data.startswith("admin_"):
        if user_id not in ADMIN_IDS:
            return await call.answer(f"{EMOJIS['cross']} Unauthorized!", show_alert=True)
        action = data[6:]

        if action == "menu":
            stats = db.get_stats()
            await call.message.edit_text(f"{EMOJIS['admin']} **Admin Panel**\n\n{EMOJIS['divider']}\n\n{EMOJIS['users']} Total Users: `{stats['total_users']}`\n{EMOJIS['package']} Total Orders: `{stats['total_orders']}`\n{EMOJIS['money']} Revenue: `{format_price(stats['total_revenue'])}`\n{EMOJIS['wallet']} In Wallets: `{format_price(stats['total_wallet'])}`\n{EMOJIS['vpn']} Active VPNs: `{stats.get('active_vpn', 0)}`\n\n{EMOJIS['clock']} Pending: `{stats['pending_orders']}`\n{EMOJIS['settings']} Processing: `{stats['processing_orders']}`\n{EMOJIS['verified']} Delivered: `{stats['delivered_orders']}`\n\n{EMOJIS['clock']} Today: {stats['today_orders']} orders | {format_price(stats['today_revenue'])}\n\n🟢 **System Online**", reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()

        if action == "dashboard":
            stats = db.get_stats()
            await call.message.edit_text(f"{EMOJIS['chart']} **Admin Dashboard**\n\n{EMOJIS['divider']}\n\n{EMOJIS['users']} Total Users: `{stats['total_users']}`\n{EMOJIS['package']} Total Orders: `{stats['total_orders']}`\n{EMOJIS['money']} Revenue: `{format_price(stats['total_revenue'])}`\n{EMOJIS['wallet']} In Wallets: `{format_price(stats['total_wallet'])}`\n{EMOJIS['vpn']} Active VPNs: `{stats.get('active_vpn', 0)}`\n\n{EMOJIS['clock']} Pending: `{stats['pending_orders']}`\n{EMOJIS['settings']} Processing: `{stats['processing_orders']}`\n{EMOJIS['verified']} Delivered: `{stats['delivered_orders']}`\n\n{EMOJIS['clock']} Today: {stats['today_orders']} orders | {format_price(stats['today_revenue'])}\n\n🟢 **System Online**", reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()

        elif action == "orders":
            orders = db.get_all_orders(limit=20)
            if not orders:
                await call.message.edit_text(f"{EMOJIS['package']} No orders found.", reply_markup=admin_kb())
                return await call.answer()
            text = f"{EMOJIS['package']} **Recent Orders**\n\n"
            for o in orders[:15]:
                text += f"`#{o['order_id']}` {get_status_emoji(o['status'])} {o['product_name'][:20]}\n   👤 `{o['user_id']}` | {format_price(o['amount'])} | {o['status']}\n"
            await call.message.edit_text(text, reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()

        elif action == "pending":
            orders = db.get_all_orders("pending", limit=20)
            if not orders:
                await call.message.edit_text(f"{EMOJIS['verified']} No pending orders!", reply_markup=admin_kb())
                return await call.answer()
            text = f"{EMOJIS['clock']} **Pending Orders**\n\n"
            for o in orders[:15]:
                text += f"`#{o['order_id']}` 👤 `{o['user_id']}`\n   {o['product_name'][:20]} | {format_price(o['amount'])}\n"
            await call.message.edit_text(text, reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()

        elif action == "add_balance":
            await call.message.edit_text(f"{EMOJIS['money']} **Add User Balance**\n\nSend the user's Telegram ID:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")]]))
            await state.set_state(AdminStates.adding_balance_user)
            return await call.answer()

        elif action == "deliver":
            await call.message.edit_text(f"{EMOJIS['rocket']} **Deliver Order**\n\nSend the Order ID to deliver:\n(Example: 1, 2, 3...)", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")]]))
            await state.set_state(AdminStates.delivering_order)
            return await call.answer()

        elif action == "edit_products":
            builder = InlineKeyboardBuilder()
            for cat in get_categories():
                if cat["id"] == "topup":
                    continue
                builder.button(text=f"{cat['emoji']} {cat['name']}", callback_data=f"editcat_{cat['id']}")
            builder.button(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")
            builder.adjust(2, 2, 2, 2, 1)
            await call.message.edit_text(f"{EMOJIS['pen']} **Edit Products**\n\nSelect a category:", reply_markup=builder.as_markup(), parse_mode="Markdown")
            return await call.answer()

        elif action == "broadcast":
            await call.message.edit_text(f"{EMOJIS['message']} **Broadcast Message**\n\nSend the message to broadcast to **all users**:\n(Can include text, emojis, and formatting)", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")]]))
            await state.set_state(AdminStates.broadcasting_msg)
            return await call.answer()

        elif action == "backup":
            try:
                db_file = FSInputFile(db.db_path)
                await call.message.answer_document(document=db_file, caption=f"{EMOJIS['verified']} **Database Backup Successfully Generated!**\nDate: `{datetime.now().strftime('%Y-%m-%d %H:%M')}`", parse_mode="Markdown")
                await call.answer("Backup sent to chat!", show_alert=True)
            except Exception as e:
                await call.answer(f"Failed to backup: {e}", show_alert=True)
            return

        elif action == "restore":
            await call.message.edit_text(f"{EMOJIS['warning']} **Database Restore**\n\nPlease send the `topup_bot.db` backup file here.\n\n{EMOJIS['warning']} **WARNING:** This will OVERWRITE the current database completely!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['cross']} Cancel", callback_data="admin_menu")]]), parse_mode="Markdown")
            await state.set_state(AdminStates.restoring_db)
            return await call.answer()

        elif action == "stats":
            stats = db.get_stats()
            await call.message.edit_text(f"{EMOJIS['chart']} **Full Statistics**\n\n{EMOJIS['divider']}\n\n**Users**\nTotal: `{stats['total_users']}`\nWallet Total: `{format_price(stats['total_wallet'])}`\n\n**Orders**\nTotal: `{stats['total_orders']}`\nRevenue: `{format_price(stats['total_revenue'])}`\nPending: `{stats['pending_orders']}`\nProcessing: `{stats['processing_orders']}`\nDelivered: `{stats['delivered_orders']}`\n\n**VPN**\nActive Configs: `{stats.get('active_vpn', 0)}`\n\n**Today**\nOrders: `{stats['today_orders']}`\nRevenue: `{format_price(stats['today_revenue'])}`", reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()

        elif action == "vpn":
            stats = db.get_stats()
            builder = InlineKeyboardBuilder()
            builder.button(text=f"{EMOJIS['plus']} Add VPN Config", callback_data="admin_vpn_add")
            builder.button(text=f"{EMOJIS['list']} List Active VPNs", callback_data="admin_vpn_list")
            builder.button(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")
            builder.adjust(2, 1)
            await call.message.edit_text(f"{EMOJIS['vpn']} **VPN Configuration Manager**\n\nManage VPN configs, add new configs, or check active ones.\n\nActive configs in DB: `{stats.get('active_vpn', 0)}`", reply_markup=builder.as_markup(), parse_mode="Markdown")
            return await call.answer()

        elif action == "vpn_add":
            await call.message.edit_text(f"{EMOJIS['vpn']} **Add VPN Configuration**\n\nSend the **Order ID** that this VPN config belongs to:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")]]))
            await state.set_state(AdminStates.vpn_adding_config)
            return await call.answer()

        elif action == "vpn_list":
            conn = db._get_conn()
            c = conn.execute("SELECT v.*, u.username, u.first_name FROM vpn_configs v LEFT JOIN users u ON v.user_id = u.user_id WHERE v.status = 'active' ORDER BY v.created_date DESC LIMIT 20")
            configs = c.fetchall()
            conn.close()
            if not configs:
                await call.message.edit_text(f"{EMOJIS['vpn']} No active VPN configs found.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")]]))
                return await call.answer()
            text = f"{EMOJIS['vpn']} **Active VPN Configs**\n\n"
            for cfg in configs[:15]:
                expiry = datetime.fromisoformat(cfg["expiry_date"]) if cfg["expiry_date"] else datetime.now()
                days_left = (expiry - datetime.now()).days
                name = cfg["first_name"] or cfg["username"] or str(cfg["user_id"])
                text += f"`#{cfg['id']}` 👤 {name}\n   {cfg['config_type']} | 🌍 {cfg['server_location']} | ⏳ {days_left}d\n"
            await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")]]), parse_mode="Markdown")
            return await call.answer()

        elif action == "users":
            users = db.get_all_users()
            total = len(users)
            banned = sum(1 for u in users if u["is_banned"])
            active = sum(1 for u in users if not u["is_banned"])
            with_balance = sum(1 for u in users if u["balance"] > 0)
            text = f"{EMOJIS['users']} **User Management**\n\nTotal Users: `{total}`\nActive: `{active}`\nBanned: `{banned}`\nWith Balance: `{with_balance}`\n\n**Actions:**\n{EMOJIS['arrow']} Use /ban [user_id] to ban\n{EMOJIS['arrow']} Use /unban [user_id] to unban\n{EMOJIS['arrow']} Use /user [user_id] for details"
            builder = InlineKeyboardBuilder()
            builder.button(text=f"{EMOJIS['lock']} Ban User", callback_data="admin_ban_user")
            builder.button(text=f"{EMOJIS['unlock']} Unban User", callback_data="admin_unban_user")
            builder.button(text=f"{EMOJIS['money']} Add Balance", callback_data="admin_add_balance")
            builder.button(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")
            builder.adjust(2, 1, 1)
            await call.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="Markdown")
            return await call.answer()

        elif action == "ban_user":
            await call.message.edit_text(f"{EMOJIS['lock']} **Ban User**\n\nSend the user's Telegram ID:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Admin", callback_data="admin_menu")]]))
            await state.set_state(AdminStates.banning_user)
            return await call.answer()

        elif action == "unban_user":
            await call.message.edit_text(f"{EMOJIS['unlock']} **Unban User**\n\nSend the user's Telegram ID:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Admin", callback_data="admin_menu")]]))
            await state.set_state(AdminStates.unbanning_user)
            return await call.answer()

    # ----- EDIT CATEGORY PRODUCTS -----
    if data.startswith("editcat_"):
        cat_id = data[8:]
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Not found!")
        builder = InlineKeyboardBuilder()
        for prod in cat["products"]:
            builder.button(text=f"{prod['name'][:20]} — {format_price(prod['price'])}", callback_data=f"editprod_{cat_id}_{prod['id']}")
        builder.button(text=f"{EMOJIS['back']} Categories", callback_data="admin_edit_products")
        builder.adjust(1)
        await call.message.edit_text(f"{cat['emoji']} **{cat['name']}** — Products:\n\nClick a product to edit:", reply_markup=builder.as_markup(), parse_mode="Markdown")
        return await call.answer()

    if data.startswith("editprod_"):
        parts = data.split("_")
        cat_id = parts[1]
        prod_id = "_".join(parts[2:])
        product = get_product(cat_id, prod_id)
        if not product:
            return await call.answer(f"{EMOJIS['cross']} Not found!")
        await state.update_data(edit_cat=cat_id, edit_prod=prod_id)
        builder = InlineKeyboardBuilder()
        builder.button(text=f"{EMOJIS['pen']} Edit Name", callback_data="edit_name")
        builder.button(text=f"{EMOJIS['money']} Edit Price", callback_data="edit_price")
        builder.button(text=f"{EMOJIS['back']} Back", callback_data=f"editcat_{cat_id}")
        builder.adjust(2, 1)
        await call.message.edit_text(f"{EMOJIS['pen']} **Editing:** {product['name']}\nPrice: {format_price(product['price'])}\n\nChoose what to edit:", reply_markup=builder.as_markup(), parse_mode="Markdown")
        return await call.answer()

    if data == "edit_name":
        await call.message.edit_text(f"{EMOJIS['pen']} Send the new product name:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="admin_edit_products")]]))
        await state.set_state(AdminStates.editing_product_name)
        return await call.answer()

    if data == "edit_price":
        await call.message.edit_text(f"{EMOJIS['money']} Send the new price (number only):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="admin_edit_products")]]))
        await state.set_state(AdminStates.editing_product_price)
        return await call.answer()


# ==================== WALLET PAYMENT PROCESSING ====================
async def process_wallet_payment(call: CallbackQuery, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    user_input = state_data.get("user_input", "Wallet TopUp")
    user_id = call.from_user.id
    price = product.get("price", 0)
    discount = product.get("discount", 0)
    user_bal = db.get_user(user_id)
    if not user_bal or user_bal["balance"] < price:
        return await call.answer(f"{EMOJIS['cross']} Insufficient balance!\nYou need {format_price(price)}\nYour balance: {format_price(user_bal['balance'] if user_bal else 0)}", show_alert=True)
    db.update_balance(user_id, -price)

    if cat.get("id") == "topup":
        bonus = discount
        db.update_balance(user_id, price + bonus)
        db.add_transaction(user_id, price, "topup", "Wallet", f"WALLET_{datetime.now().timestamp():.0f}", f"Auto top-up: +{format_price(price+bonus)}")
        await call.message.edit_text(f"{EMOJIS['verified']} **Wallet Top-Up Successful!**\n\nAmount: **{format_price(price)}**\nBonus: **+{format_price(bonus)}**\nTotal Added: **{format_price(price + bonus)}**\n\nNew Balance: **{format_price(user_bal['balance'] - price + price + bonus)}**\n\n{EMOJIS['sparkle']} Thank you for using TopUp Store BD!", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")
    else:
        trx_id = f"WALLET_{datetime.now().timestamp():.0f}"
        order_id = db.add_order(user_id, product.get("name", ""), cat.get("name", ""), price, 1, user_input, "Wallet Balance", trx_id)

        if cat.get("id") == "vpn":
            config_type = "WireGuard"
            server_location = user_input if user_input and user_input != "Wallet TopUp" else "Singapore"
            config_data = generate_vpn_config(order_id, user_id, config_type, server_location)
            expiry_days = get_vpn_expiry_days(product.get("name", ""))
            db.add_vpn_config(order_id, user_id, config_type, config_data, server_location, expiry_days)
            db.update_order_status(order_id, "delivered", note=f"VPN Config auto-delivered. Server: {server_location}")
            await call.message.edit_text(f"{EMOJIS['verified']} **VPN Order Successful!**\n\nOrder #`{order_id}`\nProduct: **{product['name']}**\nAmount: **{format_price(price)}**\nPaid via: **Wallet Balance**\nServer: **{server_location}**\n\n{EMOJIS['rocket']} **VPN Config Generated!**\n{EMOJIS['vpn']} Config Type: **{config_type}**\n{EMOJIS['expire']} Expires in: **{expiry_days} days**\n\n{EMOJIS['config']} **Your Config:**\n`{config_data[:100]}...`\n\n{EMOJIS['info']} Use this config with any WireGuard client.\nContact support if you need help setting up!", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")
        else:
            db.update_order_status(order_id, "delivered", note="Auto-delivered via wallet payment")
            await call.message.edit_text(f"{EMOJIS['verified']} **Order Successful!**\n\nOrder #`{order_id}`\nProduct: **{product['name']}**\nAmount: **{format_price(price)}**\nPaid via: **Wallet Balance**\n\n{EMOJIS['rocket']} **Auto-Delivered!**\nYour order has been processed instantly!\n\n{EMOJIS['sparkle']} Thank you for your purchase!", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")

        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"{EMOJIS['lightning']} **Auto-Delivered via Wallet**\n\nOrder #`{order_id}`\n👤 User: [{call.from_user.first_name}](tg://user?id={user_id})\n📦 {product['name']}\n💰 {format_price(price)}\n💳 Wallet Balance\n📝 Input: `{user_input}`", parse_mode="Markdown")
            except:
                pass
    await state.clear()


# ==================== MESSAGE HANDLERS — USER INPUT ====================
@dp.message(OrderStates.entering_input)
async def process_user_input(message: Message, state: FSMContext):
    user_input = message.text.strip()
    if not user_input or len(user_input) < 2:
        return await message.answer(f"{EMOJIS['cross']} Please enter valid details!\nMinimum 2 characters required.")
    await state.update_data(user_input=user_input)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    price = product.get("price", 0)
    await message.answer(f"{EMOJIS['verified']} **Details Received!**\nInput: `{user_input}`\n\nProduct: **{product.get('name', '')}**\nPrice: **{format_price(price)}**\n\n{EMOJIS['arrow']} Now select payment method:", reply_markup=payment_kb(), parse_mode="Markdown")
    await state.set_state(OrderStates.selecting_payment)

@dp.message(OrderStates.entering_trx_id)
async def process_trx_id(message: Message, state: FSMContext, bot: Bot):
    trx_id = message.text.strip()
    if not trx_id:
        return await message.answer(f"{EMOJIS['cross']} Please enter a valid Transaction ID!")
    await state.update_data(transaction_id=trx_id)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    user_input = state_data.get("user_input", "")
    payment_method = state_data.get("payment_method", "")
    user_id = message.from_user.id
    price = product.get("price", 0)
    method_names = {"bkash": "bKash", "nagad": "Nagad", "rocket": "Rocket", "upi": "UPI"}

    if cat.get("id") == "topup":
        bonus = product.get("discount", 0)
        total = price + bonus
        db.update_balance(user_id, total)
        db.add_transaction(user_id, total, "topup", method_names.get(payment_method, payment_method), trx_id, f"Top-up via {method_names.get(payment_method, payment_method)}")
        await message.answer(f"{EMOJIS['verified']} **Balance Added Successfully!**\n\nAmount: **{format_price(price)}**\nBonus: **+{format_price(bonus)}**\nTotal Added: **{format_price(total)}**\n\n{EMOJIS['sparkle']} Thank you for your payment!\nYour balance has been updated.", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, f"{EMOJIS['money']} **Balance Top-Up**\n\n👤 [{message.from_user.first_name}](tg://user?id={user_id})\n💰 {format_price(price)} + {format_price(bonus)} bonus\n💳 {method_names.get(payment_method, payment_method)}\n🔢 TrxID: `{trx_id}`\n✅ **Auto-Credited**", parse_mode="Markdown")
            except:
                pass
        await state.clear()
        return

    order_id = db.add_order(user_id, product.get("name", ""), cat.get("name", ""), price, 1, user_input, method_names.get(payment_method, payment_method), trx_id)

    if cat.get("id") == "vpn":
        config_type = "WireGuard"
        server_location = user_input if user_input else "Singapore"
        config_data = generate_vpn_config(order_id, user_id, config_type, server_location)
        expiry_days = get_vpn_expiry_days(product.get("name", ""))
        db.add_vpn_config(order_id, user_id, config_type, config_data, server_location, expiry_days)
        db.update_order_status(order_id, "delivered", note=f"VPN Config auto-generated. Server: {server_location}")
        await message.answer(f"{EMOJIS['verified']} **VPN Order Placed Successfully!**\n\nOrder #`{order_id}`\nProduct: **{product.get('name', '')}**\nAmount: **{format_price(price)}**\nPayment: **{method_names.get(payment_method, payment_method)}**\nTrxID: `{trx_id}`\n🌍 Location: `{user_input}`\n\n{EMOJIS['rocket']} **VPN Config Auto-Generated!**\n{EMOJIS['vpn']} Config Type: **{config_type}**\n🌍 Server: **{server_location}**\n{EMOJIS['expire']} Expires: **{expiry_days} days**\n\n{EMOJIS['info']} Admin will deliver the full config soon!\n{EMOJIS['phone']} Contact admin if any issue.", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")
    else:
        await message.answer(f"{EMOJIS['verified']} **Order Placed Successfully!**\n\nOrder #`{order_id}`\nProduct: **{product.get('name', '')}**\nAmount: **{format_price(price)}**\nPayment: **{method_names.get(payment_method, payment_method)}**\nTrxID: `{trx_id}`\n\n{EMOJIS['clock']} **Status: Pending Verification**\n\nWe will notify you once verified & delivered!\n{EMOJIS['phone']} Contact admin if any issue.", reply_markup=main_menu_kb(user_id), parse_mode="Markdown")

    for admin_id in ADMIN_IDS:
        try:
            msg_text = f"{EMOJIS['bell']} **New Order!**\n\n#`{order_id}`\n👤 [{message.from_user.first_name}](tg://user?id={user_id})\n📂 {cat.get('name', '')}\n📦 {product.get('name', '')}\n💰 {format_price(price)}\n📝 Input: `{user_input}`\n💳 {method_names.get(payment_method, payment_method)}\n🔢 TrxID: `{trx_id}`"
            await bot.send_message(admin_id, msg_text, parse_mode="Markdown")
        except:
            pass
    await state.clear()


# ==================== ADMIN MESSAGE HANDLERS ====================
@dp.message(AdminStates.restoring_db, F.document)
async def admin_restore_db_handler(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_IDS:
        return
    document = message.document
    if not document.file_name.endswith('.db'):
        return await message.answer(f"{EMOJIS['cross']} Invalid file! Please send a valid SQLite `.db` file.")
    await message.answer(f"{EMOJIS['clock']} Downloading and restoring database...")
    try:
        os.makedirs(os.path.dirname(db.db_path), exist_ok=True)
        file = await bot.get_file(document.file_id)
        await bot.download_file(file.file_path, db.db_path)
        db._init_tables()
        await message.answer(f"{EMOJIS['verified']} **Database Restored Successfully!**", reply_markup=admin_kb())
    except Exception as e:
        await message.answer(f"{EMOJIS['cross']} Error: {e}")
    await state.clear()

@dp.message(AdminStates.adding_balance_user)
async def admin_balance_user(message: Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        await state.update_data(target_user=target_id)
        user = db.get_user(target_id)
        if user:
            await message.answer(f"👤 **User Found:** `{target_id}`\nName: {user['first_name'] or 'Unknown'}\nCurrent Balance: {format_price(user['balance'])}\n\nSend the amount to add:", parse_mode="Markdown")
        else:
            await message.answer(f"⚠️ User `{target_id}` not found.\nSend amount anyway?", parse_mode="Markdown")
        await state.set_state(AdminStates.adding_balance_amount)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID.")

@dp.message(AdminStates.adding_balance_amount)
async def admin_balance_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0 or amount > 1000000:
            return await message.answer(f"{EMOJIS['cross']} Invalid amount (1-1000000):")
        state_data = await state.get_data()
        target_id = state_data.get("target_user")
        db.update_balance(target_id, amount)
        db.add_transaction(target_id, amount, "admin_add", "Admin", f"ADMIN_{datetime.now():%Y%m%d%H%M%S}", f"Added by @{message.from_user.username or 'admin'}")
        await message.answer(f"{EMOJIS['verified']} **Balance Added!**\n\n👤 User: `{target_id}`\n💰 Amount: **+{format_price(amount)}**", reply_markup=admin_kb(), parse_mode="Markdown")
        try:
            await bot.send_message(target_id, f"{EMOJIS['money']} **Balance Added!**\n\n+**{format_price(amount)}** added to your wallet!", parse_mode="Markdown")
        except:
            pass
        await state.clear()
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid amount.")

@dp.message(AdminStates.delivering_order)
async def admin_deliver_order(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
        order = db.get_order(order_id)
        if not order:
            return await message.answer(f"{EMOJIS['cross']} Order not found!")
        await state.update_data(deliver_order_id=order_id)
        await message.answer(f"📦 **Order #`{order_id}` Found**\n\nProduct: {order['product_name']}\nUser: `{order['user_id']}`\nAmount: {format_price(order['amount'])}\nStatus: {order['status']}\n\nSend delivery photo or note:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['lightning']} Deliver Without Photo", callback_data="deliver_no_photo")], [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin Panel", callback_data="admin_menu")]]), parse_mode="Markdown")
        await state.set_state(AdminStates.delivering_file)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid Order ID.")

@dp.message(AdminStates.delivering_file)
async def admin_deliver_file(message: Message, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
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
    await message.answer(f"{EMOJIS['verified']} **Order #`{order_id}` Delivered!**\n\n📝 Note: {note}", reply_markup=admin_kb(), parse_mode="Markdown")
    if order:
        try:
            if file_id:
                await bot.send_photo(order["user_id"], file_id, caption=f"{EMOJIS['verified']} **Order Delivered!**\n\n#`{order_id}`\n📦 {order['product_name']}\n{note}\n\n{EMOJIS['sparkle']} Thank you!", parse_mode="Markdown")
            else:
                await bot.send_message(order["user_id"], f"{EMOJIS['verified']} **Order Delivered!**\n\n#`{order_id}`\n📦 {order['product_name']}\n{note}\n\n{EMOJIS['sparkle']} Thank you!", parse_mode="Markdown")
        except:
            pass
    await state.clear()

@dp.callback_query(lambda c: c.data == "deliver_no_photo")
async def deliver_no_photo(call: CallbackQuery, state: FSMContext, bot: Bot):
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
    db.update_order_status(order_id, "delivered", note="Delivered without photo")
    order = db.get_order(order_id)
    await call.message.edit_text(f"{EMOJIS['verified']} **Order #`{order_id}` Delivered!**", reply_markup=admin_kb(), parse_mode="Markdown")
    if order:
        try:
            await bot.send_message(order["user_id"], f"{EMOJIS['verified']} **Order Delivered!**\n\n#`{order_id}`\n📦 {order['product_name']}\n✅ Completed!", parse_mode="Markdown")
        except:
            pass
    await state.clear()

@dp.message(AdminStates.broadcasting_msg)
async def admin_broadcast_msg(message: Message, state: FSMContext):
    msg_text = message.text or message.caption or "📢 Broadcast"
    await state.update_data(broadcast_text=msg_text)
    users = db.get_all_users()
    total = len(users)
    active = sum(1 for u in users if not u["is_banned"])
    await message.answer(f"{EMOJIS['message']} **Broadcast Preview**\n\n{msg_text[:200]}{'...' if len(msg_text) > 200 else ''}\n\nTotal: `{total}`\nWill receive: `{active}`\n\nConfirm?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['verified']} Send!", callback_data="broadcast_confirm"), InlineKeyboardButton(text=f"{EMOJIS['cross']} Cancel", callback_data="admin_menu")]]), parse_mode="Markdown")
    await state.set_state(AdminStates.broadcasting_confirm)

@dp.callback_query(lambda c: c.data == "broadcast_confirm")
async def admin_broadcast_confirm(call: CallbackQuery, state: FSMContext, bot: Bot):
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
            await asyncio.sleep(0.05)
        except:
            failed += 1
    await call.message.edit_text(f"{EMOJIS['verified']} **Broadcast Complete!**\n\n✅ Sent: `{sent}`\n❌ Failed: `{failed}`", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.vpn_adding_config)
async def admin_vpn_order_id(message: Message, state: FSMContext):
    try:
        order_id = int(message.text.strip())
        order = db.get_order(order_id)
        if not order:
            return await message.answer(f"{EMOJIS['cross']} Order not found!")
        await state.update_data(vpn_order_id=order_id)
        await message.answer(f"📦 **Order #`{order_id}`**\nProduct: {order['product_name']}\nUser: `{order['user_id']}`\n\nSend the VPN config data:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")]]))
        await state.set_state(AdminStates.vpn_config_data)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid Order ID!")

@dp.message(AdminStates.vpn_config_data)
async def admin_vpn_config_data(message: Message, state: FSMContext):
    config_data = message.text.strip()
    if not config_data or len(config_data) < 10:
        return await message.answer(f"{EMOJIS['cross']} Config too short!")
    await state.update_data(vpn_config_data=config_data)
    await message.answer(f"✅ Config received!\n\nSend the server location (e.g., Singapore, USA):", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{EMOJIS['back']} VPN Admin", callback_data="admin_vpn")]]))
    await state.set_state(AdminStates.vpn_config_expiry)

@dp.message(AdminStates.vpn_config_expiry)
async def admin_vpn_expiry(message: Message, state: FSMContext, bot: Bot):
    server_location = message.text.strip()
    if not server_location:
        return await message.answer(f"{EMOJIS['cross']} Enter a valid location!")
    state_data = await state.get_data()
    order_id = state_data.get("vpn_order_id")
    config_data = state_data.get("vpn_config_data")
    order = db.get_order(order_id)
    if not order:
        return await message.answer(f"{EMOJIS['cross']} Order not found!")
    db.add_vpn_config(order_id, order["user_id"], "Manual Config", config_data, server_location, 30)
    db.update_order_status(order_id, "delivered", note=f"VPN Config delivered. Server: {server_location}")
    await message.answer(f"{EMOJIS['verified']} **VPN Config Added!**\n\nOrder #`{order_id}`\nUser: `{order['user_id']}`\nLocation: {server_location}", reply_markup=admin_kb(), parse_mode="Markdown")
    try:
        await bot.send_message(order["user_id"], f"{EMOJIS['vpn']} **VPN Config Ready!**\n\n🌍 **Server:** {server_location}\n📋 **Config:**\n`{config_data[:500]}`\n\nNeed help? @{SUPPORT_USERNAME}", parse_mode="Markdown")
    except:
        pass
    await state.clear()

@dp.message(AdminStates.banning_user)
async def admin_ban_user(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = int(message.text.strip())
        if user_id in ADMIN_IDS:
            return await message.answer(f"{EMOJIS['cross']} Cannot ban admin!")
        db.set_ban(user_id, True)
        await message.answer(f"{EMOJIS['lock']} **User Banned**\n\n👤 `{user_id}`", reply_markup=admin_kb(), parse_mode="Markdown")
        await state.clear()
        try:
            await bot.send_message(user_id, f"{EMOJIS['cross']} You have been banned.")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")

@dp.message(AdminStates.unbanning_user)
async def admin_unban_user(message: Message, state: FSMContext, bot: Bot):
    try:
        user_id = int(message.text.strip())
        db.set_ban(user_id, False)
        await message.answer(f"{EMOJIS['unlock']} **User Unbanned**\n\n👤 `{user_id}`", reply_markup=admin_kb(), parse_mode="Markdown")
        await state.clear()
        try:
            await bot.send_message(user_id, f"{EMOJIS['verified']} You have been unbanned.")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")

@dp.message(AdminStates.editing_product_name)
async def admin_edit_name(message: Message, state: FSMContext):
    state_data = await state.get_data()
    cat_id = state_data.get("edit_cat")
    prod_id = state_data.get("edit_prod")
    new_name = message.text.strip()
    cat = get_category(cat_id)
    if cat:
        for prod in cat["products"]:
            if prod["id"] == prod_id:
                prod["name"] = new_name
                break
    await message.answer(f"{EMOJIS['verified']} **Product Updated!**\n\nNew name: {new_name}\n(Note: In-memory only)", reply_markup=admin_kb(), parse_mode="Markdown")
    await state.clear()

@dp.message(AdminStates.editing_product_price)
async def admin_edit_price(message: Message, state: FSMContext):
    try:
        new_price = float(message.text.strip())
        state_data = await state.get_data()
        cat_id = state_data.get("edit_cat")
        prod_id = state_data.get("edit_prod")
        cat = get_category(cat_id)
        if cat:
            for prod in cat["products"]:
                if prod["id"] == prod_id:
                    prod["price"] = new_price
                    break
        await message.answer(f"{EMOJIS['verified']} **Price Updated!**\n\nNew price: {format_price(new_price)}", reply_markup=admin_kb(), parse_mode="Markdown")
        await state.clear()
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid price!")


# ==================== MAIN FUNCTION ====================
async def main():
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║            🚀 TOPUP STORE BD — BOT v2.1             ║
    ║                                                      ║
    ║   🤖 Bot: {BOT_USERNAME}                              
    ║   👤 Admins: {len(ADMIN_IDS)} configured                         
    ║   📦 Products: {sum(len(c['products']) for c in get_categories())} items                       
    ║   📂 Categories: {len(get_categories())}                                 
    ║   🌐 NEW! VPN Plus — Premium IP Service             ║
    ║   💾 Database: SQLite                               
    ║   🎨 Style: Premium                                  
    ║                                                      ║
    ║   🟢 BOT IS RUNNING...                               ║
    ╚══════════════════════════════════════════════════════╝
    """)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
