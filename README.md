# 受限内容破解转发机器人 (Save Restricted Content Bot V3) 🚀

这是一个高度定制化的受限内容下载与转发 Telegram 机器人。它可以自动保存和转发禁止转发/保存的频道和群组中的消息、图片、视频和文件。

**本项目是在 [devgaganin](https://github.com/devgaganin/Save-Restricted-Content-Bot-v3) 原项目的基础上，进行了深度定制、全面汉化、移除强制加群、并去除了所有烦人广告和暗桩的“纯净优化版”。**

## ✨ 核心功能特色
- **强制破解限制**：轻松下载并转发那些带有“限制保存/转发”标志的频道与群组内容。
- **全中文界面**：所有菜单指令和反馈信息已彻底汉化，更符合国人使用习惯。
- **完美去广告**：剔除了原版中强制显示“Get Premium”和“Join Channel”按钮的底层加密代码。
- **去除暗桩限制**：完全移除了 `FORCE_SUB` 强制订阅频道限制逻辑，真正做到开箱即用。
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

## ⚠️ 免责声明
本工具仅供学习与技术交流使用。请尊重内容版权，勿将本工具用于任何非法传播盗版或侵权内容的商业行为。
