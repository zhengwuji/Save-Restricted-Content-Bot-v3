# 受限内容破解转发机器人 (Save Restricted Content Bot V3) 🚀

这是一个高度定制化的受限内容下载与转发 Telegram 机器人。它可以自动保存和转发禁止转发/保存的频道和群组中的消息、图片、视频和文件。

**本项目是在 [devgaganin](https://github.com/devgaganin/Save-Restricted-Content-Bot-v3) 原项目的基础上，进行了深度定制、全面汉化、移除强制加群、并去除了所有烦人广告和暗桩的“纯净优化版”。**

## ✨ 核心功能特色
- **强制破解限制**：轻松下载并转发那些带有“限制保存/转发”标志的频道与群组内容。
- **全中文界面**：所有菜单指令和反馈信息已彻底汉化，更符合国人使用习惯。
- **完美去广告**：剔除了原版中强制显示“Get Premium”和“Join Channel”按钮的底层加密代码。
- **去除暗桩限制**：完全移除了 `FORCE_SUB` 强制订阅频道限制逻辑，真正做到开箱即用。
- **高速并行下载 (NEW)**：内置基于 Pyrogram 的多线程切片下载引擎，比传统下载速度提升 5-10 倍。
- **合并转发 (Album)**：自动识别媒体组（相册），支持秒发合并和下载后合并上传，保持相册结构不被打散。
- **批量搬运 (/batch)**：支持按链接范围批量抓取历史消息，适合一键搬空目标频道。
- **私有频道支持 (/login)**：通过 Session 登录后，机器人可以代你访问并提取你所在的任何私有频道内容。
- **自动化重命名配置**：支持自定义文字替换、自定义后缀重命名、添加图片或视频水印。

## 🛠️ 环境要求
- 一台境外的 VPS (推荐 Ubuntu 20.04 或更高)
- Python 3.10+
- 一定基础的 Linux 和 SSH 操作经验
- Telegram API ID 和 API HASH (前往 [my.telegram.org](https://my.telegram.org) 获取)
- 一个 Bot Token (前往 [@BotFather](https://t.me/BotFather) 获取)
- MongoDB 数据库连接 URI

## 🚀 部署与搭建详细教程

### 第 1 步：克隆项目到服务器
```bash
git clone https://github.com/zhengwuji/Save-Restricted-Content-Bot-v3.git
cd Save-Restricted-Content-Bot-v3
```

### 第 2 步：安装依赖库
确保系统安装了 `python3-venv`、`ffmpeg` 并且启动了虚拟环境：
```bash
sudo apt update
sudo apt install python3-venv python3-pip ffmpeg -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 第 3 步：配置环境变量
复制一份配置文件模板并进行编辑：
```bash
cp .env.sample .env
nano .env
```
根据文件内的注释，填入你自己的配置项，最关键的几项：
- `API_ID` = 你的 API ID
- `API_HASH` = 你的 API HASH
- `BOT_TOKEN` = 你的机器人 Token
- `OWNER_ID` = 你的 Telegram 用户 ID (重要！只有该 ID 的用户拥有全部管理员权限)
- `MONGO_DB` = 你的 MongoDB 数据库连接 URL

*(注：本修改版已移除了 FORCE_SUB 强制加群验证逻辑，因此该项不填也不会导致机器人崩溃报错！)*

### 第 4 步：运行与守护进程
我们推荐使用 `systemd` 将机器人配置为后台自启服务，确保其 24 小时稳定运行。

创建一个服务文件：
```bash
sudo nano /etc/systemd/system/gagan-v3.service
```
写入以下内容（注意替换为你的实际路径）：
```ini
[Unit]
Description=Save Restricted Content Bot V3
After=network.target

[Service]
User=root
WorkingDirectory=/root/gagan-v3
ExecStart=/root/gagan-v3/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
保存并退出后，启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable gagan-v3
sudo systemctl start gagan-v3
```
使用 `journalctl -u gagan-v3 -f` 可实时查看运行日志。

### 第 5 步：设置 BotFather 菜单
前往 Telegram 的 [@BotFather](https://t.me/BotFather)，选择你的机器人，点击 **Edit Bot** -> **Edit Commands**。
直接复制粘贴以下内容并发送，即可瞬间拥有完美的中文快捷菜单：
```
start - 🚀 开始使用
batch - 🫠 批量抓取内容
login - 🔑 登录私有频道
settings - ⚙️ 机器人设置
help - ❓ 帮助信息
stats - 📊 运行统计
plan - 💰 订阅计划
logout - 🚪 退出登录
cancel - 🚫 取消当前操作
```

## 📖 核心功能详细使用说明

### 1. 🔑 私有频道下载 (`/login`)
*   **适用场景**：当你想下载的链接格式为 `https://t.me/c/xxx/123` 时，这属于私有频道。普通的机器人无法直接访问，必须通过您的账号授权。
*   **使用步骤**：
    1. 在机器人中发送 `/login` 指令。
    2. 按照机器人提示，发送您的 **手机号** (需包含国际区号，如 `+86138...`)。
    3. 您的 Telegram 会收到一个官方登录验证码，将该验证码发给机器人。
    4. 如果您开启了两步验证，机器人会提示您输入密码，直接发送即可。
*   **安全性**：本程序会在您的本地生成一个加密的 Session 字符串用于访问权限。您可以随时发送 `/logout` 来撤销授权并清理登录信息。

### 2. 🤖 使用个人机器人转发 (`/setbot`)
*   **适用场景**：在高并发或大文件转发时，使用主机器人可能会触发 Telegram 的流量限制。您可以设置一个属于您个人的专属机器人来执行这些任务。
*   **使用步骤**：
    1. 前往 [@BotFather](https://t.me/BotFather) 创建一个新的机器人并获取 `API Token`。
    2. 在本机器人中发送指令：`/setbot <您的机器人TOKEN>`。
    3. 之后您的下载任务将通过该专属机器人进行中转。

### 3. 📝 自动汉化处理
*   **说明**：本版本已实现**全自动识别**。您不需要输入任何特殊命令，直接将 Telegram 消息链接发送给机器人，它就会自动开始处理。
*   **配置**：发送 `/settings` 可以开启自定义重命名、添加关键词过滤等高级功能。

## ⚠️ 免责声明
本工具仅供学习与技术交流使用。请尊重内容版权，勿将本工具用于任何非法传播盗版或侵权内容的商业行为。

## 📅 更新日志 (Update History)

### [2026.05.13] - 深度汉化与功能大版本更新
- **全系统深度汉化**：
  - 彻底完成了所有插件（`ytdl`, `login`, `batch`, `stats`, `start`）的交互提示汉化。
  - 优化了登录流程、批量搬运、运行统计等模块的中文文案，更符合国人使用习惯。
  - 汉化了上传/下载进度条，包含百分比、速度、预计剩余时间等。
- **新增 `/music` 音乐搜索下载功能**：
  - 支持通过关键词（如 `/music 求佛`）直接搜索并下载最高音质音频。
  - **320kbps 极高音质**：默认提取并转换最高质量 MP3。
  - **自动元数据写入**：自动抓取并写入歌曲标题、歌手、封面图。
  - **智能来源标注**：文件下方自动标注音源来源（如 YouTube, Spotify）。
- **新增 Spotify 链接支持**：
  - 支持直接粘贴 Spotify 歌曲链接，机器人会自动寻找最佳音源进行转录下载。
- **系统底层优化与修复**：
  - **FFmpeg 环境集成**：修复了音频转码所需的 FFmpeg/ffprobe 环境依赖问题。
  - **Cookie 机制重构**：修复了 `yt-dlp` 的 Netscape Cookie 格式报错，并增加了无效 Cookie 自动跳过重试机制。
  - **移除品牌水印**：移除了所有原版残留的第三方推广水印及“由 Antigravity 驱动”等字样，保持文件纯净。
  - **快捷指令菜单**：同步更新了 Telegram 左下角 `/` 快捷指令菜单的中文说明。
