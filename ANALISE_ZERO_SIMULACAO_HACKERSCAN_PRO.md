# Análise Completa do Projeto HackScan Pro

Data da análise: 2026-04-17

## Regra aplicada

Esta análise segue a regra principal pedida: **Zero simulação**.

Isso significa que:

- Tudo o que está descrito abaixo foi verificado no código real do projeto.
- Eu só considerei como "existente" o que encontrei em `apps/api`, `apps/web`, `docker-compose.yml`, `README.md` e documentação local.
- Onde há proposta de melhoria, ela está marcada como recomendação, não como funcionalidade já implementada.
- Onde não encontrei evidência no código, registrei como **não implementado** ou **não comprovado**.

## Como a análise foi feita

Foram inspecionados:

- Estrutura do monorepo
- Backend Django/DRF/Celery/Channels
- Frontend Next.js 15
- Estratégias de scan
- Billing/Stripe
- Relatórios
- IA
- Notificações
- WebSockets
- Docker/infra
- Testes existentes
- Documentação do produto

Também foram executadas validações reais:

- `python manage.py check`
- `npm run build`

Resultado dessas validações:

- `manage.py check` falha ao subir o projeto por causa do import de `WeasyPrint` dentro de `reports`, com erro de biblioteca nativa ausente (`libgobject-2.0-0`).
- `npm run build` falha no frontend em `apps/web/app/dashboard/scans/[id]/page.tsx` por incompatibilidade de tipagem com Next.js 15.
- `pytest` não foi concluído com segurança porque o backend já falha no bootstrap/import da aplicação.

## Resumo executivo

O projeto tem uma base técnica interessante e um posicionamento comercial forte no papel, mas **não está pronto para produção, venda séria nem escala real**.

Hoje ele é, na prática:

- Um MVP parcial de scanner SaaS com autenticação, scans, billing, relatórios, IA e dashboard.
- Com várias partes importantes desacopladas entre si.
- Com divergência entre o que a documentação promete e o que realmente está operacional.
- Com alguns pontos que quebram o fluxo principal do produto.

### Estado atual em uma frase

**Há arquitetura de produto, mas ainda não há coerência operacional de ponta a ponta.**

## O que existe de verdade hoje

### Backend

Existe código real para:

- Utilizadores, login, refresh, 2FA e API keys
- Workspaces e memberships
- Targets e scans
- Estratégias de scan locais e externas
- Billing com Stripe
- Relatórios PDF/JSON/CSV
- IA para explicação e remediação
- Notificações por email/webhook e WebSocket
- Métricas Prometheus
- Celery e Channels

### Frontend

Existe interface real para:

- Login
- Registo
- Dashboard
- Lista de scans
- Detalhe de scan
- Billing plans
- Billing usage
- Settings

### O que a documentação promete, mas não foi encontrado implementado

A documentação e o README posicionam o produto como:

- Plataforma com **IA preditiva**
- **Bug Bounty**
- **Marketplace**
- Modelo híbrido B2B + B2C
- Escala enterprise

No código inspecionado, **não encontrei**:

- App `bounty`
- App `marketplace`
- Rotas/frontend de bug bounty
- Rotas/frontend de marketplace
- SDK público de marketplace
- Fluxo operacional de payout para bounty
- Gestão real de módulos externos instaláveis por clientes

Conclusão objetiva: **o posicionamento comercial está mais avançado que o produto entregue**.

## Bloqueadores críticos

Estes são os pontos que impedem o projeto de ser considerado pronto:

1. O backend falha no bootstrap por dependência de relatórios.
2. O build do frontend falha.
3. O fluxo principal de criação de scan está desalinhado entre serializer, view, service e task.
4. Várias estratégias de scan usam atributos que não existem no modelo.
5. O fluxo de relatórios está quebrado entre backend e frontend.
6. O sistema de notificações foi modelado, mas o fluxo real acionado pelo scan ainda aponta para uma task placeholder.
7. O produto promete multi-workspace/team, mas a autorização real é majoritariamente por `owner`.

## Análise por módulo

## 1. Users/Auth

### Estado

