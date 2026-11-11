<div align="center">

<img src="https://cdn.inglescurso.org/file/1eCvmMGofB-JGLwgWTcPmvDwuVnhZqEDn/nebula-ftp-logo.png" alt="Logo Nebula FTP" width="300px">

### **Unlimited space for your files, powered by Telegram**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Free](https://img.shields.io/badge/Price-Free-brightgreen.svg)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Windows | Linux](https://img.shields.io/badge/Windows%20%7C%20Linux-OK-informational.svg)](#)

[🇧🇷 Português](README.md) | [🇺🇸 English](#)

**Store as many files as you want, without paying for space.** Access them from your browser or as a drive on your computer.

</div>

---

## 💡 What you get

- ☁️ **Unlimited space** — your files are kept in a private Telegram channel. No storage fees.
- 💽 **Works like a drive on your PC** — shows up in Windows as a drive (`Z:`), without using your hard disk.
- 🌐 **Access from anywhere** — use your browser to upload, download, rename and organize.
- 🎬 **Watch and listen right away** — videos and music play in the browser, without downloading the whole file.
- 👨‍👩‍👧 **Multiple users** — each person has their own folder and sees only what is theirs.
- 🛠️ **You're in charge** — create, edit and remove users from the panel.
- 🔒 **Secure** — encrypted connection and protected passwords.
- 🆓 **Free and open source** — install it in a few minutes on your computer or server.

> ℹ️ This free edition uses **one Telegram bot**, so space is unlimited but upload speed
> has a ceiling (about 10 MB/s). Need more? Check out [**Nébula Drive**](#-want-more-meet-nébula-drive).

---

## 📸 What it looks like

<table>
<tr>
<td><img src="https://cdn.inglescurso.org/file/1CChiNQ6FJscwTyqkyAcDHwQWwA9r78Ak/nebula-ftp-print-arquivos.png" alt="Your files"></td>
<td><img src="https://cdn.inglescurso.org/file/1VYubEs1IWrRWTNEjAcvk91Q0f7SLpgf-/nebula-ftp-print-player.png" alt="Video player"></td>
</tr>
<tr>
<td align="center"><b>Your files</b> in the browser</td>
<td align="center"><b>Watch</b> without downloading</td>
</tr>
<tr>
<td><img src="https://cdn.inglescurso.org/file/1uD4GoCSTUHl3yIxpChv2GQLwlQjJECrm/nebula-ftp-print-usuarios.png" alt="Manage users"></td>
<td><img src="https://cdn.inglescurso.org/file/1txk7IYoNrd36Ka9LURBa6Z8R_8ZSnkId/nebula-ftp-print-login.png" alt="Login screen"></td>
</tr>
<tr>
<td align="center"><b>Manage</b> your users</td>
<td align="center"><b>Everyone</b> with their own access</td>
</tr>
</table>

---

## 🚀 Install in 3 steps

You'll need a Telegram account. The [📖 Telegram guide](docs/TELEGRAM_SETUP-en.md) shows how to create the bot and the channel, step by step.

```bash
# 1) Download
git clone https://github.com/samucamg/NebulaFTP.git && cd NebulaFTP

# 2) Fill in your Telegram details and the admin password
cp .env.example .env && nano .env

# 3) Start
docker compose up -d --build
```

Done! Open `http://SERVER_IP:8082` in your browser and log in as admin.

📖 **Installing without Docker, Windows, using it as a `Z:` drive (RaiDrive) and every option:** [Installation guide](docs/INSTALLATION-en.md)

---

## 💎 Want more? Meet Nébula Drive

<div align="center">
<img src="https://cdn.inglescurso.org/file/1hNoblJw-DtPJSNEO-GfrPvwFWMUPBXsb/nebula-drive-print-filmes.png" alt="Nébula Drive — movie library" width="90%">
</div>

**Nébula Drive** is the full edition: it brings together your **personal cloud** (like Google Drive),
your **movie and series streaming** (like Netflix), a **book reader that reads aloud**,
a **music player** and an **online Office** to create and edit documents.

| | 🆓 Community | 💎 Nébula Drive |
|---|:---:|:---:|
| Unlimited space on Telegram | ✅ | ✅ |
| Access as a drive on your computer | ✅ | ✅ PC, Mac, phone and TV |
| Multiple users, each with their own folder | ✅ | ✅ + groups, quotas and access expiry |
| Watch videos and play music in the browser | ✅ basic | ✅ Netflix-style |
| Upload speed | 1 bot | ⚡ several bots, much faster |
| Google Drive-style sharing (links with password and expiry) | ❌ | ✅ |
| Libraries with covers, synopses and seasons | ❌ | ✅ |
| "Continue watching" and "Continue reading" | ❌ | ✅ |
| Mini dramas, music and video lessons, organized | ❌ | ✅ |
| Book and comic reader with natural voice | ❌ | ✅ |
| Create and edit Word, Excel and PowerPoint online | ❌ | ✅ |
| Import folders from Google Drive | ❌ | ✅ |
| Version history, trash and favorites | ❌ | ✅ |
| Artificial Intelligence assistant | ❌ | ✅ |
| Watch on Smart TV (Jellyfin, Kodi) | ❌ | ✅ |
| Automatic backup of your files | ❌ | ✅ |
| App for phone and computer, dark theme | ❌ | ✅ |
| MongoDB database (for large installs) | ❌ | ✅ |
| Support | Community | Priority |

<table>
<tr>
<td><img src="https://cdn.inglescurso.org/file/1oXFOiBdiWOut8Qmib4-SOVdolX6SB0h-/nebula-drive-print-serie.png" alt="Series"></td>
<td><img src="https://cdn.inglescurso.org/file/1CsUvjgGvBGhGteDkVBHScDQsRD9epxD-/nebula-drive-print-leitor-voz.png" alt="Book and document reader"></td>
<td><img src="https://cdn.inglescurso.org/file/1DEEiowlq5aUEd3wb6XFT4ezOvSuEZMzD/nebula-drive-print-compartilhar.png" alt="Sharing"></td>
</tr>
<tr>
<td align="center">🎬 Series by season</td>
<td align="center">📚 Books that read to you</td>
<td align="center">🔗 Share with anyone</td>
</tr>
</table>

👉 **[See everything Nébula Drive does, with screenshots of every screen](docs/NEBULA-DRIVE-en.md)**

📩 **Want Nébula Drive?** Contact me: samuel@inglescurso.com.br

---

## ❓ Quick questions

**Is it really free?** Yes. NebulaFTP Community is free and open source (MIT license).

**Is the space really unlimited?** Telegram doesn't charge for or limit space. This edition's limit is upload speed.

**Are my files public?** No. They are kept in a **private** channel that only your bot can access.

**Do I need to keep my computer on?** The system must be running for you to reach your files. Installing it on a server (VPS) is ideal.

**Can I lose my files?** Keep a copy of the database file: it's what knows where each file is. Nébula Drive makes automatic backups.

---

## 🤝 Contributing

Contributions are welcome! Open an [issue](https://github.com/samucamg/NebulaFTP/issues) or a
[pull request](https://github.com/samucamg/NebulaFTP/pulls) — and ⭐ star the project!

---

## 📜 License

This project is licensed under the **MIT** license. See [LICENSE](LICENSE) for details.

---

## 💬 Support

- 🐛 **Bugs and suggestions:** [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues)
- 💡 **Discussions:** [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions)
- 💎 **Nébula Drive / business inquiries:** samuel@inglescurso.com.br *(business only — no free support by e-mail)*

---

## 📊 Stats

![GitHub Stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub Forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub Issues](https://img.shields.io/github/issues/samucamg/NebulaFTP)

---

<div align="center">

**Made with ❤️ by [Samuel de Sousa Santos](https://github.com/samucamg)**

</div>
