# Implementation Plan: CEBIO Critical Fixes

## Overview

Este plano de implementação organiza as correções em grupos prioritários, começando pelos problemas críticos que bloqueiam funcionalidades essenciais. Cada tarefa é incremental e inclui validação através de testes.

**Priorização:**
1. Grupo CRÍTICO: Download de arquivos, gestão de senhas, troca de senha
2. Grupo ALTO: Restauração de versões, proteção de dados, auditoria
3. Grupo MÉDIO: Feedback, relatórios PDF, notificações em lote, modo manutenção

## Tasks

### GRUPO 1 - CRÍTICO: Funcionalidades Bloqueadoras

- [ ] 1. Implementar sistema de download de arquivos
  - [ ] 1.1 Criar model e schema de File
    - Criar `models/file.py` com campos: uuid, original_filename, mime_type, size_bytes, storage_path, project_id, uploaded_by, uploaded_at
    - Criar `schemas/file.py` com FileResponse (sem storage_path interno)
    - Adicionar relacionamento files em Project model
    - _Requirements: 1.1_

  - [ ] 1.2 Implementar endpoint de download
    - Criar `routers/files.py` com GET /files/{file_uuid}
    - Validar permissões: usuário tem acesso ao projeto do arquivo
    - Retornar StreamingResponse com arquivo e nome original
    - Tratar erros 404 (arquivo não existe) e 403 (sem permissão)
    - _Requirements: 1.2, 1.3, 1.4_

  - [ ] 1.3 Escrever testes de propriedade para download de arquivos
    - **Property 2: File Download Round Trip**
    - **Validates: Requirements 1.2**
    - **Property 3: Unauthorized File Access Rejection**
    - **Validates: Requirements 1.3**

  - [ ] 1.4 Escrever testes unitários para casos extremos
    - Teste: arquivo não existe retorna 404
    - Teste: usuário sem permissão retorna 403
    - Teste: arquivo vazio é tratado corretamente
    - _Requirements: 1.4_

  - [ ] 1.5 Implementar links de download no frontend
    - Criar função `renderFileLinks()` em script.js
    - Adicionar links de download em pesquisador-projeto-detalhes.html
    - Adicionar links de download em bolsista-projeto-detalhes.html
    - Implementar função `downloadFile()` com tratamento de erro
    - _Requirements: 1.5, 1.6_

- [ ] 2. Implementar gestão de senhas temporárias
  - [ ] 2.1 Adicionar campo requires_password_change ao User model
    - Adicionar coluna `requires_password_change BOOLEAN DEFAULT TRUE` em User
    - Criar migration para adicionar campo
    - Atualizar usuários existentes com requires_password_change=false
    - _Requirements: 2.3_

  - [ ] 2.2 Atualizar criação de usuário para gerar senha temporária
    - Criar função `generate_secure_password()` em utils/security.py (12 caracteres, letras+números+símbolos)
    - Modificar POST /users em routers/users.py para gerar senha temporária
    - Retornar UserCreateResponse com user e temporary_password
    - Adicionar log de auditoria para criação de usuário
    - _Requirements: 2.1, 2.2_

  - [ ] 2.3 Escrever testes de propriedade para geração de senha
    - **Property 5: Temporary Password Generation**
    - **Validates: Requirements 2.1, 2.2**
    - **Property 6: Password Change Flag Initialization**
    - **Validates: Requirements 2.3**

  - [ ] 2.4 Implementar modal de exibição de senha temporária
    - Criar função `showTemporaryPasswordModal()` em admin-usuarios.html
    - Implementar função `copyPassword()` para copiar senha
    - Adicionar alerta de que senha não será exibida novamente
    - Atualizar função `createUser()` para exibir modal após criação
    - _Requirements: 2.4, 2.5_

  - [ ] 2.5 Implementar envio de email com senha temporária (opcional)
    - Criar função `send_temp_password_email()` em utils/email.py
    - Verificar se email está configurado antes de enviar
    - Adicionar template de email com senha temporária
    - _Requirements: 2.6_

