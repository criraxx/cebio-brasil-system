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

# Copiar script de inicialização
COPY start.sh .
RUN chmod +x start.sh

# Expor porta
EXPOSE 8080

# Comando para iniciar ambos os servidores
CMD ["/bin/bash", "./start.sh"]
