[🇺🇸 English](#) | [🇧🇷 Português](TELEGRAM_SETUP.md)

# 📱 Telegram Setup

This guide shows you how to create and configure everything you need on Telegram to use Nebula FTP.

---

## 🎯 What You Need

1. **API Credentials** (API_ID and API_HASH)
2. **Bot Token(s)** (1 or more bots — Community uses only the 1st)
3. **Private Channel** (where your files will be stored)
4. **Channel ID** (numeric identifier)

---

## 📋 Step 1: Get API Credentials

### 1.1 Go to my.telegram.org

Open your browser and navigate to: [**https://my.telegram.org**](https://my.telegram.org)

### 1.2 Log In

Enter your phone number with country code:
- USA: `+12025550123`
- Brazil: `+5511999999999`
- Portugal: `+351912345678`

### 1.3 Confirm the Code

You will receive a code in Telegram. Enter it on the website.

### 1.4 Create an App

1. Click **"API development tools"**
2. Fill in the form:
   - **App title:** Nebula FTP
   - **Short name:** nebulaftp
   - **Platform:** Other
3. Click **"Create application"**

### 1.5 Copy the Credentials

You will see:
```
App api_id: 12345678
App api_hash: abc123def456789...
```

✅ **Copy and save** these values — they go into `API_ID` and `API_HASH` in your `.env`.

---

## 🤖 Step 2: Create Bot(s)

### 2.1 Open BotFather

Search in Telegram for: **@BotFather** → https://t.me/BotFather

### 2.2 Create a New Bot

Send the command `/newbot` and follow the prompts:

- **Name:** `Nebula FTP Bot`
- **Username:** `nebula_ftp_bot` (must end with `bot`)

### 2.3 Copy the Token

You will receive something like:
```
Use this token to access the HTTP API:
1234567890:AABBccDDeeFFggHH...
```

✅ **Copy and save** this token — it goes into `BOT_TOKENS` in your `.env`.

### 2.4 (Optional) Create More Bots — Pro version 💎

The Community version uses **only the first token**. For Multi-Bot (4–8 bots, up to 60 MB/s),
see the [Pro version](ECOSYSTEM-en.md).

If you want to create extra bots for a future Pro upgrade, repeat the steps above and separate
the tokens with commas in `BOT_TOKENS`.

---

## 📢 Step 3: Create a Channel

### 3.1 Create a New Channel

In Telegram:
1. Menu → **New Channel**
2. Name: `Nebula FTP Storage` (any name)
3. Type: **Private** ⚠️ IMPORTANT!

### 3.2 Add the Bot(s) as Admin

1. Open the channel
2. Menu → **Administrators** → **Add Admin**
3. Search for the bot username (e.g. `@nebula_ftp_bot`)
4. Check **all permissions**
5. Save

Repeat for every bot you created.

---

## 🔢 Step 4: Get the Channel ID

### Via @userinfobot (easiest method)

1. Search for **@userinfobot** in Telegram
2. Start the conversation (`/start`)
3. **Forward** any message from your channel to the bot
4. The bot will reply with the ID:
   ```
   Chat: -1001234567890
   ```

✅ **Copy that number** — it goes into `CHAT_ID` in your `.env`.

---

## ✅ Summary — What You Have Now

Before continuing, confirm you have:

- [ ] `API_ID` (8 digits)
- [ ] `API_HASH` (32 characters)
- [ ] `BOT_TOKENS` (one or more tokens)
- [ ] Private channel created
- [ ] Bot(s) added as admin in the channel
- [ ] `CHAT_ID` of the channel (format: `-100XXXXXXXXX`)

---

## 🔧 Configure .env

In your `.env` file, fill in at least:

```env
API_ID=12345678
API_HASH=abc123def456789...
BOT_TOKENS=1234567890:AABBcc...
CHAT_ID=-1001234567890
```

---

## ❓ Common Issues

### "Peer id invalid"

**Cause:** The bot was not added as admin in the channel.

**Fix:**
1. Go to the channel → Administrators → Add Admin
2. Add the bot with **all permissions** checked

### "The user must be an administrator"

**Cause:** The bot has limited permissions.

**Fix:**
1. Remove the bot from the channel
2. Add it again with **all boxes checked**

### "Chat not found"

**Cause:** The channel ID is wrong or missing the `-100` prefix.

**Fix:**
1. Use @userinfobot to confirm the ID
2. Make sure it starts with `-100`

---

## 📚 Next Steps

✅ Telegram configured!

Now choose how to install the server:
- **[Docker Installation](DOCKER-en.md)** — fastest, recommended for Linux VPS
- **[Native Python Installation](INSTALLATION-en.md)** — Linux, Windows or macOS

---

[← Back to README](../README-en.md)