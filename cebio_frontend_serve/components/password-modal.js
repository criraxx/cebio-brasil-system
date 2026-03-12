/**
 * Modal de Troca de Senha - CEBIO Brasil
 * Gerencia modal obrigatório de troca de senha temporária
 */

function showPasswordChangeModal(mandatory = false) {
    // Remover modal existente se houver
    const existingModal = document.getElementById('password-change-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    const modal = document.createElement('div');
    modal.id = 'password-change-modal';
    modal.className = 'modal modal-password-change' + (mandatory ? ' modal-mandatory' : '');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10001;
    `;
    
    // SEGURANÇA: Criar estrutura do modal de forma segura
    const modalContent = document.createElement('div');
    modalContent.className = 'modal-content';
    modalContent.style.cssText = `
        background: #fff;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 32px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    `;
    
    const title = document.createElement('h2');
    title.style.cssText = 'margin-top: 0; color: #1b7a3a; font-size: 18px; font-weight: 600;';
    title.textContent = `Troca de Senha ${mandatory ? 'Obrigatória' : ''}`;
    modalContent.appendChild(title);
    
    if (mandatory) {
        const alert = document.createElement('p');
        alert.className = 'alert alert-info';
        alert.style.cssText = 'background: #e8f4fd; color: #1b7a3a; padding: 12px; border-radius: 4px; margin-bottom: 20px; border-left: 4px solid #1b7a3a;';
        alert.textContent = '⚠️ Você precisa trocar sua senha temporária antes de continuar.';
        modalContent.appendChild(alert);
    }
    
    // Criar formulário (conteúdo estático, seguro)
    const form = document.createElement('form');
    form.id = 'password-change-form';
    form.innerHTML = `
        <div class="form-group" style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px;">Senha Atual</label>
            <input type="password" name="current_password" required style="
                width: 100%;
                padding: 12px 16px;
                border: 1px solid #ddd;
                background: #fff;
                color: #333;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                outline: none;
                transition: border-color 0.2s;
            ">
        </div>
        
        <div class="form-group" style="margin-bottom: 20px;">
            <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px;">Nova Senha</label>
            <input type="password" name="new_password" required minlength="8" style="
                width: 100%;
                padding: 12px 16px;
                border: 1px solid #ddd;
                background: #fff;
                color: #333;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                outline: none;
                transition: border-color 0.2s;
            ">
            <small style="color: #666; font-size: 12px; display: block; margin-top: 4px;">
                Mínimo 8 caracteres, incluindo letras, números e caracteres especiais
            </small>
        </div>
        
        <div class="form-group" style="margin-bottom: 24px;">
            <label style="display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px;">Confirmar Nova Senha</label>
            <input type="password" name="confirm_password" required style="
                width: 100%;
                padding: 12px 16px;
                border: 1px solid #ddd;
                background: #fff;
                color: #333;
                border-radius: 8px;
                font-size: 14px;
                font-family: inherit;
                outline: none;
                transition: border-color 0.2s;
            ">
        </div>
        
        <div style="display: flex; gap: 12px;">
            <button type="submit" class="btn btn-green" style="
                flex: 1;
                padding: 14px 24px;
                background: #1a9a4a;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: 600;
                transition: background 0.2s;
            " onmouseover="this.style.background='#15803d'" onmouseout="this.style.background='#1a9a4a'">Alterar Senha</button>
            ${!mandatory ? '<button type="button" onclick="closePasswordModal()" class="btn btn-dark" style="flex: 1; padding: 14px 24px; background: #f5f5f5; color: #333; border: 1px solid #ddd; border-radius: 8px; cursor: pointer; font-size: 15px; font-weight: 600; transition: background 0.2s;" onmouseover="this.style.background=\"#e8e8e8\"" onmouseout="this.style.background=\"#f5f5f5\"">Cancelar</button>' : ''}
        </div>
    `;
    
    modalContent.appendChild(form);
    modal.appendChild(modalContent);
    
    document.body.appendChild(modal);
    
    // Impedir fechamento se obrigatório
    if (mandatory) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                e.preventDefault();
                showWarning('Você precisa trocar sua senha antes de continuar');
            }
        });
    } else {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closePasswordModal();
            }
        });
    }
    
    // Handler do formulário
    document.getElementById('password-change-form').addEventListener('submit', handlePasswordChange);
}

async function handlePasswordChange(event) {
    event.preventDefault();
    const formData = new FormData(event.target);
    
    const currentPassword = formData.get('current_password');
    const newPassword = formData.get('new_password');
    const confirmPassword = formData.get('confirm_password');
    
    // Validar confirmação
    if (newPassword !== confirmPassword) {
        showError('As senhas não coincidem');
        return;
    }
    
    // Validar força da senha
    if (newPassword.length < 8) {
        showError('A senha deve ter no mínimo 8 caracteres');
        return;
    }
    
    if (!/[A-Z]/.test(newPassword)) {
        showError('A senha deve conter pelo menos uma letra maiúscula');
        return;
    }
    
    if (!/[a-z]/.test(newPassword)) {
        showError('A senha deve conter pelo menos uma letra minúscula');
        return;
    }
    
    if (!/[0-9]/.test(newPassword)) {
        showError('A senha deve conter pelo menos um número');
        return;
    }
    
    showLoading();
    try {
        await Auth.changePassword(currentPassword, newPassword);
        
        showSuccess('Senha alterada com sucesso!');
        closePasswordModal();
        
        // Atualizar flag no localStorage
        const user = JSON.parse(localStorage.getItem('user') || '{}');
        user.is_temp_password = false;
        user.requires_password_change = false;
        localStorage.setItem('user', JSON.stringify(user));
        
        // Redirecionar se era obrigatório
        const modal = document.getElementById('password-change-modal');
        if (modal && modal.classList.contains('modal-mandatory')) {
            setTimeout(() => {
                redirectToDashboard(user.role);
            }, 1000);
        }
    } catch (error) {
        showError(error.message || 'Erro ao alterar senha');
    } finally {
        hideLoading();
    }
}

function closePasswordModal() {
    const modal = document.getElementById('password-change-modal');
    if (modal && !modal.classList.contains('modal-mandatory')) {
        modal.remove();
    }
}

function redirectToDashboard(role) {
    const dashboards = {
        'admin': 'admin-dashboard.html',
        'pesquisador': 'pesquisador-dashboard.html',
        'bolsista': 'bolsista-dashboard.html'
    };
    window.location.href = dashboards[role] || 'index.html';
}