É a parte mais avançada do backend, mas ainda com inconsistências importantes.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/users/auth_flow.py` -> `UserRegistrationSchema` | Password mínima é 8 caracteres, enquanto o frontend exige 12 + uppercase + número + caractere especial. | Unificar a política de password no backend e frontend. O backend deve ser a fonte da regra. |
| `apps/api/users/views.py` -> `AuthLogoutView.post` | Logout não revoga token nenhum. Apenas devolve `204`. | Implementar revogação real de refresh token e blacklist/rotação. |
| `apps/api/users/views.py` -> `AuthRefreshView.post` | Refresh gera novos tokens sem consultar `RefreshToken`, sem revogação e sem rotação persistida. | Usar o modelo `RefreshToken` de verdade, com hash, expiração, revogação e rotação auditável. |
| `apps/api/users/services.py` -> `TwoFactorService.verify_and_enable` | Gera backup codes, mas não persiste esses códigos em lado nenhum. | Guardar backup codes hashados e permitir consumo unitário. |
| `apps/api/users/services.py` -> `TwoFactorService.disable` | Se o utilizador tiver 2FA ativo e não enviar `code`, a função desativa 2FA apenas com password. | Exigir sempre TOTP válido ou backup code válido quando 2FA estiver ativo. |
| `apps/api/users/models.py` -> `RefreshToken` | O modelo existe, mas o fluxo real não o utiliza. | Integrar este modelo no login, refresh e logout. |
| `apps/api/users/models.py` -> `APIKey` | A modelagem existe, mas não há authentication backend por API key. | Adicionar autenticação por API key com escopos e auditoria de uso. |
| `apps/api/users/models.py` -> `User` | Não há `PermissionsMixin`, `is_staff`, `admin.py` nem backoffice Django configurado. | Criar backoffice mínimo para operação e suporte, ou remover a ambição de administração interna até existir. |
| `apps/api/config/settings/base.py` + `apps/api/users/auth_flow.py` | Há duas abordagens de JWT: `SIMPLE_JWT` em settings e `AuthServiceFlow` custom. A configuração `SIMPLE_JWT` não governa o fluxo real. | Escolher um único sistema de JWT. Hoje há drift arquitetural. |

### Impacto de negócio

- Sessões frágeis
- Segurança incompleta
- Operação sem backoffice
- API keys vendáveis no marketing, mas ainda não utilizáveis como acesso real

## 2. Workspaces e autorização

### Estado

O produto fala em workspaces, team e enterprise, mas o controle real ainda está muito centrado em `owner`.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/core/permissions.py` -> `WorkspacePermission` | Existe, mas quase não é usada nas views centrais. | Aplicar autorização workspace-scoped nas views de scans, billing, relatórios, IA e notificações. |
| `apps/api/scans/services.py` -> `ScanTargetService.get_or_404` | Filtra por `owner=user`, não por membership do workspace. | Permitir acesso por membership com papel adequado. |
| `apps/api/scans/services.py` -> `ScanService.get_or_404` | Também filtra por `target__owner=user`. | Mudar para acesso por workspace membership. |
| `apps/api/billing/views.py` -> `_get_workspace` | Pega apenas o primeiro workspace do owner. O comentário diz “owns or belongs to”, mas o código não cumpre isso. | Permitir seleção explícita de workspace e respeitar memberships. |
| `apps/api/websockets/consumers.py` -> `ScanConsumer.has_scan_access` | A verificação ainda é simplificada por owner. | Passar a validar membership e permissões do workspace. |

### Impacto de negócio

- Produto não serve de verdade para equipas
- Plano Team/Enterprise perde valor
- Compartilhamento operacional fica quebrado

## 3. Scans

### Estado

