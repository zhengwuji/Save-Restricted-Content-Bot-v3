# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from telethon import events, Button
import re
import os
import asyncio
import string
import random
from shared_client import client as gf
from config import OWNER_ID
from utils.func import get_user_data_key, save_user_data, users_collection

VIDEO_EXTENSIONS = {
    'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm',
    'mpeg', 'mpg', '3gp'
}
SET_PIC = 'settings.jpg'
MESS = '请配置您的自定义处理选项：'

active_conversations = {}

@gf.on(events.NewMessage(incoming=True, pattern='/settings'))
async def settings_command(event):
    user_id = event.sender_id
    await send_settings_message(event.chat_id, user_id)

async def send_settings_message(chat_id, user_id):
    buttons = [
        [
            Button.inline('📝 设置目标群组 ID', b'setchat'),
            Button.inline('🏷️ 设置重命名后缀', b'setrename')
        ],
        [
            Button.inline('📋 设置自定义图文说明', b'setcaption'),
            Button.inline('🔄 替换文件名关键词', b'setreplacement')
        ],
        [
            Button.inline('🗑️ 删除文件名关键词', b'delete'),
            Button.inline('🔄 恢复默认设置', b'reset')
        ],
        [
            Button.inline('🔑 Session 登录', b'addsession'),
            Button.inline('🚪 退出登录', b'logout')
        ],
        [
            Button.inline('🖼️ 设置视频默认封面', b'setthumb'),
            Button.inline('❌ 移除视频默认封面', b'remthumb')
        ],
        [
            Button.url('🆘 报告错误 (英文)', 'https://t.me/team_spy_pro')
        ]
    ]
    await gf.send_message(chat_id, MESS, buttons=buttons)

@gf.on(events.CallbackQuery)
async def callback_query_handler(event):
    user_id = event.sender_id
    
    callback_actions = {
        b'setchat': {
            'type': 'setchat',
            'message': "请发送目标群组或频道的 ID (必须带有 -100 前缀)：\n👉 **注意:** 如果您想直接转发到群组或频道，本机器人必须是该群组的管理员。\n👉 如果想发送到特定的话题区(Topic)，请使用 **-100频道ID/话题ID** 的格式，例如：**-1004783898/12**"
        },
        b'setrename': {
            'type': 'setrename',
            'message': '请发送您想在文件名末尾添加的重命名后缀：'
        },
        b'setcaption': {
            'type': 'setcaption',
            'message': '请发送您想要的自定义底部图文说明(Caption)：'
        },
        b'setreplacement': {
            'type': 'setreplacement',
            'message': "请发送要替换的关键词，格式如下：'原词' '新词'"
        },
        b'addsession': {
            'type': 'addsession',
            'message': '请发送您的 Pyrogram V2 Session 字符串：'
        },
        b'delete': {
            'type': 'deleteword',
            'message': '请发送想要从文件标题中删除的关键词（如果有多个，请用空格隔开）：'
        },
        b'setthumb': {
            'type': 'setthumb',
            'message': '请直接发送一张图片，它将作为您以后下载视频的默认封面。'
        }
    }
    
    if event.data in callback_actions:
        action = callback_actions[event.data]
        await start_conversation(event, user_id, action['type'], action['message'])
    elif event.data == b'logout':
        result = await users_collection.update_one(
            {'user_id': user_id},
            {'$unset': {'session_string': ''}}
        )
        if result.modified_count > 0:
            await event.respond('已成功退出登录并删除 Session。')
        else:
            await event.respond('您尚未登录。')
    elif event.data == b'reset':
        try:
            await users_collection.update_one(
                {'user_id': user_id},
                {'$unset': {
                    'delete_words': '',
                    'replacement_words': '',
                    'rename_tag': '',
                    'caption': '',
                    'chat_id': ''
                }}
            )
            thumbnail_path = f'{user_id}.jpg'
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
            await event.respond('✅ 所有设置已成功重置！如需退出账号请点击 /logout')
        except Exception as e:
            await event.respond(f'重置设置时出错：{e}')
    elif event.data == b'remthumb':
        try:
            os.remove(f'{user_id}.jpg')
            await event.respond('✅ 封面图移除成功！')
        except FileNotFoundError:
            await event.respond('❌ 未找到已设置的封面图。')

async def start_conversation(event, user_id, conv_type, prompt_message):
    if user_id in active_conversations:
        await event.respond('之前的操作已取消，开始新操作。')
    
    msg = await event.respond(f'{prompt_message}\n\n(发送 /cancel 取消本次操作)')
    active_conversations[user_id] = {'type': conv_type, 'message_id': msg.id}

