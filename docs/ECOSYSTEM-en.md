<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_cloud.png" alt="Nebula Cloud Logo" width="300px">

**Turn Telegram into your unlimited storage infrastructure**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)

</div>

---

[🇺🇸 English](#) | [🇧🇷 Português](ECOSYSTEM.md)

## 📖 Index

- [Overview](#-overview)
- [Ecosystem Products](#-ecosystem-products)
  - [NebulaFTP](#-nebulaftp)
  - [NebulaStreaming](#-nebulastreaming)
  - [NebulaWebDAV](#-nebulawebdav)
  - [NebulaSFTP](#-nebulasftp)
- [Use Cases](#-use-cases)
- [Support](#-support)
- [License](#-license)

---

## 🌟 Overview

The **Nebula Ecosystem** is an integrated suite of solutions that uses Telegram's unlimited storage
as a backend for file transfer protocols and media streaming.

### Why Nebula?

✅ **Unlimited Storage** — leverage Telegram's limitless space  
✅ **Multi-Protocol** — FTP, SFTP, WebDAV and Web Streaming  
✅ **High Performance** — Multi-Bot for speeds up to 60 MB/s *(Pro)*  
✅ **Zero Cost** — free Community versions available  
✅ **Self-Hosted** — full control over your data  

---

## 📦 Ecosystem Products

---

### 🚀 NebulaFTP

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Nebula FTP Logo" width="250px">
</div>

**FTP + SFTP Server with Telegram — this repository**

Turn any FTP/SFTP client (FileZilla, WinSCP, RaiDrive, rclone…) into an interface
for Telegram's unlimited storage.

#### Community vs Pro Comparison

<table>
<thead>
<tr><th>Feature</th><th>Community (Free)</th><th>Pro (Paid) 💎</th></tr>
</thead>
<tbody>
<tr><td><strong>FTP Protocol</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>SFTP Protocol (built-in)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Web Admin Panel</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Multi-user + Permissions</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>SQLite database (default)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>MongoDB database (optional)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Rclone / RaiDrive (FTP or SFTP)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Number of Bots</strong></td><td>1 (up to ~10 MB/s)</td><td>4–8 (up to 60 MB/s)</td></tr>
<tr><td><strong>Multi-Bot (Round Robin)</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Automatic Backup Channel</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Automatic Database Backup</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Technical Support</strong></td><td>Community</td><td>Priority</td></tr>
</tbody>
</table>

#### Repository

📂 **GitHub**: [samucamg/NebulaFTP](https://github.com/samucamg/NebulaFTP)

#### Highlights

- ✅ Works **independently** from other ecosystem products
- ✅ SFTP and web panel **included** in the Community version
- ✅ Ideal for remote file access via FTP/SFTP and mounting as a drive (rclone, RaiDrive)

---

### 🎬 NebulaStreaming

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_stream.png" alt="Nebula Streaming Logo" width="250px">
</div>

**Web-based streaming and media management server**

Modern web interface for uploading, organising and **streaming media files** stored on Telegram.

#### Key Features

- 🌐 **Full Web Interface** — upload, file manager, integrated streaming player
- 🎥 **Media Center Compatible** — Emby, Jellyfin, Kodi, Plex (`.strm` generation)
- ⚡ **Multi-Bot / Multi-Channel** — up to 60 MB/s with redundancy
- 🔄 **Automatic Backup** of database and cross-channel sync

#### Status

🚧 **In development**

---

### 🗂️ NebulaWebDAV

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_webdav.png" alt="Nebula WebDAV Logo" width="250px">
</div>

**Native WebDAV server integrated with Telegram**

Access your files via WebDAV — compatible with Windows Explorer ("Map network drive"),
macOS Finder, Kodi, Plex and any WebDAV client.

#### Key Features

- 🖥️ Native access on Windows (no extra software)
- 🍎 macOS Finder compatible
- 🎬 Kodi and Plex integration
- ⚡ Multi-Bot for high speed

#### Status

🚧 **In development**

---

### 🔒 NebulaSFTP

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_sftp.png" alt="Nebula SFTP Logo" width="250px">
</div>

> 💡 **Note:** SFTP access is already **available in NebulaFTP Community** (port `2222`).
> NebulaSFTP is a dedicated product with advanced features for high-performance SFTP workflows.

**Dedicated high-performance SFTP server with advanced security**

#### Planned Features

- 🔑 Public key authentication (Ed25519 / RSA)
- 🚀 Multi-Bot optimised for SFTP
- 📊 Access audit dashboard
- 🔒 Advanced ACLs per user/group

#### Status

📋 **Planned**

---

## 💡 Use Cases

| Scenario | Recommended solution |
|---|---|
| File backup via FTP/SFTP client | **NebulaFTP Community** |
| Mount as drive on Windows/Linux | **NebulaFTP + RaiDrive or rclone** |
| Video/music streaming on LAN | **NebulaStreaming** |
| WebDAV access via Explorer/Finder | **NebulaWebDAV** |
| High-performance SFTP with public key | **NebulaSFTP** |
| Multi-Bot (> 10 MB/s) | **NebulaFTP Pro** |

---

## 💬 Support

| Channel | Details |
|---|---|
| 🐛 Bugs / Issues | [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues) |
| 💬 Questions | [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions) |
| 💼 Pro / Commercial | samuel@inglescurso.com.br |

---

## 📜 License

Community version: [MIT](../LICENSE).

---

[← Back to README](../README-en.md)