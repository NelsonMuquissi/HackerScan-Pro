# HackScan Pro — Guia de Construção Completo para Antigravity

> Anexa este ficheiro **e** o `hackscan_pro_master_v2.md` ao chat antes de enviar o primeiro prompt.
> O modelo deve ler ambos na íntegra antes de escrever qualquer linha de código.

---

# PARTE 1 — PROMPT DE SISTEMA

```
Vais construir a plataforma HackScan Pro — um SaaS de análise automatizada de
vulnerabilidades web com modelo B2B + B2C.

Tens dois documentos anexados:
  1. hackscan_pro_master_v2.md  — fonte de verdade técnica (schema, API, arquitectura, código)
  2. Este ficheiro              — regras de construção, skills e roteamento de modelos

Lê ambos na íntegra antes de escrever qualquer linha de código.
```

---

# PARTE 2 — REGRA ABSOLUTA

**Zero simulações. Zero placeholders. Zero `# TODO`. Zero `pass` em funções com lógica.**

Cada função escrita funciona em produção no momento em que é escrita.
Se não consegues implementar algo completamente agora, diz — não escrevas código falso.
Quando o documento master especifica um comportamento, segues esse comportamento exacto.
Quando há ambiguidade, apresentas opções e aguardas confirmação antes de implementar.

---

# PARTE 3 — ROTEAMENTO DE MODELOS

## Perfil de cada modelo

| Modelo | Força principal | Quando usar |
|--------|----------------|-------------|
| **Claude Opus 4.6 (Thinking)** | Raciocínio profundo, segurança, arquitectura | Código de segurança crítica, decisões de arquitectura complexas |
| **Claude Sonnet 4.6 (Thinking)** | Código de produção, lógica de negócio | Uso principal — services, tasks, testes, API endpoints |
| **Gemini 3.1 Pro (High)** | Contexto muito longo | Quando precisas de processar o documento master inteiro |
| **Gemini 3.1 Pro (Low)** | Frontend, UI, componentes | Next.js, React, CSS, templates HTML, design system |
| **Gemini 3 Flash** | Velocidade, scaffolding | Boilerplate, configs, README, listas de dependências |
| **GPT-OSS 120B (Medium)** | YAML, Terraform, infra | Docker, Kubernetes, GitHub Actions, Prometheus |

## Regra de decisão rápida

```
Antes de cada tarefa, pergunta:

  É segurança crítica?           → Opus
  É infra / YAML / configs?      → GPT-OSS 120B
  É frontend / UI / CSS?         → Gemini Pro Low
  Precisa do documento completo? → Gemini Pro High
  É scaffolding / boilerplate?   → Flash
  É tudo o resto?                → Sonnet  ← padrão
```

## Roteamento detalhado por fase

### FASE 1 — Monorepo, infra local, core models (Passos 1-2)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| Estrutura de pastas do monorepo | **Flash** | Boilerplate puro |
| `docker-compose.yml` (PG, Redis, RabbitMQ, MinIO) | **GPT-OSS 120B** | YAML de infra |
| `Makefile` com comandos dev/test/migrate/shell/logs | **Flash** | Script simples |
| `requirements/base.txt`, `dev.txt`, `test.txt` | **Flash** | Lista de dependências |
| `package.json` raiz (Turborepo) | **Flash** | Scaffolding |
| `UUIDModel`, `TimestampedModel` (core/models.py) | **Sonnet** | Base de todos os models — deve estar perfeita |
| `.env.example` completo | **Flash** | Lista de variáveis |
| `README.md` com setup local | **Flash** | Documentação simples |

---

### FASE 2 — Users, Auth JWT RS256, Email verification (Passos 3-4)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `User` model com campos de segurança | **Sonnet** | Schema claro no documento master |
| JWT RS256 — geração de chaves, `SIMPLE_JWT` config | **Opus** | Criptografia assimétrica — erro = falha de segurança |
| Register, Login, Logout, Refresh endpoints | **Sonnet** | Fluxo bem documentado |
| Email verification com token JWT | **Sonnet** | Padrão SaaS bem definido |
| `UserService` completo | **Sonnet** | Lógica de negócio clara |
| Rate limiting em endpoints de auth | **Opus** | Decisão de segurança |
| Testes de auth (unit + integração) | **Sonnet** | Estrutura definida no documento |
| `audit_logs` model e middleware | **Sonnet** | Pattern claro |

