# Copyright (c) 2025 Gagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from shared_client import client as bot_client, app
from telethon import events
from datetime import timedelta
from config import OWNER_ID
from utils.func import add_premium_user, is_private_chat
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton as IK, InlineKeyboardMarkup as IKM
from config import OWNER_ID, JOIN_LINK as JL , ADMIN_CONTACT as AC
import base64 as spy
from plugins.start import subscribe


@bot_client.on(events.NewMessage(pattern='/add'))
async def add_premium_handler(event):
    if not await is_private_chat(event):
        await event.respond('This command can only be used in private chats for security reasons.')
        return
    user_id = event.sender_id
    if user_id not in OWNER_ID:
        await event.respond('This command is restricted to the bot owner.')
        return
    text = event.message.text.strip()
    parts = text.split(' ')
    if len(parts) != 4:
        await event.respond("Invalid format. Use: /add user_id duration_value duration_unit")
        return
    try:
        target_user_id = int(parts[1])
        duration_value = int(parts[2])
        duration_unit = parts[3].lower()
        valid_units = ['min', 'hours', 'days', 'weeks', 'month', 'year', 'decades']
        if duration_unit not in valid_units:
            await event.respond(f"Invalid duration unit. Choose from: {', '.join(valid_units)}")
            return
        success, result = await add_premium_user(target_user_id, duration_value, duration_unit)
        if success:
            expiry_utc = result
            expiry_ist = expiry_utc + timedelta(hours=5, minutes=30)
            formatted_expiry = expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')
            await event.respond(f"✅ User {target_user_id} added as premium member\nSubscription valid until: {formatted_expiry} (IST)")
            await bot_client.send_message(target_user_id, f"✅ Your have been added as premium member\n**Validity upto**: {formatted_expiry} (IST)")
        else:
            await event.respond(f'❌ Failed to add premium user: {result}')
    except ValueError:
        await event.respond('Invalid user ID or duration value. Both must be integers.')
    except Exception as e:
        await event.respond(f'Error: {str(e)}')


@app.on_message(filters.command("start"))
async def start_handler(client, message):
    subscription_status = await subscribe(client, message)
    if subscription_status == 1:
        return

    text = (
        "👋 **您好！欢迎使用专业版受限内容转发机器人 V3**\n\n"
        "✨ **核心功能介绍：**\n"
        "1️⃣ **保存受限内容**：自动破解并转发禁止转发/保存的频道和群组内容。\n"
        "2️⃣ **批量搬运 (/batch)**：支持按链接范围批量抓取历史消息，实现一键搬家。\n"
        "3️⃣ **私有频道支持**：登录后可访问您加入的所有私有频道。\n"
        "4️⃣ **全自动重命名**：在设置中开启后，可自动修改文件名和后缀。\n"
        "5️⃣ **自定义广告/水印**：支持自定义消息底部文字和视频水印。\n\n"
        "🚀 直接发送受限频道的**消息链接**即可开始！发送 /help 查看详细指令。"
    )

    await message.reply_text(text)

