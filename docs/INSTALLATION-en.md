[🇺🇸 English](#) | [🇧🇷 Português](INSTALLATION.md)

# 💾 Installation — Python (Native)

Complete guide to install Nebula FTP directly with Python (no Docker).

---

## 📋 Requirements

| Item | Details |
|---|---|
| **OS** | Linux (Ubuntu 20.04+), Windows 10/11, macOS 12+ |
| **Python** | 3.10 or higher (required) |
| **Git** | To clone the repository |
| **MongoDB** | *(Optional)* — only if using `DB_TYPE=mongodb`. The default is **SQLite** (no installation needed). |

---

## 🐧 Linux (Ubuntu/Debian)

### 1. Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git

# Verify
python3 --version   # must be >= 3.10
```

### 2. Clone the Repository

```bash
cd /opt
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

### 3. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
# Prompt changes to: (venv) user@host:...$
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure .env

**Option A — Interactive wizard (recommended):**

```bash
python setup.py
```

The wizard asks for: API_ID, API_HASH, BOT_TOKENS, CHAT_ID, FTP/SFTP/Web ports and panel password;
then generates the `.env` automatically.

**Option B — Manual:**

```bash
cp .env.example .env
nano .env
```

Fill in at least `API_ID`, `API_HASH`, `BOT_TOKENS` and `CHAT_ID`.
See the [Telegram Guide](TELEGRAM_SETUP-en.md) to obtain these values.

### 6. (Optional) MongoDB as database

If you prefer MongoDB instead of the default SQLite, install and configure it:

```bash
# Ubuntu — MongoDB (optional)
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

In `.env`:

```env
DB_TYPE=mongodb
MONGODB=mongodb://localhost:27017
```

Or use **MongoDB Atlas (cloud)** and point `MONGODB` to the connection string.

### 7. Start the Server

```bash
# With venv activated:
python main.py
```

Expected output:

```
INFO - 🤖 Nebula FTP MonoBot Connected
INFO - ✅ Channel confirmed: Nebula Storage (ID: -1001234567890)
INFO - 🚀 FTP server running on port 2121
INFO - 🔐 SFTP server running on port 2222
INFO - 🌐 Web panel running on port 8080
```

### 8. Create and Manage Users

Open `http://localhost:8080` in your browser. With SQLite, the default user is **`admin` / `admin`** —
change the password immediately.

---

## 🪟 Windows (Native)

### 1. Install Python

1. Download Python 3.11+ from https://python.org
2. ⚠️ Check **"Add Python to PATH"** during installation

### 2. Install Git

Download from https://git-scm.com/download/win

### 3. Clone the Repository

Open **PowerShell**:

```powershell
cd C:\
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

### 4. Create Virtual Environment

```powershell
python -m venv venv
venv\Scripts\activate
```

### 5. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 6. Configure and Start

```powershell
# Interactive wizard (recommended)
python setup.py

# Then start:
python main.py
```

Open the panel at `http://localhost:8080`.

---

## 🍎 macOS

```bash
# Install Homebrew (if not already installed):
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Dependencies
brew install python@3.11 git

# Follow from Step 2 of the Linux guide
```

---

## 🚀 Run as a Service (Linux — systemd)

```bash
sudo nano /etc/systemd/system/nebulaftp.service
```

Paste:

```ini
[Unit]
Description=Nebula FTP Server
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/opt/NebulaFTP
Environment="PATH=/opt/NebulaFTP/venv/bin"
ExecStart=/opt/NebulaFTP/venv/bin/python /opt/NebulaFTP/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now nebulaftp
sudo journalctl -u nebulaftp -f   # follow logs
```

---

## 🔧 Advanced Configuration

### Ports

Adjust in `.env` as needed:

```env
PORT=2121           # FTP
SFTP_PORT=2222      # SFTP
WEB_PORT=8080       # Web Panel
```

### Web Panel Protection

```env
WEB_ADMIN_PASSWORD=yoursecretpassword
```

### Multi-Bot — Pro version only 💎

```env
BOT_TOKENS=bot1_token,bot2_token,bot3_token
```

In Community, only the first token is used.

### Performance

```env
MAX_WORKERS=8      # concurrent uploads
CHUNK_SIZE_MB=64   # chunk size (Telegram max: 2 GB)
```

---

## ❓ Troubleshooting

### `ModuleNotFoundError: No module named 'pyrogram'`

```bash
source venv/bin/activate   # activate the venv first!
pip install -r requirements.txt
```

### `Connection refused` when connecting via FTP

1. Check that `python main.py` is running
2. Check firewall: `sudo ufw allow 2121/tcp`
3. Confirm port in `.env`: `PORT=2121`

### `Peer id invalid` in logs

See [Telegram Setup](TELEGRAM_SETUP-en.md#common-issues)

---

## 📚 Next Steps

✅ Server installed!

- [Mount as drive / WebDAV (rclone and RaiDrive)](../README-en.md#-mounting-as-a-network-drive--webdav-rclone-and-raidrive)
- [Docker documentation](DOCKER-en.md)
- [Nebula Ecosystem](ECOSYSTEM-en.md)

---

[← Back to README](../README-en.md)