---

### FASE 3 — 2FA TOTP, backup codes (Passo 5)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `TwoFactorService` completo (pyotp) | **Opus** | Segurança crítica |
| Backup codes com hash bcrypt | **Opus** | Armazenamento seguro de recuperação |
| Endpoints: setup, verify, disable | **Sonnet** | API layer sobre service já implementado |
| Frontend — QR code, input de código TOTP | **Gemini Pro Low** | UI component puro |

---

### FASE 4 — Workspaces, RBAC, Membros (Passo 6)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `Workspace`, `WorkspaceMember` models | **Sonnet** | Schema claro no documento |
| RBAC permission classes (owner/admin/member/viewer) | **Opus** | Hierarquia de permissões — lógica de segurança complexa |
| `WorkspacePermission`, `IsWorkspaceAdmin`, `IsWorkspaceOwner` | **Opus** | Herança de permissões tem edge cases |
| Invitations com token e expiração | **Sonnet** | Fluxo padrão de convites SaaS |
| API endpoints de workspaces | **Sonnet** | REST CRUD padrão |

---

### FASE 5 — Targets, Scanner Engine Core (Passos 7-9)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `validate_scan_target` (anti-SSRF completo) | **Opus** | **Segurança crítica** — falha aqui permite ataques internos |
| Lista de IPs/domínios bloqueados | **Opus** | Decisão de segurança com edge cases |
| `BaseEngine` (Strategy Pattern) | **Sonnet** | Padrão de design bem documentado |
| `FindingResult` dataclass | **Sonnet** | Estrutura de dados clara |
| `NucleiEngine` completo com parsing JSON | **Sonnet** | Integração com subprocess bem especificada |
| `_build_command`, `_parse_result`, `_build_curl` | **Sonnet** | Funções com lógica clara |
| `EngineRegistry` (decorator pattern) | **Sonnet** | Pattern simples e bem definido |
| Docker sandbox config (security opts, resource limits) | **GPT-OSS 120B** | Docker configs — especialidade do GPT-OSS |
| Testes: `validate_scan_target`, `NucleiEngine` | **Sonnet** | Testes com mocks de subprocess |

---

### FASE 6 — Scans, Celery Task, Findings (Passo 10)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `Scan`, `Finding` models (todos os campos, índices) | **Gemini Pro High** | Schema extenso — usar com o documento master completo como contexto |
| `run_scan` Celery task (com error handling, retry, timeout) | **Opus** | Task crítica com muitos edge cases |
| `_publish_event` (Redis pub/sub) | **Sonnet** | Função bem documentada |
| `_calculate_statistics` | **Sonnet** | Função simples e clara |
| `ScanService.create_scan` | **Sonnet** | Lógica de negócio bem definida |
| Finding streaming (generator + persistir em tempo real) | **Sonnet** | Padrão de generator documentado |
| API endpoints CRUD (scans + findings + filtros) | **Sonnet** | REST padrão com paginação |
| `generate_scan_report` task | **Sonnet** | Task de geração assíncrona |

---

### FASE 7 — WebSockets, Real-time (Passo 11)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| Django Channels setup (ASGI, channel layers Redis) | **GPT-OSS 120B** | Configuração de infra |
| `ScanConsumer` com **auth no handshake** | **Opus** | Auth no WebSocket tem edge cases de segurança |
| `_check_permission` async | **Opus** | Verificação de permissão assíncrona |
| `scan_event` handler | **Sonnet** | Handler simples e bem documentado |
| Frontend — `useScanWebSocket` hook | **Gemini Pro Low** | Hook React com reconnect exponencial |
| Frontend — terminal xterm.js | **Gemini Pro Low** | UI component puro |
| Frontend — ring buffer de 500 linhas | **Gemini Pro Low** | Lógica de UI |

---

### FASE 8 — Frontend completo (Passos 13-15)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| Setup Next.js 15, Tailwind, dark mode config | **Flash** | Scaffolding e configuração |
| Auth pages (login, register, forgot-password) | **Gemini Pro Low** | Forms e páginas — frontend puro |
| Dashboard com heatmap de severidade | **Gemini Pro Low** | Visualização — Gemini Low excelente em UI |
| Scan creation flow (multi-step form) | **Gemini Pro Low** | UX flow — frontend puro |
| Finding detail + remediation view | **Sonnet** | Tem lógica de renderização de código — Sonnet mais fiável |
| API client centralizado (`src/lib/api/`) | **Sonnet** | Tipagem TypeScript e error handling |
| Zustand stores | **Sonnet** | State management com tipos |
| Error boundaries + Suspense + Skeleton loaders | **Gemini Pro Low** | Componentes de UI |
| Testes E2E (Playwright) — fluxo de scan | **Sonnet** | Testes com lógica de asserção |

