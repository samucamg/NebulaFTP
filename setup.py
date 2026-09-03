import os
import sys

def prompt(message, default=None, allow_empty=False):
    if default:
        res = input(f"{message} [{default}]: ").strip()
        return res if res else default
    else:
        while True:
            res = input(f"{message}: ").strip()
            if res or allow_empty:
                return res
            print("Este campo é obrigatório.")

def main():
    print("=" * 50)
    print("Bem-vindo ao assistente de configuração do Nebula FTP!")
    print("=" * 50)
    print("Este script irá criar o arquivo .env com suas configurações.\n")

    api_id = prompt("Digite seu API_ID do Telegram")
    api_hash = prompt("Digite seu API_HASH do Telegram")
    bot_tokens = prompt("Digite seu(s) BOT_TOKEN(s) (separados por vírgula)")
    chat_id = prompt("Digite o CHAT_ID do canal")
    mongodb = prompt("Digite a string de conexão do MongoDB", "mongodb://localhost:27017")
    host = prompt("Host do servidor FTP", "0.0.0.0")
    ftp_port = prompt("Porta do servidor FTP", "2121")
    sftp_port = prompt("Porta do servidor SFTP", "2222")
    web_port = prompt("Porta do painel Web", "8080")
    web_password = prompt("Senha do administrador Web (deixe em branco se não quiser autenticação)", allow_empty=True)

    env_content = f"""# ==============================================
# NEBULA FTP - CONFIGURAÇÃO GERADA PELO SETUP
# ==============================================

# ============= TELEGRAM =============
API_ID={api_id}
API_HASH={api_hash}
BOT_TOKENS={bot_tokens}
CHAT_ID={chat_id}

# ============= MONGODB =============
MONGODB={mongodb}

# ============= SERVIDOR FTP/SFTP/WEB =============
HOST={host}
PORT={ftp_port}
SFTP_PORT={sftp_port}
WEB_PORT={web_port}
WEB_ADMIN_PASSWORD={web_password}
PASSIVE_PORTS=60000-60100

# ============= PERFORMANCE =============
MAX_WORKERS=4
CHUNK_SIZE_MB=64
MAX_RETRIES=5
MAX_STAGING_AGE=3600

# ============= LOGGING =============
LOG_LEVEL=INFO
"""
    with open(".env", "w") as f:
        f.write(env_content)

    print("\n" + "=" * 50)
    print("Arquivo .env criado com sucesso!")
    print("Agora você pode rodar o main.py ou docker-compose up -d")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelado.")
        sys.exit(1)
