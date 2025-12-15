<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="300px">

### **Transforme o Telegram em seu Armazenamento Ilimitado**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[🇧🇷 Português](#) | [🇺🇸 English](README-en.md)

[📖 Documentação](#-documentação) • [🚀 Início Rápido](#-início-rápido) • [🎥 Vídeo](#-vídeo-tutorial) • [💬 Suporte](#-suporte)

</div>

---

## 🎯 O que é o Nebula FTP?

**Nebula FTP** é um servidor FTP profissional que usa o **Telegram como backend de armazenamento**, oferecendo:

- ✨ **Armazenamento Ilimitado** - Sem limites de espaço (apenas do Telegram)
- ⚡ **Velocidade Real** - 10+ MB/s com MTProto (sem API HTTP lenta) **(Velocidade Máxima com Multi-Bot)**
- 🔐 **Privacidade Total** - Arquivos ofuscados com UUID (modo Stealth)
- ~~🎬 **Streaming Inteligente**~~ - Assista vídeos 4K sem baixar tudo **(Apenas no Nebula Stream)**
- 🤖 **Multi-Bot** - Distribui carga entre vários bots automaticamente, aumentando a performance. **(Apenas na Versão Pro)**
- 👥 **Multi-Usuário** - Sistema completo de permissões por pasta. 
- 🐳 **Docker Ready** - Instalação em 1 comando
- 🛡️ **Production-Grade** - Retry logic, logs, métricas e graceful shutdown

---

## 📊 Demonstração

### Upload Turbo (Staging Local)
Cliente FTP envia → Disco local (instantâneo) → Telegram (background)

✅ Sem timeouts  
✅ Sem travamentos  
✅ Compatível com RaiDrive/Windows Explorer  **(Não funciona para streaming)**

### Screenshots

<details>
<summary>📸 Clique para ver capturas de tela</summary>

![FileZilla conectado](docs/images/screenshot_filezilla.png)
*FileZilla transferindo 15GB de filmes*

![RaiDrive montado](docs/images/screenshot_raidrive.png)
*Drive Z: montado no Windows Explorer*

</details>

---

## 🎥 Vídeo Tutorial

> 🎬 **Em breve:** Tutorial completo de instalação e configuração

[![Nebula FTP Tutorial](https://img.youtube.com/vi/VIDEO_ID/0.jpg)](https://youtube.com/watch?v=VIDEO_ID)

---

## 🚀 Início Rápido

### Opção 1: Docker (Recomendado) 🐳

1. Aceder ao seu Servidor via SSH
 ```
ssh seu_usuario@IP_DO_SERVIDOR
```
2. Atualizar o Servidor
```
sudo apt update && sudo apt upgrade -y
```
3. Instalar as Ferramentas Essenciais

```
sudo apt install git python3 python3-venv python3-pip ffmpeg -y
```

4. Clone o repositório
 ```
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
 ```
5. Configure o .env
 ```
cp .env.example .env
nano .env # Preencha seus dados
 ```
6. Inicie!
```
docker-compose up -d
```
7. Veja os logs
```
docker-compose logs -f nebulaftp
```

**📖 [Guia Completo Docker →](docs/DOCKER.md)**

---

### Opção 2: Python Direto 🐍

1. Clone e prepare ambiente
 ```
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python3 -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
 ```
2. Instale dependências
 ```
pip install -r requirements.txt
 ```
3. Configure
 ```
cp .env.example .env
nano .env
 ```
4. Rode
 ```
python main.py
 ```

**📖 [Guia Instalação Completa →](docs/INSTALLATION.md)**

---

## 📖 Documentação

### 🎓 Para Iniciantes

1. **[📱 Configurar Telegram](docs/TELEGRAM_SETUP.md)**
   - Obter API ID e API Hash
   - Criar bots com @BotFather
   - Criar canais e adicionar bots como admin

2. **[💾 Instalação Python](docs/INSTALLATION.md)**
   - Windows, Linux, macOS
   - Passo a passo detalhado
   - Solução de problemas

3. **[🐳 Instalação Docker](docs/DOCKER.md)**
   - Docker Desktop (Windows/Mac)
   - Docker Engine (Linux)
   - docker-compose explicado

4. **[👥 Gerenciar Usuários](docs/USER_MANAGEMENT.md)**
   - Criar contas FTP
   - Permissões (leitura/escrita)
   - Limitar acesso por pasta

---

### 🏗️ Ecossistema Nebula

O **Nebula FTP** faz parte de um ecossistema maior:

| Projeto | Descrição | Status |
|---------|-----------|--------|
| **[NebulaFTP](docs/ECOSYSTEM.md#-nebulaftp)** | Servidor FTP com Telegram | ✅ **Você está aqui** |
| **[NebulaStream](docs/ECOSYSTEM.md#-nebulastreaming)** | Interface Web + Player | 🚧 Em desenvolvimento |
| **[NebulaWebDAV](docs/ECOSYSTEM.md#%EF%B8%8F-nebulawebdav)** | Servidor WebDAV para Kodi/Plex | 🚧 Em desenvolvimento |
| **[NebulaSFTP](docs/ECOSYSTEM.md#-nebulasftp)** | Servidor SFTP (SSH) | 📋 Planejado |

**📖 [Saiba mais sobre o Ecossistema →](docs/ECOSYSTEM.md)**

---

## ⚙️ Configuração (.env)

API do Telegram (obtenha em my.telegram.org)
 ```
API_ID=12345678
API_HASH=abc123def456...
Tokens dos Bots (crie com @BotFather)

BOT_TOKENS=1234567890:AABBcc...,9876543210:AAFFdd...
IDs dos Canais (copie de @userinfobot)

CHAT_ID=-1001234567890
BACKUP_CHAT_ID=-1009876543210 # Opcional
MongoDB (local ou Atlas)

MONGODB=mongodb://localhost:27017
Servidor FTP

HOST=0.0.0.0
PORT=2121
Performance

MAX_WORKERS=4 # Workers de upload
CHUNK_SIZE_MB=64 # Tamanho dos chunks
MAX_RETRIES=5 # Tentativas de retry
Logging

LOG_LEVEL=INFO # DEBUG, INFO, WARNING, ERROR

 ```

**📖 [Configuração Avançada →](docs/INSTALLATION.md#configuração-avançada)**

---

## 🎯 Casos de Uso

### 🏠 Uso Pessoal
- Backup automático de fotos/vídeos
- Biblioteca de filmes/séries pessoal
- Sincronização entre dispositivos

### 🏢 Uso Profissional
- Servidor de arquivos para equipe pequena
- Backup de projetos e documentos
- Streaming de conteúdo educacional

### 🎓 Educacional
- Distribuição de materiais didáticos
- Repositório de aulas gravadas
- Compartilhamento de e-books

---

## 🔧 Recursos Técnicos

### Arquitetura

┌─────────────────────────────────────────────┐
│ Cliente FTP (FileZilla) │
└─────────────────┬───────────────────────────┘
│
┌─────────────────▼───────────────────────────┐
│ Nebula FTP Server (Python) │
│ ┌──────────────────────────────────────┐ │
│ │ - Multi-Bot Manager (Round Robin) │ │
│ │ - Smart Seek (Streaming) │ │
│ │ - Retry Logic (5x + Backoff) │ │
│ │ - Garbage Collector (Auto-Clean) │ │
│ └──────────────────────────────────────┘ │
└─────────────────┬───────────────────────────┘
│
┌─────────┴─────────┐
│ │
┌───────▼────────┐ ┌───────▼────────┐
│ MongoDB │ │ Telegram │
│ (Metadados) │ │ (Arquivos) │
└────────────────┘ └────────────────┘


### Tecnologias

- **Python 3.10+** - Linguagem principal
- **Pyrogram** - Cliente MTProto (rápido)
- **pyftpdlib** - Servidor FTP assíncrono
- **Motor** - Driver MongoDB assíncrono
- **aiofiles** - I/O assíncrono de arquivos
- **Docker** - Containerização

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Veja nosso [Guia de Contribuição](CONTRIBUTING.md).

### Como ajudar:
- 🐛 Reportar bugs
- 💡 Sugerir melhorias
- 📝 Melhorar documentação
- 🌍 Traduzir para outros idiomas
- ⭐ Dar uma estrela no projeto!

---

## 📜 Licença

Este projeto está sob a licença MIT. Veja [LICENSE](LICENSE) para detalhes.

---

## 💬 Suporte

### 💬 Comunidade
- **Telegram:** [t.me/NebulaFTP](https://t.me/NebulaFTP)
- **Discord:** [discord.gg/nebula](https://discord.gg/nebula)

### 🐛 Bugs e Sugestões
- **Issues:** [GitHub Issues](https://github.com/samucamg/NebulaFTP/issues)
- **Discussões:** [GitHub Discussions](https://github.com/samucamg/NebulaFTP/discussions)

### 📧 Contato Direto
- **Email:** samuel@inglescurso.com.br  apenas para assuntos comerciais, não dou suporte, não tiro dúvidas.  Atendo apenas comercialmente.

---

## 🌟 Agradecimentos

Agradecimentos especiais a minha esposa e meu filho por aguentarem as longas horas de trabalho e desenvolvimento.

---

## 📊 Estatísticas

![GitHub Stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub Forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub Issues](https://img.shields.io/github/issues/samucamg/NebulaFTP)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/samucamg/NebulaFTP)

---

<div align="center">

**Feito com ❤️ por [Samuel de Sousa Santos](https://github.com/samucamg)**

[⬆ Voltar ao topo](#-nebula-ftp)

</div>


![SamucaFtp bash](https://i.imgur.com/PNNrmwA.jpg)

<details>
<summary><b>Você necessita configurar as variáveis abaixo:</b></summary>

`API_ID`: Acesse [my.telegram.org](https://my.telegram.org) para obter o seu.

`API_HASH`: Acesse [my.telegram.org](https://my.telegram.org) para obter o seu.

`BOT_TOKEN`: Crie um novo bot utilizando [BotFather](https://telegram.dog/botfather).

`MONGODB`: Crie um DB e obtenha o link de conexão em [mongodb.com] (https://www.mongodb.com/)

`CHAT_ID`: Id do Chat para onde serão enviados os arquivos.

`HOST`: Host do FTP deixe como padrão (Padrão: 0.0.0.0).

`PORT`: Porta do servidor FTP (Padrão: 9021).

</details>

<details>
<summary><b>Setup:</b></summary>
Antes de iniciar o setup, verifique se você tem o python3 instalado, ou instale utilizando o comando abaixo:
 ```sudo apt update && sudo apt install python3-pip -y ```
A seguir:

  1. Crie um novo bot em [BotFather](https://telegram.dog/botfather).
  2. Obtenha o API_ID e API_HASH em [my.telegram.org](https://my.telegram.org).
  3. Crie um banco de dados Mongo DB com o nome de ftp [MongoDB Cloud](https://cloud.mongodb.com/) (ou use seu servidor) e copie a string de conexão.
Aprenda aqui, [Como Criar gratuitamente sua base de dados Mongo DB] (https://www.youtube.com/watch?v=6b3YH0kK3ig)
  Caso pretenda utilizar uma quantidade muito grande de arquivos, é preferível criar o seu próprio banco de dados Mongo-db veja o tutorial sobre [Como instalar e Criar sua base de dados Mongo DB no ubuntu 20.04] (https://www.digitalocean.com/community/tutorials/how-to-install-mongodb-on-ubuntu-20-04-pt)
  4. Coloque todas as variáveis em na raiz do bot no arquivo .env
  5. Adicione o bot ao seu canal com direito de administrador.
  6. Execute o arquivo 'python3 get_channel_id.py`, envie o comando `/id` no seu canal para obter o id do canal.
  7. Copie o ID para .env
  8. Execute 'python3 setup_database.py`.
  9. Execute 'python3 accounts_manager.py` para criar sua conta ftp.
  10. Execute `main.py`.

</details>
<summary>Aconselho a utilização de Uma VPS ou windows com wsl2 com <b>Ubuntu 22.04</b></summary>