Este é o coração do produto. Também é onde estão os problemas mais graves de integração.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/scans/views.py` -> `ScanTargetListCreateView.post` | Cria/obtém `Workspace` usando apenas `owner=request.user` e sem `slug`, embora `Workspace.slug` seja obrigatório e único. | Criar target dentro de workspace explícito e válido, com slug garantido. |
| `apps/api/scans/serializers.py` -> `ScanCreateSerializer` | A API recebe `plugin_ids`. | Definir claramente se scan é por `scan_type`, por `plugin_ids`, ou ambos. Hoje está inconsistente. |
| `apps/api/scans/views.py` -> `_ScanCreateBase.create` | Chama `ScanService.create(... plugin_ids=...)`. | Alinhar a assinatura com o service real. |
| `apps/api/scans/services.py` -> `ScanService.create` | Espera `scan_type`, não `plugin_ids`. Além disso não grava `plugin_ids` no modelo. | Implementar contrato único: ou criar scans por tipo, ou por lista de plugins, com persistência correta. |
| `apps/api/scans/tasks.py` -> `run_scan` | Ignora `scan.plugin_ids` e usa apenas mapa fixo por `scan.scan_type`. | Respeitar o pedido real do utilizador e o que foi persistido. |
| `apps/api/scans/services.py` -> `ScanService.quick_scan` | Bypassa o controlo de quota/monetização. | Aplicar quota também no quick scan. |
| `apps/api/scans/services.py` -> `broadcast_scan_update` | Payload envia `scan_id`, mas o helper frontend `useScanWebSocket` procura `payload.id`. | Normalizar contrato do websocket. |
| `apps/api/scans/tasks.py` -> `notify_scan_complete` | É apenas placeholder e é esta task que o scan runner chama. | Parar de chamar placeholder local e disparar a task real de `notifications`. |
| `apps/api/scans/tests/test_services.py` | Os testes chamam `ScanService.create(... plugin_ids=...)`, mas o service atual já não aceita isso. | Atualizar testes e implementação para o mesmo contrato. |

### Impacto de negócio

- Fluxo principal de criação/execução de scans não está estável
- Produto perde confiança logo na função principal
- Difícil vender algo cujo core workflow pode quebrar

## 4. Estratégias de scan

### Estado

Há boas ideias e diversidade de scanners, mas várias estratégias não estão coerentes com o modelo real.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/scans/strategies/nuclei_scan.py` -> `NucleiVulnStrategy._run_nuclei` | Usa `target.address`, mas `ScanTarget` só possui `host`. | Padronizar todas as estratégias para usar a mesma interface de target. |
| `apps/api/scans/strategies/nuclei_scan.py` -> `NucleiFullStrategy.run` | Herda o mesmo problema de `target.address`. | Corrigir o input do target e validar output persistível. |
| `apps/api/scans/strategies/subdomain_recon.py` -> `SubdomainReconStrategy.run` | Usa `target.address`, inexistente. | Usar `target.host`. |
| `apps/api/scans/strategies/sslyze_audit.py` -> `SSLyzeAuditStrategy.run` | Usa `target.address` e contém parsing incompleto com `pass`. | Implementar parsing real dos resultados do SSLyze e findings estruturados. |
| `apps/api/scans/strategies/dir_fuzzing.py` -> `DirFuzzingStrategy.run` | Usa `target.address`, e ainda contém caminho absoluto da máquina local `c:/Users/HP/...`. | Tornar o wordlist path portátil e derivado do projeto/container. |
| `apps/api/scans/strategies/resource_discovery.py` -> `ResourceDiscoveryStrategy.run` | Usa `target.address`, cria uma variável `comments`, mas não transforma isso em findings úteis; devolve quase sempre um resultado genérico. | Produzir findings reais, estruturados e auditáveis. |
| `apps/api/scans/strategies/ssl_check.py` -> `SSLCheckStrategy.run` | Quando falha parsing do certificado, apenas faz `pass`. | Registrar finding explícito ou erro técnico rastreável. |
| `apps/api/scans/strategies/port_scan.py` -> `PortScanStrategy.run` | Esta é uma das mais sólidas do projeto. | Manter como referência de padrão para as outras estratégias. |
| `apps/api/scans/strategies/headers_check.py` -> `HeadersCheckStrategy.run` | Também está melhor estruturada que várias outras. | Usar como base de qualidade para padronizar logs, findings e evidências. |

### Impacto de negócio

- O motor de scan fica inconsistente
- Parte das features vendidas não gera valor real
- Resultados podem ser pobres, genéricos ou quebrados

## 5. Billing e monetização