- [ ] 3. Implementar sistema de troca de senha obrigatória
  - [ ] 3.1 Atualizar resposta de login com flag requires_password_change
    - Modificar LoginResponse em schemas/auth.py para incluir requires_password_change
    - Atualizar POST /auth/login para retornar flag do usuário
    - _Requirements: 3.1_

  - [ ] 3.2 Criar componente de modal de troca de senha
    - Criar `components/password-modal.js` com função `showPasswordChangeModal(mandatory)`
    - Implementar validação de senha no frontend (mínimo 8 caracteres, letras e números)
    - Implementar confirmação de senha
    - Bloquear fechamento do modal se mandatory=true
    - _Requirements: 3.2, 3.3_

  - [ ] 3.3 Implementar validação de força de senha no backend
    - Criar validator em PasswordChangeRequest schema
    - Validar: mínimo 8 caracteres, pelo menos uma letra, pelo menos um número
    - Retornar mensagens de erro descritivas
    - _Requirements: 3.4_

  - [ ] 3.4 Escrever testes de propriedade para validação de senha
    - **Property 9: Password Strength Validation**
    - **Validates: Requirements 3.4**

  - [ ] 3.5 Atualizar endpoint de troca de senha
    - Modificar POST /auth/change-password para atualizar requires_password_change=false
    - Adicionar log de auditoria para troca de senha
    - Validar senha atual antes de permitir troca
    - _Requirements: 3.5, 3.6_

  - [ ] 3.6 Escrever testes de propriedade para troca de senha
    - **Property 10: Password Change Flag Reset**
    - **Validates: Requirements 3.5**
    - **Property 11: Password Change Audit Logging**
    - **Validates: Requirements 3.6**

  - [ ] 3.7 Integrar modal de troca de senha no fluxo de login
    - Atualizar função `handleLogin()` em script.js
    - Verificar requires_password_change após login
    - Exibir modal obrigatório se flag=true
    - Bloquear navegação até senha ser trocada
    - Redirecionar para dashboard após troca bem-sucedida
    - _Requirements: 3.2, 3.3_

- [ ] 4. Checkpoint - Validar funcionalidades críticas
  - Testar fluxo completo de download de arquivos
  - Testar criação de usuário e exibição de senha temporária
  - Testar primeiro login e troca de senha obrigatória
  - Executar todos os testes de propriedade do Grupo 1
  - Garantir que todos os testes passam antes de prosseguir

### GRUPO 2 - ALTO: Funcionalidades Essenciais

- [ ] 5. Implementar restauração de versões de projeto
  - [ ] 5.1 Criar endpoint de restauração de versão
    - Criar POST /projects/{project_id}/restore/{version_id} em routers/projects.py
    - Validar que versão existe e pertence ao projeto
    - Validar permissões do usuário (require_pesquisador_or_admin)
    - _Requirements: 4.1_

  - [ ] 5.2 Implementar lógica de backup antes de restaurar
    - Criar ProjectVersion com dados atuais antes de restaurar
    - Adicionar version_note indicando que é backup automático
    - Salvar backup em transação com restauração
    - _Requirements: 4.2_

  - [ ] 5.3 Escrever testes de propriedade para restauração
    - **Property 13: Backup Before Restoration**
    - **Validates: Requirements 4.2**
    - **Property 14: Version Data Integrity**
    - **Validates: Requirements 4.3**

  - [ ] 5.4 Implementar cópia de dados da versão histórica
    - Copiar title, description, status, data da versão para projeto
    - Atualizar updated_at e updated_by
    - Preservar metadados de auditoria (quem restaurou, quando, qual versão)
    - Adicionar log de auditoria com detalhes da restauração
    - _Requirements: 4.3, 4.4, 4.6_

  - [ ] 5.5 Escrever testes unitários para restauração
    - Teste: restaurar versão inválida retorna 404
    - Teste: restaurar versão de outro projeto retorna 404
    - Teste: usuário sem permissão retorna 403
    - Teste: backup é criado antes de restaurar
    - _Requirements: 4.1_

  - [ ] 5.6 Implementar UI de restauração de versão
    - Atualizar função `renderVersionHistory()` para incluir botão "Restaurar"
    - Criar função `restoreVersion()` com confirmação
    - Recarregar dados do projeto após restauração bem-sucedida
    - Exibir toast de sucesso/erro
    - _Requirements: 4.5_

