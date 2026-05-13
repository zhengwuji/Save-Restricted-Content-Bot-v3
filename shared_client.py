# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from telethon import TelegramClient
from config import API_ID, API_HASH, BOT_TOKEN, STRING
from pyrogram import Client
import sys

client = TelegramClient("telethonbot", API_ID, API_HASH)
# 增加 workers 和并发数，显著提升大文件下载/上传速度
app = Client(
    "pyrogrambot", 
    ipv6=False, 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    workers=100,
    max_concurrent_transmissions=10
)
userbot = Client(
    "4gbbot", 
    ipv6=False, 
    api_id=API_ID, 
    api_hash=API_HASH, 
    session_string=STRING,
    workers=100,
    max_concurrent_transmissions=10
)

async def start_client():
    if not client.is_connected():
        await client.start(bot_token=BOT_TOKEN)
        print("SpyLib started...")
    if STRING:
        try:
            await userbot.start()
            print("Userbot started...")
        except Exception as e:
            print(f"Hey honey!! check your premium string session, it may be invalid of expire {e}")
            sys.exit(1)
    await app.start()
    print("Pyro App Started...")
    return client, app, userbot