### Estado

O módulo de billing é promissor, mas há bugs reais e alguns desalinhamentos com o frontend.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/billing/services.py` -> `BillingService.check_quota` | Se não existir subscription, devolve `False, "No active subscription."`, mesmo com conceito de plano free no sistema. | Tratar plano free como assinatura base funcional, não como bloqueio total. |
| `apps/api/billing/services.py` -> `BillingService.check_quota` | No caso `create_target`, importa `from scans.models import Target`, mas o modelo real chama-se `ScanTarget`. | Corrigir o import e a contagem real de targets. |
| `apps/api/billing/views.py` -> `_get_workspace` | Não suporta membership nem seleção de workspace. | Tornar billing workspace-aware. |
| `apps/api/billing/services.py` | Não há deduplicação explícita por `event.id` de webhook. | Persistir eventos Stripe processados, principalmente para emails e side effects. |
| `apps/web/app/dashboard/billing/plans/page.tsx` | Frontend envia `billing_cycle` como `MONTHLY`/`YEARLY`, mas backend aceita `monthly`/`yearly`. | Padronizar enum compartilhado entre frontend e backend. |
| `apps/web/lib/api.ts` -> `Plan` | Interface espera `description` e `stripe_price_id_*`, mas `PlanSerializer` não entrega isso. | Alinhar contrato da API com o que a UI usa. |
| `apps/web/app/dashboard/billing/plans/page.tsx` | Regras visuais usam `plan.name === 'Pro'` e `plan.name === 'Free'`; no backend o naming é orientado a `free`, `pro`, etc. | Padronizar naming e casing. |
| `apps/web/app/dashboard/billing/usage/page.tsx` | A própria página admite simulação: usa `api_calls_count` como proxy de hosts e `findings_count * 10` como token usage. | Exibir métricas reais ou esconder a feature até existir backend correspondente. |

### Impacto de negócio

- Monotização não fica confiável
- Quotas podem bloquear utilizadores errados ou ser contornadas
- Checkout pode falhar por mismatch simples
- A página de usage quebra a regra de “zero simulação”

## 6. Reports

### Estado

É um módulo estrategicamente importante para venda B2B, mas hoje é um dos mais frágeis.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/reports/generators/pdf.py` importado por `reports/tasks.py` | O import de `WeasyPrint` impede o bootstrap atual do projeto nesta máquina. | Isolar dependência pesada, fazer import lazy ou feature flag para não derrubar toda a API. |
| `apps/api/reports/views.py` -> `ReportCreateView.post` | Faz `get_object_or_404(Scan, id=scan_id)` sem validar ownership/workspace. | Restringir por acesso do utilizador ao scan. |
| `apps/api/reports/views.py` -> `ReportDetailView.get` | Busca report por ID sem validar ownership/workspace. | Restringir acesso ao dono/membro autorizado. |
| `apps/api/reports/tasks.py` -> `generate_scan_report` | Usa campos inexistentes: `finding.payload`, `finding.get_status_display()`, `scan.get_status_display()`, `scan.workspace`. | Reescrever o builder de dados com base nos modelos reais. |
| `apps/api/reports/tasks.py` | Faz geração de AI + relatório + upload num único fluxo sem isolamento suficiente. | Separar preparação de dados, enriquecimento IA e export. |
| `apps/api/core/services/storage.py` | `ensure_bucket_exists()` existe, mas não é chamada. | Garantir bucket antes do primeiro upload. |
| `apps/web/lib/api.ts` -> `generateReport` | Chama `POST /reports/`, mas a rota real criada no backend é `/v1/reports/scans/<scan_id>/report/`. | Corrigir endpoint e contrato. |
| `apps/web/lib/api.ts` -> `getReport` | Chama `/reports/${id}/`, mas a rota real está em `/v1/reports/reports/<report_id>/`. | Corrigir a rota ou simplificar o backend para `/v1/reports/<id>/`. |
| `apps/web/components/scans/ScanDetailContent.tsx` -> `handleExport` | O comentário assume polling mock; o frontend espera `id`, `status` e `file_url`, mas o create do backend devolve só `message` e `report_id`. | Criar contrato síncrono e consistente para criação + polling. |

