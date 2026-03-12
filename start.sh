#!/bin/bash

# Iniciar o FastAPI em background
cd /app/cebio_api
uvicorn app.main:app --host 127.0.0.1 --port 8000 &

# Aguardar um pouco para o FastAPI iniciar
sleep 2

# Iniciar o servidor frontend
cd /app/cebio_frontend_serve
python serve.py
