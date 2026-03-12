/**
 * Sistema Unificado de Notificações Toast - CEBIO Brasil
 * Gerencia notificações visuais temporárias na interface
 */

class ToastManager {
    constructor() {
        this.container = null;
        this.init();
    }
    
    init() {
        if (!document.getElementById('toast-container')) {
            this.container = document.createElement('div');
            this.container.id = 'toast-container';
            this.container.className = 'toast-container';
            this.container.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                display: flex;
                flex-direction: column;
                gap: 10px;
                max-width: 400px;
            `;
            document.body.appendChild(this.container);
        } else {
            this.container = document.getElementById('toast-container');
        }
    }
    
    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const colors = {
            success: '#4caf50',
            error: '#f44336',
            warning: '#ff9800',
            info: '#2196f3'
        };
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.style.cssText = `
            background: ${colors[type] || colors.info};
            color: white;
            padding: 16px 20px;
            border-radius: 4px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: flex;
            align-items: center;
            gap: 12px;
            animation: slideIn 0.3s ease-out;
            min-width: 300px;
        `;
        
        // SEGURANÇA: Criar elementos de forma segura sem innerHTML
        const iconSpan = document.createElement('span');
        iconSpan.style.cssText = 'font-size: 20px; font-weight: bold;';
        iconSpan.textContent = icons[type] || icons.info;
        
        const messageSpan = document.createElement('span');
        messageSpan.style.cssText = 'flex: 1;';
        messageSpan.textContent = message; // Seguro - usa textContent
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'toast-close';
        closeBtn.style.cssText = 'background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 0; line-height: 1;';
        closeBtn.textContent = '×';
        closeBtn.onclick = () => this.remove(toast);
        
        toast.appendChild(iconSpan);
        toast.appendChild(messageSpan);
        toast.appendChild(closeBtn);
        
        this.container.appendChild(toast);
        
        // Auto-remover após duração
        setTimeout(() => this.remove(toast), duration);
    }
    
    remove(toast) {
        toast.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, 300);
    }
}

// Adicionar animações CSS
if (!document.getElementById('toast-animations')) {
    const style = document.createElement('style');
    style.id = 'toast-animations';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
}

// Instância global
const toastManager = new ToastManager();

// Funções helper globais
function showToast(message, type = 'info') {
    toastManager.show(message, type);
}

function showSuccess(message) {
    toastManager.show(message, 'success');
}

function showError(message) {
    toastManager.show(message, 'error');
}

function showWarning(message) {
    toastManager.show(message, 'warning');
}

function showInfo(message) {
    toastManager.show(message, 'info');
}