@gf.on(events.NewMessage(pattern='/cancel'))
async def cancel_conversation(event):
    user_id = event.sender_id
    if user_id in active_conversations:
        await event.respond('操作已取消。')
        del active_conversations[user_id]

@gf.on(events.NewMessage())
async def handle_conversation_input(event):
    user_id = event.sender_id
    if user_id not in active_conversations or event.message.text.startswith('/'):
        return
        
    conv_type = active_conversations[user_id]['type']
    
    handlers = {
        'setchat': handle_setchat,
        'setrename': handle_setrename,
        'setcaption': handle_setcaption,
        'setreplacement': handle_setreplacement,
        'addsession': handle_addsession,
        'deleteword': handle_deleteword,
        'setthumb': handle_setthumb
    }
    
    if conv_type in handlers:
        await handlers[conv_type](event, user_id)
    
    if user_id in active_conversations:
        del active_conversations[user_id]

async def handle_setchat(event, user_id):
    try:
        chat_id = event.text.strip()
        await save_user_data(user_id, 'chat_id', chat_id)
        await event.respond('✅ 目标群组 ID 设置成功！')
    except Exception as e:
        await event.respond(f'❌ 设置目标群组 ID 时出错：{e}')

async def handle_setrename(event, user_id):
    rename_tag = event.text.strip()
    await save_user_data(user_id, 'rename_tag', rename_tag)
    await event.respond(f'✅ 重命名后缀已设置为：{rename_tag}')

async def handle_setcaption(event, user_id):
    caption = event.text
    await save_user_data(user_id, 'caption', caption)
    await event.respond(f'✅ 自定义图文说明设置成功！')

async def handle_setreplacement(event, user_id):
    match = re.match("'(.+)' '(.+)'", event.text)
    if not match:
        await event.respond("❌ 格式无效。正确用法：'原词' '新词'")
    else:
        word, replace_word = match.groups()
        delete_words = await get_user_data_key(user_id, 'delete_words', [])
        if word in delete_words:
            await event.respond(f"❌ 关键词 '{word}' 已在删除列表中，无法被替换。")
        else:
            replacements = await get_user_data_key(user_id, 'replacement_words', {})
            replacements[word] = replace_word
            await save_user_data(user_id, 'replacement_words', replacements)
            await event.respond(f"✅ 替换规则已保存：'{word}' 将被替换为 '{replace_word}'")

async def handle_addsession(event, user_id):
    session_string = event.text.strip()
    await save_user_data(user_id, 'session_string', session_string)
    await event.respond('✅ Session 字符串添加成功！')

async def handle_deleteword(event, user_id):
    words_to_delete = event.message.text.split()
    delete_words = await get_user_data_key(user_id, 'delete_words', [])
    delete_words = list(set(delete_words + words_to_delete))
    await save_user_data(user_id, 'delete_words', delete_words)
    await event.respond(f"✅ 已添加到删除列表的关键词：{', '.join(words_to_delete)}")

async def handle_setthumb(event, user_id):
    if event.photo:
        temp_path = await event.download_media()
        try:
            thumb_path = f'{user_id}.jpg'
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            os.rename(temp_path, thumb_path)
            await event.respond('✅ 视频封面保存成功！')
        except Exception as e:
            await event.respond(f'❌ 保存视频封面时出错：{e}')
    else:
        await event.respond('❌ 请发送一张图片。操作已取消。')

def generate_random_name(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


async def rename_file(file, sender, edit):
    try:
        delete_words = await get_user_data_key(sender, 'delete_words', [])
        custom_rename_tag = await get_user_data_key(sender, 'rename_tag', '')
        replacements = await get_user_data_key(sender, 'replacement_words', {})
        
        last_dot_index = str(file).rfind('.')
        if last_dot_index != -1 and last_dot_index != 0:
            ggn_ext = str(file)[last_dot_index + 1:]
            if ggn_ext.isalpha() and len(ggn_ext) <= 9:
                if ggn_ext.lower() in VIDEO_EXTENSIONS:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = 'mp4'
                else:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = ggn_ext
            else:
                original_file_name = str(file)[:last_dot_index]
                file_extension = 'mp4'
        else:
            original_file_name = str(file)
            file_extension = 'mp4'
        
        for word in delete_words:
            original_file_name = original_file_name.replace(word, '')
        
        for word, replace_word in replacements.items():
            original_file_name = original_file_name.replace(word, replace_word)
        
        dir_name = os.path.dirname(file)
        new_file_name = f'{original_file_name} {custom_rename_tag}.{file_extension}'
        if dir_name:
            new_file_name = os.path.join(dir_name, new_file_name)
        
        os.rename(file, new_file_name)
        return new_file_name
    except Exception as e:
        print(f"Rename error: {e}")
        return file
        
