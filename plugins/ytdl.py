# ---------------------------------------------------
# File Name: ytdl.py (pure code)
# Description: A Pyrogram bot for downloading yt and other sites videos from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# ---------------------------------------------------

import yt_dlp
import os
import tempfile
import time
import asyncio
import random
import string
import requests
import logging
import time
import math
from shared_client import client, app
from telethon import events
from telethon.sync import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from utils.func import get_video_metadata, screenshot
from telethon.tl.functions.messages import EditMessageRequest
from devgagantools import fast_upload
from concurrent.futures import ThreadPoolExecutor
import aiohttp 
import logging
import aiofiles
from config import YT_COOKIES, INSTA_COOKIES
from mutagen.id3 import ID3, TIT2, TPE1, COMM, APIC
from mutagen.mp3 import MP3
 
logger = logging.getLogger(__name__)
 
 
thread_pool = ThreadPoolExecutor()
ongoing_downloads = {}
 
def d_thumbnail(thumbnail_url, save_path):
    try:
        response = requests.get(thumbnail_url, stream=True)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return save_path
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download thumbnail: {e}")
        return None
 
 
async def download_thumbnail_async(url, path):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                with open(path, 'wb') as f:
                    f.write(await response.read())
 
 
async def extract_audio_async(ydl_opts, url):
    def sync_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)
    return await asyncio.get_event_loop().run_in_executor(thread_pool, sync_extract)
 
 
def get_random_string(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length)) 
 
 
async def process_audio(client, event, url, cookies_env_var=None):
    cookies = None
    if cookies_env_var:
        cookies = cookies_env_var
 
    temp_cookie_path = None
    if cookies and isinstance(cookies, str) and "# Netscape HTTP Cookie File" in cookies:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', encoding='utf-8') as temp_cookie_file:
            temp_cookie_file.write(cookies)
            temp_cookie_path = temp_cookie_file.name
 
    start_time = time.time()
    random_filename = f"@team_spy_pro_{event.sender_id}"
    download_path = f"{random_filename}.mp3"
 
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{random_filename}.%(ext)s",
        'cookiefile': temp_cookie_path,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
        'quiet': False,
        'noplaylist': True,
        'ffmpeg_location': '/usr/bin',
    }
    prog = None
 
    progress_message = await event.reply("🎵 **正在提取音频... 请稍候**")
 
    try:
        try:
            info_dict = await extract_audio_async(ydl_opts, url)
        except Exception as e:
            if "Netscape format cookies file" in str(e):
                logger.warning("Invalid cookies detected, retrying without cookies.")
                ydl_opts['cookiefile'] = None
                info_dict = await extract_audio_async(ydl_opts, url)
            else:
                raise e

        title = info_dict.get('title', '提取的音频')
 
        await progress_message.edit("🏷️ **正在写入歌曲信息 (元数据)...**")
 
         
        if os.path.exists(download_path):
            def edit_metadata():
                audio_file = MP3(download_path, ID3=ID3)
                try:
                    audio_file.add_tags()
                except Exception:
                    pass
                # Improve artist extraction
                artist = info_dict.get('artist') or info_dict.get('uploader') or info_dict.get('channel') or info_dict.get('creator')
                
                # If still missing, try parsing from title (Artist - Song)
                if not artist and " - " in title:
                    artist = title.split(" - ", 1)[0]
                
                if not artist:
                    artist = "网络"
                
                audio_file.tags["TIT2"] = TIT2(encoding=3, text=title)
                audio_file.tags["TPE1"] = TPE1(encoding=3, text=artist)
 
                thumbnail_url = info_dict.get('thumbnail')
                if thumbnail_url:
                    thumbnail_path = os.path.join(tempfile.gettempdir(), "thumb.jpg")
                    asyncio.run(download_thumbnail_async(thumbnail_url, thumbnail_path))
                    with open(thumbnail_path, 'rb') as img:
                        audio_file.tags["APIC"] = APIC(
                            encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img.read()
                        )
                    os.remove(thumbnail_path)
                audio_file.save()
 
            await asyncio.to_thread(edit_metadata)
 
         
 
         
        chat_id = event.chat_id
        if os.path.exists(download_path):
            await progress_message.delete()
            prog = await client.send_message(chat_id, "📤 **正在高速上传音频...**")
            uploaded = await fast_upload(
                client, download_path, 
                reply=prog, 
                name=None,
                progress_bar_function=lambda done, total: progress_callback(done, total, chat_id)
            )
            extractor = info_dict.get('extractor_key', 'YouTube')
            if extractor.lower() in ["youtube", "youtubesearch"]:
                extractor = "YouTube"
            await client.send_file(chat_id, uploaded, caption=f"🎧 **{title}**\n\n来源平台: **{extractor}**")
            if prog:
                await prog.delete()
        else:
            await event.reply("❌ **音频提取失败：未找到生成的文件。**")
 
    except Exception as e:
        logger.exception("Error during audio extraction or upload")
        await event.reply(f"❌ **发生错误:** `{e}`")
    finally:
        if os.path.exists(download_path):
            os.remove(download_path)
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)
 
