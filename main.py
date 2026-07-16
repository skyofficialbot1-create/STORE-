#!/usr/bin/env python3
"""
████████╗ ██████╗ ██████╗ ██╗   ██╗██████╗     ███████╗████████╗ ██████╗ ██████╗ ███████╗
╚══██╔══╝██╔═══██╗██╔══██╗██║   ██║██╔══██╗    ██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██╔════╝
   ██║   ██║   ██║██████╔╝██║   ██║██████╔╝    ███████╗   ██║   ██║   ██║██████╔╝█████╗  
   ██║   ██║   ██║██╔═══╝ ██║   ██║██╔══██╗    ╚════██║   ██║   ██║   ██║██╔══██╗██╔══╝  
   ██║   ╚██████╔╝██║     ╚██████╔╝██║  ██║    ███████║   ██║   ╚██████╔╝██║  ██║███████╗
   ╚═╝    ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝    ╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚══════╝
                                                                                          
   ╔══════════════════════════════════════════════════════════════════════════════════╗
   ║               🚀 TopUp Store BD — Premium Telegram Bot v2.0                      ║
   ║          🔥 Free Fire | PUBG | MLBB | Netflix | YouTube | Crunchyroll          ║
   ║                    ⚡ Instant AI Auto-Delivery System                            ║
   ╚══════════════════════════════════════════════════════════════════════════════════╝
   
   ✨ Features:
   • 8 Premium Categories with Colorful Style Buttons (primary/success/danger)
   • Real-time Order Tracking & Auto-Delivery
   • Wallet Balance System with Auto Top-up
   • Full Admin Panel (Dashboard, Orders, Deliver, Broadcast)
   • SQLite Database (no external DB needed)
   • Premium Telegram Bot API 9.4+ Design
   
   📦 Deploy: python topup_bot.py
   🔧 Requirements: aiogram>=3.10, aiofiles
"""

import asyncio
import json
import os
import sys
import sqlite3
import random
import string
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
# ⚠️ আপনার তথ্য দিয়ে পরিবর্তন করুন ⚠️

BOT_TOKEN = "8897904364:AAGB-6rKp-hkNM9Zc0fbDn4Z9jG-SVRe4xk"  # @BotFather থেকে নিন

ADMIN_IDS = [7689218221]  # আপনার টেলিগ্রাম ইউজার আইডি দিন

# পেমেন্ট নম্বরসমূহ
NAGAD_NUMBER = "01748506069"
BKASH_NUMBER = "01742958563"
ROCKET_NUMBER = "01742958563"
UPI_ID = "example@upi"

# বট সেটিংস
BOT_USERNAME = "@SKY_STOR_BOT"
BOT_NAME = "SKY STORE"
SUPPORT_USERNAME = "FBSKYSUPPORT"  # @ ছাড়া

# ==================== EMOJI & STYLE CONSTANTS ====================
EMOJIS = {
    "freefire": "🔥",
    "pubg": "🎯",
    "mlbb": "🐉",
    "netflix": "🎬",
    "youtube": "▶️",
    "crunchyroll": "🍿",
    "spotify": "🎵",
    "balance": "💰",
    "crown": "👑",
    "star": "⭐",
    "lightning": "⚡",
    "shield": "🛡️",
    "cart": "🛒",
    "wallet": "💳",
    "package": "📦",
    "clock": "⏰",
    "verified": "✅",
    "cross": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "settings": "⚙️",
    "admin": "🔐",
    "users": "👥",
    "chart": "📊",
    "message": "📨",
    "back": "🔙",
    "next": "➡️",
    "previous": "⬅️",
    "home": "🏠",
    "search": "🔍",
    "bell": "🔔",
    "gift": "🎁",
    "fire": "🔥",
    "diamond": "💎",
    "trophy": "🏆",
    "medal": "🥇",
    "rocket": "🚀",
    "sparkle": "✨",
    "rainbow": "🌈",
    "heart": "❤️",
    "thumb": "👍",
    "clap": "👏",
    "wave": "👋",
    "globe": "🌍",
    "lock": "🔒",
    "unlock": "🔓",
    "key": "🔑",
    "money": "💵",
    "cash": "💸",
    "bank": "🏦",
    "card": "💳",
    "phone": "📱",
    "computer": "💻",
    "game": "🎮",
    "headphone": "🎧",
    "music": "🎶",
    "movie": "🎥",
    "tv": "📺",
    "book": "📚",
    "pen": "✏️",
    "clip": "📎",
    "file": "📄",
    "folder": "📁",
    "trash": "🗑️",
    "plus": "➕",
    "minus": "➖",
    "check": "✔️",
    "bullet": "▸",
    "arrow": "→",
    "divider": "━━━━━━━━━━━━━━━━━━━━━"
}

