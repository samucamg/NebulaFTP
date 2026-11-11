# NebulaFTP Community

Português | [English](README-en.md)

Servidor de arquivos que guarda tudo no **Telegram**: você acessa por **SFTP** (FileZilla, WinSCP, RaiDrive) ou pelo **painel web**, e os arquivos ficam num canal do Telegram.

- **Espaço ilimitado** no Telegram. Esta edição usa **um único bot**, então o limite real é a velocidade: cada arquivo é enviado ao canal uma parte de cada vez.
- Grátis e de código aberto (MIT).

## O que tem

- **SFTP** (porta 2222): enviar, baixar, renomear, apagar, criar pasta. Compatível com FileZilla, WinSCP e RaiDrive.
- **Painel web** (porta 8082): login, gerenciador de arquivos (upload de vários GB direto para o disco, download, renomear, apagar, criar pasta) e player para vídeo e áudio que o navegador toca (mp4, webm, mp3, m4a, ogg, opus, wav).
- **Usuários:** cada usuário tem a própria pasta e só enxerga ela. Só o admin vê todas.
- **Armazenamento:** o arquivo chega primeiro ao disco (staging), é dividido em partes de 100 MB e enviado ao canal. Uploads pendentes continuam depois de reiniciar. Sobrescrever ou apagar remove também as mensagens antigas do canal.
- **Leitura sob demanda:** só as partes necessárias são baixadas para um cache local. O player e o SFTP pedem trechos (Range) sem baixar o arquivo inteiro.
- **Banco:** SQLite (um arquivo, sem servidor).

## Como funciona

```
SFTP / Web  ->  núcleo (pastas, permissões, versões)  ->  SQLite
                         |
                 staging em disco  ->  worker (1 bot)  ->  canal do Telegram
```

## Requisitos

- Python 3.11 ou mais novo (testado com 3.13), Windows ou Linux. Ou Docker.
- Uma conta em <https://my.telegram.org> para obter `API_ID` e `API_HASH`.
- Um bot criado no @BotFather e um canal privado, com o bot como **administrador**.
- Espaço em disco para o staging e o cache (pelo menos o tamanho do maior arquivo que você vai enviar).
- **Relógio do computador certo.** O Telegram recusa conexões com mais de 30 segundos de diferença; o programa avisa no início.

## Instalação (Python)

```bash
git clone https://github.com/samucamg/NebulaFTP.git
cd NebulaFTP
python -m venv .venv
# Windows: .venv\Scripts\activate    Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # no Windows: copy .env.example .env
# edite o .env
python main.py
```

## Instalação (Docker)

```bash
cp .env.example .env   # edite o .env
docker compose up -d --build
```

Os dados (banco, staging, cache, chave SFTP e sessão do bot) ficam na pasta `./data`.

## Configuração (.env)

| Variável | Padrão | Para quê |
|---|---|---|
| `API_ID`, `API_HASH` | — | Credenciais de my.telegram.org |
| `BOT_TOKENS` | — | Token do bot (um só) |
| `CHAT_ID` | — | ID do canal, ex. `-1001234567890` |
| `WEB_ADMIN_USER` | `admin` | Login do administrador |
| `WEB_ADMIN_PASSWORD` | — | Senha do admin, obrigatória na primeira execução |
| `HOST` | `0.0.0.0` | Endereço de escuta |
| `SFTP_PORT` / `WEB_PORT` | `2222` / `8082` | Portas |
| `DATA_DIR` | `data` | Staging, cache, sessão do bot |
| `DB_FILE` | `nebula.db` | Banco SQLite |
| `CHUNK_SIZE_MB` | `100` | Tamanho de cada parte enviada ao canal |
| `MAX_STAGING_AGE` / `CACHE_MAX_AGE` | `3600` | Segundos até a limpeza de arquivos locais sem uso |
| `SFTP_HOST_KEY` | `sftp_host_key` | Chave do servidor SFTP (criada sozinha) |
| `LOG_LEVEL` | `INFO` | Nível do log |

## Primeiro acesso

1. Abra `http://SEU_IP:8082` e entre com o admin.
2. Em **Usuários**, crie os usuários. Cada um ganha a pasta `/<login>`.
3. No FileZilla, WinSCP ou RaiDrive: protocolo **SFTP**, porta **2222**, mesmo login e senha.

## Segurança

- Senhas guardadas com hash (scrypt). Formulários protegidos contra CSRF.
- O painel web usa HTTP. Na internet, coloque-o atrás de um proxy com HTTPS (Caddy, Nginx).
- Não há canal de backup: o Telegram pode remover conteúdo ou ficar fora do ar. Guarde cópias do que for importante.
- Faça cópia do arquivo do banco (`DB_FILE`): sem ele, não dá para remontar os arquivos a partir do canal.

## Testes

```bash
pip install -r requirements-dev.txt
pytest -q
```

A suíte usa um Telegram simulado e compara o sha256 de ida e volta pelo núcleo, SFTP e web.

## Nébula Drive Enterprise

Existe uma edição comercial separada, com mais recursos. Instalação profissional opcional e paga: samuel@inglescurso.com.br.

## Licença

MIT.