@client.on(events.NewMessage(pattern="/adl"))
async def adl_handler(event):
    user_id = event.sender_id
    if user_id in ongoing_downloads:
        await event.reply("⚠️ **您当前已有正在运行的任务，请稍候。**")
        return
 
    if len(event.message.text.split()) < 2:
        await event.reply("❌ **格式错误！**\n使用方法: `/adl [视频链接]`")
        return    
 
    url = event.message.text.split()[1]
    ongoing_downloads[user_id] = True
 
    try:
        if "instagram.com" in url:
            await process_audio(client, event, url, cookies_env_var=INSTA_COOKIES)
        elif "youtube.com" in url or "youtu.be" in url:
            await process_audio(client, event, url, cookies_env_var=YT_COOKIES)
        else:
            await process_audio(client, event, url)
    except Exception as e:
        await event.reply(f"❌ **发生错误:** `{str(e)}`")
    finally:
        ongoing_downloads.pop(user_id, None)
 
 
async def fetch_video_info(url, ydl_opts, progress_message, check_duration_and_size):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
 
        if check_duration_and_size:
             
            duration = info_dict.get('duration', 0)
            if duration and duration > 3 * 3600:   
                await progress_message.edit("**❌ __Video is longer than 3 hours. Download aborted...__**")
                return None
 
             
            estimated_size = info_dict.get('filesize_approx', 0)
            if estimated_size and estimated_size > 2 * 1024 * 1024 * 1024:   
                await progress_message.edit("**🤞 __视频超过2GB，已中止下载。__**")
                return None
 
        return info_dict
 
def download_video(url, ydl_opts):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
 
@client.on(events.NewMessage(pattern="/dl"))
async def dl_handler(event):
    user_id = event.sender_id
    if user_id in ongoing_downloads:
        await event.reply("⚠️ **您当前已有正在运行的任务，请稍候。**")
        return
 
    if len(event.message.text.split()) < 2:
        await event.reply("❌ **格式错误！**\n使用方法: `/dl [视频链接]`")
        return    
 
    url = event.message.text.split()[1]
    ongoing_downloads[user_id] = True
 
    try:
        if "instagram.com" in url:
            await process_video(client, event, url, INSTA_COOKIES, check_duration_and_size=False)
        elif "youtube.com" in url or "youtu.be" in url:
            await process_video(client, event, url, YT_COOKIES, check_duration_and_size=True)
        else:
            await process_video(client, event, url, None, check_duration_and_size=False)
    except Exception as e:
        await event.reply(f"❌ **发生错误:** `{str(e)}`")
    finally:
        ongoing_downloads.pop(user_id, None)

@client.on(events.NewMessage(pattern="/music"))
async def music_handler(event):
    user_id = event.sender_id
    if user_id in ongoing_downloads:
        await event.reply("⚠️ **您当前已有正在运行的任务，请稍候。**")
        return
    
    args = event.message.text.split(maxsplit=1)
    if len(args) < 2:
        await event.reply("❌ **请输入歌名或关键词！**\n使用方法: `/music [歌名]`\n例如: `/music 求佛`")
        return
    
    query = args[1]
    ongoing_downloads[user_id] = True
    search_url = f"ytsearch1:{query}"
    
    try:
        await process_audio(client, event, search_url, cookies_env_var=YT_COOKIES)
    except Exception as e:
        await event.reply(f"❌ **搜索/下载失败:** `{str(e)}`")
    finally:
        ongoing_downloads.pop(user_id, None)
 
 
