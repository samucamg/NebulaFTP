#!/bin/sh
# ============================================================
# Nebula FTP - Entrypoint
# Garante que os arquivos de persistência existam como ARQUIVOS
# dentro do container (e não como diretórios).
#
# Por quê? Se o arquivo não existe no host, o Docker cria um
# DIRETÓRIO vazio no lugar do bind mount - o que quebra o SQLite,
# o log e a chave SFTP de forma silenciosa. Este entrypoint
# corrige isso automaticamente na subida do container.
# ============================================================
set -e
cd /app || exit 1

for f in nebula.db nebula.log sftp_host_key Nebula_MonoBot.session; do
  if [ -d "$f" ]; then
    if [ -n "$(ls -A "$f" 2>/dev/null)" ]; then
      echo "ERRO: '$f' é um diretório NÃO-vazio no volume." >&2
      echo "Corrija no host (apague o diretório $f e rode: touch $f) e suba de novo." >&2
      exit 1
    fi
    rmdir "$f"
    echo "Entrypoint: corrigido '$f' (diretório vazio -> arquivo)."
  fi
  if [ ! -f "$f" ]; then
    touch "$f"
    echo "Entrypoint: criado '$f'."
  fi
done

# Pasta de staging (cache de upload)
mkdir -p staging

exec "$@"
