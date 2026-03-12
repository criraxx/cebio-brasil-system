"""
CEBIO Brasil - Validação Avançada de Arquivos
Proteção contra upload de arquivos maliciosos
"""
import io
import magic
from PIL import Image
from typing import Tuple, Optional


def validate_image_file(content: bytes, max_size_mb: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Valida se o arquivo é realmente uma imagem válida.
    
    Args:
        content: Conteúdo do arquivo em bytes
        max_size_mb: Tamanho máximo em MB
    
    Returns:
        Tuple[bool, Optional[str]]: (é_válido, mensagem_erro)
    """
    # Verificar tamanho
    if len(content) > max_size_mb * 1024 * 1024:
        return False, f"Arquivo muito grande. Máximo: {max_size_mb}MB"
    
    # Verificar MIME type real (não apenas header HTTP)
    try:
        mime = magic.from_buffer(content, mime=True)
        if mime not in ['image/jpeg', 'image/png', 'image/jpg']:
            return False, f"Tipo de arquivo inválido: {mime}. Use JPEG ou PNG."
    except Exception as e:
        return False, f"Erro ao verificar tipo de arquivo: {str(e)}"
    
    # Verificar se é realmente uma imagem válida
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()  # Verifica integridade da imagem
        
        # Reabrir para verificar formato (verify() fecha o arquivo)
        img = Image.open(io.BytesIO(content))
        
        # Verificar formato
        if img.format not in ['JPEG', 'PNG']:
            return False, f"Formato de imagem inválido: {img.format}"
        
        # Verificar dimensões razoáveis (prevenir DoS com imagens gigantes)
        width, height = img.size
        if width > 10000 or height > 10000:
            return False, "Dimensões da imagem muito grandes (máximo: 10000x10000)"
        
        # Verificar se não é uma imagem com código embutido
        # (algumas vulnerabilidades exploram metadados EXIF)
        if hasattr(img, '_getexif') and img._getexif():
            # Limpar metadados EXIF potencialmente perigosos
            # Em produção, considere remover todos os metadados
            pass
        
        return True, None
        
    except Exception as e:
        return False, f"Arquivo não é uma imagem válida: {str(e)}"


def validate_pdf_file(content: bytes, max_size_mb: int = 20) -> Tuple[bool, Optional[str]]:
    """
    Valida se o arquivo é realmente um PDF válido.
    
    Args:
        content: Conteúdo do arquivo em bytes
        max_size_mb: Tamanho máximo em MB
    
    Returns:
        Tuple[bool, Optional[str]]: (é_válido, mensagem_erro)
    """
    # Verificar tamanho
    if len(content) > max_size_mb * 1024 * 1024:
        return False, f"Arquivo muito grande. Máximo: {max_size_mb}MB"
    
    # Verificar MIME type real
    try:
        mime = magic.from_buffer(content, mime=True)
        if mime != 'application/pdf':
            return False, f"Tipo de arquivo inválido: {mime}. Use PDF."
    except Exception as e:
        return False, f"Erro ao verificar tipo de arquivo: {str(e)}"
    
    # Verificar assinatura PDF (magic bytes)
    if not content.startswith(b'%PDF-'):
        return False, "Arquivo não é um PDF válido (assinatura incorreta)"
    
    # Verificar se tem EOF marker
    if b'%%EOF' not in content[-1024:]:  # Procurar nos últimos 1KB
        return False, "Arquivo PDF incompleto ou corrompido"
    
    # Verificar se não contém JavaScript embutido (comum em PDFs maliciosos)
    dangerous_keywords = [
        b'/JavaScript',
        b'/JS',
        b'/Launch',
        b'/OpenAction',
        b'/AA',  # Additional Actions
        b'/Names',
    ]
    
    content_lower = content.lower()
    for keyword in dangerous_keywords:
        if keyword.lower() in content_lower:
            # Avisar mas não bloquear (pode ser legítimo)
            # Em produção, considere bloquear ou sanitizar
            print(f"⚠️  Aviso: PDF contém {keyword.decode()} (potencialmente perigoso)")
    
    # Verificar tamanho razoável (prevenir DoS)
    if len(content) < 100:  # PDF muito pequeno é suspeito
        return False, "Arquivo PDF muito pequeno (possivelmente corrompido)"
    
    return True, None


def get_safe_filename(original_filename: str) -> str:
    """
    Gera um nome de arquivo seguro, removendo caracteres perigosos.
    
    Args:
        original_filename: Nome original do arquivo
    
    Returns:
        str: Nome de arquivo seguro
    """
    import re
    import uuid
    from pathlib import Path
    
    # Extrair extensão
    ext = Path(original_filename).suffix.lower()
    
    # Validar extensão
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.pdf'}
    if ext not in allowed_extensions:
        ext = '.bin'  # Extensão genérica se inválida
    
    # Gerar nome único e seguro
    safe_name = f"{uuid.uuid4().hex}{ext}"
    
    return safe_name


def sanitize_filename(filename: str) -> str:
    """
    Sanitiza nome de arquivo removendo caracteres perigosos.
    Usado para armazenar o nome original de forma segura.
    
    Args:
        filename: Nome do arquivo
    
    Returns:
        str: Nome sanitizado
    """
    import re
    
    # Remover path traversal
    filename = filename.replace('..', '')
    filename = filename.replace('/', '')
    filename = filename.replace('\\', '')
    
    # Remover caracteres especiais perigosos
    filename = re.sub(r'[<>:"|?*\x00-\x1f]', '', filename)
    
    # Limitar tamanho
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename.strip()


def check_file_content_safety(content: bytes) -> Tuple[bool, Optional[str]]:
    """
    Verifica se o conteúdo do arquivo não contém padrões maliciosos conhecidos.
    
    Args:
        content: Conteúdo do arquivo
    
    Returns:
        Tuple[bool, Optional[str]]: (é_seguro, mensagem_aviso)
    """
    # Padrões maliciosos comuns
    malicious_patterns = [
        b'<?php',  # PHP code
        b'<script',  # JavaScript
        b'eval(',  # Eval
        b'exec(',  # Exec
        b'system(',  # System calls
        b'passthru(',
        b'shell_exec(',
        b'`',  # Backticks (shell execution)
    ]
    
    content_lower = content.lower()
    
    for pattern in malicious_patterns:
        if pattern in content_lower:
            return False, f"Conteúdo suspeito detectado: {pattern.decode('utf-8', errors='ignore')}"
    
    return True, None
