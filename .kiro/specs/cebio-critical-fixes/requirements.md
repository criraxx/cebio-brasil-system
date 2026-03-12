# Requirements Document

## Introduction

Este documento especifica os requisitos para correção de falhas críticas identificadas na auditoria técnica do sistema CEBIO Brasil. O sistema é uma plataforma de gestão de projetos de bioinsumos que apresenta problemas graves de usabilidade e segurança que impedem operações essenciais como download de arquivos, gestão de senhas e restauração de versões.

As correções são priorizadas por criticidade e impacto no funcionamento do sistema, focando primeiro em problemas que bloqueiam completamente funcionalidades essenciais.

## Glossary

- **Sistema**: O sistema CEBIO Brasil completo (backend FastAPI + frontend HTML/JS)
- **Backend**: API FastAPI com SQLAlchemy e MySQL/TiDB
- **Frontend**: Interface HTML/JS estática
- **Admin**: Usuário com role de administrador
- **Pesquisador**: Usuário com role de pesquisador
- **Bolsista**: Usuário com role de bolsista
- **Arquivo_Anexado**: Foto ou PDF enviado por usuário e armazenado com UUID
- **Senha_Temporária**: Senha gerada automaticamente pelo sistema ao criar usuário
- **Versão_Projeto**: Snapshot histórico de um projeto armazenado no banco
- **Hash_Senha**: Senha criptografada armazenada no banco de dados
- **Toast**: Notificação visual temporária na interface do usuário
- **Modo_Manutenção**: Estado do sistema que bloqueia acesso de usuários

## Requirements

### Requirement 1: Download de Arquivos

**User Story:** Como usuário do sistema, eu quero fazer download dos arquivos que enviei, para que eu possa acessar e compartilhar os documentos e fotos dos projetos.

#### Acceptance Criteria

1. WHEN um arquivo é enviado ao sistema, THE Backend SHALL armazenar o arquivo com UUID e metadados (nome original, tipo MIME, tamanho)
2. WHEN um usuário autenticado solicita download de um arquivo, THE Backend SHALL validar permissões e retornar o arquivo com nome original
3. IF um usuário sem permissão tenta baixar um arquivo, THEN THE Backend SHALL retornar erro 403
4. WHEN um arquivo não existe, THE Backend SHALL retornar erro 404
5. THE Frontend SHALL exibir links de download para todos os arquivos anexados em projetos
6. WHEN um usuário clica em link de download, THE Frontend SHALL iniciar o download do arquivo com nome original

### Requirement 2: Gestão de Senhas Temporárias

**User Story:** Como administrador, eu quero visualizar a senha temporária ao criar um usuário, para que eu possa comunicá-la ao novo usuário de forma segura.

#### Acceptance Criteria

1. WHEN um Admin cria um novo usuário, THE Sistema SHALL gerar uma senha temporária aleatória
2. WHEN a senha temporária é gerada, THE Backend SHALL retornar a senha em texto plano na resposta de criação
3. THE Backend SHALL marcar o usuário com flag requires_password_change=true
4. WHEN o Admin recebe a resposta de criação, THE Frontend SHALL exibir a senha temporária em modal com opção de copiar
5. THE Frontend SHALL alertar o Admin que a senha não será exibida novamente
6. WHERE notificação por email está configurada, THE Sistema SHALL enviar a senha temporária por email ao novo usuário

### Requirement 3: Troca de Senha

**User Story:** Como usuário com senha temporária, eu quero trocar minha senha no primeiro login, para que eu possa usar uma senha segura de minha escolha.

#### Acceptance Criteria

1. WHEN um usuário com requires_password_change=true faz login, THE Backend SHALL incluir flag requires_password_change na resposta
2. WHEN o Frontend detecta requires_password_change=true, THE Sistema SHALL exibir modal de troca de senha obrigatória
3. THE Frontend SHALL impedir navegação até que a senha seja trocada
4. WHEN o usuário submete nova senha, THE Backend SHALL validar força da senha (mínimo 8 caracteres, letras e números)
5. WHEN a senha é trocada com sucesso, THE Backend SHALL atualizar requires_password_change=false
6. THE Backend SHALL registrar a troca de senha no log de auditoria

### Requirement 4: Restauração de Versões

**User Story:** Como pesquisador, eu quero restaurar uma versão anterior de um projeto, para que eu possa reverter alterações indesejadas.

#### Acceptance Criteria

1. WHEN um usuário solicita restauração de versão, THE Backend SHALL validar que a versão existe e pertence ao projeto
2. WHEN a restauração é autorizada, THE Backend SHALL criar nova versão com dados atuais antes de restaurar
3. THE Backend SHALL copiar dados da versão histórica para o projeto atual
4. THE Backend SHALL preservar metadados de auditoria (quem restaurou, quando, qual versão)
5. WHEN a restauração é concluída, THE Frontend SHALL recarregar dados do projeto e exibir confirmação
6. THE Backend SHALL registrar a operação de restauração no log de auditoria

