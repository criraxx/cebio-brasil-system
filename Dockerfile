FROM python:3.11-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY cebio_api/requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY cebio_api/ ./cebio_api/
COPY cebio_frontend_serve/ ./cebio_frontend_serve/

# Expor portas
EXPOSE 8000 8080

# Comando para iniciar ambos os servidores
CMD sh -c "cd /app/cebio_api && uvicorn app.main:app --host 0.0.0.0 --port 8000 & cd /app/cebio_frontend_serve && python serve.py"
