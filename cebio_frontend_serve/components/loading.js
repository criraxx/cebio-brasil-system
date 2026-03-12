/**
 * Sistema de Loading - CEBIO Brasil
 * Gerencia indicadores de carregamento
 */

class LoadingManager {
    constructor() {
        this.overlay = null;
        this.counter = 0;
        this.init();
    }
    
    init() {
        if (!document.getElementById('loading-overlay')) {
            this.overlay = document.createElement('div');
            this.overlay.id = 'loading-overlay';
            this.overlay.className = 'loading-overlay';
            this.overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            `;
            
            // SEGURANÇA: Criar estrutura de forma segura sem innerHTML
            const spinnerContainer = document.createElement('div');
            spinnerContainer.className = 'loading-spinner';
            spinnerContainer.style.textContent = 'text-align: center;';
            
            const spinner = document.createElement('div');
            spinner.className = 'spinner';
            spinner.style.cssText = `
                border: 4px solid rgba(255, 255, 255, 0.3);
                border-top: 4px solid #4dd0e1;
                border-radius: 50%;
                width: 50px;
                height: 50px;
                animation: spin 1s linear infinite;
                margin: 0 auto 16px;
            `;
            
            const text = document.createElement('p');
            text.style.cssText = 'color: white; font-size: 16px; margin: 0;';
            text.textContent = 'Carregando...';
            
            spinnerContainer.appendChild(spinner);
            spinnerContainer.appendChild(text);
            this.overlay.appendChild(spinnerContainer);
            
            document.body.appendChild(this.overlay);
            
            // Adicionar animação de spin
            if (!document.getElementById('loading-animations')) {
                const style = document.createElement('style');
                style.id = 'loading-animations';
                style.textContent = `
                    @keyframes spin {
                        0% { transform: rotate(0deg); }
                        100% { transform: rotate(360deg); }
                    }
                `;
                document.head.appendChild(style);
            }
        } else {
            this.overlay = document.getElementById('loading-overlay');
        }
    }
    
    show() {
        this.counter++;
        this.overlay.style.display = 'flex';
    }
    
    hide() {
        this.counter = Math.max(0, this.counter - 1);
        if (this.counter === 0) {
            this.overlay.style.display = 'none';
        }
    }
    
    forceHide() {
        this.counter = 0;
        this.overlay.style.display = 'none';
    }
}

// Instância global
const loadingManager = new LoadingManager();

// Funções helper globais
function showLoading() {
    loadingManager.show();
}

function hideLoading() {
    loadingManager.hide();
}

function forceHideLoading() {
    loadingManager.forceHide();
}