# ==================== PRODUCTS DATABASE ====================
# 📦 সম্পূর্ণ প্রোডাক্ট ক্যাটালগ — JSON ফরম্যাটে
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
    """SQLite Database Manager with auto-migration"""
    
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
        
        # Users table
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                balance REAL DEFAULT 0.0,
                total_spent REAL DEFAULT 0.0,
                total_orders INTEGER DEFAULT 0,
                join_date TEXT DEFAULT '',
                last_active TEXT DEFAULT '',
                is_banned INTEGER DEFAULT 0,
                is_admin INTEGER DEFAULT 0,
                referral_code TEXT DEFAULT '',
                referred_by INTEGER DEFAULT 0
            )
        """)
        
        # Orders table
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_name TEXT DEFAULT '',
                category_name TEXT DEFAULT '',
                amount REAL DEFAULT 0.0,
                quantity INTEGER DEFAULT 1,
                user_input TEXT DEFAULT '',
                payment_method TEXT DEFAULT '',
                transaction_id TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                order_date TEXT DEFAULT '',
                delivered_date TEXT DEFAULT '',
                delivery_file_id TEXT DEFAULT '',
                delivery_note TEXT DEFAULT '',
                admin_id INTEGER DEFAULT 0
            )
        """)
        
        # Transactions table
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL DEFAULT 0.0,
                type TEXT DEFAULT '',
                method TEXT DEFAULT '',
                transaction_id TEXT DEFAULT '',
                status TEXT DEFAULT 'completed',
                note TEXT DEFAULT '',
                date TEXT DEFAULT ''
            )
        """)
        
        # Referrals table
        c.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                referred_user_id INTEGER NOT NULL,
                reward_amount REAL DEFAULT 0.0,
                date TEXT DEFAULT ''
            )
        """)
        
        # Broadcasts table
        c.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT DEFAULT '',
                sent_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                date TEXT DEFAULT ''
            )
        """)
        
        conn.commit()
        conn.close()
    
    # ========== USER METHODS ==========
    def add_user(self, user_id: int, username: str = "", first_name: str = ""):
        conn = self._get_conn()
        conn.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, join_date, last_active)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, username, first_name, datetime.now().isoformat(), datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    def get_user(self, user_id: int) -> Optional[sqlite3.Row]:
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
        conn.close()
        return user
    
    def update_user_activity(self, user_id: int):
        conn = self._get_conn()
        conn.execute("UPDATE users SET last_active = ? WHERE user_id = ?",
                    (datetime.now().isoformat(), user_id))
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
    
    def get_all_users(self) -> List[sqlite3.Row]:
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM users ORDER BY join_date DESC")
        users = c.fetchall()
        conn.close()
        return users
    
    # ========== ORDER METHODS ==========
    def add_order(self, user_id: int, product_name: str, category_name: str,
                  amount: float, quantity: int, user_input: str,
                  payment_method: str, transaction_id: str) -> int:
        conn = self._get_conn()
        c = conn.execute("""
            INSERT INTO orders (user_id, product_name, category_name, amount,
                               quantity, user_input, payment_method,
                               transaction_id, order_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, product_name, category_name, amount, quantity,
              user_input, payment_method, transaction_id,
              datetime.now().isoformat()))
        order_id = c.lastrowid
        
        conn.execute("""
            UPDATE users SET total_orders = total_orders + 1,
                            total_spent = total_spent + ?
            WHERE user_id = ?
        """, (amount, user_id))
        
        conn.commit()
        conn.close()
        return order_id
    
    def get_order(self, order_id: int) -> Optional[sqlite3.Row]:
        conn = self._get_conn()
        c = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
        order = c.fetchone()
        conn.close()
        return order
    
    def get_user_orders(self, user_id: int, limit: int = 20) -> List[sqlite3.Row]:
        conn = self._get_conn()
        c = conn.execute("""
            SELECT * FROM orders WHERE user_id = ?
            ORDER BY order_date DESC LIMIT ?
        """, (user_id, limit))
        orders = c.fetchall()
        conn.close()
        return orders
    
    def get_all_orders(self, status: Optional[str] = None, limit: int = 50) -> List[sqlite3.Row]:
        conn = self._get_conn()
        if status:
            c = conn.execute("""
                SELECT * FROM orders WHERE status = ?
                ORDER BY order_date DESC LIMIT ?
            """, (status, limit))
        else:
            c = conn.execute("""
                SELECT * FROM orders ORDER BY order_date DESC LIMIT ?
            """, (limit,))
        orders = c.fetchall()
        conn.close()
        return orders
    
    def update_order_status(self, order_id: int, status: str,
                             file_id: str = "", note: str = ""):
        conn = self._get_conn()
        if status == "delivered":
            conn.execute("""
                UPDATE orders SET status = ?, delivery_file_id = ?,
                                 delivery_note = ?, delivered_date = ?
                WHERE order_id = ?
            """, (status, file_id, note, datetime.now().isoformat(), order_id))
        else:
            conn.execute("UPDATE orders SET status = ? WHERE order_id = ?",
                        (status, order_id))
        conn.commit()
        conn.close()
    
    # ========== TRANSACTION METHODS ==========
    def add_transaction(self, user_id: int, amount: float, type_: str,
                        method: str, trx_id: str, note: str = ""):
        conn = self._get_conn()
        conn.execute("""
            INSERT INTO transactions (user_id, amount, type, method,
                                     transaction_id, note, date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, amount, type_, method, trx_id, note,
              datetime.now().isoformat()))
        conn.commit()
        conn.close()
    
    # ========== STATISTICS ==========
    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_conn()
        stats = {}
        
        c = conn.execute("SELECT COUNT(*) as count, COALESCE(SUM(balance),0) as total FROM users")
        row = c.fetchone()
        stats['total_users'] = row[0]
        stats['total_wallet'] = row[1]
        
        c = conn.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(amount),0) as total FROM orders
        """)
        row = c.fetchone()
        stats['total_orders'] = row[0]
        stats['total_revenue'] = row[1]
        
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='pending'")
        stats['pending_orders'] = c.fetchone()[0]
        
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='delivered'")
        stats['delivered_orders'] = c.fetchone()[0]
        
        c = conn.execute("SELECT COUNT(*) FROM orders WHERE status='processing'")
        stats['processing_orders'] = c.fetchone()[0]
        
        # Today stats
        today = datetime.now().strftime("%Y-%m-%d")
        c = conn.execute("""
            SELECT COUNT(*), COALESCE(SUM(amount),0) FROM orders
            WHERE order_date LIKE ?
        """, (f"{today}%",))
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


# ==================== HELPER FUNCTIONS ====================

def get_categories() -> List[Dict]:
    """Get all categories from config"""
    return PRODUCTS_CONFIG["categories"]

def get_category(cat_id: str) -> Optional[Dict]:
    """Get category by ID"""
    for cat in get_categories():
        if cat["id"] == cat_id:
            return cat
    return None

def get_product(cat_id: str, prod_id: str) -> Optional[Dict]:
    """Get product by category and product ID"""
    cat = get_category(cat_id)
    if not cat:
        return None
    for prod in cat["products"]:
        if prod["id"] == prod_id:
            return {**prod, "category": cat}
    return None

def format_price(price: float) -> str:
    """Format price with BDT symbol"""
    return f"৳{price:,.0f}"

def generate_order_id() -> str:
    """Generate unique order ID"""
    chars = string.ascii_uppercase + string.digits
    return "ORD" + "".join(random.choices(chars, k=8))

def get_status_emoji(status: str) -> str:
    """Get status emoji"""
    emojis = {
        "pending": "⏳",
        "processing": "🔄", 
        "delivered": "✅",
        "cancelled": "❌",
        "refunded": "💰",
        "completed": "✅"
    }
    return emojis.get(status, "❓")


# ==================== KEYBOARD BUILDERS ====================

def main_menu_kb(user_id: int = None) -> InlineKeyboardMarkup:
    """🏠 Main Menu Keyboard — Premium Design"""
    builder = InlineKeyboardBuilder()
    
    # Check if user is admin
    is_admin = user_id in ADMIN_IDS if user_id else False
    
    builder.button(text=f"{EMOJIS['cart']} Buy TopUp", callback_data="categories", style="primary")
    builder.button(text=f"{EMOJIS['wallet']} My Wallet", callback_data="my_wallet", style="success")
    builder.button(text=f"{EMOJIS['package']} My Orders", callback_data="my_orders")
    builder.button(text=f"{EMOJIS['gift']} Promotions", callback_data="promotions")
    builder.button(text=f"{EMOJIS['phone']} Support", callback_data="support")
    builder.button(text=f"{EMOJIS['star']} Rate Us", callback_data="rate")
    
    if is_admin:
        builder.button(text=f"{EMOJIS['admin']} Admin Panel", callback_data="admin_menu", style="danger")
    
    # 2 buttons per row
    builder.adjust(2, 2, 2)
    
    return builder.as_markup()