---

### FASE 9 — Billing, Stripe (Passos 16-17)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `Plan`, `Subscription`, `Invoice`, `UsageRecord` models | **Gemini Pro High** | Schema extenso com o documento master completo como contexto |
| `BillingService.create_checkout_session` | **Sonnet** | Integração Stripe bem documentada |
| `BillingService.handle_webhook` (dispatcher) | **Opus** | Lógica de routing crítica para receita |
| `_handle_checkout_completed` (idempotente) | **Opus** | Idempotência — erros = perda de receita |
| `_handle_payment_failed`, `subscription_deleted` | **Opus** | Estados críticos de billing |
| `BillingService.check_quota` | **Opus** | Lógica que afecta todos os endpoints |
| `QuotaCheckMixin` | **Sonnet** | Mixin com pattern claro |
| Frontend — upgrade flow, billing pages | **Gemini Pro Low** | UI de billing puro |
| Frontend — usage display, plan badges | **Gemini Pro Low** | UI components |
| Testes de webhooks (idempotência, todos os eventos) | **Opus** | Testes de casos críticos de receita |

---

### FASE 10 — Relatórios PDF, AI Engine (Passos 18-19)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `PDFReportGenerator` (WeasyPrint) | **Sonnet** | Geração de PDF com template — Sonnet fiável |
| HTML templates dos relatórios (técnico + executivo) | **Gemini Pro Low** | HTML/CSS puro |
| `_calculate_business_impact` | **Opus** | Lógica de estimativa de impacto — raciocínio necessário |
| `AIService.explain_finding` — system prompt PT | **Opus** | Prompt de segurança complexo |
| `AIService.predict_attack_chains` — JSON estruturado | **Opus** | Raciocínio de correlação de vulnerabilidades |
| `AIService.generate_remediation_code` | **Sonnet** | Geração de código por linguagem |
| Caching de respostas AI (Redis, TTL por tipo) | **Sonnet** | Pattern de cache bem documentado |
| Rate limiting de chamadas à API Claude | **Sonnet** | Middleware de rate limiting |

---

### FASE 11 — Bug Bounty, EASM (Passos 21-22)

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| `BountyProgram`, `BountySubmission`, `BountyPayout` models | **Gemini Pro High** | Schema extenso com contexto do documento completo |
| `BountyTriageService.auto_triage` | **Opus** | Lógica complexa com múltiplos estados |
| `BountyTriageService._evaluate_quality` | **Sonnet** | Scoring bem definido no documento |
| `BountyTriageService.process_payout` (Stripe Connect) | **Opus** | Pagamento a terceiros — crítico |
| `EASMService.discover_subdomains` | **Sonnet** | Integração com APIs externas bem documentada |
| `EASMService._ct_logs` (crt.sh) | **Sonnet** | HTTP request simples |
| `EASMService._shodan_search` | **Sonnet** | API wrapper bem especificado |
| `run_easm_discovery` Celery task | **Sonnet** | Task com lógica de diff |
| Celery beat schedule para EASM diário | **GPT-OSS 120B** | Configuração de scheduled tasks |
| Frontend — mapa de superfície de ataque | **Gemini Pro Low** | Visualização UI |

---

### FASE 12 — Infra, Kubernetes, CI/CD

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| K8s Deployments, Services, Ingress | **GPT-OSS 120B** | YAML de infra |
| HPA para API e scanner workers | **GPT-OSS 120B** | Configuração Kubernetes |
| GitHub Actions pipeline completo | **GPT-OSS 120B** | YAML workflows |
| Terraform para EKS/GKE | **GPT-OSS 120B** | IaC — HCL |
| Dockerfiles multi-stage (API, scanner, frontend) | **GPT-OSS 120B** | Docker configs |
| Prometheus alerts YAML | **GPT-OSS 120B** | Configuração de monitoring |
| Health check + readiness check views | **Sonnet** | Lógica Python, não configs |
| Prometheus metrics Python (`prometheus_client`) | **Sonnet** | Código Python |
| Structlog setup e configuração | **Sonnet** | Configuração em Python |

