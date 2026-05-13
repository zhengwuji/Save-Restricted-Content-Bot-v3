"""
fast_download.py - 高速并行分块下载器
使用多个独立 Pyrogram 客户端并行下载文件的不同段，实现接近桌面客户端的下载速度。

原理：
  - 将文件按字节范围切分为 N 段
  - 每段由一个独立的 Pyrogram 客户端连接负责下载
  - 所有段并行下载，写入同一个文件的不同偏移位置
  - 下载完成后无需合并（直接随机写入）

期望速度：单连接 0.5 MB/s × N 个连接 = N × 0.5 MB/s
"""

import asyncio
import os
import time
from pyrogram import Client

# 下载工作池（在 bot 启动时初始化）
_download_pool: list[Client] = []
_pool_lock = asyncio.Lock()

NUM_WORKERS = 8  # 并行连接数，可根据服务器性能调整


async def init_download_pool(api_id, api_hash, session_string, num_workers=NUM_WORKERS):
    """初始化下载工作池 - 在 bot 启动时调用一次"""
    global _download_pool
    if not session_string:
        print("No session string, parallel download disabled.")
        return

    print(f"Initializing parallel download pool with {num_workers} workers...")
    tasks = []
    for i in range(num_workers):
        wc = Client(
            f"dl_worker_{i}",
            api_id=api_id,
            api_hash=api_hash,
            session_string=session_string,
            no_updates=True,  # 不接收更新，节省资源
            workers=1,
        )
        tasks.append(wc.start())
        _download_pool.append(wc)

    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    if errors:
        print(f"Warning: {len(errors)} workers failed to start: {errors[0]}")
        # Remove failed workers
        _download_pool = [wc for wc, r in zip(_download_pool, results) if not isinstance(r, Exception)]

    print(f"Download pool ready: {len(_download_pool)} workers active.")


async def stop_download_pool():
    """停止所有工作池连接"""
    global _download_pool
    tasks = [wc.stop() for wc in _download_pool]
    await asyncio.gather(*tasks, return_exceptions=True)
    _download_pool.clear()
    print("Download pool stopped.")


def _get_file_size(message) -> int:
    """从 Pyrogram 消息中获取文件大小"""
    if message.video:
        return message.video.file_size or 0
    elif message.document:
        return message.document.file_size or 0
    elif message.audio:
        return message.audio.file_size or 0
    elif message.video_note:
        return message.video_note.file_size or 0
    elif message.voice:
        return message.voice.file_size or 0
    return 0


async def fast_download(
    message,
    output_path: str,
    progress_callback=None,
    progress_args: tuple = (),
    cancel_check=None,
) -> str | None:
    """
    高速并行下载。
    
    Args:
        message: Pyrogram 消息对象（含媒体）
        output_path: 输出文件路径
        progress_callback: 进度回调函数 async(current, total, *args)
        progress_args: 传给回调的额外参数
        cancel_check: 取消检查函数 () -> bool，返回 True 时中止
    
    Returns:
        成功返回文件路径，失败返回 None（调用方应回退到普通下载）
    """
    global _download_pool

    if not _download_pool:
        return None  # 池未初始化，回退到普通下载

    file_size = _get_file_size(message)
    if file_size < 5 * 1024 * 1024:  # 小于 5MB 的文件不值得并行
        return None

    num_workers = min(len(_download_pool), NUM_WORKERS)
    # 必须对齐到 1MB (1024*1024)，否则 Telegram 会返回 OFFSET_INVALID
    alignment = 1024 * 1024
    chunk_size = ((file_size // num_workers) // alignment) * alignment
    if chunk_size == 0: chunk_size = alignment

    # 预分配文件
    try:
        with open(output_path, 'wb') as f:
            f.truncate(file_size)
    except Exception as e:
        print(f"fast_download: cannot pre-allocate file: {e}")
        return None

    downloaded_bytes = [0]
    failed = [False]
    start_time = time.time()
    write_lock = asyncio.Lock()

    async def worker(worker_client: Client, start_byte: int, end_byte: int):
        """单个工作连接：下载 [start_byte, end_byte) 范围"""
        try:
            written = start_byte
            async for chunk in worker_client.stream_media(
                message,
                offset=start_byte,
                limit=end_byte - start_byte,
            ):
                if cancel_check and cancel_check():
                    return

                # 随机写入，无需锁（不同 worker 写不同偏移区域）
                with open(output_path, 'r+b') as fh:
                    fh.seek(written)
                    fh.write(chunk)
                written += len(chunk)

                # 更新进度（需锁保护计数器）
                async with write_lock:
                    downloaded_bytes[0] += len(chunk)
                    current = downloaded_bytes[0]

                if progress_callback:
                    try:
                        elapsed = time.time() - start_time
                        await progress_callback(current, file_size, *progress_args)
                    except Exception:
                        pass

        except Exception as e:
            print(f"fast_download worker error at offset {start_byte}: {e}")
            failed[0] = True

    # 分配工作
    tasks = []
    for i in range(num_workers):
        start = i * chunk_size
        end = min(start + chunk_size, file_size)
        if start >= file_size:
            break
        tasks.append(worker(_download_pool[i], start, end))

    await asyncio.gather(*tasks)

    if failed[0]:
        # 部分失败，清理并回退
        if os.path.exists(output_path):
            os.remove(output_path)
        return None

    return output_path
