#!/bin/bash
set -e

# Iniciar o FastAPI em background
echo "Iniciando FastAPI..."
cd /app/cebio_api
uvicorn app.main:app --host 127.0.0.1 --port 8000 > /tmp/fastapi.log 2>&1 &
FASTAPI_PID=$!

# Aguardar um pouco para o FastAPI iniciar
sleep 3

# Verificar se FastAPI está rodando
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "Erro: FastAPI não iniciou corretamente"
    cat /tmp/fastapi.log
    exit 1
fi

echo "FastAPI iniciado com sucesso (PID: $FASTAPI_PID)"

# Iniciar o servidor frontend
echo "Iniciando servidor frontend..."
cd /app/cebio_frontend_serve
exec python serve.py
