<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="300px">

### **Transforme o Telegram em seu Armazenamento Ilimitado via SFTP e Web**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/testes-79%20passando-brightgreen.svg)](tests)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/samucamg/NebulaFTP/pulls)

[🇧🇷 Português](#) | [🇺🇸 English](README-en.md)

**Servidor SFTP** com **painel web** (gerenciador de arquivos + player), usando o **Telegram como backend de armazenamento**.

</div>

---

## 📌 O que é o Nebula FTP?

O **Nebula FTP** transforma qualquer canal do Telegram em um "disco" acessível por **SFTP** e pelo **navegador**.
Você continua usando seus clientes de sempre (FileZilla, WinSCP, RaiDrive, rclone...) e o sistema
cuida de **fragmentar, enviar e indexar** cada arquivo no Telegram.

> 🆕 **Versão 2 (Community):** reescrita do zero, com núcleo único, testes automáticos e foco em
> **SFTP + Web**. O protocolo FTP foi removido: o SFTP é mais seguro (criptografado), atravessa
> firewall/NAT com uma porta só e é suportado pelos mesmos clientes.

### ✨ Funcionalidades

- **🔐 Servidor SFTP (SSH)** — porta `2222` (padrão): listar, enviar, baixar, renomear, mover, excluir
  e criar pastas. Compatível com **FileZilla, WinSCP, RaiDrive e rclone**. Chave de host gerada automaticamente.
- **🖥️ Painel Web** — porta `8082` (padrão):
  - 📂 Gerenciador de arquivos: upload (inclusive arquivos de vários GB), download, renomear, excluir, criar pastas;
  - 🎬 **Player** de vídeo e áudio no navegador (mp4, webm, mp3, m4a, ogg, opus, wav), com avanço/retrocesso;
  - 👥 Administração de usuários (somente o admin).
- **👥 Multi-usuário isolado** — cada usuário tem a **própria pasta** e só enxerga ela. Só o **admin** vê a raiz.
- **⚡ Upload Turbo (Staging)** — o upload cai primeiro no **disco local (instantâneo)** e vai para o
  Telegram em **background**, sem timeouts no cliente. Uploads pendentes **continuam após reiniciar**.
- **☁️ Leitura sob demanda** — o arquivo é remontado a partir das partes no Telegram, mesmo sem cópia local.
  Só os trechos pedidos são baixados (Range/seek), então dá para **assistir mídia sem baixar o arquivo inteiro**.
- **♻️ Sem lixo no canal** — sobrescrever ou apagar um arquivo remove também as partes antigas do Telegram.
- **🗄️ SQLite** — um único arquivo, nada para instalar. *(MongoDB opcional: 🚧 planejado)*
- **🛡️ Robusto e seguro** — senhas com hash **scrypt**, proteção **CSRF**, bloqueio após 5 senhas erradas,
  retry com backoff (FloodWait), verificação do relógio na partida, logs sem segredos.
- **🧪 Testado** — 79 testes automáticos com Telegram simulado, conferindo o **sha256** de ida e volta.

> 💾 **Espaço ilimitado:** o Telegram não impõe limite de espaço. Na Community o limite real é a
> **velocidade**: um único bot envia uma parte de cada vez (até ~10 MB/s).

> 💎 **Community vs Pro:** esta é a versão **Community (open source)** — 1 bot.
> A versão **Pro** traz Multi-Bot (4–8 bots, até 60 MB/s), canal de backup automático e suporte prioritário.
> Veja a tabela completa no [ECOSYSTEM.md](docs/ECOSYSTEM.md).

---

## 🏗️ Arquitetura

```
┌──────────────────────────────┐          ┌──────────────────────────┐
│  Cliente SFTP (FileZilla,    │          │  Navegador               │
│  WinSCP, RaiDrive, rclone)   │          │  (painel web :8082)      │
└──────────────┬───────────────┘          └────────────┬─────────────┘
               │ :2222                                 │
               └──────────────────┬────────────────────┘
                                  ▼
              ┌───────────────────────────────────────┐
              │         NEBULA FTP (núcleo)           │
              │  ┌─────────────────────────────────┐  │
              │  │ NebulaVFS: pastas, usuários,    │  │
              │  │ permissões, versões, travas     │  │
              │  │ Staging local (upload turbo)    │  │
              │  │ Upload Worker (1 bot)           │  │
              │  │ Cache de partes + limpeza (GC)  │  │
              │  └─────────────────────────────────┘  │
              └──────┬─────────────────────┬──────────┘
                     ▼                     ▼
         ┌──────────────────┐   ┌──────────────────────┐
         │ SQLite           │   │      Telegram        │
         │ (metadados)      │   │ (canal: partes       │
         │                  │   │  nome.part001...)    │
         └──────────────────┘   └──────────────────────┘
```

**Fluxo de upload:** cliente envia → arquivo gravado em `data/staging` (instantâneo) →
o worker corta em partes (`CHUNK_SIZE_MB`) e envia ao canal → as partes são registradas no banco →
a cópia local é removida.

**Fluxo de download:** o servidor lê o mapa de partes e **baixa do Telegram só o trecho pedido**,
guardando num cache local temporário.

---

## 📁 Requisitos

- 🐍 **Python 3.10+** (Windows ou Linux) ou 🐳 **Docker** (Linux/VPS recomendado).
- 📱 **Telegram**: API ID/Hash ([my.telegram.org](https://my.telegram.org)), um **bot** ([@BotFather](https://t.me/BotFather)) e um **canal** com o bot como administrador.
  [📖 Guia completo do Telegram →](docs/TELEGRAM_SETUP.md)
- 💽 Espaço em disco para staging e cache (pelo menos o tamanho do maior arquivo que você vai enviar).
- 🕒 **Relógio do servidor certo** — o Telegram recusa conexões com mais de 30 s de diferença (o programa avisa na partida).

---

## 🚀 Instalação

### Opção 1 — Docker (recomendado para Linux/VPS) 🐳

```bash
# 1) Clone o repositório
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP

# 2) Configure o .env (API_ID, API_HASH, BOT_TOKENS, CHAT_ID, WEB_ADMIN_PASSWORD...)
cp .env.example .env
nano .env

# 3) Suba
docker compose up -d --build

# 4) Acompanhe os logs
docker compose logs -f nebulaftp
```

> Tudo que precisa persistir (banco, staging, cache, chave SFTP e sessão do bot) fica em `./data`.

### Opção 2 — Python direto 🐍

```bash
# 1) Clone e prepare o ambiente
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2) Dependências
pip install -r requirements.txt

# 3) Configure
cp .env.example .env             # Windows: copy .env.example .env
nano .env

# 4) Rode
python main.py
```

### 🐧 Rodando como serviço (systemd)

```ini
# /etc/systemd/system/nebulaftp.service
[Unit]
Description=NebulaFTP Community
After=network-online.target

[Service]
WorkingDirectory=/opt/NebulaFTP
ExecStart=/opt/NebulaFTP/.venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload && sudo systemctl enable --now nebulaftp
journalctl -u nebulaftp -f
```

---

## 🔐 Primeiro acesso e usuários

- O usuário **admin** é criado na primeira execução com o login `WEB_ADMIN_USER` (padrão `admin`)
  e a senha `WEB_ADMIN_PASSWORD` do `.env` (**obrigatória**, não existe senha padrão).
- Abra o **painel web** em `http://IP_DO_SERVIDOR:8082` e entre com o admin.
- Em **Usuários**: crie, altere senha ou exclua. Cada usuário ganha a pasta `/<login>`
  e, ao conectar, **enxerga só ela** como raiz.
- O mesmo login e senha valem para o **SFTP** (porta `2222`).
- ⛔ Após 5 senhas erradas, o login fica bloqueado por 60 segundos.

---

## ⚙️ Configuração (.env)

| Variável | Padrão | Descrição |
|---|---|---|
| `API_ID` / `API_HASH` | — | Credenciais de [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKENS` | — | Token do bot *(Community usa 1 bot; Multi-Bot = Pro 💎)* |
| `CHAT_ID` | — | ID do canal onde os arquivos são salvos (formato `-100...`) |
| `WEB_ADMIN_USER` | `admin` | Login do administrador |
| `WEB_ADMIN_PASSWORD` | — | Senha do administrador (obrigatória na 1ª execução) |
| `HOST` | `0.0.0.0` | Interface de escuta |
| `SFTP_PORT` | `2222` | Porta do **SFTP** |
| `WEB_PORT` | `8082` | Porta do **painel web** |
| `DATA_DIR` | `data` | Staging, cache e sessão do bot |
| `DB_FILE` | `nebula.db` | Arquivo do banco SQLite |
| `SFTP_HOST_KEY` | `sftp_host_key` | Chave de host do SFTP (criada automaticamente) |
| `CHUNK_SIZE_MB` | `100` | Tamanho de cada parte enviada ao Telegram |
| `MAX_STAGING_AGE` | `3600` | Segundos até limpar arquivos órfãos do staging |
| `CACHE_MAX_AGE` | `3600` | Segundos até limpar partes sem uso do cache |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

Modelo completo com comentários: [`.env.example`](.env.example).

---

## 📁 Montando como unidade de disco (RaiDrive e rclone)

O Nebula FTP é um servidor SFTP padrão — pode ser montado como **unidade de rede**:

| Objetivo | Ferramenta |
|---|---|
| Windows — unidade com letra (Z:, Y:...) | **RaiDrive** (SFTP) |
| Linux — pasta montada ou WebDAV para outros apps | **rclone** (mount + `serve webdav`) |
| Windows/Linux — linha de comando | **rclone** |

### 🪟 Windows — RaiDrive (recomendado)

1. Baixe e instale o [RaiDrive](https://www.raidrive.com/).
2. Abra o RaiDrive → **Add** → grupo **NAS** → **SFTP**.
3. Preencha:
   - **Address:** `IP_DO_SERVIDOR`
   - **Port:** `2222`
   - **Username / Password:** usuário criado no painel web
4. Escolha a letra (ex.: `Z:`) → **Connect**.
5. Pronto: o "disco" aparece no **Windows Explorer** com seus arquivos do Telegram. ✅

> Também funciona com **FileZilla** e **WinSCP**: protocolo **SFTP**, porta `2222`.

### 🐧 Linux — rclone (mount e WebDAV)

```bash
sudo apt update && sudo apt install -y rclone fuse3
```

Edite `~/.config/rclone/rclone.conf`:

```ini
[nebula]
type = sftp
host = IP_DO_SERVIDOR
user = SEU_USUARIO
pass = COLOQUE_AQUI_O_OUTPUT_DE:  rclone obscure "SUA_SENHA"
port = 2222
```

Teste e monte como pasta:

```bash
rclone lsd nebula:                   # testa a conexão
mkdir -p ~/NebulaFTP
rclone mount nebula: ~/NebulaFTP --vfs-cache-mode writes &
# para desmontar: fusermount -u ~/NebulaFTP
```

**Transformar em WebDAV** (Windows "Mapear unidade de rede", Kodi, Jellyfin...):

```bash
rclone serve webdav nebula: --addr :8090 --user SEU_USUARIO --pass SUA_SENHA
# Endpoint WebDAV: http://IP_DO_SERVIDOR:8090
```

### 🪟 Windows — rclone (alternativa)

```powershell
winget install Rclone.Rclone
rclone config                       # mesmo remote "nebula" (type = sftp, port 2222)
rclone mount nebula: N: --vfs-cache-mode writes
```

### ⚠️ Notas sobre montagem

- **Uploads**: instantâneos (staging local) e finalizam em background no Telegram. ✅
- **Vídeos**: o SFTP lê por trechos (seek), então dá para reproduzir sem baixar tudo.
  O primeiro acesso a cada parte depende da velocidade de download do Telegram.
- RaiDrive e rclone fazem cache de listagem — ajuste o cache em pastas muito grandes.

---

## 🌌 Ecossistema Nebula

| Projeto | Descrição | Status |
|---------|-----------|--------|
| **[NebulaFTP](docs/ECOSYSTEM.md#-nebulaftp)** | Servidor SFTP + painel web com Telegram (**este repositório**) | ✅ **Disponível** |
| **[NebulaStream](docs/ECOSYSTEM.md#-nebulastreaming)** | Interface Web + Player de streaming | 🚧 Em desenvolvimento |
| **[NebulaWebDAV](docs/ECOSYSTEM.md#%EF%B8%8F-nebulawebdav)** | Servidor WebDAV para Kodi/Plex | 🚧 Em desenvolvimento |
| **[NebulaSFTP](docs/ECOSYSTEM.md#-nebulasftp)** | Produto SFTP dedicado de alta performance | 📋 Planejado |

> 💎 **Multi-Bot, canal de backup e velocidades até 60 MB/s são recursos exclusivos da versão Pro.**
> [Saiba mais sobre o Ecossistema →](docs/ECOSYSTEM.md)

---

## 🔒 Segurança

- 🔑 Senhas com hash **scrypt**; formulários com proteção **CSRF**.
- 🌐 O painel web usa HTTP. Na internet, coloque-o atrás de um proxy com **HTTPS** (Caddy, Nginx).
- 💾 **Faça backup do banco** (`DB_FILE`): sem ele não é possível remontar os arquivos a partir do canal.
- ☁️ A Community não tem canal de backup: guarde cópias do que for importante.

---

## ❓ Solução de problemas (rápida)

| Problema | Causa provável / solução |
|---|---|
| `Connection refused` | Servidor parado, porta errada ou firewall. Libere `2222` e `8082`. |
| Erro de relógio / `msg_id too low` na partida | Relógio do servidor errado. Ative o NTP (`timedatectl set-ntp true`). |
| `Peer id invalid` nos logs | O bot não é admin do canal — adicione como administrador. |
| Esqueci a senha do admin | Defina no `.env` um **novo** `WEB_ADMIN_USER` com `WEB_ADMIN_PASSWORD` e reinicie: um novo admin é criado. Entre com ele e troque a senha do antigo pelo painel. |
| Upload com erro genérico no cliente | Veja o `nebula.log`: erros inesperados do SFTP são registrados com detalhes. |
| Container recriado perdeu arquivos | A pasta `./data` não estava em volume — veja a seção Docker. |

---

## 🧪 Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

A suíte usa um Telegram simulado e compara o **sha256** de ida e volta pelo núcleo, SFTP e web.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma [issue](https://github.com/samucamg/NebulaFTP/issues) ou um
[pull request](https://github.com/samucamg/NebulaFTP/pulls) — e ⭐ dê uma estrela no projeto!

---

## 📜 Licença

Este projeto está sob a licença **MIT**. Veja [LICENSE](LICENSE) para detalhes.

---

## 💬 Suporte

- 🐛 **Bugs e sugestões:** [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues)
- 💡 **Discussões:** [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions)
- 💎 **Versão Pro / assuntos comerciais:** samuel@inglescurso.com.br *(apenas comercial — sem suporte gratuito por e-mail)*

---

## 📊 Estatísticas

![GitHub Stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub Forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub Issues](https://img.shields.io/github/issues/samucamg/NebulaFTP)

---

<div align="center">

**Feito com ❤️ por [Samuel de Sousa Santos](https://github.com/samucamg)**

</div>