### Requirement 5: Proteção de Dados Sensíveis

**User Story:** Como administrador de segurança, eu quero garantir que hashes de senha nunca sejam expostos, para que a segurança das contas seja mantida.

#### Acceptance Criteria

1. THE Backend SHALL excluir campo hashed_password de todos os schemas de resposta
2. WHEN o endpoint /auth/me é chamado, THE Backend SHALL retornar dados do usuário sem hashed_password
3. WHEN listagem de usuários é solicitada, THE Backend SHALL retornar dados sem hashed_password
4. THE Backend SHALL validar que nenhum endpoint retorna hashed_password em logs ou respostas
5. WHERE serialização de User model ocorre, THE Sistema SHALL usar schema que exclui hashed_password

### Requirement 6: Histórico de Auditoria Consistente

**User Story:** Como auditor, eu quero visualizar histórico preciso de todas as operações, para que eu possa rastrear mudanças e identificar problemas.

#### Acceptance Criteria

1. WHEN dados de auditoria são retornados, THE Backend SHALL formatar datas ISO em formato consistente
2. THE Frontend SHALL parsear e exibir datas em formato local (DD/MM/YYYY HH:mm)
3. THE Frontend SHALL remover dados mock e usar apenas dados reais do banco
4. WHEN erro de formatação ocorre, THE Frontend SHALL exibir data original sem quebrar a interface
5. THE Sistema SHALL registrar todas as operações críticas (criação, edição, exclusão, restauração)

### Requirement 7: Feedback de Operações

**User Story:** Como usuário, eu quero receber feedback claro sobre o resultado de minhas ações, para que eu saiba se operações foram concluídas com sucesso ou falharam.

#### Acceptance Criteria

1. WHEN uma operação é iniciada, THE Frontend SHALL exibir indicador de loading
2. WHEN uma operação é concluída com sucesso, THE Frontend SHALL exibir toast de sucesso com mensagem descritiva
3. IF uma operação falha, THEN THE Frontend SHALL exibir toast de erro com mensagem do backend
4. WHEN erro de rede ocorre, THE Frontend SHALL exibir mensagem específica de falha de conexão
5. THE Frontend SHALL usar sistema de toast consistente em todas as páginas
6. WHEN timeout ocorre, THE Frontend SHALL informar o usuário e sugerir tentar novamente

### Requirement 8: Geração de Relatórios PDF

**User Story:** Como pesquisador, eu quero gerar relatórios em PDF dos projetos, para que eu possa compartilhar informações formatadas.

#### Acceptance Criteria

1. WHEN um usuário solicita relatório PDF, THE Backend SHALL gerar PDF com dados completos do projeto
2. THE Backend SHALL incluir no PDF: título, descrição, datas, responsáveis, status e histórico
3. WHEN o PDF é gerado, THE Backend SHALL retornar arquivo com nome descritivo
4. THE Frontend SHALL iniciar download automático do PDF gerado
5. IF geração falha, THEN THE Backend SHALL retornar erro descritivo
6. THE Backend SHALL registrar geração de relatórios no log de auditoria

### Requirement 9: Notificações em Massa

**User Story:** Como administrador, eu quero enviar notificações para múltiplos usuários simultaneamente, para que operações em lote sejam eficientes.

#### Acceptance Criteria

1. WHEN Admin envia notificação para múltiplos usuários, THE Backend SHALL processar em lote (batch)
2. THE Backend SHALL usar transação única para criar todas as notificações
3. WHEN processamento em lote é iniciado, THE Frontend SHALL exibir progresso
4. THE Backend SHALL retornar resumo: total enviado, sucessos, falhas
5. WHEN timeout pode ocorrer, THE Backend SHALL processar de forma assíncrona
6. THE Frontend SHALL exibir resultado final com contadores de sucesso/falha

### Requirement 10: Modo Manutenção

**User Story:** Como administrador de sistema, eu quero que usuários sejam redirecionados quando modo manutenção é ativado, para que eles não tentem usar o sistema durante manutenção.

#### Acceptance Criteria

1. WHEN modo manutenção é ativado, THE Backend SHALL retornar status 503 para requisições
2. THE Frontend SHALL verificar modo manutenção periodicamente
3. WHEN modo manutenção é detectado, THE Frontend SHALL redirecionar para página de manutenção
4. THE Frontend SHALL exibir mensagem informativa sobre manutenção
5. WHEN modo manutenção é desativado, THE Frontend SHALL permitir acesso normal
6. WHERE usuário está logado, THE Frontend SHALL fazer logout automático ao detectar modo manutenção
