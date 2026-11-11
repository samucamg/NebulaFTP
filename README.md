<div align="center">

<img src="https://raw.githubusercontent.com/samucamg/NebulaFTP/refs/heads/master/img/logo_nebula_ftp.png" alt="Logo Nebula FTP" width="300px">

### **Espaço ilimitado para os seus arquivos, usando o Telegram**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Grátis](https://img.shields.io/badge/Pre%C3%A7o-Gr%C3%A1tis-brightgreen.svg)](#)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![Windows | Linux](https://img.shields.io/badge/Windows%20%7C%20Linux-OK-informational.svg)](#)

[🇧🇷 Português](#) | [🇺🇸 English](README-en.md)

**Guarde quantos arquivos quiser, sem pagar por espaço.** Acesse pelo navegador ou como um disco no seu computador.

</div>

---

## 💡 O que você ganha

- ☁️ **Espaço ilimitado** — seus arquivos ficam guardados em um canal privado do Telegram. Sem mensalidade de armazenamento.
- 💽 **Funciona como um disco no seu PC** — aparece no Windows como uma unidade (`Z:`), sem ocupar o seu HD.
- 🌐 **Acesse de qualquer lugar** — entre pelo navegador para enviar, baixar, renomear e organizar.
- 🎬 **Assista e ouça na hora** — vídeos e músicas tocam direto no navegador, sem baixar o arquivo inteiro.
- 👨‍👩‍👧 **Vários usuários** — cada pessoa tem a própria pasta e só vê o que é dela.
- 🛠️ **Você no comando** — crie, edite e remova usuários pelo painel.
- 🔒 **Seguro** — conexão criptografada e senhas protegidas.
- 🆓 **Grátis e de código aberto** — instale em poucos minutos no seu computador ou servidor.

> ℹ️ Esta edição gratuita usa **um robô do Telegram**, então o espaço é ilimitado, mas a velocidade
> de envio tem um teto (cerca de 10 MB/s). Precisa de mais? Veja o [**Nébula Drive**](#-quer-mais-conheça-o-nébula-drive).

---

## 📸 Como é

<table>
<tr>
<td><img src="img/community/arquivos.svg" alt="Seus arquivos"></td>
<td><img src="img/community/player.svg" alt="Player de vídeo"></td>
</tr>
<tr>
<td align="center"><b>Seus arquivos</b> no navegador</td>
<td align="center"><b>Assista</b> sem baixar</td>
</tr>
<tr>
<td><img src="img/community/usuarios.svg" alt="Gerenciar usuários"></td>
<td><img src="img/community/login.svg" alt="Tela de login"></td>
</tr>
<tr>
<td align="center"><b>Gerencie</b> os usuários</td>
<td align="center"><b>Cada um</b> com seu acesso</td>
</tr>
</table>

---

## 🚀 Instale em 3 passos

Você vai precisar de uma conta no Telegram. O [📖 guia do Telegram](docs/TELEGRAM_SETUP.md) mostra como criar o robô e o canal, passo a passo.

```bash
# 1) Baixe
git clone https://github.com/samucamg/NebulaFTP.git && cd NebulaFTP

# 2) Preencha os dados do Telegram e a senha do administrador
cp .env.example .env && nano .env

# 3) Ligue
docker compose up -d --build
```

Pronto! Abra `http://IP_DO_SERVIDOR:8082` no navegador e entre como administrador.

📖 **Instalação sem Docker, Windows, usar como disco `Z:` (RaiDrive) e todas as opções:** [Guia de instalação](docs/INSTALACAO.md)

---

## 💎 Quer mais? Conheça o Nébula Drive

<div align="center">
<img src="img/drive/filmes.svg" alt="Nébula Drive — biblioteca de filmes" width="90%">
</div>

O **Nébula Drive** é a edição completa: junta em um só lugar a sua **nuvem pessoal** (como o Google Drive),
o seu **streaming de filmes e séries** (como a Netflix), um **leitor de livros que lê em voz alta**,
um **player de músicas** e um **Office online** para criar e editar documentos.

| | 🆓 Community | 💎 Nébula Drive |
|---|:---:|:---:|
| Espaço ilimitado no Telegram | ✅ | ✅ |
| Acesso como disco no computador | ✅ | ✅ PC, Mac, celular e TV |
| Vários usuários, cada um com sua pasta | ✅ | ✅ + grupos, cotas e prazo de acesso |
| Assistir vídeos e ouvir músicas no navegador | ✅ básico | ✅ estilo Netflix |
| Velocidade de envio | 1 robô | ⚡ vários robôs, muito mais rápido |
| Compartilhar como no Google Drive (links com senha e validade) | ❌ | ✅ |
| Bibliotecas com capas, sinopses e temporadas | ❌ | ✅ |
| "Continuar assistindo" e "Continuar lendo" | ❌ | ✅ |
| Mini novelas, músicas e vídeo aulas organizadas | ❌ | ✅ |
| Leitor de livros e quadrinhos com voz natural | ❌ | ✅ |
| Criar e editar Word, Excel e PowerPoint online | ❌ | ✅ |
| Importar pastas do Google Drive | ❌ | ✅ |
| Histórico de versões, lixeira e favoritos | ❌ | ✅ |
| Assistente de Inteligência Artificial | ❌ | ✅ |
| Assistir na Smart TV (Jellyfin, Kodi) | ❌ | ✅ |
| Cópia de segurança automática dos arquivos | ❌ | ✅ |
| App para celular e computador, tema escuro | ❌ | ✅ |
| Banco MongoDB (para instalações grandes) | ❌ | ✅ |
| Suporte | Comunidade | Prioritário |

<table>
<tr>
<td><img src="img/drive/serie.svg" alt="Séries"></td>
<td><img src="img/drive/leitor-voz.svg" alt="Leitor com voz"></td>
<td><img src="img/drive/compartilhar.svg" alt="Compartilhar"></td>
</tr>
<tr>
<td align="center">🎬 Séries por temporada</td>
<td align="center">📚 Livros que leem para você</td>
<td align="center">🔗 Compartilhe com quem quiser</td>
</tr>
</table>

👉 **[Veja tudo o que o Nébula Drive faz, com fotos de cada tela](docs/NEBULA-DRIVE.md)**

📩 **Quer o Nébula Drive?** Fale comigo: samuel@inglescurso.com.br

---

## ❓ Perguntas rápidas

**É de graça mesmo?** Sim. O NebulaFTP Community é grátis e de código aberto (licença MIT).

**O espaço é ilimitado de verdade?** O Telegram não cobra nem limita o espaço. O limite desta edição é a velocidade de envio.

**Meus arquivos ficam públicos?** Não. Eles ficam em um canal **privado**, que só o seu robô acessa.

**Preciso deixar o computador ligado?** O sistema precisa ficar ligado para você acessar os arquivos. O ideal é instalar em um servidor (VPS).

**Posso perder meus arquivos?** Guarde uma cópia do arquivo do banco de dados: é ele que sabe onde cada arquivo está. O Nébula Drive faz cópias de segurança automáticas.

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
- 💎 **Nébula Drive / assuntos comerciais:** samuel@inglescurso.com.br *(apenas comercial — sem suporte gratuito por e-mail)*

---

## 📊 Estatísticas

![GitHub Stars](https://img.shields.io/github/stars/samucamg/NebulaFTP?style=social)
![GitHub Forks](https://img.shields.io/github/forks/samucamg/NebulaFTP?style=social)
![GitHub Issues](https://img.shields.io/github/issues/samucamg/NebulaFTP)

---

<div align="center">

**Feito com ❤️ por [Samuel de Sousa Santos](https://github.com/samucamg)**

</div>