---

## Regras de escalação entre modelos

```
Situação                          → Acção
──────────────────────────────────────────────────────────────
Sonnet erra na arquitectura       → Passa para Opus
Sonnet erra segurança             → Passa para Opus imediatamente
Gemini Pro Low erra TypeScript    → Passa para Sonnet
GPT-OSS erra lógica Python        → Nunca usas GPT-OSS para Python
Flash gera código com TODOs       → Flash só para scaffolding, não lógica
Gemini Pro High dá timeout        → Divide o contexto e usa Sonnet
```

---

# PARTE 4 — SKILLS DE CONSTRUÇÃO

## SKILL: Backend Django

**Usa quando:** models, serializers, views, services, tasks Celery, consumers WebSocket,
middleware, signals, validators, permissions.

**Regras obrigatórias:**
- Todos os models herdam de `UUIDModel` e `TimestampedModel`
- IDs são sempre UUID v4 — nunca auto-increment
- Soft delete via `deleted_at` em: User, Workspace, Target, Scan
- `select_related` e `prefetch_related` obrigatórios — zero queries N+1
- Dados sensíveis: `EncryptedTextField` ou `EncryptedCharField`
- Views só orquestram HTTP — lógica de negócio fica em `services.py`
- Celery tasks: `acks_late=True`, `reject_on_worker_lost=True`, `soft_time_limit` e
  `time_limit` sempre definidos
- Migrations zero-downtime (add nullable → backfill → make required)
- Testes unitários para cada service, integração para cada endpoint

**Estrutura obrigatória de cada módulo:**
```
apps/api/{módulo}/
├── models.py
├── serializers.py
├── views.py
├── urls.py
├── services.py        ← lógica de negócio
├── tasks.py           ← só se tiver Celery tasks
├── permissions.py     ← só se tiver permissões específicas
└── tests/
    ├── test_models.py
    ├── test_services.py
    └── test_api.py
```

---

## SKILL: Frontend Next.js

**Usa quando:** páginas, componentes, hooks, stores, API client, WebSocket hooks, layouts.

**Regras obrigatórias:**
- App Router (Next.js 15) — nunca Pages Router
- TypeScript estrito — sem `any`, sem `// @ts-ignore`
- Componentes com responsabilidade única (max ~100 linhas)
- Estado em Zustand stores ou custom hooks
- Error boundaries em todas as secções críticas
- Suspense + Skeleton loaders em todo o conteúdo assíncrono
- `useEffect` com cleanup function sempre que abre conexão
- API client centralizado em `src/lib/api/`
- Formulários com react-hook-form + zod
- Dark mode nativo, hacker-themed, Tailwind CSS

```typescript
// Estrutura obrigatória de componente
interface ComponentNameProps {
  // props tipadas explicitamente
}

export function ComponentName({ prop1, prop2 }: ComponentNameProps) {
  // 1. hooks
  // 2. handlers
  // 3. return JSX
}
```

---

## SKILL: Scanner Engine

**Usa quando:** lógica de scan, integração Nuclei, custom checks, validação de targets,
parsing de resultados, sandboxing Docker.

**Regras obrigatórias:**
- Todo o engine implementa `BaseEngine` (Strategy Pattern)
- Engines são generators — `yield FindingResult`
- Validação de target ANTES de qualquer execução
- Docker sandbox com: network isolado, CPU max 2 vCPU, RAM max 2GB,
  filesystem read-only, `no-new-privileges: true`, user non-root
- Timeout obrigatório (soft + hard) em todo o subprocess
- Parsing Nuclei via JSON (`-json` flag) — nunca parsing de texto
- Findings persistidos à medida que chegam — não em batch no final
- Eventos publicados via Redis pub/sub para WebSocket em tempo real

**IPs e domínios sempre bloqueados (nunca mudar esta lista):**
```
10.0.0.0/8
172.16.0.0/12
192.168.0.0/16
127.0.0.0/8
169.254.0.0/16      ← AWS/GCP metadata
::1
fc00::/7
localhost
metadata.google.internal
169.254.169.254
100.100.100.200     ← Alibaba Cloud metadata
```

---

## SKILL: Real-time & WebSockets

