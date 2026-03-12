/**
 * CEBIO Brasil - Utilitários de Sanitização
 * Proteção contra XSS (Cross-Site Scripting)
 */

/**
 * Escapa caracteres HTML para prevenir XSS
 * @param {string} text - Texto a ser escapado
 * @returns {string} Texto seguro para inserção em HTML
 */
function escapeHtml(text) {
  if (text === null || text === undefined) return '';
  
  const div = document.createElement('div');
  div.textContent = String(text);
  return div.innerHTML;
}

/**
 * Sanitiza HTML removendo scripts e atributos perigosos
 * Usa uma whitelist de tags e atributos seguros
 * @param {string} html - HTML a ser sanitizado
 * @returns {string} HTML seguro
 */
function sanitizeHtml(html) {
  if (!html) return '';
  
  // Tags permitidas (whitelist)
  const allowedTags = ['b', 'i', 'em', 'strong', 'u', 'p', 'br', 'span', 'div', 'a', 'ul', 'ol', 'li'];
  
  // Atributos permitidos
  const allowedAttrs = ['href', 'title', 'class', 'id'];
  
  // Criar elemento temporário
  const temp = document.createElement('div');
  temp.innerHTML = html;
  
  // Função recursiva para limpar elementos
  function cleanElement(element) {
    // Remover scripts
    const scripts = element.querySelectorAll('script');
    scripts.forEach(script => script.remove());
    
    // Remover event handlers inline
    const allElements = element.querySelectorAll('*');
    allElements.forEach(el => {
      // Remover atributos de evento (onclick, onerror, etc)
      Array.from(el.attributes).forEach(attr => {
        if (attr.name.startsWith('on')) {
          el.removeAttribute(attr.name);
        }
        // Remover atributos não permitidos
        if (!allowedAttrs.includes(attr.name) && attr.name !== 'style') {
          el.removeAttribute(attr.name);
        }
      });
      
      // Remover tags não permitidas
      if (!allowedTags.includes(el.tagName.toLowerCase())) {
        // Manter o conteúdo mas remover a tag
        const text = document.createTextNode(el.textContent);
        el.parentNode.replaceChild(text, el);
      }
    });
    
    return element.innerHTML;
  }
  
  return cleanElement(temp);
}

/**
 * Define HTML de forma segura em um elemento
 * Usa textContent por padrão (mais seguro)
 * @param {string|HTMLElement} elementOrId - ID do elemento ou elemento DOM
 * @param {string} content - Conteúdo a ser inserido
 * @param {boolean} allowHtml - Se true, permite HTML sanitizado
 */
function setContent(elementOrId, content, allowHtml = false) {
  const element = typeof elementOrId === 'string' 
    ? document.getElementById(elementOrId) 
    : elementOrId;
  
  if (!element) return;
  
  if (allowHtml) {
    // Sanitiza antes de inserir
    element.innerHTML = sanitizeHtml(content);
  } else {
    // Usa textContent (mais seguro - não interpreta HTML)
    element.textContent = content;
  }
}

/**
 * Cria elemento HTML de forma segura
 * @param {string} tag - Tag HTML (ex: 'div', 'span')
 * @param {object} options - Opções do elemento
 * @param {string} options.text - Texto (escapado automaticamente)
 * @param {string} options.html - HTML (sanitizado automaticamente)
 * @param {object} options.attrs - Atributos do elemento
 * @param {string} options.className - Classes CSS
 * @returns {HTMLElement} Elemento criado
 */
function createElement(tag, options = {}) {
  const element = document.createElement(tag);
  
  // Adicionar texto (seguro)
  if (options.text) {
    element.textContent = options.text;
  }
  
  // Adicionar HTML (sanitizado)
  if (options.html) {
    element.innerHTML = sanitizeHtml(options.html);
  }
  
  // Adicionar atributos
  if (options.attrs) {
    Object.keys(options.attrs).forEach(key => {
      // Não permitir atributos de evento
      if (!key.startsWith('on')) {
        element.setAttribute(key, options.attrs[key]);
      }
    });
  }
  
  // Adicionar classes
  if (options.className) {
    element.className = options.className;
  }
  
  return element;
}

/**
 * Sanitiza URL para prevenir javascript: e data: URIs
 * @param {string} url - URL a ser sanitizada
 * @returns {string} URL segura ou '#' se inválida
 */
function sanitizeUrl(url) {
  if (!url) return '#';
  
  const urlStr = String(url).trim().toLowerCase();
  
  // Bloquear protocolos perigosos
  const dangerousProtocols = ['javascript:', 'data:', 'vbscript:', 'file:'];
  
  for (const protocol of dangerousProtocols) {
    if (urlStr.startsWith(protocol)) {
      console.warn('URL bloqueada por segurança:', url);
      return '#';
    }
  }
  
  return url;
}

// Exportar funções
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    escapeHtml,
    sanitizeHtml,
    setContent,
    createElement,
    sanitizeUrl
  };
}