### Impacto de negócio

- Relatórios, que seriam ativos fortes para venda B2B, hoje não são confiáveis
- O módulo ainda derruba o arranque do backend na validação atual

## 7. IA

### Estado

A camada de IA existe, mas ainda não entrega o que o posicionamento do produto promete.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/ai/views.py` -> `AIExplanationView.post` | Busca `Finding` apenas por ID, sem validar ownership/workspace. | Restringir acesso por scan/workspace. |
| `apps/api/ai/views.py` -> `AIRemediationView.post` | Mesmo problema de autorização. | Aplicar autorização workspace-scoped. |
| `apps/api/ai/services.py` -> `AIService.predict_attack_chains` | Existe no backend, mas não encontrei endpoint nem uso no frontend. | Expor como feature real no produto antes de vendê-la como diferencial. |
| `apps/api/ai/services.py` -> `MODEL_ID` | Modelo está hardcoded no código. | Parametrizar por ambiente e validar fallback operacional. |

### Impacto de negócio

- “IA preditiva” ainda não se traduz em feature consumível
- Valor comercial prometido > valor disponível no produto

## 8. Notifications

### Estado

Há base técnica boa, mas o produto ainda não fecha o ciclo.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/notifications/services.py` -> `NotificationService.notify_scan_completed` | Está pronta para uso, mas o runner de scan não a usa no fluxo real. | Integrar esta service/task ao final do scan. |
| `apps/api/notifications/models.py` -> `NotificationPreference` | Modelo existe, mas não encontrei endpoint/UI para o utilizador gerir preferências. | Criar CRUD de preferências com validação por canal. |
| `apps/api/notifications/views.py` -> `NotificationViewSet` | Backend expõe notificações, mas não encontrei interface frontend correspondente. | Criar centro de notificações no dashboard. |
| `apps/api/notifications/channels/email.py` e `webhook.py` | A base diz que canais não devem levantar exceção, mas os concretos fazem `raise` para retry. | Escolher um contrato único e documentá-lo corretamente. |

### Impacto de negócio

- Alertas não viram experiência completa de produto
- Menor retenção e menor valor percebido do plano pago

## 9. WebSockets e realtime

### Estado

A base existe, mas há desalinhamento de contrato com o frontend.

### Funções/classes que precisam ser melhoradas

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/web/hooks/useScanWebSocket.ts` | Filtra `data.payload.id`, mas o backend envia `scan_id`. | Unificar o payload do websocket. |
| `apps/web/components/TerminalOutput.tsx` | O indicador visual “LIVE” não depende de um estado reativo real de conexão. | Refletir o estado real da ligação. |
| `apps/api/websockets/consumers.py` -> `ScanConsumer.has_scan_access` | Continua owner-based. | Tornar workspace-based. |

## 10. Frontend

### Estado

O frontend tem presença e alguma identidade visual, mas ainda sofre com contratos quebrados, páginas parcialmente simuladas e links errados.

### Funções/componentes que precisam ser melhorados

| Arquivo / função | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/web/app/dashboard/scans/[id]/page.tsx` | O build falha em Next.js 15 por tipagem de `params`. | Corrigir assinatura da page conforme App Router atual. |
| `apps/web/app/dashboard/scans/page.tsx` | A tabela tenta ler `scan.target?.host`, mas o backend entrega `target_host`. | Usar o contrato real ou ajustar a API. |
| `apps/web/components/scans/ScanDetailContent.tsx` | Renderiza `f.evidence` diretamente dentro de `<pre>`. Se vier objeto JSON, isso quebra o React. | Serializar evidência com `JSON.stringify`. |
| `apps/web/components/scans/ScanDetailContent.tsx` | Espera `f.ai_insight`, mas o backend trabalha com `ai_explanation` e `ai_remediation`. | Alinhar naming dos campos. |
| `apps/web/app/dashboard/billing/usage/page.tsx` | Contém simulação explícita de métricas. | Trocar por métricas reais ou remover. |
| `apps/web/app/dashboard/settings/page.tsx` | Botão de gerar API key não está ligado ao backend. Notificações são toggles estáticos. | Conectar ações reais à API. |
| `apps/web/components/layout/Header.tsx` | Links apontam para `/billing/usage` e `/billing/plans`, mas as páginas existentes estão em `/dashboard/billing/...`. | Corrigir rotas internas. |
| `apps/web/app/dashboard/billing/usage/page.tsx` | CTA final também aponta para `/billing/plans`. | Corrigir para rota existente. |
| `apps/web/lib/api.ts` | Login guarda só `access`. `refresh` é descartado no cliente. | Implementar refresh automático de sessão. |

