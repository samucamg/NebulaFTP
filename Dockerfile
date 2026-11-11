FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY nebula ./nebula
COPY main.py .
ENV DATA_DIR=/app/data DB_FILE=/app/data/nebula.db SFTP_HOST_KEY=/app/data/sftp_host_key PYTHONUNBUFFERED=1
VOLUME ["/app/data"]
EXPOSE 2222 8082
CMD ["python", "main.py"]
