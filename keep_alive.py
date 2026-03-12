#!/usr/bin/env python3
"""
Script para manter o site CEBIO Brasil sempre acordado.
Faz requisições HTTP a cada 5 minutos para evitar que o Render faça spin down.
"""

import requests
import time
import logging
from datetime import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('/tmp/keep_alive.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# URL do site
SITE_URL = "https://cebio-brasil.onrender.com"
INTERVAL = 300  # 5 minutos em segundos

def keep_alive():
    """Faz uma requisição ao site para mantê-lo acordado."""
    try:
        response = requests.get(SITE_URL, timeout=10)
        status = response.status_code
        logger.info(f"✓ Keep-alive ping: {SITE_URL} - Status: {status}")
        return True
    except Exception as e:
        logger.error(f"✗ Keep-alive ping falhou: {e}")
        return False

def main():
    """Loop principal que faz ping a cada 5 minutos."""
    logger.info(f"Iniciando keep-alive para {SITE_URL}")
    logger.info(f"Intervalo: {INTERVAL} segundos ({INTERVAL // 60} minutos)")
    
    while True:
        try:
            keep_alive()
            time.sleep(INTERVAL)
        except KeyboardInterrupt:
            logger.info("Keep-alive interrompido pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal: {e}")
            time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