def categories_kb() -> InlineKeyboardMarkup:
    """📂 Categories Keyboard"""
    builder = InlineKeyboardBuilder()
    
    for cat in get_categories():
        if cat["id"] == "topup":
            continue  # Skip wallet top-up from main listing
        style = cat.get("color", "primary")
        builder.button(
            text=f"{cat['emoji']} {cat['name']}",
            callback_data=f"cat_{cat['id']}",
            style=style
        )
    
    builder.button(text=f"{EMOJIS['wallet']} {EMOJIS['plus']} Wallet Top-Up", callback_data="cat_topup", style="success")
    builder.button(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")
    
    builder.adjust(2, 2, 2, 2, 1)
    
    return builder.as_markup()


def products_kb(cat_id: str, page: int = 0) -> InlineKeyboardMarkup:
    """📦 Products Keyboard with Pagination"""
    cat = get_category(cat_id)
    if not cat:
        return main_menu_kb()
    
    builder = InlineKeyboardBuilder()
    products = cat["products"]
    
    # Pagination: 6 products per page
    per_page = 8
    total_pages = max(1, (len(products) + per_page - 1) // per_page)
    page = min(page, total_pages - 1)
    start = page * per_page
    end = start + per_page
    page_products = products[start:end]
    
    for prod in page_products:
        price_text = format_price(prod["price"])
        if prod.get("discount", 0) > 0:
            price_text += f" 🔥-{format_price(prod['discount'])}"
        
        # Style based on popularity or price
        style = "primary"
        if prod.get("popular"):
            style = "danger"
        elif prod["price"] > 500:
            style = "success"
        
        name = prod["name"]
        if prod.get("popular"):
            name = f"{EMOJIS['fire']} {name}"
        
        builder.button(
            text=f"{name} — {price_text}",
            callback_data=f"prod_{cat_id}_{prod['id']}",
            style=style
        )
    
    # Navigation row (back + page info + next)
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"{EMOJIS['previous']} Page {page}",
                callback_data=f"page_{cat_id}_{page-1}"
            )
        )
    
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{page+1}/{total_pages}",
            callback_data="noop"
        )
    )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text=f"Page {page+2} {EMOJIS['next']}",
                callback_data=f"page_{cat_id}_{page+1}"
            )
        )
    
    builder.row(*nav_buttons)
    
    builder.button(text=f"{EMOJIS['back']} Back to Categories", callback_data="categories")
    builder.button(text=f"{EMOJIS['home']} Main Menu", callback_data="main_menu")
    
    builder.adjust(1, len(nav_buttons), 1)
    
    return builder.as_markup()


def payment_kb() -> InlineKeyboardMarkup:
    """💳 Payment Method Keyboard"""
    builder = InlineKeyboardBuilder()
    
    builder.button(text=f"{EMOJIS['bank']} bKash", callback_data="pay_bkash", style="success")
    builder.button(text=f"{EMOJIS['bank']} Nagad", callback_data="pay_nagad", style="primary")
    builder.button(text=f"{EMOJIS['rocket']} Rocket", callback_data="pay_rocket", style="danger")
    builder.button(text=f"{EMOJIS['card']} UPI", callback_data="pay_upi", style="primary")
    builder.button(text=f"{EMOJIS['wallet']} Wallet Balance", callback_data="pay_wallet", style="success")
    builder.button(text=f"{EMOJIS['back']} Change Product", callback_data="prod_back")
    
    builder.adjust(2, 2, 1, 1)
    
    return builder.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    """🔐 Admin Panel Keyboard"""
    builder = InlineKeyboardBuilder()
    
    stats = db.get_stats()
    
    builder.button(text=f"{EMOJIS['chart']} Dashboard", callback_data="admin_dashboard", style="primary")
    builder.button(text=f"{EMOJIS['package']} Orders ({stats['total_orders']})", callback_data="admin_orders", style="success")
    builder.button(text=f"{EMOJIS['clock']} Pending ({stats['pending_orders']})", callback_data="admin_pending", style="danger")
    builder.button(text=f"{EMOJIS['money']} Add Balance", callback_data="admin_add_balance", style="success")
    builder.button(text=f"{EMOJIS['rocket']} Deliver Order", callback_data="admin_deliver", style="primary")
    builder.button(text=f"{EMOJIS['pen']} Edit Products", callback_data="admin_edit_products")
    builder.button(text=f"{EMOJIS['message']} Broadcast", callback_data="admin_broadcast")
    builder.button(text=f"{EMOJIS['users']} Users ({stats['total_users']})", callback_data="admin_users")
    builder.button(text=f"{EMOJIS['chart']} Full Stats", callback_data="admin_stats")
    builder.button(text=f"{EMOJIS['back']} Main Menu", callback_data="main_menu")
    
    builder.adjust(2, 2, 2, 2, 2)
    
    return builder.as_markup()


# ==================== START HANDLER ====================

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """🚀 /start command — Welcome screen"""
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
        f"{EMOJIS['bullet']} {EMOJIS['netflic']} Netflix, YouTube Premium, Crunchyroll\n"
        f"{EMOJIS['bullet']} {EMOJIS['gift']} Gift Cards & Social Media Services\n\n"
        
        f"{EMOJIS['lightning']} **Key Features:**\n"
        f"{EMOJIS['bullet']} {EMOJIS['rocket']} **Instant AI Auto-Delivery**\n"
        f"{EMOJIS['bullet']} {EMOJIS['shield']} **100% Secure & Trusted**\n"
        f"{EMOJIS['bullet']} {EMOJIS['money']} **Best Prices in Bangladesh**\n"
        f"{EMOJIS['bullet']} {EMOJIS['phone']} **24/7 Customer Support**\n\n"
        
        f"{EMOJIS['arrow']} Use the buttons below to get started!"
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=main_menu_kb(user.id),
        parse_mode="Markdown"
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """🔐 /admin command — Admin access"""
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer(f"{EMOJIS['cross']} Unauthorized access!")
    
    await message.answer(
        f"{EMOJIS['admin']} **Admin Panel**\n\n"
        f"Welcome to the admin control center.\n"
        f"Manage orders, users, products & broadcast.",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )


# ==================== CALLBACK QUERY HANDLER ====================

