<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="300px">

</div>

---

# 🚀 Guia de Instalação: NebulaFTP Community (Docker)

Bem-vindo ao **NebulaFTP Community Edition**! Este guia ensina como colocar o servidor
**FTP + SFTP + Painel Web** no ar em uma VPS Ubuntu 22.04 usando Docker.

> **Pré-requisitos:**
> 1. **API ID e API HASH** → [my.telegram.org](https://my.telegram.org)
> 2. **BOT TOKEN** → crie com [@BotFather](https://t.me/BotFather)
> 3. **CHAT ID** → canal privado com o bot como admin (pegue o ID no [@userinfobot](https://t.me/userinfobot))
>
> 📖 Guia detalhado: [Configurar Telegram](TELEGRAM_SETUP.md)

---

## 🛠️ Passo 1: Instalar Docker

```bash
# Download e instalação do Docker oficial
curl -fsSL https://get.docker.com | sudo sh

# Iniciar e habilitar serviço
sudo systemctl enable --now docker

# (Opcional) Rodar docker sem sudo
sudo usermod -aG docker $USER && newgrp docker
```

---

## 📂 Passo 2: Clonar o Repositório

```bash
cd /opt
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
```

---

## ⚙️ Passo 3: Configurar o .env

```bash
cp .env.example .env
nano .env
```

Preencha as variáveis obrigatórias:

```env
# ============= TELEGRAM =============
API_ID=12345678
API_HASH=abc123def456789abcdef123456789ab
BOT_TOKENS=1234567890:AABBccDDeeFFggHH...
CHAT_ID=-1001234567890

# ============= DATABASE =============
# 'sqlite' (padrão, sem instalação) ou 'mongodb'
DB_TYPE=sqlite
DB_FILE=nebula.db

# ============= SERVIDORES =============
HOST=0.0.0.0
PORT=2121        # FTP
SFTP_PORT=2222   # SFTP/SSH
WEB_PORT=8080    # Painel Web

# Senha de acesso ao painel web (vazio = sem senha)
WEB_ADMIN_PASSWORD=

# ============= PERFORMANCE =============
MAX_WORKERS=4
CHUNK_SIZE_MB=64
MAX_RETRIES=5
MAX_STAGING_AGE=3600
LOG_LEVEL=INFO
```

**Salve** com `Ctrl+O → Enter → Ctrl+X`.

---

## 🗂️ Passo 4: Criar Arquivos de Persistência (1ª vez)

> Os volumes do compose montam **arquivos** — se não existirem, o Docker cria **diretórios** no lugar
> (o que quiebra o SQLite e a sessão). O `entrypoint.sh` corrige isso automaticamente, mas criar
> antes é mais seguro:

```bash
mkdir -p staging
touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session
```

---

## 🏗️ Passo 5: Build e Subida

```bash
# Build da imagem (primeira vez leva 3-5 min)
docker compose build

# Subir em background
docker compose up -d

# Verificar se está rodando
docker ps
```

Saída esperada:

```
CONTAINER ID   IMAGE         STATUS         PORTS
abc123...      nebulaftp     Up 10 seconds
```

*(Rede host: não aparecem portas mapeadas — o container usa as portas da máquina diretamente.)*

---

## 👀 Passo 6: Verificar Logs

```bash
docker compose logs -f nebulaftp
```

Saída esperada:

```
INFO - 🤖 Nebula FTP MonoBot Conectado
INFO - ✅ Canal confirmado: Nebula Storage (ID: -1001234567890)
INFO - 🚀 Servidor FTP rodando na porta 2121
INFO - 🔐 Servidor SFTP rodando na porta 2222
INFO - 🌐 Painel Web rodando na porta 8080
```

**Pressione `Ctrl+C`** para sair dos logs.

---

## 👥 Passo 7: Usuários

### Com SQLite (padrão)

Na **primeira execução** o sistema cria automaticamente o usuário **`admin` / `admin`**.
**Troque a senha imediatamente** pelo painel web!

### Criar e gerenciar usuários — Painel Web

1. Abra `http://IP_DO_SERVIDOR:8080` no navegador.
2. (Se `WEB_ADMIN_PASSWORD` estiver definida, faça login com essa senha.)
3. Crie, altere ou exclua usuários e configure permissões por pasta.

---

## 📡 Passo 8: Conectar

### Via FTP (FileZilla, WinSCP, RaiDrive…)

| Campo | Valor |
|---|---|
| Host | IP do servidor |
| Porta | `2121` |
| Usuário | `admin` (ou o que criou) |
| Senha | sua senha |
| Modo | Passivo / EPSV |

### Via SFTP (WinSCP, FileZilla, sshfs, rclone…)

| Campo | Valor |
|---|---|
| Host | IP do servidor |
| Porta | `2222` |
| Usuário | `admin` |
| Autenticação | Senha |

---

## 🔥 Firewall (Importante!)

```bash
sudo ufw allow 2121/tcp   # FTP
sudo ufw allow 2222/tcp   # SFTP
sudo ufw allow 8080/tcp   # Painel Web
sudo ufw reload
sudo ufw status numbered
```

Para **cloud** (AWS, DigitalOcean, etc.): abra as mesmas portas no Security Group / Firewall
do painel do provedor.

---

## 💡 Comandos Úteis

```bash
# Parar
docker compose down

# Reiniciar
docker compose restart nebulaftp

# Logs em tempo real
docker compose logs -f nebulaftp

# Atualizar o código
docker compose down
git pull
docker compose build
docker compose up -d
```

### Backup do banco SQLite (padrão)

```bash
# Copiar para uma pasta de backup local
cp /opt/NebulaFTP/nebula.db /opt/NebulaFTP/backups/nebula-$(date +%Y%m%d).db
```

### Se usar MongoDB (DB_TYPE=mongodb)

```bash
# Backup
docker exec -it <container_mongo> mongodump --db ftp --out /backup
docker cp <container_mongo>:/backup ./backup-$(date +%Y%m%d)

# Restaurar
docker cp ./backup-20260903 <container_mongo>:/backup
docker exec -it <container_mongo> mongorestore --db ftp /backup/ftp
```

### Espaço em disco

```bash
docker system df -v
df -h
```

---

## ❓ Problemas Comuns

### `Connection refused` ao conectar no FTP/SFTP

```bash
docker ps                         # ver se o container está rodando
docker compose logs nebulaftp     # checar erros
telnet IP_DO_SERVIDOR 2121        # testar porta FTP
sudo ufw status                   # verificar firewall
```

### `Peer id invalid` nos logs

O bot não é administrador do canal. Adicione-o como admin com **todas as permissões** no Telegram.

### Container reinicia constantemente

```bash
docker compose logs nebulaftp
# Causas comuns:
# ❌ API_ID / API_HASH inválidos
# ❌ BOT_TOKEN inválido
# ❌ CHAT_ID errado
# ❌ Bot sem permissões no canal
```

### `nebula.db` é um diretório (bind mount defeituoso)

O `entrypoint.sh` corrige automaticamente ao subir (remove o dir vazio e cria o arquivo).
Se for não-vazio, faça manualmente:

```bash
docker compose down
rm -rf /opt/NebulaFTP/nebula.db   # se estiver vazio
touch /opt/NebulaFTP/nebula.db
docker compose up -d
```

### Porta já em uso

Mude `PORT`/`SFTP_PORT`/`WEB_PORT` no `.env` e reinicie.

---

## 🚀 Próximos Passos

- ⭐ [GitHub](https://github.com/samucamg/NebulaFTP) — dê uma estrela!
- 💎 [Versão Pro](ECOSYSTEM.md) — Multi-Bot (4–8 bots, até 60 MB/s), canal de backup, suporte prioritário
- 🐛 [Reportar bugs](https://github.com/samucamg/NebulaFTP/issues)
- 💬 [Discussões](https://github.com/samucamg/NebulaFTP/discussions)

---

## 🆘 Suporte

| Canal | Detalhe |
|---|---|
| 🐛 Bugs / Features | [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues) |
| 💬 Dúvidas gerais | [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions) |
| 💼 Suporte pago | samuel@inglescurso.com.br |

> ⚠️ Suporte gratuito **apenas** pelos canais da comunidade acima (não por e-mail/WhatsApp).

---

<div align="center">

**Feito com ❤️ por [Samuel de Sousa Santos](https://github.com/samucamg)**

[⬅️ Voltar ao README](../README.md) • [🌌 Ecossistema Nebula](ECOSYSTEM.md)

</div>