**Usa quando:** output em tempo real, notificações instantâneas, progresso de scan ao vivo.

**Regras obrigatórias:**
- Autenticação no WebSocket handshake — fechar com code 4001 se não autenticado
- Verificar permissão no recurso — fechar com 4003 se não autorizado
- Grupos por recurso: `scan_{scan_id}`, `workspace_{workspace_id}`
- Frontend com reconexão exponential backoff (max 5 tentativas, max 30s delay)
- Máximo 500 linhas de output em memória (ring buffer)
- Cleanup obrigatório no `disconnect()` — remover do grupo

**Formato de evento — nunca alterar esta estrutura:**
```json
{ "type": "scan.progress",  "data": { "progress": 45 } }
{ "type": "scan.finding",   "data": { "id": "...", "severity": "high" } }
{ "type": "scan.output",    "data": { "line": "[nuclei] Testing..." } }
{ "type": "scan.completed", "data": { "duration": 142, "total_findings": 7 } }
{ "type": "scan.failed",    "data": { "reason": "timeout" } }
```

---

## SKILL: Auth & Segurança

**Usa quando:** autenticação, autorização, permissões, 2FA, API keys, rate limiting,
headers de segurança.

**Regras obrigatórias — nunca negociáveis:**
- JWT com **RS256** (RSA assimétrico) — nunca HS256
- Access token: **15 minutos**. Refresh token: **7 dias** com rotação
- Passwords: **bcrypt rounds=12**
- 2FA TOTP com `pyotp` — secret **encriptado** em repouso
- Backup codes: 8 códigos armazenados como **hashes bcrypt** (nunca em texto)
- API Keys: prefixo `hs_live_` + `secrets.token_urlsafe(32)`, só o **hash SHA-256** guardado
- Rate limiting:
  ```
  Login:          5/15min por IP
  Register:       3/hora por IP
  Password reset: 3/hora por IP
  TOTP verify:    5/15min por IP
  ```
- Security headers obrigatórios: `HSTS`, `CSP`, `X-Frame-Options: DENY`, `Referrer-Policy`
- CORS estrito — apenas origens explícitas na lista de permissões
- **Nunca logar:** passwords, tokens JWT, API keys, dados de cartão

**Audit log obrigatório para:**
```
user.login, user.logout, user.register
2fa.enabled, 2fa.disabled
password.changed, password.reset
scan.created, scan.cancelled
api_key.created, api_key.deleted
plan.upgraded, plan.cancelled
```

---

## SKILL: Database & Migrations

**Usa quando:** criar/modificar models, queries complexas, optimizações, migrations.

**Regras obrigatórias:**
- Índices em **todas** as colunas de filtro frequente
- Índices parciais (`WHERE`) quando aplicável
- Migrations zero-downtime: 3 fases para operações destrutivas
- `select_related` para ForeignKey, `prefetch_related` para ManyToMany — sempre
- Paginação cursor-based em todas as listagens grandes
- `CONN_MAX_AGE=0` com pgBouncer
- Queries de séries temporais via TimescaleDB

**Convenção de naming:**
```sql
Tabelas:  snake_case plural            → users, scan_events
Índices:  idx_{tabela}_{campo(s)}      → idx_users_email
FKs:      {tabela}_id                  → workspace_id, user_id
Soft del: deleted_at TIMESTAMPTZ NULL  → filtrar WHERE deleted_at IS NULL
```

**Anti-padrões proibidos:**
```python
# ❌ NUNCA — N+1 query
for scan in scans:
    print(scan.target.value)  # query extra por scan

# ✅ SEMPRE
scans = Scan.objects.select_related("target", "workspace").filter(...)
```

---

## SKILL: Billing & Stripe

**Usa quando:** subscriptions, checkout, webhooks Stripe, quota, invoices, payouts.

**Regras obrigatórias:**
- Webhooks verificados com `stripe.Webhook.construct_event`
- Handlers de webhook **idempotentes** — `update_or_create` com Stripe ID como chave
- Quota verificada **antes** de cada operação que consome recursos
- Resposta 402 com `upgrade_url` quando quota excedida
- Nunca guardar dados de cartão
- Stripe Connect para payouts a researchers (Bug Bounty)
- Planos e limites em `Plan.limits` (JSONB) — não hardcoded

