<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_cloud.png" alt="Logo Nebula Cloud" width="300px">

**Transforme o Telegram em sua infraestrutura de armazenamento ilimitada**

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)

</div>

---

## 📖 Índice

- [Visão Geral](#-visão-geral)
- [Produtos do Ecossistema](#-produtos-do-ecossistema)
  - [NebulaFTP](#-nebulaftp)
  - [NebulaStreaming](#-nebulastreaming)
  - [NebulaWebDAV](#-nebulawebdav)
  - [NebulaSFTP](#-nebulasftp)
- [Comparativo de Versões](#-comparativo-de-versões)
- [Casos de Uso](#-casos-de-uso)
- [Suporte](#-suporte)
- [Licença](#-licença)

---

## 🌟 Visão Geral

O **Nebula Ecosystem** é uma suíte integrada de soluções que usa o armazenamento ilimitado do Telegram
como backend para protocolos de transferência de arquivos e streaming de mídia.

### Por que Nebula?

✅ **Armazenamento Ilimitado** — aproveite o espaço sem limites do Telegram  
✅ **Multi-Protocolo** — FTP, SFTP, WebDAV e Streaming Web  
✅ **Alta Performance** — Multi-Bot para velocidades de até 60 MB/s *(Pro)*  
✅ **Custo Zero** — versões Community gratuitas disponíveis  
✅ **Auto-Hospedado** — controle total sobre seus dados  

---

## 📦 Produtos do Ecossistema

---

### 🚀 NebulaFTP

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="250px">
</div>

**Servidor FTP + SFTP com Telegram — este repositório**

Transforme qualquer cliente FTP/SFTP (FileZilla, WinSCP, RaiDrive, rclone…) em uma interface
para o armazenamento ilimitado do Telegram.

#### Comparativo Community vs Pro

<table>
<thead>
<tr><th>Recurso</th><th>Community (Grátis)</th><th>Pro (Pago) 💎</th></tr>
</thead>
<tbody>
<tr><td><strong>Protocolo FTP</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Protocolo SFTP (built-in)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Painel Web de Usuários</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Multi-usuários + Permissões</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Bank SQLite (padrão)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Banco MongoDB (opcional)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Rclone / RaiDrive (FTP ou SFTP)</strong></td><td>✅</td><td>✅</td></tr>
<tr><td><strong>Número de Bots</strong></td><td>1 (até ~10 MB/s)</td><td>4–8 (até 60 MB/s)</td></tr>
<tr><td><strong>Multi-Bot (Round Robin)</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Canal de Backup Automático</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Backup Automático do Banco</strong></td><td>❌</td><td>✅</td></tr>
<tr><td><strong>Suporte Técnico</strong></td><td>Comunidade</td><td>Prioritário</td></tr>
</tbody>
</table>

#### Repositório

📂 **GitHub**: [samucamg/NebulaFTP](https://github.com/samucamg/NebulaFTP)

#### Características

- ✅ Funciona **independentemente** dos outros produtos do ecossistema
- ✅ SFTP e painel web **incluídos** na versão Community
- ✅ Ideal para acesso remoto de arquivos via FTP/SFTP e montagem como disco (rclone, RaiDrive)

---

### 🎬 NebulaStreaming

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_stream.png" alt="Logo Nebula Streaming" width="250px">
</div>

**Servidor de streaming e gerenciamento de mídia via Web**

Interface web moderna para upload, organização e **streaming de arquivos de mídia** armazenados no Telegram.

#### Recursos Principais

- 🌐 **Interface Web Completa** — upload, gerenciador de arquivos, player de streaming integrado
- 🎥 **Compatível com Media Centers** — Emby, Jellyfin, Kodi, Plex (geração de `.strm`)
- ⚡ **Multi-Bot / Multi-Canal** — até 60 MB/s com redundância
- 🔄 **Backup Automático** do banco e sincronização entre canais

#### Status

🚧 **Em desenvolvimento**

---

### 🗂️ NebulaWebDAV

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_webdav.png" alt="Logo Nebula WebDAV" width="250px">
</div>

**Servidor WebDAV nativo integrado ao Telegram**

Acesse seus arquivos via protocolo WebDAV — compatível com Windows Explorer ("Mapear unidade"),
macOS Finder, Kodi, Plex e qualquer cliente WebDAV.

#### Recursos Principais

- 🖥️ Acesso nativo no Windows (sem software adicional)
- 🍎 Compatível com macOS Finder
- 🎬 Integração com Kodi e Plex
- ⚡ Multi-Bot para alta velocidade

#### Status

🚧 **Em desenvolvimento**

---

### 🔒 NebulaSFTP

<div align="center">
<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_sftp.png" alt="Logo Nebula SFTP" width="250px">
</div>

> 💡 **Nota:** o acesso SFTP já está **disponível no NebulaFTP Community** (porta `2222`).
> O NebulaSFTP é um produto dedicado com recursos avançados para fluxos SFTP de alta performance.

**Servidor SFTP dedicado, de alta performance e segurança avançada**

#### Recursos Planejados

- 🔑 Autenticação por chave pública (Ed25519 / RSA)
- 🚀 Multi-Bot otimizado para SFTP
- 📊 Dashboard de auditoria de acessos
- 🔒 ACLs avançadas por usuário/grupo

#### Status

📋 **Planejado**

---

## 💡 Casos de Uso

| Cenário | Solução recomendada |
|---|---|
| Backup de arquivos via FTP/SFTP client | **NebulaFTP Community** |
| Montar como disco no Windows/Linux | **NebulaFTP + RaiDrive ou rclone** |
| Streaming de vídeo/música na LAN | **NebulaStreaming** |
| Acesso WebDAV pelo Explorer/Finder | **NebulaWebDAV** |
| SFTP de alta performance com chave pública | **NebulaSFTP** |
| Multi-Bot (> 10 MB/s) | **NebulaFTP Pro** |

---

## 💬 Suporte

| Canal | Detalhe |
|---|---|
| 🐛 Bugs / Issues | [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues) |
| 💬 Dúvidas | [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions) |
| 💼 Versão Pro / Comercial | samuel@inglescurso.com.br |

---

## 📜 Licença

Versão Community: [MIT](../LICENSE).

---

[← Voltar ao README](../README.md)