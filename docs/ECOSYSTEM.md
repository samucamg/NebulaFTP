<div align="center">

# <img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_cloud.png" alt="Logo Nebula FTP" width="300px">

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
- [Arquitetura e Integração](#-arquitetura-e-integração)
- [Casos de Uso](#-casos-de-uso)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Suporte](#-suporte)
- [Roadmap](#-roadmap)
- [Licença](#-licença)

---

## 🌟 Visão Geral

O **Nebula Ecosystem** é uma suíte integrada de soluções que utiliza o armazenamento ilimitado do Telegram como backend para protocolos de transferência de arquivos e streaming de mídia. 

### Por que Nebula?

✅ **Armazenamento Ilimitado**: Aproveite o espaço sem limites do Telegram  
✅ **Multi-Protocolo**: FTP, WebDAV, SFTP e Streaming Web  
✅ **Alta Performance**: Multi-bot para velocidades de até 60 MB/s  
✅ **Redundância Integrada**: Canais de backup automáticos  
✅ **Custo Zero**: Versões Community gratuitas disponíveis  
✅ **Auto-Hospedado**: Controle total sobre seus dados  

---

## 📦 Produtos do Ecossistema

### 🚀 NebulaFTP

**Servidor FTP integrado ao Telegram**

Transforme qualquer cliente FTP (FileZilla, WinSCP, etc.) em uma interface para o armazenamento ilimitado do Telegram.

#### Versões Disponíveis

<table>
<thead>
<tr>
<th>Recurso</th>
<th>Community (Grátis)</th>
<th>Pro (Pago)</th>
</tr>
</thead>
<tbody>
<tr>
<td><strong>Protocolo FTP</strong></td>
<td>✅</td>
<td>✅</td>
</tr>
<tr>
<td><strong>Multi-usuários</strong></td>
<td>✅</td>
<td>✅</td>
</tr>
<tr>
<td><strong>MongoDB</strong></td>
<td>✅</td>
<td>✅</td>
</tr>
<tr>
<td><strong>Número de Bots</strong></td>
<td>1 (até 10 MB/s)</td>
<td>4-8 (até 60 MB/s)</td>
</tr>
<tr>
<td><strong>Canal de Backup</strong></td>
<td>❌</td>
<td>✅ Automático</td>
</tr>
<tr>
<td><strong>Backup MongoDB</strong></td>
<td>❌</td>
<td>✅ Automático</td>
</tr>
<tr>
<td><strong>Suporte Rclone</strong></td>
<td>❌</td>
<td>✅</td>
</tr>
<tr>
<td><strong>Deploy</strong></td>
<td>Docker / Python</td>
<td>Docker / Python</td>
</tr>
<tr>
<td><strong>Suporte Técnico</strong></td>
<td>Comunidade</td>
<td>Prioritário</td>
</tr>
</tbody>
</table>

#### Repositório

📂 **GitHub**: [samucamg/NebulaFTP](https://github.com/samucamg/NebulaFTP)

#### Características Stand-Alone

- ✅ Funciona **independentemente** dos outros produtos
- ✅ Banco de dados **isolado**
- ✅ Ideal para quem precisa **apenas FTP**

---

### 🎬 NebulaStreaming

**Servidor de streaming e gerenciamento de mídia via Web**

Interface web moderna para upload, organização e streaming de arquivos de mídia armazenados no Telegram.

#### Recursos Principais

- 🌐 **Interface Web Completa**
  - Upload de arquivos e pastas
  - Gerenciador de arquivos (mover, renomear, excluir)
  - Player de streaming integrado

- 🎥 **Compatibilidade com Media Centers**
  - Geração automática de arquivos `.strm`
  - Compatível com **Emby**, **Jellyfin**, **Kodi** e **Plex**
  - Organização por pastas

- ⚡ **Performance**
  - Multi-bot (4-8 bots simultâneos)
  - Multi-canal (distribuição de carga)
  - Canal de backup redundante
  - Velocidade de até 60 MB/s

- 🔄 **Backup Automático**
  - Rotina automática de backup do MongoDB
  - Sincronização entre canais

#### Integração com Banco de Dados

**Compartilha banco MongoDB com:**
- NebulaWebDAV
- NebulaSFTP

> 📁 **Exemplo**: Um arquivo enviado via WebDAV aparece automaticamente na interface web do Streaming e vice-versa.

#### Status

🚧 **Em Desenvolvimento** (Lançamento previsto: Q1 2026)

---

### 🗂️ NebulaWebDAV

**Servidor WebDAV integrado ao Telegram**

Monte o armazenamento do Telegram como uma unidade de rede no Windows, macOS ou Linux.

#### Recursos Principais

- 🔗 **Mapeamento de Rede**
  - Windows Explorer (Map Network Drive)
  - macOS Finder (Connect to Server)
  - Linux (via davfs2)

- ⚡ **Performance**
  - Multi-bot (4-8 bots simultâneos)
  - Multi-canal (distribuição de carga)
  - Canal de backup redundante

- 🗄️ **Banco de Dados Compartilhado**
  - Integrado com NebulaStreaming
  - Integrado com NebulaSFTP
  - MongoDB como backend

#### Casos de Uso

- 💼 Sincronização de arquivos corporativos
- 📂 Backup automático via software de terceiros
- 🎬 Bibliotecas de mídia para Plex/Jellyfin

#### Status

🚧 **Em Desenvolvimento** (Lançamento previsto: Q2 2026)

---

### 🔐 NebulaSFTP

**Servidor SFTP integrado ao Telegram**

Acesso seguro via protocolo SFTP (SSH File Transfer Protocol) ao armazenamento do Telegram.

#### Recursos Principais

- 🔒 **Segurança**
  - Autenticação por chave SSH
  - Criptografia de ponta a ponta
  - Suporte a chroot (isolamento de usuários)

- ⚡ **Performance**
  - Multi-bot (4-8 bots simultâneos)
  - Multi-canal (distribuição de carga)
  - Canal de backup redundante

- 🗄️ **Banco de Dados Compartilhado**
  - Integrado com NebulaStreaming
  - Integrado com NebulaWebDAV
  - MongoDB como backend

#### Casos de Uso

- 🖥️ Administração remota de servidores
- 🤖 Scripts automatizados (rsync, scp)
- 🔐 Transferências seguras e auditáveis

#### Status

🚧 **Em Desenvolvimento** (Lançamento previsto: Q2 2026)

---

## 📊 Comparativo de Versões

### NebulaFTP: Community vs Pro

| Categoria | Community | Pro |
|-----------|-----------|-----|
| **Velocidade** | Até 10 MB/s | Até 60 MB/s |
| **Bots** | 1 bot | 4-8 bots |
| **Redundância** | ❌ | ✅ Canal backup |
| **Rclone** | ❌ | ✅ |
| **Backup MongoDB** | Manual | Automático |
| **Suporte** | GitHub Issues | Email + Prioridade |
| **Preço** | **Grátis** | Sob consulta |

### NebulaStreaming / WebDAV / SFTP

> ⚠️ **Atenção**: Estes produtos **não possuem versão Community**.  
> Todos incluem multi-bot, multi-canal e backup automático por padrão.

---

## 🏗️ Arquitetura e Integração

### Arquitetura Stand-Alone (NebulaFTP)

```
┌─────────────────┐
│  Cliente FTP    │
│  (FileZilla)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐       ┌──────────────┐
│   NebulaFTP     │◄─────►│  MongoDB     │
│   (Community)   │       │  (Isolado)   │
└────────┬────────┘       └──────────────┘
         │
         ▼
┌─────────────────┐
│   Telegram      │
│   (1 Bot)       │
└─────────────────┘
```

### Arquitetura Integrada (Streaming + WebDAV + SFTP)

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Browser  │  │ Windows  │  │ SSH      │  │  Plex    │
│   Web    │  │ Explorer │  │ Client   │  │ Jellyfin │
└─────┬────┘  └─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │             │             │
      ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────┐
│           NEBULA ECOSYSTEM (PRO)                    │
├──────────────┬──────────────┬─────────────┬─────────┤
│  Streaming   │   WebDAV     │    SFTP     │  Rclone │
└──────┬───────┴──────┬───────┴──────┬──────┴─────────┘
       │              │              │
       └──────────────┼──────────────┘
                      ▼
              ┌──────────────┐
              │  MongoDB     │
              │ (Compartilhado)│
              └──────┬───────┘
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ Bot 1     │ │ Bot 2-4   │ │ Bot 5-8   │
│ (Principal)│ │ (Workers) │ │ (Backup)  │
└─────┬─────┘ └─────┬─────┘ └─────┬─────┘
      │             │             │
      └─────────────┼─────────────┘
                    ▼
            ┌───────────────┐
            │   Telegram    │
            │ Canal Principal│
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │   Telegram    │
            │ Canal Backup  │
            └───────────────┘
```

### Fluxo de Integração

**Exemplo de uso integrado:**

1. 📤 **Upload via WebDAV** (Windows Explorer)
   - Arquivo salvo no MongoDB
   - Enviado ao Telegram via multi-bot

2. 🔍 **Visualização via Streaming** (Web)
   - Consulta no MongoDB compartilhado
   - Exibe arquivo sem re-upload

3. 🎬 **Streaming para Jellyfin**
   - Gera arquivo `.strm` automático
   - Jellyfin lê metadados do MongoDB
   - Stream direto do Telegram

4. 🔐 **Download via SFTP** (Terminal)
   - Mesmo arquivo, acesso via SSH
   - Mesma fonte de dados (MongoDB)

> 💡 **Vantagem**: Um único upload serve para **todos os protocolos**.

---

## 💼 Casos de Uso

### Para Uso Pessoal

- 🎥 **Biblioteca de Mídia Pessoal**
  - Jellyfin/Plex com backend do Telegram
  - Streaming de filmes/séries de qualquer lugar

- 📁 **Backup de Arquivos**
  - Sincronização automática via WebDAV
  - Backup infinito sem custo

- 🎓 **Armazenamento de Cursos**
  - Organização por pastas
  - Acesso via web ou FTP

### Para Empresas/Freelancers

- 💼 **Colaboração em Projetos**
  - Compartilhamento via SFTP
  - Controle de acesso por usuário

- 🎬 **Produção de Vídeo**
  - Upload de material bruto via FTP
  - Streaming para revisão via web
  - Backup redundante automático

- 📊 **Arquivamento de Dados**
  - Compliance com retenção de longo prazo
  - Custo zero de armazenamento

### Para Desenvolvedores

- 🤖 **CI/CD Artifacts**
  - Armazenamento de builds via Rclone
  - Download via SFTP em pipelines

- 📦 **Repositório de Pacotes**
  - Distribuição de releases
  - Mirror via WebDAV

---

## 🛠️ Requisitos

### NebulaFTP Community

- 🐧 **Sistema Operacional**: Ubuntu 22.04+ / Debian 11+ / Windows (via Docker)
- 🐍 **Python**: 3.10+ (se instalação local)
- 🐳 **Docker**: 20.10+ (se instalação via Docker)
- 🗄️ **MongoDB**: 4.4+ (local ou cloud)
- 📡 **Telegram**:
  - API ID e API Hash ([my.telegram.org](https://my.telegram.org))
  - Bot Token (via [@BotFather](https://t.me/BotFather))
  - Canal privado com bot como admin

### NebulaFTP Pro / Streaming / WebDAV / SFTP

- ✅ Mesmos requisitos da versão Community
- ➕ **4-8 Bot Tokens** adicionais
- ➕ **Canal de Backup** no Telegram
- ➕ **VPS com 2+ CPU cores** (recomendado para multi-bot)

---

## 🚀 Instalação

### NebulaFTP Community

#### Via Docker (Recomendado)

```bash
# Clonar repositório
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP

# Configurar credenciais
cp .env.example .env
nano .env  # Editar com seus dados

# Iniciar
docker compose up -d
```

#### Via Python

```bash
# Clonar repositório
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar
cp .env.example .env
nano .env

# Criar usuário FTP
python accounts_manager.py

# Iniciar
python main.py
```

📖 **Documentação completa**: [INSTALLATION.md](https://github.com/samucamg/NebulaFTP/blob/master/docs/INSTALLATION.md)

### NebulaFTP Pro / Outros Produtos

📧 **Contato para aquisição**: samuel@inglescurso.com.br

---

## 🆘 Suporte

### Comunidade (Gratuito)

- 💬 **GitHub Issues**: [Reportar bugs](https://github.com/samucamg/NebulaFTP/issues)
- 💡 **GitHub Discussions**: [Perguntas e ideias](https://github.com/samucamg/NebulaFTP/discussions)
- 📚 **Documentação**: [Guias e tutoriais](https://github.com/samucamg/NebulaFTP/tree/master/docs)

### Profissional (Pago)

| Serviço | Investimento |
|---------|--------------|
| Instalação VPS Linux | R$ 150,00 |
| Instalação Windows | R$ 250,00 |
| Consultoria Técnica (1h) | R$ 200,00 |
| Upgrade Community → Pro | Sob consulta |
| Migração de dados | Sob consulta |

📧 **Email**: samuel@inglescurso.com.br  
⏰ **Agendamento**: Apenas com pagamento antecipado via PIX

> ⚠️ **Importante**: Suporte gratuito não é fornecido por email/WhatsApp.

---

## 🗺️ Roadmap

### ✅ Concluído

- [x] NebulaFTP Community (Open Source)
- [x] NebulaFTP Pro (Privado)
- [x] Documentação NebulaFTP
- [x] Docker support
- [x] Multi-usuários
- [x] Obfuscação de código

### 🚧 Em Desenvolvimento (Q1 2026)

- [ ] NebulaStreaming Web Interface
  - [ ] Upload de arquivos/pastas
  - [ ] Gerenciador de arquivos
  - [ ] Player de streaming
  - [ ] Geração de .strm
- [ ] NebulaWebDAV Beta
- [ ] Dashboard administrativo (todas as versões)

### 📅 Planejado (Q2 2026)

- [ ] NebulaSFTP Release
- [ ] NebulaWebDAV Release Oficial
- [ ] API REST para automação
- [ ] Mobile App (iOS/Android)
- [ ] Suporte a S3 (além do Telegram)

### 💡 Futuro (Q3-Q4 2026)

- [ ] NebulaSync (cliente desktop)
- [ ] Plugin para Jellyfin/Plex
- [ ] Criptografia E2E opcional
- [ ] Multi-tenant (SaaS)

---

## 📄 Licença

### NebulaFTP Community

**MIT License** - Código open source disponível no GitHub.

### NebulaFTP Pro / Streaming / WebDAV / SFTP

**Licença Proprietária** - Código fechado, uso mediante licenciamento.

---

## 🌟 Contribua

Gostou do projeto? Você pode ajudar:

- ⭐ **Dê uma estrela** no [GitHub](https://github.com/samucamg/NebulaFTP)
- 🐛 **Reporte bugs** via Issues
- 💡 **Sugira melhorias** via Discussions
- 📖 **Melhore a documentação** via Pull Request
- 💰 **Adquira a versão Pro** e apoie o desenvolvimento

---

## 👨‍💻 Autor

**Samuel de Sousa Santos**

- 🐙 GitHub: [@samucamg](https://github.com/samucamg)
- 📧 Email: samuel@inglescurso.com.br
- 🌐 Website: [inglescurso.com.br](https://inglescurso.com.br)

---

## 📊 Estatísticas

<div align="center">

![GitHub stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/samucamg/NebulaFTP?style=social)

</div>

---

<div align="center">

**Feito com ❤️ no Brasil** 🇧🇷

</div>