- [ ] 6. Implementar proteção de dados sensíveis
  - [ ] 6.1 Atualizar UserResponse schema para excluir hashed_password
    - Modificar UserResponse em schemas/user.py
    - Usar Config.fields para excluir hashed_password
    - Criar método from_orm customizado que nunca inclui hashed_password
    - _Requirements: 5.1_

  - [ ] 6.2 Atualizar todos os endpoints que retornam dados de usuário
    - Atualizar GET /auth/me para usar UserResponse
    - Atualizar GET /users para usar List[UserResponse]
    - Atualizar GET /users/{id} para usar UserResponse
    - Verificar que nenhum endpoint retorna hashed_password
    - _Requirements: 5.2, 5.3_

  - [ ] 6.3 Escrever teste de segurança para proteção de senha
    - **Property 17: Password Hash Exclusion from All Endpoints**
    - **Validates: Requirements 5.1, 5.2, 5.3**
    - Testar todos os endpoints que retornam dados de usuário
    - Verificar que "hashed_password" nunca aparece na resposta

- [ ] 7. Melhorar histórico de auditoria
  - [ ] 7.1 Padronizar formatação de datas no backend
    - Atualizar AuditLogResponse em schemas/log.py
    - Adicionar json_encoders para datetime (formato ISO)
    - Garantir que todas as datas são retornadas em formato consistente
    - _Requirements: 6.1_

  - [ ] 7.2 Escrever teste de propriedade para formatação de datas
    - **Property 18: Consistent Date Formatting**
    - **Validates: Requirements 6.1**

  - [ ] 7.3 Implementar formatação de datas no frontend
    - Criar função `formatDate()` em script.js
    - Parsear ISO string e formatar para DD/MM/YYYY HH:mm
    - Tratar erros de formatação sem quebrar interface
    - Aplicar formatação em todas as telas de auditoria
    - _Requirements: 6.2, 6.4_

  - [ ] 7.4 Remover dados mock do frontend
    - Identificar e remover todos os dados mock em telas de auditoria
    - Garantir que apenas dados reais do banco são exibidos
    - _Requirements: 6.3_

  - [ ] 7.5 Garantir log de operações críticas
    - Verificar que todas as operações críticas chamam log_action()
    - Adicionar logs faltantes se necessário
    - _Requirements: 6.5_

- [ ] 8. Checkpoint - Validar funcionalidades essenciais
  - Testar restauração de versões com backup automático
  - Verificar que hashed_password não é exposto em nenhum endpoint
  - Validar formatação consistente de datas
  - Executar todos os testes de propriedade do Grupo 2
  - Garantir que todos os testes passam antes de prosseguir


### GRUPO 3 - MÉDIO: Melhorias de UX e Performance

- [ ] 9. Implementar sistema unificado de feedback
  - [ ] 9.1 Criar componente de toast
    - Criar `components/toast.js` com classe ToastManager
    - Implementar métodos show(), getIcon()
    - Criar container de toasts no DOM
    - Adicionar auto-remoção após duração configurável
    - _Requirements: 7.2, 7.3_

  - [ ] 9.2 Criar componente de loading
    - Criar `components/loading.js` com classe LoadingManager
    - Implementar contador para múltiplas operações simultâneas
    - Criar overlay de loading no DOM
    - Implementar métodos show() e hide()
    - _Requirements: 7.1_

  - [ ] 9.3 Escrever testes unitários para componentes de feedback
    - Teste: toast é exibido e removido automaticamente
    - Teste: loading overlay é exibido e ocultado corretamente
    - Teste: múltiplas operações de loading são tratadas

  - [ ] 9.4 Atualizar api.js com tratamento de erros melhorado
    - Adicionar tratamento específico para erro de rede
    - Adicionar tratamento para timeout
    - Adicionar verificação de modo manutenção (503)
    - Retornar mensagens de erro descritivas
    - _Requirements: 7.4, 7.6_

  - [ ] 9.5 Integrar sistema de feedback em todas as páginas
    - Adicionar imports de toast.js e loading.js em todas as páginas HTML
    - Substituir alerts por showToast()
    - Adicionar showLoading()/hideLoading() em todas as operações assíncronas
    - Garantir consistência em admin-*.html, pesquisador-*.html, bolsista-*.html
    - _Requirements: 7.5_