@dp.callback_query()
async def callback_handler(call: CallbackQuery, state: FSMContext):
    """Main callback handler"""
    data = call.data
    user_id = call.from_user.id
    
    # Update activity
    db.update_user_activity(user_id)
    
    # Check banned users
    user = db.get_user(user_id)
    if user and user["is_banned"] and not user_id in ADMIN_IDS:
        return await call.answer(f"{EMOJIS['cross']} You are banned!", show_alert=True)
    
    # ========== MAIN MENU ==========
    if data == "main_menu":
        await state.clear()
        await call.message.edit_text(
            f"{EMOJIS['home']} **Main Menu**\n\nChoose an option:",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== CATEGORIES ==========
    if data == "categories":
        await state.clear()
        await call.message.edit_text(
            f"{EMOJIS['cart']} **Select Category**\n\n"
            f"Choose what you want to purchase:",
            reply_markup=categories_kb(),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== CATEGORY SELECTED ==========
    if data.startswith("cat_"):
        cat_id = data[4:]
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Category not found!", show_alert=True)
        
        await state.update_data(category=cat_id)
        
        desc_text = f"\n\n{cat['description']}\n" if cat.get("description") else ""
        
        await call.message.edit_text(
            f"{cat['emoji']} **{cat['name']}**{desc_text}\n\n"
            f"Select your package below:",
            reply_markup=products_kb(cat_id),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== PAGINATION ==========
    if data.startswith("page_"):
        parts = data.split("_")
        cat_id = parts[1]
        page = int(parts[2])
        
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Error!", show_alert=True)
        
        await call.message.edit_text(
            f"{cat['emoji']} **{cat['name']}**\n\n"
            f"Select your package below:",
            reply_markup=products_kb(cat_id, page),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== PRODUCT SELECTED ==========
    if data.startswith("prod_"):
        parts = data.split("_")
        cat_id = parts[1]
        prod_id = "_".join(parts[2:])  # Handle product IDs with underscores
        
        product = get_product(cat_id, prod_id)
        if not product:
            return await call.answer(f"{EMOJIS['cross']} Product not found!", show_alert=True)
        
        cat = product["category"]
        
        # If this is wallet top-up, process directly
        if cat_id == "topup":
            # Go to payment directly for balance top-up
            await state.update_data(
                product=product,
                category=cat
            )
            
            await call.message.edit_text(
                f"{EMOJIS['wallet']} **{product['name']}**\n\n"
                f"Price: {format_price(product['price'])}\n"
                f"Bonus: +{format_price(product.get('discount', 0))} Free\n\n"
                f"Select payment method:",
                reply_markup=payment_kb(),
                parse_mode="Markdown"
            )
            await state.set_state(OrderStates.selecting_payment)
            return await call.answer()
        
        # Save product to state
        await state.update_data(
            product=product,
            category=cat
        )
        
        # Build product info
        discount_text = ""
        if product.get("discount", 0) > 0:
            discount_text = f"\n{EMOJIS['fire']} **Discount:** -{format_price(product['discount'])}"
        
        popular_text = ""
        if product.get("popular"):
            popular_text = f"\n{EMOJIS['fire']} **Popular Choice!**"
        
        await call.message.edit_text(
            f"{cat['emoji']} **{product['name']}**\n\n"
            f"{EMOJIS['money']} Price: **{format_price(product['price'])}**{discount_text}"
            f"{popular_text}\n\n"
            f"{EMOJIS['info']} **{cat.get('input_label', 'Enter your details:')}**",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Back to Products",
                    callback_data=f"cat_{cat_id}"
                )]
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.entering_input)
        return await call.answer()
    
    # ========== PRODUCT BACK ==========
    if data == "prod_back":
        state_data = await state.get_data()
        cat_id = state_data.get("category", {}).get("id", "freefire")
        await call.message.edit_text(
            f"Select your package below:",
            reply_markup=products_kb(cat_id),
            parse_mode="Markdown"
        )
        await state.set_state(OrderStates.selecting_product)
        return await call.answer()
    
    # ========== PAYMENT METHOD ==========
    if data.startswith("pay_"):
        method = data[4:]
        state_data = await state.get_data()
        product = state_data.get("product", {})
        
        method_names = {
            "bkash": "bKash",
            "nagad": "Nagad", 
            "rocket": "Rocket",
            "upi": "UPI",
            "wallet": "Wallet Balance"
        }
        
        method_numbers = {
            "bkash": BKASH_NUMBER,
            "nagad": NAGAD_NUMBER,
            "rocket": ROCKET_NUMBER,
            "upi": UPI_ID
        }
        
        await state.update_data(payment_method=method)
        
        if method == "wallet":
            # Check balance
            user = db.get_user(user_id)
            price = product.get("price", 0)
            if not user or user["balance"] < price:
                return await call.answer(
                    f"{EMOJIS['cross']} Insufficient balance!\n"
                    f"Need: {format_price(price)}\n"
                    f"Have: {format_price(user['balance'] if user else 0)}",
                    show_alert=True
                )
            
            # Process wallet payment
            return await process_wallet_payment(call, state)
        
        else:
            # Show payment instructions
            price = product.get("price", 0)
            number = method_numbers.get(method, "Contact admin")
            
            payment_text = (
                f"{EMOJIS['money']} **Payment Instructions**\n\n"
                f"Product: **{product.get('name', 'N/A')}**\n"
                f"Amount: **{format_price(price)}**\n"
                f"Method: **{method_names.get(method, method)}**\n\n"
                f"{EMOJIS['phone']} Send to:\n"
                f"`{number}`\n\n"
                f"{EMOJIS['camera']} After sending payment, enter your\n"
                f"**Transaction ID (TrxID)** below:"
            )
            
            await call.message.edit_text(
                payment_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['back']} Change Method",
                        callback_data="prod_back"
                    )]
                ]),
                parse_mode="Markdown"
            )
            await state.set_state(OrderStates.entering_trx_id)
            return await call.answer()
    
    # ========== MY WALLET ==========
    if data == "my_wallet":
        user = db.get_user(user_id)
        if not user:
            return await call.answer(f"{EMOJIS['cross']} User not found!")
        
        wallet_text = (
            f"{EMOJIS['wallet']} **My Wallet**\n\n"
            f"Balance: **{format_price(user['balance'])}**\n"
            f"Total Spent: **{format_price(user['total_spent'])}**\n"
            f"Total Orders: **{user['total_orders']}**\n\n"
            f"{EMOJIS['arrow']} Use Wallet Top-Up to add balance!\n"
            f"{EMOJIS['arrow']} Pay with wallet for instant delivery!"
        )
        
        await call.message.edit_text(
            wallet_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['wallet']} {EMOJIS['plus']} Top-Up Wallet",
                    callback_data="cat_topup",
                    style="success"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== MY ORDERS ==========
    if data == "my_orders":
        orders = db.get_user_orders(user_id)
        
        if not orders:
            await call.message.edit_text(
                f"{EMOJIS['package']} **My Orders**\n\n"
                f"You haven't placed any orders yet!\n\n"
                f"{EMOJIS['arrow']} Start shopping from Categories!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['cart']} Browse Categories",
                        callback_data="categories",
                        style="primary"
                    )],
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['back']} Main Menu",
                        callback_data="main_menu"
                    )]
                ]),
                parse_mode="Markdown"
            )
            return await call.answer()
        
        # Show recent 8 orders
        order_text = f"{EMOJIS['package']} **My Orders**\n\n"
        for o in orders[:8]:
            status = get_status_emoji(o["status"])
            order_text += (
                f"`#{o['order_id']}` {status} "
                f"{o['product_name']}\n"
                f"   {format_price(o['amount'])} — {o['status'].upper()}\n\n"
            )
        
        if len(orders) > 8:
            order_text += f"\n... and {len(orders)-8} more orders"
        
        await call.message.edit_text(
            order_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== PROMOTIONS ==========
    if data == "promotions":
        promo_text = (
            f"{EMOJIS['gift']} **Promotions & Offers**\n\n"
            f"{EMOJIS['fire']} **New User Offer:**\n"
            f"Get **10% extra** on first wallet top-up!\n\n"
            f"{EMOJIS['fire']} **Referral Program:**\n"
            f"Invite friends & earn **৳50** per referral!\n\n"
            f"{EMOJIS['fire']} **Bulk Discount:**\n"
            f"Order over ৳1000 and get **5% cashback**!\n\n"
            f"{EMOJIS['fire']} **Weekly Special:**\n"
            f"Every Friday — **Free 10 diamonds** with 115+ pack!\n\n"
            f"Follow our channel for updates!"
        )
        
        await call.message.edit_text(
            promo_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['bell']} Join Channel",
                    url=f"https://t.me/{SUPPORT_USERNAME}"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== SUPPORT ==========
    if data == "support":
        support_text = (
            f"{EMOJIS['phone']} **24/7 Support**\n\n"
            f"Need help? Contact us anytime!\n\n"
            f"{EMOJIS['arrow']} **Admin:** @{SUPPORT_USERNAME}\n"
            f"{EMOJIS['arrow']} **Response:** Within 5 minutes\n"
            f"{EMOJIS['arrow']} **Hours:** 24/7/365\n\n"
            f"Common issues:\n"
            f"• Order not delivered → Contact with Order ID\n"
            f"• Payment issue → Send payment screenshot\n"
            f"• Account problem → We'll help resolve\n\n"
            f"{EMOJIS['lightning']} We're here to help!"
        )
        
        await call.message.edit_text(
            support_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['message']} Message Admin",
                    url=f"https://t.me/{SUPPORT_USERNAME}"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== RATE US ==========
    if data == "rate":
        rate_text = (
            f"{EMOJIS['star']} **Rate Our Service**\n\n"
            f"Enjoying our service? Leave a review!\n\n"
            f"Your feedback helps us improve! {EMOJIS['heart']}"
        )
        
        await call.message.edit_text(
            rate_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['star']} 5 Stars — Excellent!",
                    callback_data="rate_5"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['star']} 4 Stars — Good",
                    callback_data="rate_4"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['star']} 3 Stars — Average",
                    callback_data="rate_3"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    if data.startswith("rate_"):
        rating = data[5:]
        await call.answer(f"{EMOJIS['heart']} Thanks for rating us {rating}/5!", show_alert=True)
        await call.message.edit_text(
            f"{EMOJIS['heart']}{EMOJIS['heart']}{EMOJIS['heart']}\n\n"
            f"Thank you for your feedback!\n"
            f"Your {rating}-star rating means a lot to us!\n\n"
            f"Come back anytime! {EMOJIS['wave']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['home']} Main Menu",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        return
    
    # ========== NOOP ==========
    if data == "noop":
        return await call.answer()
    
    # ========== ADMIN CALLBACKS ==========
    if data.startswith("admin_"):
        if user_id not in ADMIN_IDS:
            return await call.answer(f"{EMOJIS['cross']} Unauthorized!", show_alert=True)
        
        action = data[6:]
        
        if action == "dashboard":
            stats = db.get_stats()
            text = (
                f"{EMOJIS['chart']} **Admin Dashboard**\n\n"
                f"{EMOJIS['divider']}\n\n"
                f"{EMOJIS['users']} Total Users: `{stats['total_users']}`\n"
                f"{EMOJIS['package']} Total Orders: `{stats['total_orders']}`\n"
                f"{EMOJIS['money']} Revenue: `{format_price(stats['total_revenue'])}`\n"
                f"{EMOJIS['wallet']} In Wallets: `{format_price(stats['total_wallet'])}`\n\n"
                f"{EMOJIS['clock']} Pending: `{stats['pending_orders']}`\n"
                f"{EMOJIS['gear']} Processing: `{stats['processing_orders']}`\n"
                f"{EMOJIS['verified']} Delivered: `{stats['delivered_orders']}`\n\n"
                f"{EMOJIS['calendar']} Today: {stats['today_orders']} orders | {format_price(stats['today_revenue'])}\n\n"
                f"{EMOJIS['green_circle']} **System Online**"
            )
            await call.message.edit_text(text, reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()
        
        elif action == "orders":
            orders = db.get_all_orders(limit=20)
            if not orders:
                await call.message.edit_text(
                    f"{EMOJIS['package']} No orders found.",
                    reply_markup=admin_kb()
                )
                return await call.answer()
            
            text = f"{EMOJIS['package']} **Recent Orders**\n\n"
            for o in orders[:15]:
                status = get_status_emoji(o["status"])
                text += (
                    f"`#{o['order_id']}` {status} "
                    f"{o['product_name'][:20]}\n"
                    f"   👤 {o['user_id']} | {format_price(o['amount'])} | {o['status']}\n"
                )
            
            await call.message.edit_text(
                text,
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
            return await call.answer()
        
        elif action == "pending":
            orders = db.get_all_orders("pending", limit=20)
            if not orders:
                await call.message.edit_text(
                    f"{EMOJIS['verified']} No pending orders!",
                    reply_markup=admin_kb()
                )
                return await call.answer()
            
            text = f"{EMOJIS['clock']} **Pending Orders**\n\n"
            for o in orders[:15]:
                text += (
                    f"`#{o['order_id']}` 👤 `{o['user_id']}`\n"
                    f"   {o['product_name'][:20]} | {format_price(o['amount'])}\n"
                )
            
            await call.message.edit_text(
                text,
                reply_markup=admin_kb(),
                parse_mode="Markdown"
            )
            return await call.answer()
        
        elif action == "add_balance":
            await call.message.edit_text(
                f"{EMOJIS['money']} **Add User Balance**\n\n"
                f"Send the user's Telegram ID:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['back']} Admin Panel",
                        callback_data="main_menu"
                    )]
                ])
            )
            await state.set_state(AdminStates.adding_balance_user)
            return await call.answer()
        
        elif action == "deliver":
            await call.message.edit_text(
                f"{EMOJIS['rocket']} **Deliver Order**\n\n"
                f"Send the Order ID to deliver:\n"
                f"(Example: 1, 2, 3...)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['back']} Admin Panel",
                        callback_data="main_menu"
                    )]
                ])
            )
            await state.set_state(AdminStates.delivering_order)
            return await call.answer()
        
        elif action == "edit_products":
            builder = InlineKeyboardBuilder()
            for cat in get_categories():
                if cat["id"] == "topup":
                    continue
                builder.button(
                    text=f"{cat['emoji']} {cat['name']}",
                    callback_data=f"editcat_{cat['id']}",
                    style=cat.get("color", "primary")
                )
            builder.button(text=f"{EMOJIS['back']} Admin Panel", callback_data="main_menu")
            builder.adjust(2, 2, 2, 2, 1)
            
            await call.message.edit_text(
                f"{EMOJIS['pen']} **Edit Products**\n\nSelect a category:",
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            return await call.answer()
        
        elif action == "broadcast":
            await call.message.edit_text(
                f"{EMOJIS['message']} **Broadcast Message**\n\n"
                f"Send the message to broadcast to **all users**:\n"
                f"(Can include text, emojis, and formatting)",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text=f"{EMOJIS['back']} Admin Panel",
                        callback_data="main_menu"
                    )]
                ])
            )
            await state.set_state(AdminStates.broadcasting_msg)
            return await call.answer()
        
        elif action == "stats":
            stats = db.get_stats()
            text = (
                f"{EMOJIS['chart']} **Full Statistics**\n\n"
                f"{EMOJIS['divider']}\n\n"
                f"**Users**\n"
                f"Total: `{stats['total_users']}`\n"
                f"Wallet Total: `{format_price(stats['total_wallet'])}`\n\n"
                f"**Orders**\n"
                f"Total: `{stats['total_orders']}`\n"
                f"Revenue: `{format_price(stats['total_revenue'])}`\n"
                f"Pending: `{stats['pending_orders']}`\n"
                f"Processing: `{stats['processing_orders']}`\n"
                f"Delivered: `{stats['delivered_orders']}`\n\n"
                f"**Today**\n"
                f"Orders: `{stats['today_orders']}`\n"
                f"Revenue: `{format_price(stats['today_revenue'])}`\n"
            )
            await call.message.edit_text(text, reply_markup=admin_kb(), parse_mode="Markdown")
            return await call.answer()
        
        elif action == "users":
            users = db.get_all_users()
            total = len(users)
            banned = sum(1 for u in users if u["is_banned"])
            active = sum(1 for u in users if not u["is_banned"])
            with_balance = sum(1 for u in users if u["balance"] > 0)
            
            text = (
                f"{EMOJIS['users']} **User Management**\n\n"
                f"Total Users: `{total}`\n"
                f"Active: `{active}`\n"
                f"Banned: `{banned}`\n"
                f"With Balance: `{with_balance}`\n\n"
                f"**Actions:**\n"
                f"{EMOJIS['arrow']} Use /ban [user_id] to ban\n"
                f"{EMOJIS['arrow']} Use /unban [user_id] to unban\n"
                f"{EMOJIS['arrow']} Use /user [user_id] for details"
            )
            
            builder = InlineKeyboardBuilder()
            builder.button(text=f"{EMOJIS['lock']} Ban User", callback_data="admin_ban_user", style="danger")
            builder.button(text=f"{EMOJIS['unlock']} Unban User", callback_data="admin_unban_user", style="success")
            builder.button(text=f"{EMOJIS['money']} Add Balance", callback_data="admin_add_balance", style="primary")
            builder.button(text=f"{EMOJIS['back']} Admin Panel", callback_data="main_menu")
            builder.adjust(2, 1, 1)
            
            await call.message.edit_text(
                text,
                reply_markup=builder.as_markup(),
                parse_mode="Markdown"
            )
            return await call.answer()
        
        elif action == "ban_user":
            await call.message.edit_text(
                f"{EMOJIS['lock']} **Ban User**\n\nSend the user's Telegram ID:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin", callback_data="main_menu")]
                ])
            )
            await state.set_state(AdminStates.banning_user)
            return await call.answer()
        
        elif action == "unban_user":
            await call.message.edit_text(
                f"{EMOJIS['unlock']} **Unban User**\n\nSend the user's Telegram ID:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"{EMOJIS['back']} Admin", callback_data="main_menu")]
                ])
            )
            await state.set_state(AdminStates.unbanning_user)
            return await call.answer()
    
    # ========== EDIT CATEGORY PRODUCTS ==========
    if data.startswith("editcat_"):
        cat_id = data[8:]
        cat = get_category(cat_id)
        if not cat:
            return await call.answer(f"{EMOJIS['cross']} Not found!")
        
        builder = InlineKeyboardBuilder()
        for prod in cat["products"]:
            name = prod["name"][:20]
            price = format_price(prod["price"])
            builder.button(
                text=f"{name} — {price}",
                callback_data=f"editprod_{cat_id}_{prod['id']}"
            )
        builder.button(text=f"{EMOJIS['back']} Categories", callback_data="admin_edit_products")
        builder.adjust(1)
        
        await call.message.edit_text(
            f"{cat['emoji']} **{cat['name']}** — Products:\n\n"
            f"Click a product to edit:",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    # ========== EDIT PRODUCT ==========
    if data.startswith("editprod_"):
        parts = data.split("_")
        cat_id = parts[1]
        prod_id = "_".join(parts[2:])
        
        product = get_product(cat_id, prod_id)
        if not product:
            return await call.answer(f"{EMOJIS['cross']} Not found!")
        
        await state.update_data(edit_cat=cat_id, edit_prod=prod_id)
        
        builder = InlineKeyboardBuilder()
        builder.button(text=f"{EMOJIS['pen']} Edit Name", callback_data="edit_name", style="primary")
        builder.button(text=f"{EMOJIS['money']} Edit Price", callback_data="edit_price", style="success")
        builder.button(text=f"{EMOJIS['back']} Back", callback_data=f"editcat_{cat_id}")
        builder.adjust(2, 1)
        
        await call.message.edit_text(
            f"{EMOJIS['pen']} **Editing:** {product['name']}\n"
            f"Price: {format_price(product['price'])}\n\n"
            f"Choose what to edit:",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        return await call.answer()
    
    if data == "edit_name":
        await call.message.edit_text(
            f"{EMOJIS['pen']} Send the new product name:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="admin_edit_products")]
            ])
        )
        await state.set_state(AdminStates.editing_product_name)
        return await call.answer()
    
    if data == "edit_price":
        await call.message.edit_text(
            f"{EMOJIS['money']} Send the new price (number only):",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"{EMOJIS['back']} Back", callback_data="admin_edit_products")]
            ])
        )
        await state.set_state(AdminStates.editing_product_price)
        return await call.answer()


