[🇧🇷 Português](#) | [🇺🇸 English](TELEGRAM_SETUP-en.md)

# 📱 Configuração do Telegram

Este guia ensina como criar e configurar tudo que você precisa no Telegram para usar o Nebula FTP.

---

## 🎯 O Que Você Precisa

1. **API Credentials** (API_ID e API_HASH)
2. **Bot Token(s)** (1 ou mais bots — Community usa apenas o 1º)
3. **Canal Privado** (onde os arquivos ficam)
4. **ID do Canal** (número de identificação)

---

## 📋 Passo 1: Obter API Credentials

### 1.1 Acesse my.telegram.org

Abra seu navegador e vá para: [**https://my.telegram.org**](https://my.telegram.org)

### 1.2 Faça Login

Digite seu número de telefone com código do país:
- Brasil: `+5511999999999`
- Portugal: `+351912345678`

### 1.3 Confirme o Código

Você receberá um código no Telegram. Digite-o no site.

### 1.4 Crie um App

1. Clique em **"API development tools"**
2. Preencha o formulário:
   - **App title:** Nebula FTP
   - **Short name:** nebulaftp
   - **Platform:** Other
3. Clique em **"Create application"**

### 1.5 Copie as Credenciais

Você verá:
```
App api_id: 12345678
App api_hash: abc123def456789...
```

✅ **Copie e salve** esses valores — eles vão para `API_ID` e `API_HASH` no `.env`.

---

## 🤖 Passo 2: Criar Bot(s)

### 2.1 Abra o BotFather

No Telegram, busque por: **@BotFather** → https://t.me/BotFather

### 2.2 Crie um Novo Bot

Envie o comando `/newbot` e siga as instruções:

- **Nome:** `Nebula FTP Bot`
- **Username:** `nebula_ftp_bot` (deve terminar com `bot`)

### 2.3 Copie o Token

Você receberá algo como:
```
Use this token to access the HTTP API:
1234567890:AABBccDDeeFFggHH...
```

✅ **Copie e salve** esse token — ele vai para `BOT_TOKENS` no `.env`.

### 2.4 (Opcional) Criar Mais Bots — Versão Pro 💎

A versão Community usa **apenas o primeiro token**. Para Multi-Bot (4-8 bots, até 60 MB/s),
veja a [versão Pro](ECOSYSTEM.md).

Se quiser criar bots extras para futura migração Pro, repita os passos acima e separe os tokens
por vírgula em `BOT_TOKENS`.

---

## 📢 Passo 3: Criar Canal

### 3.1 Criar Novo Canal

No Telegram:
1. Menu → **New Channel**
2. Nome: `Nebula FTP Storage` (qualquer nome)
3. Tipo: **Private** ⚠️ IMPORTANTE!

### 3.2 Adicionar o(s) Bot(s) como Admin

1. Abra o canal
2. Menu → **Administrators** → **Add Admin**
3. Busque pelo username do bot (ex: `@nebula_ftp_bot`)
4. Marque **todas as permissões**
5. Salve

Repita para todos os bots criados.

---

## 🔢 Passo 4: Obter ID do Canal

### Via @userinfobot (mais fácil)

1. Busque por **@userinfobot** no Telegram
2. Inicie a conversa (`/start`)
3. **Encaminhe** uma mensagem do seu canal para o bot
4. O bot responderá com o ID:
   ```
   Chat: -1001234567890
   ```

✅ **Copie esse número** — ele vai para `CHAT_ID` no `.env`.

---

## ✅ Resumo — O Que Você Tem Agora

Antes de continuar, confirme:

- [ ] `API_ID` (8 dígitos)
- [ ] `API_HASH` (32 caracteres)
- [ ] `BOT_TOKENS` (um ou mais tokens)
- [ ] Canal privado criado
- [ ] Bot(s) adicionado(s) como admin no canal
- [ ] `CHAT_ID` do canal (formato: `-100XXXXXXXXX`)

---

## 🔧 Configurar o .env

No arquivo `.env`, preencha ao menos:

```env
API_ID=12345678
API_HASH=abc123def456789...
BOT_TOKENS=1234567890:AABBcc...
CHAT_ID=-1001234567890
```

---

## ❓ Problemas Comuns

### "Peer id invalid"

**Causa:** O bot não foi adicionado como admin no canal.

**Solução:**
1. Vá no canal → Administrators → Add Admin
2. Adicione o bot com **todas as permissões**

### "The user must be an administrator"

**Causa:** O bot tem permissões limitadas.

**Solução:**
1. Remova o bot do canal
2. Adicione novamente marcando **todas as caixas**

### "Chat not found"

**Causa:** O ID do canal está errado ou sem o prefixo `-100`.

**Solução:**
1. Use @userinfobot para confirmar o ID
2. Verifique se começa com `-100`

---

## 📚 Próximos Passos

✅ Telegram configurado!

Agora escolha como instalar o servidor:
- **[Instalação via Docker](DOCKER.md)** — mais rápido, recomendado para VPS Linux
- **[Instalação Python nativa](INSTALLATION.md)** — Linux, Windows ou macOS

---

[← Voltar ao README](../README.md)