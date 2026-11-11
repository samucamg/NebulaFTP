# NebulaFTP Community

[Português](README.md) | English

File server that stores everything on **Telegram**: you access it over **SFTP** (FileZilla, WinSCP, RaiDrive) or through the **web panel**, and the files live in a Telegram channel.

- **Unlimited storage** on Telegram. This edition uses **a single bot**, so the real limit is speed: each file is sent to the channel one part at a time.
- Free and open source (MIT).

## Features

- **SFTP** (port 2222): upload, download, rename, delete, create folders. Compatible with FileZilla, WinSCP and RaiDrive.
- **Web panel** (port 8082): login, file manager (upload several GB directly to disk, download, rename, delete, create folders) and a player for video and audio that the browser can play (mp4, webm, mp3, m4a, ogg, opus, wav).
- **Users:** each user has their own folder and can only see it. Only the admin sees everything.
- **Storage:** the file first goes to disk (staging), is split into 100 MB parts and sent to the channel. Pending uploads continue after a restart. Overwriting or deleting also removes the old messages from the channel.
- **On-demand reading:** only the parts needed are downloaded into a local cache. The player and SFTP request ranges (Range) without downloading the whole file.
- **Database:** SQLite (one file, no server).

## How it works

```
SFTP / Web  ->  core (folders, permissions, versions)  ->  SQLite
                         |
                 disk staging  ->  worker (1 bot)  ->  Telegram channel
```

## Requirements

- Python 3.11 or newer (tested with 3.13), Windows or Linux. Or Docker.
- An account at <https://my.telegram.org> to obtain `API_ID` and `API_HASH`.
- A bot created with @BotFather and a private channel, with the bot as **administrator**.
- Disk space for staging and cache (at least the size of the largest file you will send).
- **Correct computer clock.** Telegram refuses connections when the difference is more than 30 seconds; the program warns at startup.

## Installation (Python)

```bash
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # on Windows: copy .env.example .env
# edit .env
python main.py
```

## Installation (Docker)

```bash
cp .env.example .env   # edit .env
docker compose up -d --build
```

Data (database, staging, cache, SFTP key and bot session) is stored in the `./data` folder.

## Configuration (.env)

| Variable | Default | Purpose |
|---|---|---|
| `API_ID`, `API_HASH` | — | Credentials from my.telegram.org |
| `BOT_TOKENS` | — | Bot token (only one) |
| `CHAT_ID` | — | Channel ID, e.g. `-1001234567890` |
| `WEB_ADMIN_USER` | `admin` | Administrator login |
| `WEB_ADMIN_PASSWORD` | — | Admin password, required on first run |
| `HOST` | `0.0.0.0` | Listening address |
| `SFTP_PORT` / `WEB_PORT` | `2222` / `8082` | Ports |
| `DATA_DIR` | `data` | Staging, cache, bot session |
| `DB_FILE` | `nebula.db` | SQLite database |
| `CHUNK_SIZE_MB` | `100` | Size of each part sent to the channel |
| `MAX_STAGING_AGE` / `CACHE_MAX_AGE` | `3600` | Seconds until unused local files are cleaned up |
| `SFTP_HOST_KEY` | `sftp_host_key` | SFTP server key (created automatically) |
| `LOG_LEVEL` | `INFO` | Log level |

## First access

1. Open `http://YOUR_IP:8082` and log in as admin.
2. Under **Users**, create the users. Each one gets the folder `/<login>`.
3. In FileZilla, WinSCP or RaiDrive: protocol **SFTP**, port **2222**, same login and password.

## Security

- Passwords are stored hashed (scrypt). Forms are protected against CSRF.
- The web panel uses HTTP. On the internet, put it behind an HTTPS proxy (Caddy, Nginx).
- There is no backup channel: Telegram may remove content or go offline. Keep copies of anything important.
- Back up the database file (`DB_FILE`): without it, the files cannot be reassembled from the channel.

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

The test suite uses a simulated Telegram and compares the sha256 of the round trip through the core, SFTP and web.

## Nébula Drive Enterprise

There is a separate commercial edition with more features. Optional paid professional installation: samuel@inglescurso.com.br.

## License

MIT.