user_progress = {}
 
def progress_callback(done, total, user_id):
     
    if user_id not in user_progress:
        user_progress[user_id] = {
            'previous_done': 0,
            'previous_time': time.time()
        }
 
     
    user_data = user_progress[user_id]
 
     
    percent = (done / total) * 100
 
     
    completed_blocks = int(percent // 10)
    remaining_blocks = 10 - completed_blocks
    progress_bar = "♦" * completed_blocks + "◇" * remaining_blocks
 
     
    done_mb = done / (1024 * 1024)   
    total_mb = total / (1024 * 1024)
 
     
    speed = done - user_data['previous_done']
    elapsed_time = time.time() - user_data['previous_time']
 
    if elapsed_time > 0:
        speed_bps = speed / elapsed_time   
        speed_mbps = (speed_bps * 8) / (1024 * 1024)   
    else:
        speed_mbps = 0
 
     
    if speed_bps > 0:
        remaining_time = (total - done) / speed_bps
    else:
        remaining_time = 0
 
     
    remaining_time_min = remaining_time / 60
 
     
    final = (
        f"╭──────────────────╮\n"
        f"│        **__Uploading...__**       \n"
        f"├──────────\n"
        f"│ {progress_bar}\n\n"
        f"│ **__Progress:__** {percent:.2f}%\n"
        f"│ **__已完成:__** {done_mb:.2f} MB / {total_mb:.2f} MB\n"
        f"│ **__速度:__** {speed_mbps:.2f} Mbps\n"
        f"│ **__剩余时间:__** {remaining_time_min:.2f} 分钟\n"
        f"╰──────────────────╯\n\n"
        f"**__正在处理您的请求...__**"
    )
 
     
    user_data['previous_done'] = done
    user_data['previous_time'] = time.time()
 
    return final
 
async def process_video(client, event, url, cookies_env_var, check_duration_and_size=False):
    start_time = time.time()
    logger.info(f"Received link: {url}")
     
    cookies = None
    if cookies_env_var:
        cookies = cookies_env_var
 
     
    random_filename = get_random_string() + ".mp4"
    download_path = os.path.abspath(random_filename)
    logger.info(f"Generated random download path: {download_path}")
 
     
    temp_cookie_path = None
    if cookies and isinstance(cookies, str) and "# Netscape HTTP Cookie File" in cookies:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.txt', encoding='utf-8') as temp_cookie_file:
            temp_cookie_file.write(cookies)
            temp_cookie_path = temp_cookie_file.name
        logger.info(f"Created temporary cookie file at: {temp_cookie_path}")
 
     
    thumbnail_file = None
    metadata = {'width': None, 'height': None, 'duration': None, 'thumbnail': None}
 
     
    ydl_opts = {
        'outtmpl': download_path,
        'format': 'best',
        'cookiefile': temp_cookie_path if temp_cookie_path else None,
        'writethumbnail': True,
        'verbose': True,
        'ffmpeg_location': '/usr/bin',
    }
    prog = None
    
    async def reply(text):
        if hasattr(event, 'reply'): 
            return await event.reply(text)
        else: 
            return await event.reply_text(text)

    progress_message = await reply("📥 **正在开始下载... 请稍候**")
    logger.info("Starting the download process...")
    try:
        try:
            info_dict = await fetch_video_info(url, ydl_opts, progress_message, check_duration_and_size)
            if not info_dict:
                return
            await asyncio.to_thread(download_video, url, ydl_opts)
        except Exception as e:
            if "Netscape format cookies file" in str(e):
                logger.warning("Invalid cookies detected, retrying without cookies.")
                ydl_opts['cookiefile'] = None
                info_dict = await fetch_video_info(url, ydl_opts, progress_message, check_duration_and_size)
                if not info_dict:
                    return
                await asyncio.to_thread(download_video, url, ydl_opts)
            else:
                raise e
        title = info_dict.get('title', '视频下载成功')
        k = await get_video_metadata(download_path)      
        W = k['width']
        H = k['height']
        D = k['duration']
        metadata['width'] = info_dict.get('width') or W
        metadata['height'] = info_dict.get('height') or H
        metadata['duration'] = int(info_dict.get('duration') or 0) or D
        thumbnail_url = info_dict.get('thumbnail', None)
        THUMB = None
 
         
        if thumbnail_url:
            thumbnail_file = os.path.join(tempfile.gettempdir(), get_random_string() + ".jpg")
            downloaded_thumb = d_thumbnail(thumbnail_url, thumbnail_file)
            if downloaded_thumb:
                logger.info(f"Thumbnail saved at: {downloaded_thumb}")
 
        sender_id = event.sender_id if hasattr(event, 'sender_id') else event.from_user.id
        if thumbnail_file:
            THUMB = thumbnail_file
        else:
            THUMB = await screenshot(download_path, metadata['duration'], sender_id)

        chat_id = event.chat_id if hasattr(event, 'chat_id') else event.chat.id
        SIZE = 2 * 1024 * 1024
        
        if os.path.exists(download_path) and os.path.getsize(download_path) > SIZE:
            prog = await reply("🚀 **文件较大，正在分段上传中...**")
            await split_and_upload_file(app, chat_id, download_path, title)
            await prog.delete()
         
        if os.path.exists(download_path):
            await progress_message.delete()
            prog = await reply("📤 **正在高速上传到电报...**")
            
            from pyrogram.types import DocumentAttributeVideo as PyroVideo
            
            uploaded = await fast_upload(
                client, download_path,
                reply=prog,
                progress_bar_function=lambda done, total: progress_callback(done, total, chat_id)
            )
            
            if hasattr(event, 'sender_id'): 
                await client.send_file(
                    chat_id,
                    uploaded,
                    caption=f"**{title}**",
                    attributes=[
                        DocumentAttributeVideo(
                            duration=metadata['duration'],
                            w=metadata['width'],
                            h=metadata['height'],
                            supports_streaming=True
                        )
                    ],
                    thumb=THUMB if THUMB else None
                )
            else: 
                await app.send_video(
                    chat_id,
                    video=download_path,
                    caption=f"**{title}**",
                    duration=metadata['duration'],
                    width=metadata['width'],
                    height=metadata['height'],
                    thumb=THUMB if THUMB else None,
                    progress=progress_bar,
                    progress_args=("📤 **正在上传视频...**", prog, time.time())
                )

            if prog:
                try: await prog.delete()
                except: pass
        else:
            await reply("❌ **下载失败：未找到生成的文件。**")
    except Exception as e:
        logger.exception("An error occurred during download or upload.")
        await reply(f"❌ **发生错误:** `{str(e)}`")
    finally:
         
        if os.path.exists(download_path):
            os.remove(download_path)
        if temp_cookie_path and os.path.exists(temp_cookie_path):
            os.remove(temp_cookie_path)
        if thumbnail_file and os.path.exists(thumbnail_file):
            os.remove(thumbnail_file)

from pyrogram import filters
from shared_client import app as pyro_app

@pyro_app.on_message(filters.regex(r"https?://(www\.)?(youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com|facebook\.com|terabox\.com|spotify\.com)") & filters.private)
async def auto_ytdl(c, m):
    user_id = m.from_user.id
    if user_id in ongoing_downloads:
        await m.reply_text("⚠️ **您当前已有正在运行的任务，请稍候。**")
        return
    
    url = m.text
    ongoing_downloads[user_id] = True
    try:
        from shared_client import client as telethon_client
        if "instagram.com" in url:
            await process_video(telethon_client, m, url, INSTA_COOKIES, check_duration_and_size=False)
        elif "youtube.com" in url or "youtu.be" in url:
            await process_video(telethon_client, m, url, YT_COOKIES, check_duration_and_size=True)
        else:
            await process_video(telethon_client, m, url, None, check_duration_and_size=False)
    finally:
        ongoing_downloads.pop(user_id, None)

async def split_and_upload_file(app, sender, file_path, caption):
    if not os.path.exists(file_path):
        await app.send_message(sender, "❌ 未找到文件！")
        return

    file_size = os.path.getsize(file_path)
    start = await app.send_message(sender, f"ℹ️ **文件体积:** {file_size / (1024 * 1024):.2f} MB")
    PART_SIZE =  1.9 * 1024 * 1024 * 1024

    part_number = 0
    async with aiofiles.open(file_path, mode="rb") as f:
        while True:
            chunk = await f.read(PART_SIZE)
            if not chunk:
                break

            # Create part filename
            base_name, file_ext = os.path.splitext(file_path)
            part_file = f"{base_name}.part{str(part_number).zfill(3)}{file_ext}"

            # Write part to file
            async with aiofiles.open(part_file, mode="wb") as part_f:
                await part_f.write(chunk)

            # Uploading part
            edit = await app.send_message(sender, f"⬆️ **正在上传分段 {part_number + 1}...**")
            part_caption = f"{caption} \n\n**分段 : {part_number + 1}**"
            await app.send_document(sender, document=part_file, caption=part_caption,
                progress=progress_bar,
                progress_args=("╭─────────────────────╮\n│      **分段上传中**\n├─────────────────────", edit, time.time())
            )
            await edit.delete()
            os.remove(part_file)

            part_number += 1

    await start.delete()
    os.remove(file_path)


PROGRESS_BAR = """
│ **__进度:__** {0}%
│ **__完成:__** {1}/{2}
│ **__速度:__** {3}/s
│ **__预计剩余:__** {4}
╰─────────────────────╯
"""

async def get_seconds(time_string: str) -> int:
    """
    Converts a time string (e.g., '5min', '2hour') into seconds.
    """
    def extract_value_and_unit(ts: str):
        value = ''.join(filter(str.isdigit, ts))
        unit = ts[len(value):].strip()
        return int(value) if value else 0, unit
    
    value, unit = extract_value_and_unit(time_string)
    time_units = {
        's': 1,
        'min': 60,
        'hour': 3600,
        'day': 86400,
        'month': 86400 * 30,
        'year': 86400 * 365
    }
    
    return value * time_units.get(unit, 0)

async def progress_bar(current: int, total: int, ud_type: str, message, start: float):
    """
    Updates the progress bar for an ongoing process.
    """
    now = time.time()
    diff = now - start
    
    if round(diff % 10) == 0 or current == total:
        percentage = (current * 100) / total
        speed = current / diff if diff else 0
        elapsed_time = round(diff * 1000)
        time_to_completion = round((total - current) / speed) * 1000 if speed else 0
        estimated_total_time = elapsed_time + time_to_completion

        elapsed_time_str = TimeFormatter(elapsed_time)
        estimated_total_time_str = TimeFormatter(estimated_total_time)

        progress = "".join(["♦" for _ in range(math.floor(percentage / 10))]) + \
                   "".join(["◇" for _ in range(10 - math.floor(percentage / 10))])
        
        progress_text = progress + PROGRESS_BAR.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time_str if estimated_total_time_str else "0 s"
        )
        try:
            await message.edit(text=f"{ud_type}\n│ {progress_text}")
        except:
            pass

def humanbytes(size: int) -> str:
    """
    Converts bytes into a human-readable format.
    """
    if not size:
        return ""
    
    power = 2**10
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    n = 0
    while size > power and n < len(units) - 1:
        size /= power
        n += 1
    
    return f"{round(size, 2)} {units[n]}"

def TimeFormatter(milliseconds: int) -> str:
    """
    Formats milliseconds into a human-readable duration.
    """
    seconds, milliseconds = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    
    parts = []
    if days: parts.append(f"{days}d")
    if hours: parts.append(f"{hours}h")
    if minutes: parts.append(f"{minutes}m")
    if seconds: parts.append(f"{seconds}s")
    if milliseconds: parts.append(f"{milliseconds}ms")
    
    return ', '.join(parts)

def convert(seconds: int) -> str:
    """
    Converts seconds into HH:MM:SS format.
    """
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"
