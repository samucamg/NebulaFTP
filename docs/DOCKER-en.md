<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Nebula FTP Logo" width="300px">

</div>

---

[🇺🇸 English](#) | [🇧🇷 Português](DOCKER.md)

# 🚀 Installation Guide: NebulaFTP Community (Docker)

Welcome to **NebulaFTP Community Edition**! This guide shows you how to run the
**FTP + SFTP + Web Panel** server on an Ubuntu 22.04 VPS using Docker.

> **Prerequisites:**
> 1. **API ID and API HASH** → [my.telegram.org](https://my.telegram.org)
> 2. **BOT TOKEN** → create one with [@BotFather](https://t.me/BotFather)
> 3. **CHAT ID** → private channel with the bot as admin (get the ID via [@userinfobot](https://t.me/userinfobot))
>
> 📖 Full guide: [Configure Telegram](TELEGRAM_SETUP-en.md)

---

## 🛠️ Step 1: Install Docker

```bash
# Official Docker installation
curl -fsSL https://get.docker.com | sudo sh

# Start and enable service
sudo systemctl enable --now docker

# (Optional) Run docker without sudo
sudo usermod -aG docker $USER && newgrp docker
```

---

## 📂 Step 2: Clone the Repository

```bash
cd /opt
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

---

## ⚙️ Step 3: Configure .env

```bash
cp .env.example .env
nano .env
```

Fill in the required variables:

```env
# ============= TELEGRAM =============
API_ID=12345678
API_HASH=abc123def456789abcdef123456789ab
BOT_TOKENS=1234567890:AABBccDDeeFFggHH...
CHAT_ID=-1001234567890

# ============= DATABASE =============
# 'sqlite' (default, no installation needed) or 'mongodb'
DB_TYPE=sqlite
DB_FILE=nebula.db

# ============= SERVERS =============
HOST=0.0.0.0
PORT=2121        # FTP
SFTP_PORT=2222   # SFTP/SSH
WEB_PORT=8080    # Web Panel

# Web panel password (empty = no password)
WEB_ADMIN_PASSWORD=

# ============= PERFORMANCE =============
MAX_WORKERS=4
CHUNK_SIZE_MB=64
MAX_RETRIES=5
MAX_STAGING_AGE=3600
LOG_LEVEL=INFO
```

**Save** with `Ctrl+O → Enter → Ctrl+X`.

---

## 🗂️ Step 4: Create Persistence Files (first time)

> Compose volumes mount **files** — if they don't exist, Docker will create **directories** instead
> (which breaks SQLite and the session). The `entrypoint.sh` auto-fixes this, but creating
> the files beforehand is safer:

```bash
mkdir -p staging
touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session
```

---

## 🏗️ Step 5: Build and Start

```bash
# Build the image (first time takes 3-5 min)
docker compose build

# Start in background
docker compose up -d

# Check if running
docker ps
```

Expected output:

```
CONTAINER ID   IMAGE         STATUS         PORTS
abc123...      nebulaftp     Up 10 seconds
```

*(Host network: no mapped ports shown — the container uses the machine's ports directly.)*

---

## 👀 Step 6: Check Logs

```bash
docker compose logs -f nebulaftp
```

Expected output:

```
INFO - 🤖 Nebula FTP MonoBot Connected
INFO - ✅ Channel confirmed: Nebula Storage (ID: -1001234567890)
INFO - 🚀 FTP server running on port 2121
INFO - 🔐 SFTP server running on port 2222
INFO - 🌐 Web panel running on port 8080
```

**Press `Ctrl+C`** to exit the log stream.

---

## 👥 Step 7: Users

### With SQLite (default)

On **first run**, the system automatically creates the user **`admin` / `admin`**.
**Change the password immediately** via the web panel!

### Create and manage users — Web Panel

1. Open `http://SERVER_IP:8080` in your browser.
2. (If `WEB_ADMIN_PASSWORD` is set, log in with that password.)
3. Create, edit or delete users and configure per-folder permissions.

---

## 📡 Step 8: Connect

### Via FTP (FileZilla, WinSCP, RaiDrive…)

| Field | Value |
|---|---|
| Host | Server IP |
| Port | `2121` |
| User | `admin` (or the one you created) |
| Password | your password |
| Mode | Passive / EPSV |

### Via SFTP (WinSCP, FileZilla, sshfs, rclone…)

| Field | Value |
|---|---|
| Host | Server IP |
| Port | `2222` |
| User | `admin` |
| Auth | Password |

---

## 🔥 Firewall (Important!)

```bash
sudo ufw allow 2121/tcp   # FTP
sudo ufw allow 2222/tcp   # SFTP
sudo ufw allow 8080/tcp   # Web Panel
sudo ufw reload
sudo ufw status numbered
```

For **cloud providers** (AWS, DigitalOcean, etc.): open the same ports in your Security Group
or provider firewall panel.

---

## 💡 Useful Commands

```bash
# Stop
docker compose down

# Restart
docker compose restart nebulaftp

# Real-time logs
docker compose logs -f nebulaftp

# Update the code
docker compose down
git pull
docker compose build
docker compose up -d
```

### SQLite backup (default)

```bash
cp /opt/NebulaFTP/nebula.db /opt/NebulaFTP/backups/nebula-$(date +%Y%m%d).db
```

### If using MongoDB (DB_TYPE=mongodb)

```bash
# Backup
docker exec -it <mongo_container> mongodump --db ftp --out /backup
docker cp <mongo_container>:/backup ./backup-$(date +%Y%m%d)

# Restore
docker cp ./backup-20260903 <mongo_container>:/backup
docker exec -it <mongo_container> mongorestore --db ftp /backup/ftp
```

---

## ❓ Common Issues

### `Connection refused` when connecting via FTP/SFTP

```bash
docker ps                          # check if container is running
docker compose logs nebulaftp      # look for errors
telnet SERVER_IP 2121              # test FTP port
sudo ufw status                    # check firewall
```

### `Peer id invalid` in logs

The bot is not an administrator of the channel. Add it as admin with **all permissions** in Telegram.

### Container keeps restarting

```bash
docker compose logs nebulaftp
# Common causes:
# ❌ Invalid API_ID / API_HASH
# ❌ Invalid BOT_TOKEN
# ❌ Wrong CHAT_ID
# ❌ Bot has no permissions in the channel
```

### `nebula.db` is a directory (broken bind mount)

The `entrypoint.sh` fixes this automatically on startup (removes the empty dir and creates the file).
If needed, fix manually:

```bash
docker compose down
rm -rf /opt/NebulaFTP/nebula.db
touch /opt/NebulaFTP/nebula.db
docker compose up -d
```

### Port already in use

Change `PORT`/`SFTP_PORT`/`WEB_PORT` in `.env` and restart.

---

## 🚀 Next Steps

- ⭐ [GitHub](https://github.com/samucamg/NebulaFTP) — give us a star!
- 💎 [Pro version](ECOSYSTEM-en.md) — Multi-Bot (4–8 bots, up to 60 MB/s), backup channel, priority support
- 🐛 [Report bugs](https://github.com/samucamg/NebulaFTP/issues)
- 💬 [Discussions](https://github.com/samucamg/NebulaFTP/discussions)

---

## 🆘 Support

| Channel | Details |
|---|---|
| 🐛 Bugs / Features | [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues) |
| 💬 General questions | [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions) |
| 💼 Paid support | samuel@inglescurso.com.br |

> ⚠️ Free support is available **only** via the community channels above (not by e-mail/WhatsApp).

---

<div align="center">

**Made with ❤️ by [Samuel de Sousa Santos](https://github.com/samucamg)**

[⬅️ Back to README](../README-en.md) • [🌌 Nebula Ecosystem](ECOSYSTEM-en.md)

</div>