**Todos os eventos de webhook devem ter handler:**
```
checkout.session.completed
invoice.payment_succeeded
invoice.payment_failed
invoice.upcoming
customer.subscription.updated
customer.subscription.deleted
customer.subscription.trial_will_end
```

---

## SKILL: Celery & Tasks Assíncronas

**Usa quando:** operações > 2 segundos, scans, relatórios, emails, EASM, notificações.

**Regras obrigatórias:**
- `acks_late=True` — confirmar só após conclusão
- `reject_on_worker_lost=True` — recolocar na fila se worker morrer
- `soft_time_limit` e `time_limit` em todas as tasks
- Retry com backoff exponencial para falhas temporárias
- `worker_prefetch_multiplier=1` para tasks pesadas (scans)

**Roteamento de queues — nunca misturar:**
```python
"scans.tasks.run_scan"            → queue: "urgent"
"reports.tasks.generate_report"   → queue: "reports"
"notifications.tasks.*"           → queue: "notifications"
"easm.tasks.*"                    → queue: "scheduled"
```

---

## SKILL: AI Integration

**Usa quando:** AI Chat, AI Forecaster, explicações, remediações, attack chains.

**Regras obrigatórias:**
- Modelo para análise complexa: `claude-opus-4-5`
- Modelo para respostas rápidas: `claude-haiku-4-5-20251001`
- System prompt sempre em português
- Cache de respostas em Redis (TTL: explicações 1h, remediações 24h)
- Rate limiting por workspace (evitar custo excessivo)
- **Nunca passar para Claude:** passwords, tokens, dados de cartão, PII completo
- Truncar evidências e payloads (max 500 chars de contexto raw)
- Fallback gracioso se a API Claude falhar — nunca deixar a UI quebrar

---

## SKILL: Docker & Infra

**Usa quando:** Dockerfiles, docker-compose, Kubernetes, health checks, scripts de deploy.

**Regras obrigatórias:**
- Imagens multi-stage (builder + runner)
- Non-root user (UID 1000) em todas as imagens
- Secrets via variáveis de ambiente — nunca no Dockerfile
- Health check (`/health/`) e readiness check (`/health/ready/`) em todos os serviços
- Resource limits em todos os containers

**Configuração obrigatória para containers de scan:**
```yaml
read_only: true
tmpfs: [/tmp:size=512m,noexec]
cap_drop: [ALL]
security_opt: [no-new-privileges:true]
networks: [scanner_egress_only]
deploy:
  resources:
    limits: { cpus: '2', memory: 2G }
```

---

## SKILL: Testes

**Usa quando:** qualquer feature nova. Testes escritos **junto** com o código — não depois.

**Regras obrigatórias:**
- Cobertura mínima: 80% geral, 95% em auth e billing
- Unit: services, validators, engines, utils — mocks para dependências externas
- Integration: endpoints com `APIClient` do DRF
- E2E: fluxos críticos com Playwright
- Fixtures em `conftest.py` — sem dados duplicados entre testes
- Mocks obrigatórios para: Stripe, Anthropic, Shodan, subprocess (Nuclei), email

**Naming obrigatório:**
```python
# Padrão: test_{o_que_faz}_{condição}_{resultado_esperado}

def test_create_scan_returns_402_when_free_plan_limit_reached(): ...
def test_validate_target_raises_error_for_private_ip(): ...
def test_webhook_handler_idempotent_on_duplicate_event(): ...
def test_login_blocks_after_5_failed_attempts(): ...
```

**Testes de segurança obrigatórios em cada módulo:**
```python
# Exemplos do que testar
def test_cannot_access_other_workspace_findings(): ...
def test_cannot_scan_private_ip_range(): ...
def test_cannot_scan_aws_metadata_endpoint(): ...
def test_api_requires_authentication(): ...
def test_viewer_cannot_create_scan(): ...
```

---

## SKILL: Observabilidade

**Usa quando:** logging, métricas Prometheus, health checks, alertas.

**Regras obrigatórias:**
- Logs estruturados em JSON com `structlog` — nunca `print()`
- Contexto em todos os logs: `scan_id`, `workspace_id`, `user_id`
- **Nunca logar:** passwords, tokens, API keys, dados de cartão
- Métricas Prometheus em operações críticas
- Sentry para excepções não tratadas

