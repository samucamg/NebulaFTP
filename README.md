<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="300px">

### **Transforme o Telegram em seu Armazenamento Ilimitado via FTP/SFTP**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](https://github.com/samucamg/NebulaFTP/pulls)

**Servidor FTP + SFTP** com painel web de administração, usando o **Telegram como backend de armazenamento**.

</div>

---

## 📌 O que é o Nebula FTP?

O **Nebula FTP** transforma qualquer canal do Telegram em um "disco" acessível por protocolos padrão de arquivo.
Você continua usando seus clientes de sempre (FileZilla, WinSCP, RaiDrive, rclone, WinSCP/SFTP...) e o sistema
cuida de **fragmentar, enviar e indexar** cada arquivo no Telegram.

### ✨ Funcionalidades atuais

- **📡 Servidor FTP** — porta `2121` (padrão), servidor assíncrono próprio com suporte a PASV/EPSV,
  listagem, upload, download, renomear, mover, excluir, criar pastas e **retomada de download (REST)**.
- **🔐 Servidor SFTP (SSH)** — porta `2222` (padrão), com os **mesmos usuários e permissões do FTP**
  (chave de host gerada automaticamente em `sftp_host_key`).
- **🖥️ Painel Web de administração** — porta `8080` (padrão): crie usuários, altere senhas e
  gerencie **permissões por pasta** (leitura/escrita) sem tocar no banco.
- **⚡ Upload Turbo (Staging)** — o upload cai primeiro no **disco local (instantâneo)** e vai para o
  Telegram em **background**, sem timeouts no cliente.
- **☁️ Download/Streaming por partes** — o arquivo é remontado a partir das partes (`part_NNN`)
  já enviadas ao Telegram, mesmo que não exista mais cópia local. A leitura por offset (seek) via SFTP permite assistir mídia sem baixar o arquivo inteiro.
- **🗄️ SQLite (padrão) ou MongoDB** — escolha pelo `.env` (`DB_TYPE`). Sem necessidade de instalar MongoDB
  para começar.
- **🛡️ Robusto** — retry com backoff (FloodWait/RPC), garbage collector do staging, logs rotativos,
  métricas e graceful shutdown.
- **👥 Multi-usuário** — home próprio por usuário (`/<login>`) e permissões por caminho.
- **🤖 Multi-Bot** — distribui carga entre vários bots. **Apenas na versão Pro 💎**
  (na Community, o primeiro token de `BOT_TOKENS` é utilizado).

> 💎 **Community vs Pro:** esta é a versão **Community (open source)** — 1 bot e até ~10 MB/s.
> A versão **Pro** traz Multi-Bot (4–8 bots, até 60 MB/s), canal de backup automático e suporte prioritário.
> Veja a tabela completa no [ECOSYSTEM.md](docs/ECOSYSTEM.md).

---

## 🏗️ Arquitetura

```
┌─────────────────────────────┐   ┌──────────────────────────┐   ┌──────────────────┐
│  Cliente FTP (FileZilla,    │   │  Cliente SFTP (WinSCP,   │   │  Painel Web      │
│  RaiDrive, rclone...)       │   │  sshfs, rclone...)       │   │  (porta 8080)    │
└──────────────┬──────────────┘   └────────────┬─────────────┘   └────────┬─────────┘
               │                               │                          │
               └───────────────┬───────────────┘──────────────────────────┘
                               ▼
              ┌───────────────────────────────────┐
              │      NEBULA FTP SERVER            │
              │  ┌─────────────────────────────┐  │
              │  │ Folder Watcher (staging)    │  │
              │  │ Upload Workers (fila)       │  │
              │  │ PathIO (monta/desmonta)     │  │
              │  │ Garbage Collector           │  │
              │  │ Permissões por usuário      │  │
              │  └─────────────────────────────┘  │
              └──────┬──────────────────┬─────────┘
                     ▼                  ▼
         ┌──────────────────┐  ┌──────────────────┐
         │ SQLite (padrão)  │  │    Telegram      │
         │ ou MongoDB       │  │ (canal: partes   │
         │ (metadados)      │  │  UUID.part_NNN)  │
         └──────────────────┘  └──────────────────┘
```

**Fluxo de upload (Upload Turbo):** cliente FTP envia → arquivo gravado em `staging/` (instantâneo) →
`folder_watcher` detecta e enfileira → workers fragmentam em chunks (`CHUNK_SIZE_MB`) e enviam ao canal →
metadados (partes) são salvos no banco → cópia local é removida.