### Impacto de negócio

- Experiência de utilizador instável
- Algumas telas parecem prontas, mas não estão ligadas ao backend real
- Menor confiança, menor retenção, menor conversão

## 11. Infra, build e operação

### Estado

Existe esforço de containerização, mas ainda com drift e lacunas operacionais.

### Pontos que precisam ser melhorados

| Arquivo / área | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `docker-compose.yml` | Não existe serviço `web` para o frontend, embora o projeto tenha app Next.js. | Subir frontend no compose ou corrigir a documentação para separar responsabilidades. |
| `README.md` | O texto sugere stack mais integrada do que a compose realmente sobe. | Atualizar documentação para o estado real. |
| `apps/api/config/settings/base.py` + `docker-compose.yml` | Existe serviço RabbitMQ e dependência `pika`, mas Celery usa Redis como broker e backend. | Remover o que não é usado ou usar RabbitMQ de forma real. |
| `apps/api/Dockerfile` | `collectstatic` em produção pode ser impactado pelo bootstrap quebrado de `reports`. | Garantir que build de produção não dependa de módulos opcionais quebrados. |
| `apps/api/docker-entrypoint.sh` | Sempre roda migrations no start. | Em produção, separar bootstrap/migration de startup normal. |
| Segurança de settings | `SECRET_KEY`, Stripe e Anthropic têm defaults placeholder no código. | Tornar variáveis obrigatórias em produção e falhar cedo com mensagem clara. |

## 12. Testes e qualidade

### Estado

Encontrei testes apenas para:

- `users`
- `scans`
- `billing`

Não encontrei testes para:

- `reports`
- `ai`
- `notifications`
- `websockets`
- frontend

### Problemas confirmados

| Área | Problema confirmado | Como deve ser |
| --- | --- | --- |
| `apps/api/scans/tests` | Os testes ainda assumem contrato antigo por `plugin_ids`, enquanto a implementação atual usa `scan_type`. | Atualizar testes e código ao mesmo contrato. |
| `apps/api/reports` | Não há cobertura automatizada para o módulo que hoje bloqueia o bootstrap da aplicação. | Criar testes mínimos de import, geração, upload e autorização. |
| `apps/api/ai` | Não há testes para autorização nem para fallback do serviço. | Testar cache, fallback, autorização e sanitização. |
| `apps/api/notifications` | Não há testes para preferências, canais e task assíncrona. | Testar dispatch por canal e falhas por retry. |
| `apps/api/websockets` | Não há testes para auth WS nem autorização de scan/workspace. | Testar handshake, acesso negado e entrega de eventos. |
| `apps/web` | Não encontrei testes de componentes, integração ou build contract. | Adicionar pelo menos testes de páginas críticas e smoke tests de contratos da API. |

### Impacto de negócio

- Bugs de integração escapam com facilidade
- Módulos mais sensíveis ficam sem rede de segurança
- Cada evolução futura tende a aumentar o custo de manutenção

## Distância entre promessa e entrega

### Promessa atual encontrada na documentação

- Scanner automático enterprise
- IA preditiva
- Bug bounty integrado
- Marketplace de módulos
- Receita híbrida B2B + B2C
- Escala enterprise

### Entrega real observada

- Scanner base parcialmente implementado
- IA de explicação/remediação disponível no backend
- Billing inicial com Stripe
- Dashboard e páginas principais
- Sem bug bounty implementado
- Sem marketplace implementado
- Sem fluxo enterprise maduro
- Sem multi-workspace realmente consistente

### Conclusão