```python
import structlog
logger = structlog.get_logger(__name__)

# ✅ Correcto
logger.info("scan.started", scan_id=scan_id, workspace_id=workspace_id)
logger.error("scan.failed", scan_id=scan_id, error=str(exc), exc_info=True)

# ❌ Proibido
print(f"Scan {scan_id} started")
logger.info(f"User password: {password}")
```

---

# PARTE 5 — ORDEM DE CONSTRUÇÃO

Segue esta ordem. Não avanças sem o anterior estar completo e testado.

```
FASE 1 — FUNDAÇÃO
  1.  Monorepo setup + Docker Compose local
  2.  Core models (UUIDModel, TimestampedModel, base classes)

FASE 2 — AUTH (usar Opus nos pontos críticos)
  3.  Users — model, serializer, service, endpoints, testes
  4.  Auth — JWT RS256, register, login, logout, refresh, email verification
  5.  2FA — TOTP setup, verify, disable, backup codes
  6.  Workspaces — model, RBAC, members, invitations
  7.  Rate limiting + audit logs middleware

FASE 3 — SCANNER
  8.  Targets — model, validação anti-SSRF, CRUD
  9.  Scan Engine — BaseEngine, NucleiEngine, EngineRegistry, Docker sandbox
  10. Scans — model, service, Celery task, endpoints CRUD
  11. Django Channels — consumer WebSocket, pub/sub
  12. Findings — model, endpoints, filtros, paginação

FASE 4 — FRONTEND
  13. Next.js setup, design system dark mode, auth pages
  14. Dashboard, scan creation flow, terminal real-time
  15. Findings detail, remediation view, API client

FASE 5 — BILLING
  16. Plans, Subscription, Stripe checkout, webhooks, quota
  17. Billing pages, upgrade flow, usage display

FASE 6 — RELATÓRIOS E AI
  18. Reports — PDF técnico, PDF executivo, export JSON/CSV
  19. AI Engine — explain, attack chains, remediation code
  20. Notifications — email, in-app, webhook

FASE 7 — BETA FEATURES
  21. Bug Bounty — program, submission, triage, payout
  22. EASM — asset discovery, change detection, alerts
  23. Marketplace — module registry, SDK, revenue share
  24. Team collaboration — assign, comments, Jira/Slack
```

---

# PARTE 6 — COMO TRABALHAR

**Para cada passo:**
1. Confirma a lista de ficheiros que serão criados ou modificados
2. Implementa completamente
3. Escreve os testes correspondentes
4. Mostra como testar localmente (`make test` ou comando específico)
5. Lista o que o passo seguinte vai precisar

**Quando encontrares uma decisão de arquitectura não coberta pelo documento master:**
- Apresenta 2-3 opções com trade-offs
- Recomenda uma com justificativa
- Aguarda confirmação antes de implementar

**Quando precisares de credenciais ou variáveis de ambiente:**
- Lista todas as que o passo precisa
- Explica como obter cada uma
- Fornece o `.env.example` actualizado

**Quando um passo depender de serviço externo (Stripe, Shodan, Claude API):**
- Implementa o código com a interface real
- Fornece mock/stub apenas para os testes
- Nunca mocks em código de produção

---

# PARTE 7 — PRIMEIRO PASSO

Começa pelo **Passo 1: Monorepo setup + Docker Compose local**.

Usa os modelos nesta ordem para este passo:
- Estrutura de pastas → **Flash**
- `docker-compose.yml` → **GPT-OSS 120B**
- `Makefile`, `requirements`, `package.json`, `.env.example`, `README` → **Flash**
- `core/models.py` (`UUIDModel`, `TimestampedModel`) → **Sonnet**

Entrega completa esperada:
1. Árvore de directórios completa do monorepo
2. `docker-compose.yml` funcional com PG 16, TimescaleDB, Redis 7, RabbitMQ 3, MinIO
3. `Makefile` com: `make dev`, `make test`, `make migrate`, `make shell`, `make logs`, `make clean`
4. `requirements/base.txt`, `requirements/dev.txt`, `requirements/test.txt`
5. `package.json` raiz com Turborepo
6. `.env.example` completo com todas as variáveis do documento master
7. `apps/api/core/models.py` com `UUIDModel`, `TimestampedModel`, `SoftDeleteModel`
8. `README.md` — do `git clone` ao `make dev` funcional em menos de 5 comandos

Cada ficheiro completo e funcional. Sem placeholders.