**Fluxo de download:** o servidor lê os metadados das partes e **baixa do Telegram sob demanda**,
entregando o arquivo ao cliente FTP/SFTP — não é preciso manter cópia local.

---

## 📁 Requisitos

- 🐍 **Python 3.10+** (instalação nativa) ou 🐳 **Docker** (Linux/VPS recomendado).
- 📱 **Telegram**: API ID/Hash ([my.telegram.org](https://my.telegram.org)), um **bot** ([@BotFather](https://t.me/BotFather)) e um **canal** com o bot como administrador.
  [📖 Guia completo do Telegram →](docs/TELEGRAM_SETUP.md)
- 🗄️ *(Opcional)* **MongoDB** local/Atlas — somente se quiser usar `DB_TYPE=mongodb`.
  No padrão **SQLite** nada precisa ser instalado.

---

## 🚀 Instalação

### Opção 1 — Docker (recomendado para Linux/VPS) 🐳

```bash
# 1) Acesse o servidor e clone o repositório
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP

# 2) Configure o .env (API_ID, API_HASH, BOT_TOKENS, CHAT_ID...)
cp .env.example .env
nano .env

# 3) Crie os arquivos de persistência (apenas na 1ª vez)
mkdir -p staging
touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session

# 4) Suba
docker compose up -d

# 5) Acompanhe os logs
docker compose logs -f nebulaftp
```

> O `docker-compose.yml` usa **rede host** (funciona de forma transparente com FTP passivo em VPS).
> Em **Windows/macOS com Docker Desktop** (sem suporte a rede host) prefira a **Opção 3 — Python nativo**.

### Opção 2 — Portainer 🐳

1. Clone o repositório no host: `git clone https://github.com/samucamg/NebulaFTP.git` (ex.: `/opt/NebulaFTP`).
2. Crie o arquivo `.env` (`cp .env.example .env` e edite).
3. Crie os arquivos de persistência (1ª vez):
   `mkdir -p staging && touch nebula.db nebula.log sftp_host_key Nebula_MonoBot.session`
4. Construa a imagem uma vez: `docker compose build` (ou `docker build -t nebulaftp .`).
5. No **Portainer**: `Stacks → Add stack → Web editor` → cole o conteúdo do arquivo
   [**`portainer-stack.yml`**](portainer-stack.yml) → ajuste os caminhos dos volumes
   (padrão: `/opt/NebulaFTP`) → preencha as variáveis de ambiente → **Deploy the stack**.

### Opção 3 — Python direto 🐍

```bash
# 1) Clone e prepare o ambiente
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2) Dependências
pip install -r requirements.txt

# 3) Configure — use o assistente interativo (recomendado)
python setup.py
# ...ou manualmente:
cp .env.example .env && nano .env

# 4) Rode
python main.py
```

**📖 Guias detalhados:** [Instalação Python](docs/INSTALLATION.md) · [Docker](docs/DOCKER.md)

---

## 🔐 Primeiro acesso e usuários

- Com o backend **SQLite** (padrão), o sistema cria automaticamente o usuário
  **`admin` / `admin`** na primeira execução. **⚠️ Troque a senha** pelo painel web!
- Com o backend **MongoDB**, não há usuário padrão: crie o primeiro pelo painel web.
- Abra o **painel web** em `http://IP_DO_SERVIDOR:8080` e gerencie os usuários:
  - Criar usuário, alterar senha, excluir;
  - Adicionar permissões por pasta (`readable` / `writable`);
  - Cada usuário tem acesso total ao próprio home `/<login>` — pastas fora dele só com permissão explícita.
- Opcionalmente proteja o painel definindo `WEB_ADMIN_PASSWORD` no `.env` (Basic Auth).

---

## ⚙️ Configuração (.env)

| Variável | Padrão | Descrição |
|---|---|---|
| `API_ID` / `API_HASH` | — | Credenciais de [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKENS` | — | Token(s) do(s) bot(s), separados por vírgula *(Community usa o 1º; Multi-Bot = Pro 💎)* |
| `CHAT_ID` | — | ID do canal onde os arquivos são salvos (formato `-100...`) |
| `DB_TYPE` | `sqlite` | Banco de metadados: `sqlite` ou `mongodb` |
| `DB_FILE` | `nebula.db` | Arquivo do SQLite (quando `DB_TYPE=sqlite`) |
| `MONGODB` | — | URI do MongoDB (quando `DB_TYPE=mongodb`) |
| `HOST` | `0.0.0.0` | Interface do servidor (veja dica de PASV abaixo) |
| `PORT` | `2121` | Porta do **FTP** |
| `SFTP_PORT` | `2222` | Porta do **SFTP/SSH** |
| `WEB_PORT` | `8080` | Porta do **painel web** |
| `WEB_ADMIN_PASSWORD` | *(vazio)* | Senha para proteger o painel web (opcional) |
| `MAX_WORKERS` | `4` | Uploads simultâneos (workers) |
| `CHUNK_SIZE_MB` | `64` | Tamanho de cada parte enviada ao Telegram |
| `MAX_RETRIES` | `5` | Tentativas por parte em caso de erro |
| `MAX_STAGING_AGE` | `3600` | Idade máxima (s) de arquivos órfãos em `staging/` antes do GC apagar |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> 💡 **Dica PASV/EPSV:** com `HOST=0.0.0.0` clientes que usam **EPSV** funcionam normalmente.
> Se o cliente insistir em **PASV** e vier de outra máquina, defina `HOST` com o IP (LAN ou público)
> da interface do servidor para que o endereço anunciado seja alcançável.

Modelo completo com comentários: [`.env.example`](.env.example).

---

## 📁 Montando como unidade de disco / WebDAV (rclone e RaiDrive)

O Nebula FTP é um servidor FTP/SFTP padrão — portanto pode ser montado como **unidade de rede**
por ferramentas comuns. Dois jeitos fáceis:

| Objetivo | Ferramenta |
|---|---|
| Windows — unidade com letra (Z:, Y:...) | **RaiDrive** (protocolo FTP) |
| Linux — pasta montada ou WebDAV para outros apps | **rclone** (mount + `serve webdav`) |
| Windows/Linux — alternativa via linha de comando | **rclone** |

> Use as credenciais de um usuário criado no painel web. No padrão SQLite, o usuário inicial é
> `admin/admin` (troque a senha depois!). A pasta inicial do usuário é `/<login>`.

### 🪟 Windows — RaiDrive (recomendado)

1. Baixe e instale o [RaiDrive](https://www.raidrive.com/) (versão gratuita suporta FTP).
2. Abra o RaiDrive → **Add** → escolha o grupo **FTP** → **FTP**.
3. Preencha:
   - **Address:** `IP_DO_SERVIDOR`
   - **Port:** `2121`
   - **Username / Password:** usuário criado no painel web (ex.: `admin`)
4. Em **Drive**, escolha a letra (ex.: `Z:`) → **Connect**.
5. Pronto: o "disco" aparece no **Windows Explorer** com seus arquivos do Telegram.

> Se o Explorer travar em listagens/downloads, verifique no Firewall do Windows as portas
> `2121` (e `2222`/`8080` se for usar SFTP/painel) e prefira conexão local/VPN.

### 🐧 Linux — rclone (mount e WebDAV)

Instale o rclone e o FUSE:

```bash
sudo apt update && sudo apt install -y rclone fuse3
```

Configure o remote (resposta interativa):

```bash
rclone config
# n) Novo remote
# name> nebula
# type> ftp
# host> IP_DO_SERVIDOR
# user> admin
# pass> SUA_SENHA
# port> 2121
```

Ou edite manualmente `~/.config/rclone/rclone.conf`:

```ini
[nebula]
type = ftp
host = IP_DO_SERVIDOR
user = admin
pass = COLOQUE_AQUI_O_OUTPUT_DE:  rclone obscure "SUA_SENHA"
port = 2121
```

Teste e monte como pasta:

```bash
rclone lsd nebula:              # lista as pastas
mkdir -p ~/NebulaFTP
rclone mount nebula: ~/NebulaFTP --vfs-cache-mode writes &
# para desmontar: fusermount -u ~/NebulaFTP
```

**Transformar em WebDAV** (para Windows "Mapear unidade de rede", Kodi, Jellyfin, etc.):

```bash
rclone serve webdav nebula: --addr :8082 --user admin --pass SUA_SENHA
# Endpoint WebDAV: http://IP_DO_SERVIDOR:8082
```

### 🐧 Linux — rclone via SFTP (recomendado para streaming)

O servidor SFTP do Nebula (porta `2222`) suporta **leitura por partes (seek)** — para
**reproduzir vídeos** direto do "disco"/WebDAV, prefira o remote por SFTP:

```ini
[nebula-sftp]
type = sftp
host = IP_DO_SERVIDOR
user = admin
pass = COLOQUE_AQUI_O_OUTPUT_DE:  rclone obscure "SUA_SENHA"
port = 2222
```

```bash
rclone lsd nebula-sftp:              # testa a conexão
mkdir -p ~/NebulaFTP
rclone mount nebula-sftp: ~/NebulaFTP --vfs-cache-mode writes &

# Expor como WebDAV (Kodi, Plex, Windows "Mapear unidade"):
rclone serve webdav nebula-sftp: --addr :8082 --user admin --pass SUA_SENHA
```

### 🪟 Windows — rclone (alternativa)

```powershell
winget install Rclone.Rclone
rclone config                       # mesmo remote "nebula" (type = ftp)
rclone mount nebula: N: --vfs-cache-mode writes
# ou exponha WebDAV na rede local:
rclone serve webdav nebula: --addr :8082 --user admin --pass SUA_SENHA
```

### ⚠️ Notas sobre montagem FTP

- **Uploads**: são instantâneos (staging local) e finalizam em background no Telegram. ✅
- **Downloads**: completos funcionam bem. Para **assistir vídeos grandes direto do "disco"**
  (seek constante), o FTP mount não é o ideal — prefira o remote via SFTP acima ou os produtos de streaming
  do ecossistema (Nebula Stream).
- RaiDrive e rclone fazem listagem/cache — dar uma olhada nas configurações de cache ajuda em pastas grandes.

---

## 🌌 Ecossistema Nebula

O **Nebula FTP** faz parte de um ecossistema maior:

| Projeto | Descrição | Status |
|---------|-----------|--------|
| **[NebulaFTP](docs/ECOSYSTEM.md#-nebulaftp)** | Servidor FTP + SFTP com Telegram (**este repositório**) | ✅ **Disponível** |
| **[NebulaStream](docs/ECOSYSTEM.md#-nebulastreaming)** | Interface Web + Player de streaming | 🚧 Em desenvolvimento |
| **[NebulaWebDAV](docs/ECOSYSTEM.md#%EF%B8%8F-nebulawebdav)** | Servidor WebDAV para Kodi/Plex | 🚧 Em desenvolvimento |
| **[NebulaSFTP](docs/ECOSYSTEM.md#-nebulasftp)** | Produto SFTP dedicado (o acesso SFTP já existe no NebulaFTP) | 📋 Planejado |

> 💎 **Multi-Bot, canal de backup e velocidades até 60 MB/s são recursos exclusivos da versão Pro.**
> A Community usa 1 bot. [Saiba mais sobre o Ecossistema →](docs/ECOSYSTEM.md)

---

## 🐳 Docker — detalhes

- **`docker-compose.yml`** — deploy padrão com `docker compose` (rede host; persiste `staging/`,
  `nebula.db`, logs, sessão do bot e chave SFTP em volumes).
- **`portainer-stack.yml`** — mesma stack pronta para colar no **Portainer** (Stacks → Web editor).

**Portas padrão expostas na máquina:** `2121` (FTP) · `2222` (SFTP) · `8080` (painel web).

**Persistência importante (não esqueça):** o `nebula.db` (metadados) e o `Nebula_MonoBot.session`
(sessão do bot) precisam estar em volumes — o compose já faz isso. Se rodar manualmente
(`docker run`), monte essas pastas/arquivos para não perder os dados ao recriar o container.

**Auto-correção (entrypoint):** a imagem traz um `entrypoint.sh` que garante que `nebula.db`,
`nebula.log`, `sftp_host_key` e `Nebula_MonoBot.session` existam como **arquivos** dentro do
container — se você esquecer o passo de criação no host e o Docker criar um diretório vazio no
lugar do bind mount, o entrypoint corrige automaticamente na subida. (Arquivos vazios são válidos:
o SQLite e o Pyrogram os inicializam na primeira execução.)

**Backend MongoDB no Docker:** se usar `DB_TYPE=mongodb`, aponte `MONGODB` para um MongoDB
acessível (ex.: MongoDB Atlas ou um container Mongo separado).

---

## ❓ Solução de problemas (rápida)

| Problema | Causa provável / solução |
|---|---|
| `Connection refused` | Servidor parado, porta errada ou firewall. Libere `2121` (e `2222`, `8080`). |
| Trava em listar/baixar | Modo passivo: use EPSV no cliente ou defina `HOST` com o IP da máquina (dica acima). |
| `Peer id invalid` nos logs | O bot não é admin do canal — adicione como administrador. |
| Esqueci a senha do `admin` | No SQLite, pare o serviço, apague o `nebula.db` (ou o usuário na tabela `users`) e reinicie — o `admin/admin` é recriado. |
| Container recriado perdeu arquivos | `nebula.db`/sessão não estavam em volume — veja a seção Docker. |

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
