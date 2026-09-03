<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Nebula FTP Logo" width="300px">

### **Turn Telegram into Your Unlimited Storage via FTP/SFTP**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/samucamg/NebulaFTP/pulls)

[🇧🇷 Português](README.md) | [🇺🇸 English](#)

**FTP + SFTP Server** with a web admin panel, using **Telegram as a storage backend**.

</div>

---

## 📌 What is Nebula FTP?

**Nebula FTP** turns any Telegram channel into a "drive" accessible via standard file protocols.
Keep using your favourite clients (FileZilla, WinSCP, RaiDrive, rclone, WinSCP/SFTP…) and the system
handles **chunking, uploading and indexing** every file in Telegram.

### ✨ Current Features

- **📡 FTP Server** — port `2121` (default), custom async server with PASV/EPSV support,
  listing, upload, download, rename, move, delete, mkdir and **download resume (REST)**.
- **🔐 SFTP Server (SSH)** — port `2222` (default), sharing the **same users and permissions as FTP**
  (host key auto-generated at `sftp_host_key`).
- **🖥️ Web Admin Panel** — port `8080` (default): create users, change passwords and
  manage **per-folder permissions** (read/write) without touching the database.
- **⚡ Turbo Upload (Staging)** — uploads land first on **local disk (instant)** and go to
  Telegram in the **background**, with no client timeouts.
- **☁️ Download/Streaming by Parts** — the file is reassembled from the parts (`part_NNN`)
  already sent to Telegram, even if no local copy exists. Offset (seek) reads via SFTP enable
  media streaming without downloading the entire file.
- **🗄️ SQLite (default) or MongoDB** — choose via `.env` (`DB_TYPE`). No need to install MongoDB
  to get started.
- **🛡️ Robust** — retry with backoff (FloodWait/RPC), staging garbage collector, rotating logs,
  metrics and graceful shutdown.
- **👥 Multi-user** — each user has their own home (`/<login>`) and per-path permissions.
- **🤖 Multi-Bot** — distributes load across multiple bots. **Pro version only 💎**
  (Community uses the first token in `BOT_TOKENS`).

> 💎 **Community vs Pro:** this is the **Community (open source)** version — 1 bot, up to ~10 MB/s.
> The **Pro** version includes Multi-Bot (4–8 bots, up to 60 MB/s), automatic backup channel and
> priority support. See the full comparison in [ECOSYSTEM.md](docs/ECOSYSTEM.md).

---

## 🏗️ Architecture

```
┌─────────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────┐
│  FTP Client (FileZilla,     │   │  SFTP Client (WinSCP,    │   │  Web Panel       │
│  RaiDrive, rclone...)       │   │  sshfs, rclone...)       │   │  (port 8080)     │
└──────────────┬──────────────┘   └────────────┬─────────────┘   └────────┬─────────┘
               │                               │                          │
               └───────────────┬───────────────┘──────────────────────────┘
                               ▼
              ┌───────────────────────────────────┐
              │      NEBULA FTP SERVER            │
              │  ┌─────────────────────────────┐  │
              │  │ Folder Watcher (staging)    │  │
              │  │ Upload Workers (queue)      │  │
              │  │ PathIO (assemble/stream)    │  │
              │  │ Garbage Collector           │  │
              │  │ Per-user Permissions        │  │
              │  └─────────────────────────────┘  │
              └──────┬──────────────────┬─────────┘
                     ▼                  ▼
         ┌──────────────────┐  ┌──────────────────┐
         │ SQLite (default) │  │    Telegram      │
         │ or MongoDB       │  │ (channel: parts  │
         │ (metadata)       │  │  UUID.part_NNN)  │
         └──────────────────┘  └──────────────────┘
```

**Upload flow (Turbo Upload):** FTP client sends → file written to `staging/` (instant) →
`folder_watcher` enqueues → workers chunk the file (`CHUNK_SIZE_MB`) and push to channel →
metadata (parts) saved to the database → local copy removed.

**Download flow:** the server reads the parts metadata and **downloads from Telegram on demand**,
delivering the file to the FTP/SFTP client — no local copy needed.

---

## 📁 Requirements

- 🐍 **Python 3.10+** (native install) or 🐳 **Docker** (Linux/VPS recommended).
- 📱 **Telegram**: API ID/Hash ([my.telegram.org](https://my.telegram.org)), a **bot** ([@BotFather](https://t.me/BotFather)) and a **channel** with the bot as admin.
  [📖 Full Telegram guide →](docs/TELEGRAM_SETUP.md)
- 🗄️ *(Optional)* **MongoDB** local/Atlas — only if you want `DB_TYPE=mongodb`.
  With the default **SQLite** nothing needs to be installed.

---

## 🚀 Installation

### Option 1 — Docker (recommended for Linux/VPS) 🐳

```bash
# 1) Clone the repository
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP

# 2) Configure .env (API_ID, API_HASH, BOT_TOKENS, CHAT_ID...)
cp .env.example .env
nano .env

# 3) Create persistence files (first time only)
mkdir -p staging
touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session

# 4) Start
docker compose up -d

# 5) Follow logs
docker compose logs -f nebulaftp
```

> `docker-compose.yml` uses **host networking** (works transparently with passive FTP on a VPS).
> On **Windows/macOS with Docker Desktop** (no host network support) prefer **Option 3 — Python**.

### Option 2 — Portainer 🐳

1. Clone the repository on the host: `git clone https://github.com/samucamg/NebulaFTP.git` (e.g., `/opt/NebulaFTP`).
2. Create the `.env` file (`cp .env.example .env` and edit).
3. Create persistence files (first time):
   `mkdir -p staging && touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session`
4. Build the image once: `docker compose build` (or `docker build -t nebulaftp .`).
5. In **Portainer**: `Stacks → Add stack → Web editor` → paste the content of
   [**`portainer-stack.yml`**](portainer-stack.yml) → adjust volume paths
   (default: `/opt/NebulaFTP`) → set environment variables → **Deploy the stack**.

### Option 3 — Python directly 🐍

```bash
# 1) Clone and set up environment
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Configure — use the interactive wizard (recommended)
python setup.py
# ...or manually:
cp .env.example .env && nano .env

# 4) Run
python main.py
```

**📖 Detailed guides:** [Python Installation](docs/INSTALLATION.md) · [Docker](docs/DOCKER.md)

---

## 🔐 First Access and Users

- With the **SQLite** backend (default), the system automatically creates the user
  **`admin` / `admin`** on first run. **⚠️ Change the password** via the web panel!
- With the **MongoDB** backend, no default user is created: add the first one via the web panel.
- Open the **web panel** at `http://SERVER_IP:8080` to manage users:
  - Create user, change password, delete;
  - Add per-folder permissions (`readable` / `writable`);
  - Each user has full access to their own home `/<login>` — folders outside require explicit permissions.
- Optionally protect the panel by setting `WEB_ADMIN_PASSWORD` in `.env` (Basic Auth).

---

## ⚙️ Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `API_ID` / `API_HASH` | — | Credentials from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKENS` | — | Bot token(s), comma-separated *(Community uses the 1st; Multi-Bot = Pro 💎)* |
| `CHAT_ID` | — | Channel ID where files are stored (format `-100...`) |
| `DB_TYPE` | `sqlite` | Metadata backend: `sqlite` or `mongodb` |
| `DB_FILE` | `nebula.db` | SQLite database file (when `DB_TYPE=sqlite`) |
| `MONGODB` | — | MongoDB URI (when `DB_TYPE=mongodb`) |
| `HOST` | `0.0.0.0` | Server bind interface (see PASV/EPSV tip below) |
| `PORT` | `2121` | **FTP** port |
| `SFTP_PORT` | `2222` | **SFTP/SSH** port |
| `WEB_PORT` | `8080` | **Web panel** port |
| `WEB_ADMIN_PASSWORD` | *(empty)* | Password to protect the web panel (optional) |
| `MAX_WORKERS` | `4` | Concurrent upload workers |
| `CHUNK_SIZE_MB` | `64` | Size of each chunk sent to Telegram |
| `MAX_RETRIES` | `5` | Retries per chunk on failure |
| `MAX_STAGING_AGE` | `3600` | Max age (s) of orphan staging files before GC removes them |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> 💡 **PASV/EPSV Tip:** with `HOST=0.0.0.0`, clients using **EPSV** work fine.
> If a client insists on **PASV** from another machine, set `HOST` to the server's LAN or public IP
> so the advertised address is reachable.

Full template with comments: [`.env.example`](.env.example).

---

## 📁 Mounting as a Network Drive / WebDAV (rclone and RaiDrive)

Nebula FTP is a standard FTP/SFTP server — so it can be mounted as a **network drive**
with common tools:

| Goal | Tool |
|---|---|
| Windows — drive letter (Z:, Y:...) | **RaiDrive** (FTP protocol) |
| Linux — mounted folder or WebDAV for other apps | **rclone** (mount + `serve webdav`) |
| Windows/Linux — command-line alternative | **rclone** |

> Use credentials from a user created in the web panel.
> With SQLite default, the initial user is `admin/admin` (change the password!).
> The user's root folder is `/<login>`.

### 🪟 Windows — RaiDrive (recommended)

1. Download and install [RaiDrive](https://www.raidrive.com/) (free version supports FTP).
2. Open RaiDrive → **Add** → choose **FTP** group → **FTP**.
3. Fill in:
   - **Address:** `SERVER_IP`
   - **Port:** `2121`
   - **Username / Password:** web panel user (e.g., `admin`)
4. Under **Drive**, pick a letter (e.g., `Z:`) → **Connect**.
5. Done: the "drive" shows up in **Windows Explorer** with your Telegram files.

> If Explorer freezes on listings/downloads, check Windows Firewall for ports
> `2121` (and `2222`/`8080` for SFTP/panel) and prefer local/VPN connections.

### 🐧 Linux — rclone via SFTP (recommended for streaming)

The Nebula SFTP server (port `2222`) supports **offset reads (seek)** — for
**video playback** directly from the "drive"/WebDAV, prefer the SFTP remote:

```ini
[nebula-sftp]
type = sftp
host = SERVER_IP
user = admin
pass = PUT_HERE_THE_OUTPUT_OF:  rclone obscure "YOUR_PASSWORD"
port = 2222
```

```bash
rclone lsd nebula-sftp:              # test the connection
mkdir -p ~/NebulaFTP
rclone mount nebula-sftp: ~/NebulaFTP --vfs-cache-mode writes &

# Expose as WebDAV (Kodi, Plex, Windows "Map network drive"):
rclone serve webdav nebula-sftp: --addr :8082 --user admin --pass YOUR_PASSWORD
```

### 🐧 Linux — rclone via FTP

Install rclone and FUSE:

```bash
sudo apt update && sudo apt install -y rclone fuse3
```

Configure the remote interactively:

```bash
rclone config
# n) New remote
# name> nebula
# type> ftp
# host> SERVER_IP
# user> admin
# pass> YOUR_PASSWORD
# port> 2121
```

Or edit `~/.config/rclone/rclone.conf` manually:

```ini
[nebula]
type = ftp
host = SERVER_IP
user = admin
pass = PUT_HERE_THE_OUTPUT_OF:  rclone obscure "YOUR_PASSWORD"
port = 2121
```

Mount as a folder:

```bash
rclone lsd nebula:
mkdir -p ~/NebulaFTP
rclone mount nebula: ~/NebulaFTP --vfs-cache-mode writes &
# to unmount: fusermount -u ~/NebulaFTP
```

Expose as WebDAV (for Windows "Map network drive", Kodi, Jellyfin, etc.):

```bash
rclone serve webdav nebula: --addr :8082 --user admin --pass YOUR_PASSWORD
# WebDAV endpoint: http://SERVER_IP:8082
```

### 🪟 Windows — rclone (alternative)

```powershell
winget install Rclone.Rclone
rclone config                        # same "nebula" remote (type = ftp or sftp)
rclone mount nebula: N: --vfs-cache-mode writes
# or expose as WebDAV:
rclone serve webdav nebula: --addr :8082 --user admin --pass YOUR_PASSWORD
```

### ⚠️ FTP Mount Notes

- **Uploads**: instant (local staging), finalised in the background on Telegram. ✅
- **Downloads**: full file downloads work well. For **seeking within large videos**
  (constant seek), prefer the **SFTP remote above** or the streaming products in
  the ecosystem (Nebula Stream).
- RaiDrive and rclone cache listings — adjusting cache settings helps with large folders.

---

## 🌌 Nebula Ecosystem

**Nebula FTP** is part of a larger ecosystem:

| Project | Description | Status |
|---------|-------------|--------|
| **[NebulaFTP](docs/ECOSYSTEM.md#-nebulaftp)** | FTP + SFTP server with Telegram (**this repo**) | ✅ **Available** |
| **[NebulaStream](docs/ECOSYSTEM.md#-nebulastreaming)** | Web interface + streaming player | 🚧 In development |
| **[NebulaWebDAV](docs/ECOSYSTEM.md#-nebulawebdav)** | WebDAV server for Kodi/Plex | 🚧 In development |
| **[NebulaSFTP](docs/ECOSYSTEM.md#-nebulasftp)** | Dedicated SFTP product (basic SFTP already in NebulaFTP) | 📋 Planned |

> 💎 **Multi-Bot, backup channel and speeds up to 60 MB/s are Pro-only features.**
> Community uses 1 bot. [Learn more about the Ecosystem →](docs/ECOSYSTEM.md)

---

## 🐳 Docker — Details

- **`docker-compose.yml`** — standard deploy with `docker compose` (host network; persists `staging/`,
  `nebula.db`, logs, bot session and SFTP key in volumes).
- **`portainer-stack.yml`** — same stack ready to paste into **Portainer** (Stacks → Web editor).

**Default ports on the machine:** `2121` (FTP) · `2222` (SFTP) · `8080` (web panel).

**Persistence (important):** `nebula.db` (metadata) and `Nebula_MonoBot.session`
(bot session) must be in volumes — the compose already handles this. If running manually
(`docker run`), mount these files/folders to avoid losing data on container recreation.

**Auto-correction (entrypoint):** the image ships an `entrypoint.sh` that ensures `nebula.db`,
`nebula.log`, `sftp_host_key` and `Nebula_MonoBot.session` exist as **files** inside the
container — if you skip the host file creation step and Docker creates an empty directory instead
of a bind-mount file, the entrypoint corrects it automatically at startup. (Empty files are valid:
SQLite and Pyrogram initialise them on first use.)

**MongoDB backend in Docker:** if using `DB_TYPE=mongodb`, point `MONGODB` to an accessible
MongoDB instance (e.g., MongoDB Atlas or a separate Mongo container).

---

## ❓ Troubleshooting (quick)

| Problem | Likely cause / fix |
|---|---|
| `Connection refused` | Server stopped, wrong port or firewall. Open `2121` (and `2222`, `8080`). |
| Freezes on listing/download | Passive mode: use EPSV in the client or set `HOST` to the machine's IP (see tip above). |
| `Peer id invalid` in logs | The bot is not admin of the channel — add it as administrator. |
| Forgot `admin` password | With SQLite, stop the service, delete `nebula.db` (or the user row in `users` table) and restart — `admin/admin` is recreated. |
| Container recreated lost data | `nebula.db`/session were not in a volume — see Docker section. |

---

## 🤝 Contributing

Contributions are welcome! Open an [issue](https://github.com/samucamg/NebulaFTP/issues) or a
[pull request](https://github.com/samucamg/NebulaFTP/pulls) — and ⭐ star the project!

---

## 📜 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 💬 Support

- 🐛 **Bugs & suggestions:** [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues)
- 💡 **Discussions:** [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions)
- 💎 **Pro version / commercial:** samuel@inglescurso.com.br *(commercial only — no free support by e-mail)*

---

## 📊 Stats

![GitHub Stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub Forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub Issues](https://img.shields.io/github/issues/samucamg/NebulaFTP)

---

<div align="center">

**Made with ❤️ by [Samuel de Sousa Santos](https://github.com/samucamg)**

</div>