# ==================== WALLET PAYMENT PROCESSING ====================

async def process_wallet_payment(call: CallbackQuery, state: FSMContext):
    """Process payment via wallet balance"""
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    user_input = state_data.get("user_input", "Wallet TopUp")
    user_id = call.from_user.id
    price = product.get("price", 0)
    discount = product.get("discount", 0)
    actual_deduct = price  # ওয়ালেট টপ-আপের জন্য
    
    # Check balance
    user = db.get_user(user_id)
    if not user or user["balance"] < actual_deduct:
        return await call.answer(
            f"{EMOJIS['cross']} Insufficient balance!\nYou need {format_price(actual_deduct)}"
            f"\nYour balance: {format_price(user['balance'] if user else 0)}",
            show_alert=True
        )
    
    # Deduct balance
    db.update_balance(user_id, -actual_deduct)
    
    # For wallet top-up, add bonus
    if cat.get("id") == "topup":
        bonus = discount
        db.update_balance(user_id, price + bonus)
        
        # Record transaction
        db.add_transaction(user_id, price, "topup", "Wallet",
                          f"WALLET_{datetime.now().timestamp():.0f}",
                          f"Auto top-up: +{format_price(price+bonus)}")
        
        await call.message.edit_text(
            f"{EMOJIS['verified']} **Wallet Top-Up Successful!**\n\n"
            f"Amount: **{format_price(price)}**\n"
            f"Bonus: **+{format_price(bonus)}**\n"
            f"Total Added: **{format_price(price + bonus)}**\n\n"
            f"New Balance: **{format_price(user['balance'] - actual_deduct + price + bonus)}**\n\n"
            f"{EMOJIS['sparkle']} Thank you for using TopUp Store BD!",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
    else:
        # For regular products — create order and auto-deliver
        trx_id = f"WALLET_{datetime.now().timestamp():.0f}"
        order_id = db.add_order(
            user_id, product.get("name", ""),
            cat.get("name", ""),
            price, 1, user_input,
            "Wallet Balance", trx_id
        )
        
        db.update_order_status(order_id, "delivered", note="Auto-delivered via wallet payment")
        
        await call.message.edit_text(
            f"{EMOJIS['verified']} **Order Successful!**\n\n"
            f"Order #`{order_id}`\n"
            f"Product: **{product['name']}**\n"
            f"Amount: **{format_price(price)}**\n"
            f"Paid via: **Wallet Balance**\n\n"
            f"{EMOJIS['rocket']} **Auto-Delivered!**\n"
            f"Your order has been processed instantly!\n\n"
            f"{EMOJIS['sparkle']} Thank you for your purchase!",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"{EMOJIS['lightning']} **Auto-Delivered via Wallet**\n\n"
                    f"Order #`{order_id}`\n"
                    f"👤 User: [{call.from_user.first_name}](tg://user?id={user_id})\n"
                    f"📦 {product['name']}\n"
                    f"💰 {format_price(price)}\n"
                    f"💳 Wallet Balance",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    await state.clear()


# ==================== MESSAGE HANDLERS — USER INPUT ====================

@dp.message(OrderStates.entering_input)
async def process_user_input(message: Message, state: FSMContext):
    """Process user detail input (UID, email, etc.)"""
    user_input = message.text.strip()
    
    if not user_input or len(user_input) < 2:
        return await message.answer(
            f"{EMOJIS['cross']} Please enter valid details!\n"
            f"Minimum 2 characters required."
        )
    
    await state.update_data(user_input=user_input)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    price = product.get("price", 0)
    
    await message.answer(
        f"{EMOJIS['verified']} **Details Received!**\n"
        f"Input: `{user_input}`\n\n"
        f"Product: **{product.get('name', '')}**\n"
        f"Price: **{format_price(price)}**\n\n"
        f"{EMOJIS['arrow']} Now select payment method:",
        reply_markup=payment_kb(),
        parse_mode="Markdown"
    )
    await state.set_state(OrderStates.selecting_payment)


@dp.message(OrderStates.entering_trx_id)
async def process_trx_id(message: Message, state: FSMContext):
    """Process transaction ID from user"""
    trx_id = message.text.strip()
    
    if not trx_id:
        return await message.answer(
            f"{EMOJIS['cross']} Please enter a valid Transaction ID!"
        )
    
    await state.update_data(transaction_id=trx_id)
    state_data = await state.get_data()
    product = state_data.get("product", {})
    cat = state_data.get("category", {})
    user_input = state_data.get("user_input", "")
    payment_method = state_data.get("payment_method", "")
    user_id = message.from_user.id
    price = product.get("price", 0)
    
    method_names = {
        "bkash": "bKash", "nagad": "Nagad",
        "rocket": "Rocket", "upi": "UPI"
    }
    
    # For Wallet Top-Up
    if cat.get("id") == "topup":
        # Auto-add balance
        bonus = product.get("discount", 0)
        total = price + bonus
        db.update_balance(user_id, total)
        db.add_transaction(user_id, total, "topup", method_names.get(payment_method, payment_method),
                          trx_id, f"Top-up via {method_names.get(payment_method, payment_method)}")
        
        await message.answer(
            f"{EMOJIS['verified']} **Balance Added Successfully!**\n\n"
            f"Amount: **{format_price(price)}**\n"
            f"Bonus: **+{format_price(bonus)}**\n"
            f"Total Added: **{format_price(total)}**\n\n"
            f"{EMOJIS['sparkle']} Thank you for your payment!\n"
            f"Your balance has been updated.",
            reply_markup=main_menu_kb(user_id),
            parse_mode="Markdown"
        )
        
        # Notify admins
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"{EMOJIS['money']} **Balance Top-Up**\n\n"
                    f"👤 [{message.from_user.first_name}](tg://user?id={user_id})\n"
                    f"💰 {format_price(price)} + {format_price(bonus)} bonus\n"
                    f"💳 {method_names.get(payment_method, payment_method)}\n"
                    f"🔢 TrxID: `{trx_id}`\n"
                    f"✅ **Auto-Credited**",
                    parse_mode="Markdown"
                )
            except:
                pass
        
        await state.clear()
        return
    
    # Regular product order
    order_id = db.add_order(
        user_id, product.get("name", ""),
        cat.get("name", ""),
        price, 1, user_input,
        method_names.get(payment_method, payment_method),
        trx_id
    )
    
    await message.answer(
        f"{EMOJIS['verified']} **Order Placed Successfully!**\n\n"
        f"Order #`{order_id}`\n"
        f"Product: **{product.get('name', '')}**\n"
        f"Amount: **{format_price(price)}**\n"
        f"Payment: **{method_names.get(payment_method, payment_method)}**\n"
        f"TrxID: `{trx_id}`\n\n"
        f"{EMOJIS['clock']} **Status: Pending Verification**\n\n"
        f"We will notify you once verified & delivered!\n"
        f"{EMOJIS['phone']} Contact admin if any issue.",
        reply_markup=main_menu_kb(user_id),
        parse_mode="Markdown"
    )
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"{EMOJIS['bell']} **New Order!**\n\n"
                f"#`{order_id}`\n"
                f"👤 [{message.from_user.first_name}](tg://user?id={user_id})\n"
                f"📦 {product.get('name', '')}\n"
                f"💰 {format_price(price)}\n"
                f"📝 ID: `{user_input}`\n"
                f"💳 {method_names.get(payment_method, payment_method)}\n"
                f"🔢 TrxID: `{trx_id}`",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await state.clear()


# ==================== ADMIN MESSAGE HANDLERS ====================

@dp.message(AdminStates.adding_balance_user)
async def admin_balance_user(message: Message, state: FSMContext):
    """Admin: Receive target user ID"""
    try:
        target_id = int(message.text.strip())
        await state.update_data(target_user=target_id)
        
        user = db.get_user(target_id)
        if user:
            name = user["first_name"] or "Unknown"
            balance = user["balance"]
            await message.answer(
                f"👤 **User Found:** `{target_id}`\n"
                f"Name: {name}\n"
                f"Current Balance: {format_price(balance)}\n\n"
                f"Send the amount to add:",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                f"⚠️ User `{target_id}` not found in database.\n"
                f"Send amount anyway? (They'll get it when they start the bot)",
                parse_mode="Markdown"
            )
        
        await state.set_state(AdminStates.adding_balance_amount)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID. Send a numeric Telegram ID:")


@dp.message(AdminStates.adding_balance_amount)
async def admin_balance_amount(message: Message, state: FSMContext):
    """Admin: Receive amount to add"""
    try:
        amount = float(message.text.strip())
        if amount <= 0 or amount > 1000000:
            return await message.answer(f"{EMOJIS['cross']} Invalid amount (1-1000000):")
        
        state_data = await state.get_data()
        target_id = state_data.get("target_user")
        
        db.update_balance(target_id, amount)
        db.add_transaction(target_id, amount, "admin_add", "Admin",
                          f"ADMIN_{datetime.now():%Y%m%d%H%M%S}",
                          f"Added by admin @{message.from_user.username or 'admin'}")
        
        await message.answer(
            f"{EMOJIS['verified']} **Balance Added!**\n\n"
            f"👤 User: `{target_id}`\n"
            f"💰 Amount: **+{format_price(amount)}**\n"
            f"✅ **Successfully credited!**",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        
        # Notify user
        try:
            await bot.send_message(
                target_id,
                f"{EMOJIS['money']} **Balance Added!**\n\n"
                f"+**{format_price(amount)}** has been added to your wallet!\n"
                f"Check your balance in Profile.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        await state.clear()
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid amount. Send a number:")


@dp.message(AdminStates.delivering_order)
async def admin_deliver_order(message: Message, state: FSMContext):
    """Admin: Receive order ID to deliver"""
    try:
        order_id = int(message.text.strip())
        order = db.get_order(order_id)
        
        if not order:
            return await message.answer(f"{EMOJIS['cross']} Order `{order_id}` not found!")
        
        await state.update_data(deliver_order_id=order_id)
        
        await message.answer(
            f"📦 **Order #`{order_id}` Found**\n\n"
            f"Product: {order['product_name']}\n"
            f"User: `{order['user_id']}`\n"
            f"Amount: {format_price(order['amount'])}\n"
            f"Status: {order['status']}\n\n"
            f"Send a delivery **screenshot/photo** or type delivery note:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"{EMOJIS['lightning']} Deliver Without Photo",
                    callback_data="deliver_no_photo"
                )],
                [InlineKeyboardButton(
                    text=f"{EMOJIS['back']} Admin Panel",
                    callback_data="main_menu"
                )]
            ]),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.delivering_file)
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid Order ID. Send a number:")


