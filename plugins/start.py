# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from shared_client import app
from pyrogram import filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from config import LOG_GROUP, OWNER_ID, FORCE_SUB

async def subscribe(app, message):
    return 0
     
@app.on_message(filters.command("set"))
async def set(_, message):
    if message.from_user.id not in OWNER_ID:
        await message.reply("You are not authorized to use this command.")
        return
     
    await app.set_bot_commands([
        BotCommand("start", "🚀 开始使用"),
        BotCommand("batch", "🫠 批量抓取内容"),
        BotCommand("login", "🔑 登录私有频道"),
        BotCommand("settings", "⚙️ 机器人设置"),
        BotCommand("help", "❓ 帮助信息"),
        BotCommand("stats", "📊 运行统计"),
        BotCommand("plan", "💰 订阅计划"),
        BotCommand("logout", "🚪 退出登录"),
        BotCommand("cancel", "🚫 取消当前操作")
    ])
 
    await message.reply("✅ Commands configured successfully!")
 
help_pages = [
    (
        "📝 **机器人指令概览 (1/2)**:\n\n"
        "1. **/login**\n"
        "> 登录您的电报账号。登录后可以抓取您加入的**私有频道**内容。\n\n"
        "2. **/batch**\n"
        "> **批量抓取**。发送起始链接和结束链接，机器人会自动搬运期间的所有内容。\n\n"
        "3. **/dl [链接]**\n"
        "> **全网视频下载**。支持 YouTube, TikTok, Instagram, Twitter 等数千个网站。直接发送链接也可触发。\n\n"
        "4. **/adl [链接]**\n"
        "> **音频提取**。下载视频并自动转换成 MP3 格式，带封面和元数据。\n\n"
        "5. **/music [关键词或链接]**\n"
        "> **音乐搜索**。支持输入歌名或 **Spotify 链接**。机器人会自动搜索并以 **320kbps 极高音质**下载音频。\n\n"
        "6. **/settings**\n"
        "> **个人设置中心**。配置自定义重命名、自定义后缀、视频水印、转发目标频道等。\n\n"
        "7. **/stats**\n"
        "> 查看机器人的当前运行状态和您的使用统计。\n\n"
    ),
    (
        "📝 **机器人指令概览 (2/2)**:\n\n"
        "8. **/cancel** 或 **/stop**\n"
        "> **停止任务**。立即取消当前的批量搬运或下载任务。\n\n"
        "9. **/logout**\n"
        "> 退出登录并清除您的 Session 数据。\n\n"
        "10. **/myplan**\n"
        "> 查看您的会员状态和额度详情。\n\n"
        "⚙️ **进阶设置说明 (/settings)**:\n"
        "- **SETCHATID**: 设置转发目标，文件处理完后会自动发到该频道。\n"
        "- **SETRENAME**: 设置全局重命名规则，支持正则替换。\n"
        "- **CAPTION**: 设置自定义文案，支持保留原始文案或完全替换。\n"
        "- **VIDEO WATERMARK**: 为所有转发的视频添加您的专属图片水印。\n\n"
        "**__由 Antigravity 强力驱动__**"
    )
]
 
async def send_or_edit_help_page(_, message, page_number):
    if page_number < 0 or page_number >= len(help_pages):
        return
     
    prev_button = InlineKeyboardButton("◀️ 上一页", callback_data=f"help_prev_{page_number}")
    next_button = InlineKeyboardButton("下一页 ▶️", callback_data=f"help_next_{page_number}")
     
    buttons = []
    if page_number > 0:
        buttons.append(prev_button)
    if page_number < len(help_pages) - 1:
        buttons.append(next_button)
     
    keyboard = InlineKeyboardMarkup([buttons])
     
    await message.delete()
     
    await message.reply(
        help_pages[page_number],
        reply_markup=keyboard
    )
 
@app.on_message(filters.command("help"))
async def help(client, message):
    join = await subscribe(client, message)
    if join == 1:
        return
     
    await send_or_edit_help_page(client, message, 0)
 
@app.on_callback_query(filters.regex(r"help_(prev|next)_(\d+)"))
async def on_help_navigation(client, callback_query):
    action, page_number = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
 
    if action == "prev":
        page_number -= 1
    elif action == "next":
        page_number += 1

    await send_or_edit_help_page(client, callback_query.message, page_number)
     
    await callback_query.answer()
 
@app.on_message(filters.command("terms") & filters.private)
async def terms(client, message):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
    await message.reply_text(terms_text)
 
@app.on_message(filters.command("plan") & filters.private)
async def plan(client, message):
    plan_text = (
        "> 💰 **Premium Price**:\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__** (terms and conditions apply).\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "   - Users are advised to wait for the process to automatically cancel before proceeding with any downloads or uploads.\n\n"
        "📜 **Terms and Conditions**: For further details and complete terms and conditions, please send /terms.\n"
    )
    await message.reply_text(plan_text)
 
@app.on_callback_query(filters.regex("see_plan"))
async def see_plan(client, callback_query):
    plan_text = (
        "> 💰**Premium Price**\n\n Starting from $2 or 200 INR accepted via **__Amazon Gift Card__** (terms and conditions apply).\n"
        "📥 **Download Limit**: Users can download up to 100,000 files in a single batch command.\n"
        "🛑 **Batch**: You will get two modes /bulk and /batch.\n"
        "   - Users are advised to wait for the process to automatically cancel before proceeding with any downloads or uploads.\n\n"
        "📜 **Terms and Conditions**: For further details and complete terms and conditions, please send /terms or click See Terms👇\n"
    )
    await callback_query.message.edit_text(plan_text)
 
@app.on_callback_query(filters.regex("see_terms"))
async def see_terms(client, callback_query):
    terms_text = (
        "> 📜 **Terms and Conditions** 📜\n\n"
        "✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.\n"
        "✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__\n"
        "✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood.\n"
    )
    await callback_query.message.edit_text(terms_text)