- [ ] 10. Implementar geração de relatórios PDF
  - [ ] 10.1 Criar utilitário de geração de PDF
    - Criar `utils/pdf.py` com função generate_project_pdf()
    - Usar reportlab para criar PDF estruturado
    - Incluir: título, descrição, datas, responsáveis, status
    - Incluir tabela de histórico de versões
    - _Requirements: 8.1, 8.2_

  - [ ] 10.2 Escrever testes de propriedade para geração de PDF
    - **Property 24: PDF Content Completeness**
    - **Validates: Requirements 8.1, 8.2**

  - [ ] 10.3 Criar endpoint de geração de relatório
    - Criar GET /reports/project/{project_id}/pdf em routers/reports.py
    - Validar permissões do usuário
    - Gerar PDF usando generate_project_pdf()
    - Retornar StreamingResponse com nome descritivo
    - Adicionar log de auditoria
    - Tratar erros com mensagens descritivas
    - _Requirements: 8.3, 8.5, 8.6_

  - [ ] 10.4 Escrever testes unitários para relatórios
    - Teste: PDF é gerado com todos os campos
    - Teste: nome do arquivo é descritivo
    - Teste: erro de geração retorna 500 com mensagem
    - Teste: log de auditoria é criado

  - [ ] 10.5 Implementar botão de geração de PDF no frontend
    - Adicionar botão "Gerar PDF" em pesquisador-projeto-detalhes.html
    - Criar função `generateProjectPDF()` em script.js
    - Iniciar download automático do PDF
    - Exibir loading durante geração
    - Exibir toast de sucesso/erro
    - _Requirements: 8.4_

- [ ] 11. Implementar notificações em massa
  - [ ] 11.1 Criar schema de notificação em lote
    - Criar BatchNotificationRequest em schemas/notification.py
    - Validar máximo de 100 usuários por lote
    - _Requirements: 9.1_

  - [ ] 11.2 Implementar endpoint de notificação em lote
    - Criar POST /notifications/batch em routers/notifications.py
    - Processar em transação única
    - Contar sucessos e falhas
    - Retornar resumo com total, success, failed, failed_users
    - Adicionar log de auditoria com detalhes
    - _Requirements: 9.1, 9.4, 9.6_

  - [ ] 11.3 Escrever testes de propriedade para notificações em lote
    - **Property 28: Batch Notification Processing**
    - **Validates: Requirements 9.1**
    - **Property 29: Batch Notification Summary**
    - **Validates: Requirements 9.4**

  - [ ] 11.4 Escrever teste de performance para notificações
    - Teste: 100 notificações completam em menos de 5 segundos
    - Validar que processamento é eficiente

  - [ ] 11.5 Atualizar UI de notificações em massa
    - Atualizar função `sendBatchNotifications()` em admin-notificacoes.html
    - Exibir loading durante processamento
    - Exibir resultado com contadores de sucesso/falha
    - Mostrar toast com resumo
    - _Requirements: 9.3, 9.6_

