[🇧🇷 Português](#) | [🇺🇸 English](INSTALLATION-en.md)

# 💾 Instalação — Python Manual

Guia completo para instalar o Nebula FTP diretamente com Python (sem Docker).

---

## 📋 Requisitos

| Item | Detalhe |
|---|---|
| **OS** | Linux (Ubuntu 20.04+), Windows 10/11, macOS 12+ |
| **Python** | 3.10 ou superior (obrigatório) |
| **Git** | Para clonar o repositório |
| **MongoDB** | *(Opcional)* — somente se usar `DB_TYPE=mongodb`. O padrão é **SQLite** (sem instalação). |

---

## 🐧 Linux (Ubuntu/Debian)

### 1. Instalar Dependências

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv git

# Verificar
python3 --version   # deve ser >= 3.10
```

### 2. Clonar Repositório

```bash
cd /opt
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

### 3. Criar Ambiente Virtual

```bash
python3 -m venv venv
source venv/bin/activate
# Prompt muda para: (venv) user@host:...$
```

### 4. Instalar Dependências Python

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configurar o .env

**Opção A — Assistente interativo (recomendado):**

```bash
python setup.py
```

O assistente pergunta: API_ID, API_HASH, BOT_TOKENS, CHAT_ID, portas FTP/SFTP/Web e senha do painel;
depois gera o `.env` automaticamente.

**Opção B — Manual:**

```bash
cp .env.example .env
nano .env
```

Preencha ao menos `API_ID`, `API_HASH`, `BOT_TOKENS` e `CHAT_ID`.
Consulte o [Guia Telegram](TELEGRAM_SETUP.md) para obter esses valores.

### 6. (Opcional) MongoDB como banco

Se preferir usar MongoDB em vez do SQLite padrão, instale e configure:

```bash
# Ubuntu — MongoDB (opcional)
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
sudo apt update && sudo apt install -y mongodb-org
sudo systemctl enable --now mongod
```

No `.env`:

```env
DB_TYPE=mongodb
MONGODB=mongodb://localhost:27017
```

Ou use **MongoDB Atlas (cloud)** e aponte `MONGODB` para a connection string.

### 7. Iniciar o Servidor

```bash
# Com venv ativado:
python main.py
```

Saída esperada:

```
INFO - 🤖 Nebula FTP MonoBot Conectado
INFO - ✅ Canal confirmado: Nebula Storage (ID: -1001234567890)
INFO - 🚀 Servidor FTP rodando na porta 2121
INFO - 🔐 Servidor SFTP rodando na porta 2222
INFO - 🌐 Painel Web rodando na porta 8080
```

### 8. Criar e Gerenciar Usuários

Abra `http://localhost:8080` no navegador. Com SQLite, o usuário padrão é **`admin` / `admin`** —
troque a senha imediatamente.

---

## 🪟 Windows (Nativo)

### 1. Instalar Python

1. Baixe Python 3.11+ de https://python.org
2. ⚠️ Marque **"Add Python to PATH"** durante a instalação

### 2. Instalar Git

Baixe de https://git-scm.com/download/win

### 3. Clonar Repositório

Abra **PowerShell**:

```powershell
cd C:\
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

### 4. Criar Ambiente Virtual

```powershell
python -m venv venv
venv\Scripts\activate
```

### 5. Instalar Dependências

```powershell
pip install -r requirements.txt
```

### 6. Configurar e Iniciar

```powershell
# Assistente interativo (recomendado)
python setup.py

# Depois iniciar:
python main.py
```

Acesse o painel em `http://localhost:8080`.

---

## 🍎 macOS

```bash
# Instalar Homebrew (se não tiver):
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Dependências
brew install python@3.11 git

# Seguir a partir do passo 2 do guia Linux
```

---

## 🚀 Executar como Serviço (Linux — systemd)

```bash
sudo nano /etc/systemd/system/nebulaftp.service
```

Cole:

```ini
[Unit]
Description=Nebula FTP Server
After=network.target

[Service]
Type=simple
User=seu_usuario
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
sudo journalctl -u nebulaftp -f   # acompanhar logs
```

---

## 🔧 Configuração Avançada

### Portas

Em `.env` ajuste conforme necessário:

```env
PORT=2121           # FTP
SFTP_PORT=2222      # SFTP
WEB_PORT=8080       # Painel Web
```

### Proteção do Painel Web

```env
WEB_ADMIN_PASSWORD=suasenhasecreta
```

### Multi-Bot — Apenas versão Pro 💎

```env
BOT_TOKENS=bot1_token,bot2_token,bot3_token
```

Na Community, apenas o primeiro token é utilizado.

### Performance

```env
MAX_WORKERS=8      # uploads simultâneos
CHUNK_SIZE_MB=64   # tamanho dos chunks (máx Telegram: 2 GB)
```

---

## ❓ Solução de Problemas

### `ModuleNotFoundError: No module named 'pyrogram'`

```bash
source venv/bin/activate   # ative o venv!
pip install -r requirements.txt
```

### `Connection refused` ao conectar no FTP

1. Verifique se `python main.py` está rodando
2. Verifique o firewall: `sudo ufw allow 2121/tcp`
3. Confirme a porta no `.env`: `PORT=2121`

### `Peer id invalid` nos logs

Veja [Configuring Telegram](TELEGRAM_SETUP.md#problemas-comuns)

---

## 📚 Próximos Passos

✅ Servidor instalado!

- [Conectar como disco / WebDAV (rclone e RaiDrive)](../README.md#-montando-como-unidade-de-disco--webdav-rclone-e-raidrive)
- [Documentação Docker](DOCKER.md)
- [Ecossistema Nebula](ECOSYSTEM.md)

---

[← Voltar ao README](../README.md)