Hoje o projeto está **mais perto de um MVP técnico em consolidação** do que de uma plataforma completa e lucrativa pronta para mercado amplo.

## O que deve ser adicionado para virar um produto completo, viável, lucrativo e muito usado

## Prioridade 0: fazer o core funcionar sem falhar

Adicionar/ajustar imediatamente:

- Contrato único de criação de scan
- Correção de todas as estratégias que usam `target.address`
- Integração real de relatórios sem derrubar a aplicação
- Build verde no frontend
- Quota enforcement real no quick scan e no scan normal
- Autorização por workspace em scans, reports, IA e billing
- Refresh token real no cliente e no backend

Sem isso, o produto não é confiável para cobrança.

## Prioridade 1: tornar o produto vendável

Adicionar:

- Histórico e comparação entre scans do mesmo alvo
- Scans agendados
- Notificações configuráveis pelo cliente
- Centro de notificações no frontend
- Página real de relatórios com fila, status e download
- Gestão real de API keys
- Gestão de múltiplos workspaces
- Convites e colaboração entre membros
- Logs de auditoria acessíveis ao admin da conta

Isso transforma o produto de demo avançada em SaaS utilizável.

## Prioridade 2: tornar o produto lucrativo

Adicionar:

- Planos com limites reais e impossíveis de contornar
- Onboarding com plano free funcional e upsell claro
- Trials controlados
- Upgrade in-app sem fricção
- Métricas de uso reais por conta, não proxies
- Relatórios premium
- Scans contínuos premium
- API paga por volume
- White-label report para B2B
- Segmentação de planos por:
  - freelancer
  - agência
  - equipa de produto
  - SOC/MSP

## Prioridade 3: tornar o produto muito usado

Adicionar:

- Asset inventory por workspace
- Descoberta contínua de superfícies expostas
- Alertas úteis, não genéricos
- Score de risco por ativo
- Timeline de correção
- Export para Slack, Teams, Jira, webhook enterprise
- Templates de relatórios para compliance
- Experiência de onboarding em menos de 5 minutos
- Conteúdo educativo gerado a partir dos findings

## O que eu faria em ordem prática

### Fase 1

- Corrigir bootstrap do backend
- Corrigir build do frontend
- Corrigir contrato de scans
- Corrigir estratégias quebradas

### Fase 2

- Fechar quotas, billing e workspaces
- Fechar relatórios ponta a ponta
- Fechar notificações ponta a ponta

### Fase 3

- Melhorar retenção: agendamento, histórico, alertas, centro de notificações
- Melhorar monetização: trial, upgrade, premium reports, API paga

### Fase 4

- Só depois disso iniciar bug bounty e marketplace

Motivo:

- Bug bounty e marketplace são produtos por si só.
- Se entrarem agora, aumentam a complexidade antes do core gerar confiança e receita.

## Veredito final

### O projeto hoje

O HackScan Pro **tem potencial real**, mas ainda está numa fase em que:

- a narrativa comercial está à frente da execução
- o core scanner ainda precisa estabilizar
- billing e colaboração ainda não suportam bem o modelo Team/Enterprise
- relatórios e IA ainda não estão fechados como produto

### Nota objetiva

Se eu tivesse de classificar o estado atual:

- **Base técnica:** boa
- **Coerência entre módulos:** média para baixa
- **Prontidão para produção:** baixa
- **Prontidão para monetização séria:** baixa
- **Potencial de produto:** alto

## Conclusão curta

**Não falta ideia. Falta fechar o produto real.**

Se o objetivo é torná-lo completo, viável, lucrativo e muito usado, o caminho certo não é adicionar mais features agora. O caminho certo é:

1. estabilizar o core
2. alinhar contratos entre backend e frontend
3. fechar multi-workspace, quotas e relatórios
4. só depois expandir para IA preditiva exposta ao utilizador, bug bounty e marketplace

## Observação final de rigor

Neste documento eu **não marquei como defeito** funções sem evidência concreta de problema.

Eu marquei apenas:

- bugs confirmados no código
- desalinhamentos confirmados entre módulos
- promessas comerciais sem implementação correspondente
- áreas com simulação explícita no próprio código
