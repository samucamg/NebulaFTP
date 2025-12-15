# Usa uma imagem Python leve
FROM python:3.10-slim

# Define a pasta de trabalho dentro do container
WORKDIR /app

# Instala dependências de sistema (gcc é necessário para algumas libs de criptografia do Telegram)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código para dentro do container
COPY . .

# Cria a pasta staging
RUN mkdir -p staging

# Expõe as portas (FTP e Passivas)
EXPOSE 2121
EXPOSE 60000-60100

# Comando para iniciar
CMD ["python", "main.py"]
