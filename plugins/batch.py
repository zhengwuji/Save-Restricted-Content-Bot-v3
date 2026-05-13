# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import os, re, time, asyncio, json, asyncio 
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, LOG_GROUP, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
from utils.encrypt import dcs
from typing import Dict, Any, Optional


Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC, emp = {}, {}, {}, {}, {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"

# fixed directory file_name problems 
def sanitize(filename):
    return re.sub(r'[<>:"/\\|?*\']', '_', filename).strip(" .")[:255]

def load_active_users():
    try:
        if os.path.exists(ACTIVE_USERS_FILE):
            with open(ACTIVE_USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

async def save_active_users_to_file():
    try:
        with open(ACTIVE_USERS_FILE, 'w') as f:
            json.dump(ACTIVE_USERS, f)
    except Exception as e:
        print(f"Error saving active users: {e}")

async def add_active_batch(user_id: int, batch_info: Dict[str, Any]):
    ACTIVE_USERS[str(user_id)] = batch_info
    await save_active_users_to_file()

def is_user_active(user_id: int) -> bool:
    return str(user_id) in ACTIVE_USERS

async def update_batch_progress(user_id: int, current: int, success: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success
        await save_active_users_to_file()

async def request_batch_cancel(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["cancel_requested"] = True
        await save_active_users_to_file()
        return True
    return False

def should_cancel(user_id: int) -> bool:
    user_str = str(user_id)
    return user_str in ACTIVE_USERS and ACTIVE_USERS[user_str].get("cancel_requested", False)

async def remove_active_batch(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        del ACTIVE_USERS[str(user_id)]
        await save_active_users_to_file()

def get_batch_info(user_id: int) -> Optional[Dict[str, Any]]:
    return ACTIVE_USERS.get(str(user_id))

ACTIVE_USERS = load_active_users()

async def upd_dlg(c):
    try:
        async for _ in c.get_dialogs(limit=100): pass
        return True
    except Exception as e:
        print(f'Failed to update dialogs: {e}')
        return False

# fixed the old group of 2021-2022 extraction 🌝 (buy krne ka fayda nhi ab old group) ✅ 
async def get_msg(c, u, i, d, lt):
    try:
        if lt == 'public':
            # Try fetching with bot client first
            try:
                xm = await c.get_messages(i, d)
                if xm and not getattr(xm, "empty", False):
                    return xm
            except Exception:
                pass
            
            # If bot fails, try with user client
            if u:
                try:
                    xm = await u.get_messages(i, d)
                    if xm and not getattr(xm, "empty", False):
                        return xm
                except Exception:
                    pass
            return None
        else:
            # Private channel handling
            if u:
                try:
                    # Refresh dialogs to ensure access
                    # async for _ in u.get_dialogs(limit=20): pass
                    
                    # Try various ID formats
                    ids_to_try = [i]
                    if str(i).startswith('-100'):
                        ids_to_try.append(int(i))
                        ids_to_try.append(int(str(i).replace('-100', '-')))
                    elif str(i).isdigit():
                        ids_to_try.append(int(f"-100{i}"))
                        ids_to_try.append(int(f"-{i}"))
                    
                    for chat_id in ids_to_try:
                        try:
                            result = await u.get_messages(chat_id, d)
                            if result and not getattr(result, "empty", False):
                                return result
                        except Exception:
                            continue
                except Exception as e:
                    print(f'Private channel error: {e}')
            return None
    except Exception as e:
        print(f'Error fetching message: {e}')
        return None


async def get_ubot(uid):
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt:
        from shared_client import app
        return app
    if uid in UB: return UB.get(uid)
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception as e:
        print(f"Error starting bot for user {uid}: {e}")
        from shared_client import app
        return app

async def get_uclient(uid):
    ud = await get_user_data(uid)
    ubot = UB.get(uid)
    cl = UC.get(uid)
    if cl: return cl
    if not ud: return ubot if ubot else None
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss)
            await gg.start()
            await upd_dlg(gg)
            UC[uid] = gg
            return gg
        except Exception as e:
            print(f'User client error: {e}')
            return ubot if ubot else Y
    return Y

async def prog(c, t, C, h, m, st, extra="", uid=None):
    if uid and should_cancel(uid):
        raise Exception("任务已由用户取消")
    
    global P
    p = c / t * 100
    interval = 10 if t >= 100 * 1024 * 1024 else 20 if t >= 50 * 1024 * 1024 else 30 if t >= 10 * 1024 * 1024 else 50
    step = int(p // interval) * interval
    if m not in P or P[m] != step or p >= 100:
        P[m] = step
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        bar = '🟢' * int(p / 10) + '🔴' * (10 - int(p / 10))
        speed = c / (time.time() - st) / (1024 * 1024) if time.time() > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        
        status_text = f"**📥 正在处理 {extra}**\n\n" if extra else "**📥 正在处理...**\n\n"
        status_text += f"{bar}\n\n"
        status_text += f"⚡ **已完成**: `{c_mb:.2f} MB` / `{t_mb:.2f} MB`\n"
        status_text += f"📊 **进度**: `{p:.2f}%`\n"
        status_text += f"🚀 **速度**: `{speed:.2f} MB/s`\n"
        status_text += f"⏳ **预计剩余**: `{eta}`\n\n"
        status_text += "**Powered by @cc100g_zhuanfa_bot**"
        
        reply_markup = None
        if uid:
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 取消当前任务", callback_data=f"cancel_{uid}")]])
            
        try:
            await C.edit_message_text(h, m, status_text, reply_markup=reply_markup)
        except Exception:
            pass
        if p >= 100: P.pop(m, None)

async def send_direct_group(c, messages, tcid, ft=None, rtmid=None):
    """
    尝试直接转发媒体组（秒发）。
    优先：机器人直接 copy_media_group
    其次：用户代理 copy_media_group 到 LOG_GROUP，机器人再 copy 出来
    """
    try:
        from_chat = messages[0].chat.id
        msg_ids = [m.id for m in messages]
        
        # 方法 1: 机器人直接复制
        try:
            await c.copy_media_group(tcid, from_chat, msg_ids, reply_to_message_id=rtmid)
            return True
        except Exception:
            pass
            
        # 方法 2: 用户代理中转
        if Y and LOG_GROUP:
            try:
                tms = await Y.copy_media_group(LOG_GROUP, from_chat, msg_ids)
                await c.copy_media_group(tcid, LOG_GROUP, [m.id for m in tms], reply_to_message_id=rtmid)
                return True
            except Exception as e:
                print(f"Transfer group forward failed: {e}")
                pass
    except Exception as e:
        print(f"send_direct_group error: {e}")
    return False

async def send_direct(c, m, tcid, ft=None, rtmid=None):
    """
    尝试直接转发（秒发）逻辑。
    """
    try:
        # 方法 1: 机器人直接复制
        try:
            await c.copy_message(tcid, m.chat.id, m.id, caption=ft, reply_to_message_id=rtmid)
            return True
        except Exception:
            pass

        # 方法 2: 用户代理中转
        if Y and LOG_GROUP:
            try:
                tm = await Y.copy_message(LOG_GROUP, m.chat.id, m.id)
                await c.copy_message(tcid, LOG_GROUP, tm.id, caption=ft, reply_to_message_id=rtmid)
                return True
            except Exception as e:
                print(f"Transfer forward failed: {e}")
                pass

        # 方法 3: 通过 File ID 发送
        if m.video:
            await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note:
            await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice:
            await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker:
            await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio:
            await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo:
            photo_id = m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id
            await c.send_photo(tcid, photo_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document:
            await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else:
            return False
        return True
    except Exception as e:
        print(f'Direct send error: {e}')
        return False

async def process_msg(c, u, m, d, lt, uid, i, extra=""):
    # 每次开始前检查是否已取消
    if should_cancel(uid):
        return 'Cancelled'
    try:
        cfg_chat = await get_user_data_key(d, 'chat_id', None)
        tcid = d
        rtmid = None
        if cfg_chat:
            if '/' in cfg_chat:
                parts = cfg_chat.split('/', 1)
                tcid = int(parts[0])
                rtmid = int(parts[1]) if len(parts) > 1 else None
            else:
                tcid = int(cfg_chat)
        
        if m.media:
            orig_text = m.caption.markdown if m.caption else ''
            proc_text = await process_text_with_rules(d, orig_text)
            user_cap = await get_user_data_key(d, 'caption', '')
            ft = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            # --- 尝试秒发 (全类型，优先使用 copy_message 逻辑) ---
            if not emp.get(i, False):
                if await send_direct(c, m, tcid, ft, rtmid):
                    return 'Sent directly.'
                else:
                    print(f"Direct send failed for {i}, falling back to download/upload.")
            
            st = time.time()
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🚫 取消任务", callback_data=f"cancel_{uid}")]])
            p = await c.send_message(d, f'正在准备下载 {extra}...', reply_markup=reply_markup)

            # 确保下载目录存在并使用绝对路径
            DOWNLOAD_DIR = os.path.abspath("downloads")
            if not os.path.exists(DOWNLOAD_DIR):
                os.makedirs(DOWNLOAD_DIR)

            c_name = os.path.join(DOWNLOAD_DIR, f"{time.time()}")
            if m.video:
                file_name = m.video.file_name or f"{time.time()}.mp4"
                c_name = os.path.join(DOWNLOAD_DIR, sanitize(file_name))
            elif m.audio:
                file_name = m.audio.file_name or f"{time.time()}.mp3"
                c_name = os.path.join(DOWNLOAD_DIR, sanitize(file_name))
            elif m.document:
                file_name = m.document.file_name or f"{time.time()}"
                c_name = os.path.join(DOWNLOAD_DIR, sanitize(file_name))
            elif m.photo:
                c_name = os.path.join(DOWNLOAD_DIR, f"{time.time()}.jpg")
            elif m.video_note:
                c_name = os.path.join(DOWNLOAD_DIR, f"{time.time()}.mp4")
            elif m.voice:
                c_name = os.path.join(DOWNLOAD_DIR, f"{time.time()}.ogg")
    
            # --- 尝试并行高速下载 ---
            f = None
            try:
                from utils.fast_download import fast_download as parallel_dl, _download_pool
                if _download_pool:
                    await c.edit_message_text(d, p.id, f'🚀 并行加速下载 {extra}...',
                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 取消任务", callback_data=f"cancel_{uid}")]]))
                    f = await parallel_dl(
                        m, c_name,
                        progress_callback=prog,
                        progress_args=(c, d, p.id, st, extra, uid),
                        cancel_check=lambda: should_cancel(uid),
                    )
            except Exception as pe:
                print(f"Parallel download error: {pe}")

            # --- 回退到普通下载 ---
            if not f:
                await c.edit_message_text(d, p.id, f'正在准备下载 {extra}...',
                                          reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚫 取消任务", callback_data=f"cancel_{uid}")]]))
                f = await u.download_media(m, file_name=c_name, progress=prog, progress_args=(c, d, p.id, st, extra, uid))
            
            if not f:
                await c.edit_message_text(d, p.id, '下载失败。')
                return 'Failed.'
            
            await c.edit_message_text(d, p.id, '正在重命名...')
            if (
                (m.video and m.video.file_name) or
                (m.audio and m.audio.file_name) or
                (m.document and m.document.file_name)
            ):
                f = await rename_file(f, d, p)
            
            fsize = os.path.getsize(f) / (1024 * 1024 * 1024)
            th = thumbnail(d)
            
            if fsize > 2 and Y:
                st = time.time()
                await c.edit_message_text(d, p.id, '文件超过 2GB，正在使用大文件模式上传...')
                await upd_dlg(Y)
                mtd = await get_video_metadata(f)
                dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                th = await screenshot(f, dur, d)
                
                send_funcs = {'video': Y.send_video, 'video_note': Y.send_video_note, 
                            'voice': Y.send_voice, 'audio': Y.send_audio, 
                            'photo': Y.send_photo, 'document': Y.send_document}
                
                for mtype, func in send_funcs.items():
                    if f.endswith('.mp4'): mtype = 'video'
                    if getattr(m, mtype, None):
                        sent = await func(LOG_GROUP, f, thumb=th if mtype == 'video' else None, 
                                        duration=dur if mtype == 'video' else None,
                                        height=h if mtype == 'video' else None,
                                        width=w if mtype == 'video' else None,
                                        caption=ft if m.caption and mtype not in ['video_note', 'voice'] else None, 
                                        reply_to_message_id=rtmid, progress=prog, progress_args=(c, d, p.id, st, extra, uid))
                        break
                else:
                    sent = await Y.send_document(LOG_GROUP, f, thumb=th, caption=ft if m.caption else None,
                                                reply_to_message_id=rtmid, progress=prog, progress_args=(c, d, p.id, st, extra, uid))
                
                await c.copy_message(d, LOG_GROUP, sent.id)
                os.remove(f)
                await c.delete_messages(d, p.id)
                
                return 'Done (Large file).'
            
            await c.edit_message_text(d, p.id, '正在上传...')
            st = time.time()

            try:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
                audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.ac3']
                file_ext = os.path.splitext(f)[1].lower()
                if m.video or (m.document and file_ext in video_extensions):
                    mtd = await get_video_metadata(f)
                    dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                    th = await screenshot(f, dur, d)
                    await c.send_video(tcid, video=f, caption=ft if m.caption else None, 
                                    thumb=th, width=w, height=h, duration=dur, 
                                        progress=prog, progress_args=(c, d, p.id, st, extra, uid), 
                                        reply_to_message_id=rtmid)
                elif m.photo:
                    await c.send_photo(tcid, photo=f, caption=ft if m.caption else None, 
                                    progress=prog, progress_args=(c, d, p.id, st, extra, uid), 
                                    reply_to_message_id=rtmid)
                elif m.document:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, d, p.id, st, extra, uid), 
                                        reply_to_message_id=rtmid)
                else:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, d, p.id, st, extra, uid), 
                                        reply_to_message_id=rtmid)
            except Exception as e:
                await c.edit_message_text(d, p.id, f'上传失败: {str(e)[:30]}')
                if f and os.path.exists(f): os.remove(f)
                return 'Failed.'
            
            if f and os.path.exists(f): os.remove(f)
            await c.delete_messages(d, p.id)
            
            return 'Done.'
            
        elif m.text:
            await c.send_message(tcid, text=m.text.markdown, reply_to_message_id=rtmid)
            return 'Sent.'
    except Exception as e:
        paths_to_check = []
        if 'f' in locals() and f:
            paths_to_check.extend([f, f + ".temp"])
        if 'c_name' in locals() and c_name:
            possible_path = os.path.join("downloads", c_name)
            paths_to_check.extend([possible_path, possible_path + ".temp", c_name, c_name + ".temp"])
            
        for path in paths_to_check:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
                    
        return f'Error: {str(e)[:50]}'
        
@X.on_message(filters.command(['batch', 'single']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0]
    
    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot does not provide free servies, get subscription from OWNER")
        return
    
    if await sub(c, m) == 1: return
    pro = await m.reply_text('Doing some checks hold on...')
    
    if is_user_active(uid):
        await pro.edit('You have an active task. Use /stop to cancel it.')
        return
    
    ubot = await get_ubot(uid)
    if not ubot:
        from shared_client import app
        ubot = app
    
    Z[uid] = {'step': 'start' if cmd == 'batch' else 'start_single'}
    await pro.edit(f'Send {"start link..." if cmd == "batch" else "link you to process"}.')

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('🚫 任务停止请求已发送。当前文件下载完成后将停止。')
        else:
            # 强制清理状态，以防万一
            await remove_active_batch(uid)
            Z.pop(uid, None)
            await m.reply_text('⚠️ 停止请求失败，已强制重置状态。')
    else:
        Z.pop(uid, None) # 确保 Z 也被清理
        await m.reply_text('目前没有正在运行的任务。')

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot']))
async def text_handler(c, m):
    uid = m.from_user.id
    
    # Handle direct links without command
    if uid not in Z:
        if m.text and ("t.me/" in m.text or "telegram.me/" in m.text):
            L = m.text
            i, d, lt = E(L)
            if i and d:
                Z[uid] = {'step': 'process_single', 'cid': i, 'sid': d, 'lt': lt}
            else:
                return
        else:
            return

    s = Z[uid].get('step')
    x = await get_ubot(uid)
    if not x:
        await m.reply("Add your bot /setbot `token` or use the default one.")
        x = c # fallback

    if s == 'start':
        L = m.text
        i, d, lt = E(L)
        if not i or not d:
            await m.reply_text('Invalid link format.')
            Z.pop(uid, None)
            return
        Z[uid].update({'step': 'count', 'cid': i, 'sid': d, 'lt': lt})
        await m.reply_text('How many messages?')

    elif s == 'start_single' or s == 'process_single':
        if s == 'start_single':
            L = m.text
            i, d, lt = E(L)
            if not i or not d:
                await m.reply_text('Invalid link format.')
                Z.pop(uid, None)
                return
            Z[uid].update({'step': 'process_single', 'cid': i, 'sid': d, 'lt': lt})
        
        i, s, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['lt']
        pt = await m.reply_text('Processing...')
        
        ubot = await get_ubot(uid)
        if not ubot:
            from shared_client import app
            ubot = app
        
        uc = await get_uclient(uid)
        if not uc:
            await pt.edit('Cannot proceed without user client.')
            Z.pop(uid, None)
            return
            
        if is_user_active(uid):
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 强制停止并重置", callback_data=f"force_stop_{uid}")]])
            await pt.edit('⚠️ 任务正在运行中。如果您确定要开启新任务，请先停止当前任务。', reply_markup=reply_markup)
            Z.pop(uid, None)
            return

        await add_active_batch(uid, {
            "total": 0,
            "current": 0,
            "success": 0,
            "cancel_requested": False,
            "progress_message_id": pt.id
        })

        try:
            # Check for media group
            messages = []
            try:
                # Use user client to get media group if possible
                messages = await uc.get_media_group(i, s)
            except Exception:
                # Fallback to single message
                msg = await get_msg(ubot, uc, i, s, lt)
                if msg:
                    messages = [msg]

            if messages:
                total = len(messages)
                print(f"Detected {total} messages for grouping.")
                
                # 获取转发设置
                cfg_chat = await get_user_data_key(str(m.chat.id), 'chat_id', None)
                tcid = str(m.chat.id)
                rtmid = None
                if cfg_chat:
                    if '/' in cfg_chat:
                        parts = cfg_chat.split('/', 1)
                        tcid = int(parts[0])
                        rtmid = int(parts[1]) if len(parts) > 1 else None
                    else:
                        tcid = int(cfg_chat)

                # --- 1. 尝试合并秒发 (转发/复制) ---
                if total > 1:
                    await pt.edit(f'检测到媒体组 ({total} 个文件)，正在尝试合并秒发...')
                    
                    # 尝试多种秒发方式
                    success = False
                    
                    # 方式 A: copy_media_group (最整洁)
                    if await send_direct_group(ubot, messages, tcid, rtmid=rtmid):
                        success = True
                    
                    # 方式 B: forward_messages (作为备份)
                    if not success:
                        try:
                            from_chat = messages[0].chat.id
                            msg_ids = [msg.id for msg in messages]
                            await ubot.forward_messages(tcid, from_chat, msg_ids)
                            success = True
                        except Exception as fe:
                            print(f"Forward fallback failed: {fe}")
                    
                    if success:
                        await pt.edit(f'✅ 媒体组已秒发成功！')
                        return
                    else:
                        await pt.edit(f'合并秒发失败，将尝试并行下载并合并发送...')

                # --- 2. 如果秒发失败且是媒体组，尝试下载后合并发送 ---
                if total > 1:
                    downloaded_files = []
                    try:
                        for index, msg in enumerate(messages):
                            if should_cancel(uid): break
                            info = f"正在下载组内文件 {index+1}/{total}"
                            # 调用 process_msg 但让它只返回文件路径而不发送
                            # 为了不重构太多，我们直接在这里写下载逻辑
                            
                            # 预处理文件名和路径
                            DOWNLOAD_DIR = os.path.abspath("downloads")
                            if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
                            
                            ext = ".mp4" if msg.video or msg.video_note else ".jpg" if msg.photo else ".zip"
                            if msg.document: ext = os.path.splitext(msg.document.file_name)[1] or ".zip"
                            
                            tmp_name = os.path.join(DOWNLOAD_DIR, f"{time.time()}_{index}{ext}")
                            
                            await pt.edit(f'🚀 正在并行下载第 {index+1}/{total} 个文件...')
                            
                            # 使用并行下载器 (带进度条)
                            from utils.fast_download import fast_download as parallel_dl, _download_pool
                            f = None
                            if _download_pool:
                                f = await parallel_dl(
                                    msg, tmp_name, 
                                    progress_callback=prog,
                                    progress_args=(c, d, pt.id, st, f"({index+1}/{total})", uid),
                                    cancel_check=lambda: should_cancel(uid)
                                )
                            
                            if not f: # 回退到普通下载
                                f = await uc.download_media(msg, file_name=tmp_name, progress=prog, progress_args=(c, d, pt.id, st, f"({index+1}/{total})", uid))
                            
                            if f:
                                # 重命名
                                f = await rename_file(f, uid, pt)
                                downloaded_files.append((f, msg))
                        
                        if len(downloaded_files) == total:
                            await pt.edit(f'✅ 所有文件下载完成，正在合并上传为媒体组...')
                            
                            from pyrogram.types import InputMediaVideo, InputMediaPhoto, InputMediaDocument
                            media = []
                            for f_path, msg in downloaded_files:
                                if f_path.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.m4v')):
                                    media.append(InputMediaVideo(f_path, caption=msg.caption))
                                elif f_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                                    media.append(InputMediaPhoto(f_path, caption=msg.caption))
                                else:
                                    media.append(InputMediaDocument(f_path, caption=msg.caption))
                            
                            if media:
                                await ubot.send_media_group(tcid, media, reply_to_message_id=rtmid)
                                await pt.edit(f'✅ 媒体组合并发送成功！')
                                # 清理文件
                                for f, _ in downloaded_files:
                                    if os.path.exists(f): os.remove(f)
                                return
                    except Exception as ge:
                        print(f"Group download/upload error: {ge}")
                        # 清理已下载的文件
                        for f, _ in downloaded_files:
                            if os.path.exists(f): os.remove(f)
                        await pt.edit(f'合并发送失败 ({str(ge)[:30]})，将回退到逐个发送...')

                # --- 3. 最后的手段：逐个处理 ---
                for index, msg in enumerate(messages):
                    if should_cancel(uid):
                        break
                    info = f"第 {index+1}/{total} 个文件"
                    res = await process_msg(ubot, uc, msg, str(m.chat.id), lt, uid, i, extra=info)
                    if res == 'Cancelled':
                        break
                
                if should_cancel(uid):
                    await pt.delete()
                else:
                    await pt.edit(f'✅ 处理完成：共 {total} 个文件。')
            else:
                await pt.edit('Message not found')
        except Exception as e:
            await pt.edit(f'Error: {str(e)[:50]}')
        finally:
            await remove_active_batch(uid)
            Z.pop(uid, None)

    elif s == 'count':
        if not m.text.isdigit():
            await m.reply_text('Enter valid number.')
            return
        
        count = int(m.text)
        maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else FREEMIUM_LIMIT

        if count > maxlimit:
            await m.reply_text(f'Maximum limit is {maxlimit}.')
            return

        Z[uid].update({'step': 'process', 'did': str(m.chat.id), 'num': count})
        i, s, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
        success = 0

        pt = await m.reply_text('Processing batch...')
        uc = await get_uclient(uid)
        ubot = await get_ubot(uid)
        
        if not uc or not ubot:
            from shared_client import app
            ubot = app
            if not uc:
                await pt.edit('Missing client setup')
                Z.pop(uid, None)
                return
            
        if is_user_active(uid):
            await pt.edit('Active task exists')
            Z.pop(uid, None)
            return
        
        await add_active_batch(uid, {
            "total": n,
            "current": 0,
            "success": 0,
            "cancel_requested": False,
            "progress_message_id": pt.id
            })
        
        try:
            for j in range(n):
                
                if should_cancel(uid):
                    await pt.edit(f'Cancelled at {j}/{n}. Success: {success}')
                    break
                
                await update_batch_progress(uid, j, success)
                
                mid = int(s) + j
                
                try:
                    msg = await get_msg(ubot, uc, i, mid, lt)
                    if msg:
                        res = await process_msg(ubot, uc, msg, str(m.chat.id), lt, uid, i)
                        if 'Done' in res or 'Copied' in res or 'Sent' in res:
                            success += 1
                        elif 'Cancelled' in res:
                            await pt.edit(f'❌ 任务已取消。成功: {success}/{n}')
                            break
                    else:
                        pass
                except Exception as e:
                    try: await pt.edit(f'{j+1}/{n}: Error - {str(e)[:30]}')
                    except: pass
                
                await asyncio.sleep(10)
            
            if j+1 == n:
                await m.reply_text(f'Batch Completed ✅ Success: {success}/{n}')
        
        finally:
            await remove_active_batch(uid)
            Z.pop(uid, None)




@X.on_callback_query(filters.regex(r"^cancel_(\d+)$"))
async def cancel_callback(c, cb):
    uid = int(cb.matches[0].group(1))
    if cb.from_user.id != uid:
        await cb.answer("这不是您的任务哦 ~", show_alert=True)
        return
    
    await request_batch_cancel(uid)
    Z.pop(uid, None)
    await remove_active_batch(uid)
    await cb.answer("已尝试取消，状态已清理。", show_alert=True)
    try:
        await cb.message.delete()
    except Exception:
        pass

@X.on_callback_query(filters.regex(r"^force_stop_(\d+)$"))
async def force_stop_callback(c, cb):
    uid = int(cb.matches[0].group(1))
    if cb.from_user.id != uid:
        await cb.answer("这不是您的任务哦 ~", show_alert=True)
        return
    
    await remove_active_batch(uid)
    Z.pop(uid, None)
    await cb.answer("状态已强制重置！", show_alert=True)
    try:
        await cb.message.edit("✅ 状态已强制重置，您可以重新发送链接了。")
    except Exception:
        pass
