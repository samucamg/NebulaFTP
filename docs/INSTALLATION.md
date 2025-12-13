# 💾 Instalação - Python Manual

Guia completo para instalar o Nebula FTP usando Python diretamente (sem Docker).

---

## 📋 Requisitos

### Sistema Operacional
- ✅ Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+)
- ✅ Windows 10/11 (com WSL2 ou nativo)
- ✅ macOS 12+

### Software
- **Python 3.10+** (obrigatório)
- **MongoDB 5.0+** (local ou MongoDB Atlas)
- **Git** (para clonar o repositório)

---

## 🐧 Linux (Ubuntu/Debian)

### 1. Instalar Dependências

Atualizar sistema

 ```
sudo apt update && sudo apt upgrade -y
 ```
Instalar Python 3.10+ e ferramentas

 ```
sudo apt install -y python3 python3-pip python3-venv git

 ```
Verificar versão
 ```
python3 --version # Deve ser >= 3.10
 ```

### 2. Instalar MongoDB (Local)

**Opção A: MongoDB Local**

Importar chave GPG
 ```
wget -qO - https://www.mongodb.org/static/pgp/server-6.0.asc | sudo apt-key add -
 ```
Adicionar repositório
 ```
echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/6.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-6.0.list
 ```
Instalar
 ```
sudo apt update
sudo apt install -y mongodb-org
 ```
Iniciar e habilitar
 ```
sudo systemctl enable --now mongod
 ```
Verificar
 ```
sudo systemctl status mongod
 ```


**Opção B: MongoDB Atlas (Cloud - Recomendado)**

Pule a instalação local e use o Atlas:
1. Crie conta em https://cloud.mongodb.com
2. Crie um cluster gratuito (M0)
3. Copie a connection string

### 3. Clonar Repositório
Escolha um local
 ```
cd /opt 
 ```
Clone
 ```
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
 ```

### 4. Criar Ambiente Virtual

Criar venv
 ```
python3 -m venv venv
 ```
Ativar
 ```
source venv/bin/activate
 ```
Seu prompt mudará para: (venv) user@host:...$

### 5. Instalar Dependências Python

```
pip install --upgrade pip
pip install -r requirements.txt
```


### 6. Configurar .env

Copiar exemplo
```
cp .env.example .env
```
Editar (use nano ou vim)
```
nano .env
```


Preencha os valores conforme o [Guia Telegram](TELEGRAM_SETUP.md).

### 7. Configurar MongoDB

```
python setup_database.py
```


### 8. Criar Usuário FTP
```
python accounts_manager.py
```


Exemplo:
Username: samuel
Password: minhasenha123
Home path (default /samuel): [ENTER]


### 9. Iniciar Servidor
```
python main.py
```


Você verá:
2025-12-13 00:00:00,000 - INFO - 🤖 Inicializando 2 bots...
2025-12-13 00:00:01,000 - INFO - ✅ Canal Principal Confirmado: Nebula FTP (ID: -1001234567890)
2025-12-13 00:00:02,000 - INFO - 🚀 Nebula FTP v2.3 Rodando na porta 2121


✅ **Servidor Online!**

---

## 🪟 Windows (Nativo)

### 1. Instalar Python

1. Baixe Python 3.11 de https://python.org
2. ⚠️ **IMPORTANTE:** Marque **"Add Python to PATH"**
3. Instale

### 2. Instalar MongoDB

**Opção A: MongoDB Compass (GUI)**
- Baixe de https://www.mongodb.com/try/download/compass
- Instale e inicie

**Opção B: MongoDB Atlas (Cloud - Recomendado)**
- Mais fácil que instalar local no Windows

### 3. Instalar Git

Baixe de https://git-scm.com/download/win

### 4. Clonar Repositório

Abra **PowerShell** ou **CMD**:

```
cd C:
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```


### 5. Criar Ambiente Virtual
```
python -m venv venv
venv\Scripts\activate
```

### 6. Instalar Dependências
```
pip install -r requirements.txt
```


### 7. Configurar .env

Copie `.env.example` para `.env` e edite no Notepad.

### 8. Configurar MongoDB

```
python setup_database.py
```


### 9. Criar Usuário
```
python accounts_manager.py
```


### 10. Iniciar

```
python main.py
```


---

## 🍎 macOS

### 1. Instalar Homebrew

Se não tiver:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```


### 2. Instalar Dependências

```
brew install python@3.11 mongodb-community git
brew services start mongodb-community
```


### 3. Seguir Passos do Linux

A partir do passo 3 do guia Linux, os comandos são idênticos.

---

## 🚀 Executar como Serviço (Linux)

### Criar Systemd Service

```
sudo nano /etc/systemd/system/nebulaftp.service
```


Cole:

```
[Unit]
Description=Nebula FTP Server
After=network.target mongod.service

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

Ativar:
```
sudo systemctl enable --now nebulaftp
```

Ver logs
```
sudo journalctl -u nebulaftp -f
```


---

## 🔧 Configuração Avançada

### Alterar Porta FTP

Em `.env`:
PORT=2121 # Mude para qualquer porta > 1024


### Adicionar Mais Bots

Crie novos bots e adicione ao `.env` separados por vírgula:

BOT_TOKENS=bot1:token,bot2:token,bot3:token


### Aumentar Performance

MAX_WORKERS=8 # Mais workers = mais uploads simultâneos
CHUNK_SIZE_MB=128 # Chunks maiores = menos partes por arquivo


---

## ❓ Solução de Problemas

### "ModuleNotFoundError: No module named 'pyrogram'"

**Solução:**
```
source venv/bin/activate # Ative o venv primeiro!
pip install -r requirements.txt
```


### "Connection refused" ao conectar no FTP

**Causas possíveis:**
1. Servidor não está rodando
2. Firewall bloqueando porta 2121
3. Porta já em uso

**Solução:**
Verificar se porta está em uso

sudo netstat -tulpn | grep 2121
Liberar no firewall

sudo ufw allow 2121/tcp


### "Peer id invalid" nos logs

Veja [Guia Telegram](TELEGRAM_SETUP.md#problemas-comuns)

---

## 📚 Próximos Passos

✅ Servidor instalado!

Agora:
1. **[Conectar com cliente FTP](../README.md#conectando)**
2. **[Gerenciar usuários](USER_MANAGEMENT.md)**
3. **[Configurar backup automático](BACKUP.md)**

---

[← Voltar ao README](../README.md)