@dp.message(AdminStates.delivering_file)
async def admin_deliver_file(message: Message, state: FSMContext):
    """Admin: Receive delivery file/photo"""
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
    
    file_id = ""
    note = "Delivered by admin ✅"
    
    if message.photo:
        file_id = message.photo[-1].file_id
        note = message.caption or "Delivered with proof ✅"
    elif message.document:
        file_id = message.document.file_id
        note = message.caption or "Delivered with file ✅"
    else:
        note = message.text or "Delivered by admin ✅"
    
    db.update_order_status(order_id, "delivered", file_id, note)
    
    order = db.get_order(order_id)
    
    await message.answer(
        f"{EMOJIS['verified']} **Order #`{order_id}` Delivered!**\n\n"
        f"📝 Note: {note}\n"
        f"✅ Status updated successfully!",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    # Notify user
    if order:
        try:
            if file_id:
                await bot.send_photo(
                    order["user_id"],
                    file_id,
                    caption=(
                        f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                        f"#`{order_id}`\n"
                        f"📦 {order['product_name']}\n"
                        f"{note}\n\n"
                        f"{EMOJIS['sparkle']} Thank you for shopping with TopUp Store BD!"
                    ),
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    order["user_id"],
                    f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                    f"#`{order_id}`\n"
                    f"📦 {order['product_name']}\n"
                    f"{EMOJIS['file']} {note}\n\n"
                    f"{EMOJIS['sparkle']} Thank you for shopping with TopUp Store BD!",
                    parse_mode="Markdown"
                )
        except Exception as e:
            await message.answer(f"⚠️ Could not notify user: {e}")
    
    await state.clear()


@dp.callback_query(lambda c: c.data == "deliver_no_photo")
async def deliver_no_photo(call: CallbackQuery, state: FSMContext):
    """Deliver without photo"""
    state_data = await state.get_data()
    order_id = state_data.get("deliver_order_id")
    
    db.update_order_status(order_id, "delivered", note="Delivered without photo (admin note)")
    
    order = db.get_order(order_id)
    
    await call.message.edit_text(
        f"{EMOJIS['verified']} **Order #`{order_id}` Delivered!**\n\n"
        f"✅ Delivered without photo.",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    if order:
        try:
            await bot.send_message(
                order["user_id"],
                f"{EMOJIS['verified']} **Order Delivered!**\n\n"
                f"#`{order_id}`\n"
                f"📦 {order['product_name']}\n"
                f"✅ Your order has been completed!\n\n"
                f"{EMOJIS['sparkle']} Thank you for your purchase!",
                parse_mode="Markdown"
            )
        except:
            pass
    
    await state.clear()


@dp.message(AdminStates.broadcasting_msg)
async def admin_broadcast_msg(message: Message, state: FSMContext):
    """Admin: Receive broadcast message"""
    msg_text = message.text or message.caption or "📢 Broadcast"
    
    await state.update_data(broadcast_text=msg_text)
    
    # Count users
    users = db.get_all_users()
    total = len(users)
    active = sum(1 for u in users if not u["is_banned"])
    
    await message.answer(
        f"{EMOJIS['message']} **Broadcast Preview**\n\n"
        f"{msg_text[:200]}{'...' if len(msg_text) > 200 else ''}\n\n"
        f"Total users: `{total}`\n"
        f"Will receive: `{active}`\n\n"
        f"Confirm broadcast?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJIS['verified']} Yes, Send!",
                    callback_data="broadcast_confirm",
                    style="danger"
                ),
                InlineKeyboardButton(
                    text=f"{EMOJIS['cross']} Cancel",
                    callback_data="main_menu",
                    style="primary"
                )
            ]
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.broadcasting_confirm)


