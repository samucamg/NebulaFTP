# Imagem leve do Python
FROM python:3.10-slim

# Pasta de trabalho dentro do container
WORKDIR /app

# Dependências de sistema (gcc é necessário para libs de criptografia do Telegram)
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código
COPY . .

# Entrypoint: garante que nebula.db, logs, sessão e chave SFTP
# existam como arquivos dentro do container (corrige bind mounts).
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Cria a pasta de staging (cache de upload)
RUN mkdir -p staging

# Portas padrão: FTP 2121 · SFTP/SSH 2222 · Painel Web 8080
# (com network_mode: host no compose, as portas efetivas são as do .env)
EXPOSE 2121 2222 8080

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "main.py"]