- [ ] 12. Implementar modo manutenção
  - [ ] 12.1 Criar middleware de modo manutenção
    - Criar função `maintenance_middleware()` em main.py
    - Verificar SystemConfig.maintenance_mode
    - Retornar 503 se modo ativado (exceto endpoints de admin/maintenance)
    - Adicionar middleware à aplicação FastAPI
    - _Requirements: 10.1_

  - [ ] 12.2 Escrever testes de propriedade para modo manutenção
    - **Property 30: Maintenance Mode HTTP Status**
    - **Validates: Requirements 10.1**
    - **Property 32: Maintenance Mode Round Trip**
    - **Validates: Requirements 10.5**

  - [ ] 12.3 Criar endpoints de controle de modo manutenção
    - Criar POST /admin/maintenance em routers/admin.py
    - Criar GET /admin/maintenance para verificar status
    - Adicionar log de auditoria ao ativar/desativar
    - _Requirements: 10.1_

  - [ ] 12.4 Implementar verificação periódica no frontend
    - Criar função `startMaintenanceCheck()` em script.js
    - Verificar status a cada 30 segundos
    - Chamar `handleMaintenanceMode()` se detectado
    - Iniciar verificação ao carregar página se usuário logado
    - _Requirements: 10.2_

  - [ ] 12.5 Escrever testes de propriedade para verificação periódica
    - **Property 31: Maintenance Mode Periodic Check**
    - **Validates: Requirements 10.2**

  - [ ] 12.6 Implementar redirecionamento para página de manutenção
    - Criar função `handleMaintenanceMode()` em script.js
    - Fazer logout automático
    - Redirecionar para /maintenance.html
    - _Requirements: 10.3, 10.6_

  - [ ] 12.7 Escrever teste de propriedade para logout automático
    - **Property 33: Maintenance Mode Logout**
    - **Validates: Requirements 10.6**

  - [ ] 12.8 Criar página de manutenção
    - Criar maintenance.html com mensagem informativa
    - Adicionar botão "Tentar Novamente"
    - Implementar função `checkAndRedirect()` para verificar se manutenção terminou
    - _Requirements: 10.4_

- [ ] 13. Checkpoint final - Validar todas as correções
  - Testar sistema de feedback em todas as páginas
  - Gerar relatórios PDF de projetos
  - Enviar notificações em lote
  - Ativar e desativar modo manutenção
  - Executar todos os testes de propriedade do Grupo 3
  - Executar suite completa de testes (unitários + propriedades)
  - Validar cobertura de testes (mínimo 80% backend, 70% frontend)
  - Garantir que todos os testes passam

### GRUPO 4 - Integração e Documentação

- [ ] 14. Testes de integração end-to-end
  - [ ] 14.1 Escrever teste de integração: fluxo completo de criação de usuário
    - Admin cria usuário → Senha gerada → Modal exibido → Email enviado (se configurado)

  - [ ] 14.2 Escrever teste de integração: fluxo completo de primeiro login
    - Login → Flag detectada → Modal obrigatório → Senha trocada → Navegação liberada

  - [ ] 14.3 Escrever teste de integração: fluxo completo de upload e download
    - Upload → Metadados salvos → Link exibido → Download → Conteúdo idêntico

  - [ ] 14.4 Escrever teste de integração: fluxo completo de restauração
    - Versão selecionada → Backup criado → Dados restaurados → Auditoria → UI atualizada

- [ ] 15. Adicionar migrations de banco de dados
  - [ ] 15.1 Criar migration para tabela files
    - Adicionar tabela files com todos os campos
    - Adicionar índices em uuid e project_id
    - Adicionar foreign keys

  - [ ] 15.2 Criar migration para campo requires_password_change
    - Adicionar coluna requires_password_change em users
    - Atualizar usuários existentes com valor false

  - [ ] 15.3 Testar migrations em ambiente de desenvolvimento
    - Executar migrations
    - Verificar que schema está correto
    - Testar rollback se necessário

- [ ] 16. Atualizar documentação
  - [ ] 16.1 Documentar novos endpoints na API
    - Documentar GET /files/{file_uuid}
    - Documentar POST /projects/{id}/restore/{version_id}
    - Documentar POST /notifications/batch
    - Documentar GET /reports/project/{id}/pdf
    - Documentar POST /admin/maintenance e GET /admin/maintenance

  - [ ] 16.2 Criar guia de uso para administradores
    - Como criar usuários e gerenciar senhas temporárias
    - Como ativar modo manutenção
    - Como enviar notificações em massa

  - [ ] 16.3 Atualizar README com novas funcionalidades
    - Listar todas as correções implementadas
    - Adicionar instruções de configuração de email (opcional)
    - Adicionar instruções para executar testes

## Notes

- Todas as tarefas são obrigatórias para garantir cobertura completa de testes
- Cada task referencia requisitos específicos para rastreabilidade
- Checkpoints garantem validação incremental
- Testes de propriedade validam correção universal (mínimo 100 iterações cada)
- Testes unitários validam exemplos específicos e casos extremos
- Priorização garante que problemas críticos são resolvidos primeiro
- Meta de cobertura: 80% backend, 70% frontend