@dp.callback_query(lambda c: c.data == "broadcast_confirm")
async def admin_broadcast_confirm(call: CallbackQuery, state: FSMContext):
    """Execute broadcast"""
    if call.from_user.id not in ADMIN_IDS:
        return await call.answer(f"{EMOJIS['cross']} Unauthorized!", show_alert=True)
    
    state_data = await state.get_data()
    msg_text = state_data.get("broadcast_text", "📢 Broadcast")
    
    await call.message.edit_text(
        f"{EMOJIS['message']} **Broadcasting...**\n\n"
        f"Sending messages to all users...\n"
        f"{EMOJIS['clock']} This may take a while.",
        parse_mode="Markdown"
    )
    
    users = db.get_all_users()
    sent = 0
    failed = 0
    
    for user in users:
        if user["is_banned"]:
            continue
        try:
            await bot.send_message(user["user_id"], msg_text, parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)  # Rate limit protection
        except:
            failed += 1
    
    await call.message.edit_text(
        f"{EMOJIS['verified']} **Broadcast Complete!**\n\n"
        f"✅ Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`\n"
        f"📝 Total: `{sent + failed}`",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
    
    await state.clear()


# ==================== BAN/UNBAN HANDLERS ====================

@dp.message(AdminStates.banning_user)
async def admin_ban_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        if user_id in ADMIN_IDS:
            return await message.answer(f"{EMOJIS['cross']} Cannot ban admin!")
        
        db.set_ban(user_id, True)
        
        await message.answer(
            f"{EMOJIS['lock']} **User Banned**\n\n"
            f"👤 `{user_id}` has been banned.",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        await state.clear()
        
        try:
            await bot.send_message(user_id, f"{EMOJIS['cross']} You have been banned from TopUp Store BD.")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")


@dp.message(AdminStates.unbanning_user)
async def admin_unban_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        db.set_ban(user_id, False)
        
        await message.answer(
            f"{EMOJIS['unlock']} **User Unbanned**\n\n"
            f"👤 `{user_id}` has been unbanned.",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        await state.clear()
        
        try:
            await bot.send_message(user_id, f"{EMOJIS['verified']} You have been unbanned from TopUp Store BD.")
        except:
            pass
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid ID!")


# ==================== EDIT PRODUCT HANDLERS ====================

@dp.message(AdminStates.editing_product_name)
async def admin_edit_name(message: Message, state: FSMContext):
    state_data = await state.get_data()
    cat_id = state_data.get("edit_cat")
    prod_id = state_data.get("edit_prod")
    new_name = message.text.strip()
    
    # Update in-memory (would need file save for persistence)
    cat = get_category(cat_id)
    if cat:
        for prod in cat["products"]:
            if prod["id"] == prod_id:
                prod["name"] = new_name
                break
    
    await message.answer(
        f"{EMOJIS['verified']} **Product Updated!**\n\n"
        f"New name: {new_name}\n"
        f"(Note: This is in-memory. Edit products.json for permanent changes)",
        reply_markup=admin_kb(),
        parse_mode="Markdown"
    )
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
        
        await message.answer(
            f"{EMOJIS['verified']} **Price Updated!**\n\n"
            f"New price: {format_price(new_price)}\n"
            f"(Note: This is in-memory. Edit products.json for permanent changes)",
            reply_markup=admin_kb(),
            parse_mode="Markdown"
        )
        await state.clear()
    except ValueError:
        await message.answer(f"{EMOJIS['cross']} Invalid price! Send a number:")


# ==================== MAIN FUNCTION ====================

async def main():
    """Main entry point"""
    print(f"""
    ╔══════════════════════════════════════════════════════╗
    ║            🚀 TOPUP STORE BD — BOT v2.0             ║
    ║                                                      ║
    ║   🤖 Bot: @{BOT_USERNAME}                              
    ║   👤 Admins: {len(ADMIN_IDS)} configured                         
    ║   📦 Products: {sum(len(c['products']) for c in get_categories())} items                       
    ║   📂 Categories: {len(get_categories())}                                 
    ║   💾 Database: SQLite                               
    ║   🎨 Style: Premium (Bot API 9.4+)                  
    ║                                                      ║
    ║   🟢 BOT IS RUNNING...                               ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
