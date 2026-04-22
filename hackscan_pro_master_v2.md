# HackScan Pro — Documento Master de Consolidação Técnica

> **Versão:** 2.0 · **Data:** Março 2026  
> **Propósito:** Especificação completa de produto, arquitectura, padrões de desenvolvimento e roadmap para construção.  
> **Princípio:** Cada feature é real, escalável, segura e mantível. Zero simulações.

---

## Índice

1. [Visão do Produto](#1-visão-do-produto)
2. [Princípios de Engenharia](#2-princípios-de-engenharia)
3. [Arquitectura do Sistema](#3-arquitectura-do-sistema)
4. [Estrutura de Pastas e Repositórios](#4-estrutura-de-pastas-e-repositórios)
5. [Schema de Base de Dados](#5-schema-de-base-de-dados)
6. [Especificação da API](#6-especificação-da-api)
7. [Módulos Funcionais — Spec Detalhada](#7-módulos-funcionais--spec-detalhada)
   - 7.1 [Auth & Gestão de Utilizadores](#71-auth--gestão-de-utilizadores)
   - 7.2 [Scanner de Vulnerabilidades](#72-scanner-de-vulnerabilidades)
   - 7.3 [Dashboard & Real-time](#73-dashboard--real-time)
   - 7.4 [Billing & Planos](#74-billing--planos)
   - 7.5 [AI Engine](#75-ai-engine)
   - 7.6 [Bug Bounty](#76-bug-bounty)
   - 7.7 [EASM — Attack Surface Management](#77-easm--attack-surface-management)
   - 7.8 [Marketplace de Módulos](#78-marketplace-de-módulos)
   - 7.9 [Relatórios & Compliance](#79-relatórios--compliance)
   - 7.10 [Colaboração em Equipa](#710-colaboração-em-equipa)
8. [Segurança — Arquitectura Zero-Trust](#8-segurança--arquitectura-zero-trust)
9. [Escalabilidade e Performance](#9-escalabilidade-e-performance)
10. [Padrões de Código e Clean Code](#10-padrões-de-código-e-clean-code)
11. [Testes — Estratégia Completa](#11-testes--estratégia-completa)
12. [CI/CD e DevOps](#12-cicd-e-devops)
13. [Monitoring e Observabilidade](#13-monitoring-e-observabilidade)
14. [Roadmap Detalhado com Tarefas](#14-roadmap-detalhado-com-tarefas)
15. [Stack de Tecnologia — Decisões e Justificativas](#15-stack-de-tecnologia--decisões-e-justificativas)
16. [Variáveis de Ambiente e Configuração](#16-variáveis-de-ambiente-e-configuração)
17. [Glossário](#17-glossário)

---

## 1. Visão do Produto

### O Que é

**HackScan Pro** é uma plataforma SaaS de análise automatizada de vulnerabilidades web com modelo de negócio híbrido **B2B + B2C**. Combina scanner automático enterprise, IA preditiva de exploits, programa de Bug Bounty integrado e marketplace de módulos — com suporte nativo em Português e foco no mercado africano e lusófono.

### Proposta de Valor Central

```
Scanner Automático  +  IA Preditiva  +  Bug Bounty  +  Marketplace
        ↓                   ↓               ↓              ↓
   (Detectify)          (exclusivo)    (HackerOne)    (Burp Suite)
                               ↓
              Tudo numa plataforma · Em Português · Freemium
```

### Modelo de Negócio

| Stream | Mecanismo | Fase |
|--------|-----------|------|
| Subscriptions (Free/Pro/Team/Enterprise) | MRR recorrente | MVP |
| Marketplace commission (30%) | Receita passiva sobre módulos | Beta |
| Bug Bounty platform fee (15%) | Fee sobre bounties pagos | Beta |
| Pay-as-you-go API | Por scan extra além do plano | Scale |
| White-label / OEM | MSSPs revendem a marca | Scale |
| Compliance reports add-on | PDF normativos premium | Scale |

---

## 2. Princípios de Engenharia

Estes princípios são não-negociáveis em todas as decisões de arquitectura e código.

### 2.1 SOLID

- **S — Single Responsibility:** cada classe, função e módulo tem uma única razão para mudar.
- **O — Open/Closed:** extensível sem modificar código existente (ex: novos tipos de scan via plugins).
- **L — Liskov Substitution:** subclasses são intercambiáveis com a base (ex: todos os scanners implementam a mesma interface).
- **I — Interface Segregation:** interfaces pequenas e específicas; nenhum módulo depende do que não usa.
- **D — Dependency Inversion:** módulos de alto nível não dependem de implementações — dependem de abstrações.

### 2.2 DRY, KISS, YAGNI

- **DRY:** nenhuma lógica duplicada — extrair para utils, mixins ou serviços partilhados.
- **KISS:** a solução mais simples que funciona correctamente; complexidade só quando necessária.
- **YAGNI:** não construir o que não é necessário agora; arquitectura extensível mas código mínimo.

### 2.3 Twelve-Factor App

A plataforma segue os [12 factores](https://12factor.net/) para SaaS escalável:

1. Codebase única com múltiplos deploys
2. Dependências declaradas explicitamente
3. Configuração via variáveis de ambiente
4. Backing services como recursos anexados
5. Build, release, run separados
6. Processos stateless
7. Port binding (auto-contained)
8. Concorrência por tipo de processo
9. Descartabilidade (startup rápido, shutdown gracioso)
10. Paridade dev/staging/prod
11. Logs como streams de eventos
12. Admin tasks como processos únicos

### 2.4 Security by Design

- Nenhuma feature é construída sem considerar o vector de ataque correspondente.
- Todos os inputs são validados, sanitizados e rate-limited.
- Princípio do menor privilégio em todas as permissões.
- Auditoria de todas as acções sensíveis.

### 2.5 Observability First

- Cada operação significativa emite logs estruturados (JSON).
- Métricas expostas via Prometheus em todos os serviços.
- Traces distribuídos para operações cross-service.
- Alertas definidos antes do deploy de cada feature.

---

## 3. Arquitectura do Sistema

### 3.1 Visão Geral

```
                        ┌─────────────────────────────┐
                        │     Utilizadores              │
                        │  Browser · Mobile · API       │
                        └──────────────┬───────────────┘
                                       │ HTTPS / WSS
                        ┌──────────────▼───────────────┐
                        │        Cloudflare              │
                        │   WAF · DDoS · CDN · TLS 1.3  │
                        └──────────────┬───────────────┘
                                       │
              ┌────────────────────────▼────────────────────────┐
              │                  API Gateway                      │
              │           Nginx Ingress (Kubernetes)              │
              │        Rate limiting · SSL termination            │
              └───────┬──────────────────────────┬──────────────┘
                      │                          │
        ┌─────────────▼──────────┐  ┌────────────▼─────────────┐
        │    Web API Service      │  │   WebSocket Service        │
        │  Django REST Framework  │  │   Django Channels          │
        │  JWT Auth · RBAC        │  │   Real-time scan output    │
        │  Versioned API v1/v2    │  │   Alerts · Notifications   │
        └──────────┬─────────────┘  └────────────┬─────────────┘
                   │                              │
        ┌──────────▼──────────────────────────────▼─────────────┐
        │                   Internal Services                     │
        │                                                         │
        │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
        │  │ Scan Service  │  │  AI Service   │  │ Bounty Svc  │  │
        │  │ Nuclei engine │  │ Claude API    │  │ Triage      │  │
        │  │ Custom checks │  │ ML predictor  │  │ Payments    │  │
        │  └──────┬───────┘  └──────┬────────┘  └──────┬──────┘  │
        │         │                 │                   │         │
        │  ┌──────▼───────┐  ┌──────▼────────┐  ┌──────▼──────┐  │
        │  │  Task Queue   │  │  Report Svc   │  │ EASM Svc    │  │
        │  │  Celery +     │  │  PDF gen      │  │ Shodan API  │  │
        │  │  RabbitMQ     │  │  Export JSON  │  │ Subdomain   │  │
        │  └──────┬───────┘  └───────────────┘  └─────────────┘  │
        └─────────┼───────────────────────────────────────────────┘
                  │
        ┌─────────▼───────────────────────────────────────────────┐
        │                    Data Layer                            │
        │                                                          │
        │  PostgreSQL 16     TimescaleDB        Redis 7            │
        │  (primary data)    (scan logs/TS)     (cache/sessions)   │
        │                                                          │
        │  MinIO / S3                           HashiCorp Vault    │
        │  (reports, PoCs)                      (secrets)          │
        └──────────────────────────────────────────────────────────┘
```

### 3.2 Comunicação Entre Serviços

| Canal | Protocolo | Uso |
|-------|-----------|-----|
| API externa ↔ Web Service | HTTPS REST | Todas as requests de cliente |
| Web Service ↔ Scan Service | Celery tasks (RabbitMQ) | Dispatch de scans assíncronos |
| Scan Service → Frontend | Django Channels (Redis pub/sub) | Output real-time de scans |
| Services ↔ DB | PostgreSQL connection pool (pgBouncer) | Dados persistentes |
| Services ↔ Cache | Redis Sentinel | Cache, sessions, pub/sub |
| Scan Runners | Docker socket (isolado) | Execução de scans em containers |

### 3.3 Fluxo de um Scan (End-to-End)

```
1. Cliente POST /api/v1/scans/
2. API valida permissões (JWT + RBAC) e quota do plano
3. Cria registo Scan(status=QUEUED) em PostgreSQL
4. Envia task ao RabbitMQ com prioridade (urgent/normal/scheduled)
5. Celery worker recebe task, actualiza status=RUNNING
6. Worker publica eventos via Redis pub/sub → Django Channels → WebSocket → Frontend
7. Docker container isolado executa Nuclei + custom engines
8. Findings são persistidos em PostgreSQL à medida que chegam
9. Ao terminar: status=COMPLETED, gera relatório assíncrono (PDF via Celery)
10. Notificação push (email + webhook + in-app) enviada ao utilizador
```

### 3.4 Isolamento de Scans

Cada scan é executado num container Docker efémero com:
- Network namespace isolado (sem acesso à rede interna)
- CPU limitado (max 2 vCPU por scan)
- Memória limitada (max 2GB por scan)
- Filesystem read-only excepto `/tmp`
- Timeout máximo configurável por plano
- PID namespace isolado
- User namespace: non-root dentro do container

```yaml
# docker-compose.scanner.yml (template por scan)
services:
  scanner:
    image: hackscan/runner:latest
    read_only: true
    tmpfs:
      - /tmp:size=512m,noexec
    networks:
      - scanner_egress_only  # sem acesso à rede interna
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    ulimits:
      nofile:
        soft: 1024
        hard: 2048
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 4. Estrutura de Pastas e Repositórios

### 4.1 Monorepo Structure

```
hackscan-pro/
├── apps/
│   ├── api/                    # Django REST Framework — core API
│   ├── frontend/               # Next.js 15 — interface web
│   ├── scanner/                # Scanner engine service
│   ├── ai/                     # AI service (Claude + ML)
│   └── worker/                 # Celery workers
├── packages/
│   ├── scanner-sdk/            # SDK público para módulos do marketplace
│   ├── ui-components/          # Design system partilhado
│   └── shared-types/           # TypeScript types partilhados
├── infra/
│   ├── terraform/              # Infra as code (EKS/GKE)
│   ├── kubernetes/             # K8s manifests
│   ├── docker/                 # Dockerfiles
│   └── scripts/                # Scripts de deploy e manutenção
├── docs/
│   ├── api/                    # OpenAPI spec
│   ├── architecture/           # ADRs (Architecture Decision Records)
│   └── runbooks/               # Operações e incidentes
└── .github/
    └── workflows/              # CI/CD pipelines
```

### 4.2 Estrutura do Backend (Django)

```
apps/api/
├── config/
│   ├── settings/
│   │   ├── base.py             # Settings base (comuns)
│   │   ├── development.py      # Override local
│   │   ├── staging.py          # Override staging
│   │   └── production.py       # Override produção
│   ├── urls.py                 # URL routing principal
│   ├── wsgi.py
│   └── asgi.py                 # ASGI para WebSockets
├── core/
│   ├── models.py               # Models base (UUIDModel, TimestampedModel)
│   ├── permissions.py          # RBAC permissions base
│   ├── pagination.py           # Paginação padrão
│   ├── exceptions.py           # Exception handlers customizados
│   ├── middleware/
│   │   ├── audit.py            # Audit log middleware
│   │   ├── rate_limit.py       # Rate limiting por IP e utilizador
│   │   └── security.py         # Security headers
│   └── utils/
│       ├── crypto.py           # Funções criptográficas
│       ├── validators.py       # Validadores customizados
│       └── notifications.py    # Sistema de notificações
├── users/
│   ├── models.py               # User, UserProfile, APIKey
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py             # Lógica de negócio
│   ├── signals.py              # Django signals
│   └── tests/
├── scans/
│   ├── models.py               # Scan, Finding, ScanConfig
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── services.py
│   ├── tasks.py                # Celery tasks
│   ├── engines/
│   │   ├── base.py             # Abstract engine
│   │   ├── nuclei.py           # Nuclei integration
│   │   ├── custom/             # Custom check engines
│   │   └── registry.py         # Engine registry
│   └── tests/
├── billing/
│   ├── models.py               # Subscription, Plan, Invoice
│   ├── services.py             # Stripe integration
│   ├── webhooks.py             # Stripe webhook handlers
│   └── tests/
├── bounty/
│   ├── models.py               # Program, Submission, Reward
│   ├── services.py
│   └── tests/
├── reports/
│   ├── generators/
│   │   ├── pdf.py              # PDF generation (WeasyPrint)
│   │   ├── json.py
│   │   └── csv.py
│   └── templates/
├── marketplace/
│   ├── models.py               # Module, Purchase, Review
│   └── services.py
└── notifications/
    ├── channels/
    │   ├── email.py
    │   ├── webhook.py
    │   └── slack.py
    └── services.py
```

### 4.3 Estrutura do Frontend (Next.js)

```
apps/frontend/
├── src/
│   ├── app/                    # App Router (Next.js 15)
│   │   ├── (auth)/             # Route group — páginas públicas
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/        # Route group — autenticado
│   │   │   ├── layout.tsx      # Dashboard layout + auth guard
│   │   │   ├── scans/
│   │   │   ├── findings/
│   │   │   ├── reports/
│   │   │   ├── bounty/
│   │   │   ├── marketplace/
│   │   │   ├── team/
│   │   │   └── settings/
│   │   └── api/                # Next.js API routes (proxies + webhooks)
│   ├── components/
│   │   ├── ui/                 # Design system base (shadcn/ui + custom)
│   │   ├── scans/              # Componentes de scan
│   │   ├── charts/             # Visualizações
│   │   ├── terminal/           # Terminal simulado (xterm.js)
│   │   └── layouts/
│   ├── lib/
│   │   ├── api/                # API client (fetch wrapper + types)
│   │   ├── auth/               # Auth context + hooks
│   │   ├── websocket/          # WebSocket client
│   │   └── utils/
│   ├── hooks/                  # Custom React hooks
│   ├── stores/                 # Zustand stores
│   └── types/                  # TypeScript types
├── public/
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/                    # Playwright
```

---

## 5. Schema de Base de Dados

### 5.1 Convenções

- Todos os IDs são `UUID v4` (não auto-increment — evita enumeração)
- Todos os modelos têm `created_at` e `updated_at` com index
- Soft delete via `deleted_at` (nullable timestamp) nos modelos sensíveis
- Dados sensíveis encriptados em repouso (campo por campo via django-encrypted-fields)
- Foreign keys com `on_delete` explícito sempre
- Índices em todas as colunas de filtro frequente

### 5.2 Schema Principal (PostgreSQL)

```sql
-- ============================================================
-- USERS & AUTH
-- ============================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    email_verified  BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash   VARCHAR(255) NOT NULL,  -- bcrypt
    full_name       VARCHAR(255),
    avatar_url      TEXT,
    role            VARCHAR(50) NOT NULL DEFAULT 'user',  -- user, admin, superadmin
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    totp_secret     TEXT,           -- encriptado, nullable
    totp_enabled    BOOLEAN NOT NULL DEFAULT FALSE,
    last_login_at   TIMESTAMPTZ,
    last_login_ip   INET,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at);

CREATE TABLE user_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company         VARCHAR(255),
    country         VARCHAR(2),     -- ISO 3166-1 alpha-2
    timezone        VARCHAR(100) NOT NULL DEFAULT 'UTC',
    language        VARCHAR(10) NOT NULL DEFAULT 'pt',
    notification_settings JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE SET NULL,
    name            VARCHAR(255) NOT NULL,
    key_prefix      VARCHAR(8) NOT NULL,        -- ex: "hs_live_"
    key_hash        VARCHAR(255) NOT NULL,       -- SHA-256 da key completa
    scopes          TEXT[] NOT NULL DEFAULT '{}', -- ["scans:read","scans:write"]
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash) WHERE is_active = TRUE;

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) NOT NULL UNIQUE,
    device_info     JSONB,
    ip_address      INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          VARCHAR(100) NOT NULL,  -- "user.login", "scan.created"
    resource_type   VARCHAR(100),
    resource_id     UUID,
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- ============================================================
-- WORKSPACES & TEAMS (B2B)
-- ============================================================

CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    plan            VARCHAR(50) NOT NULL DEFAULT 'free',  -- free, pro, team, enterprise
    logo_url        TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    settings        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE TABLE workspace_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(50) NOT NULL DEFAULT 'member',  -- owner, admin, member, viewer
    invited_by      UUID REFERENCES users(id),
    accepted_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, user_id)
);

CREATE TABLE workspace_invitations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    email           VARCHAR(255) NOT NULL,
    role            VARCHAR(50) NOT NULL DEFAULT 'member',
    token           VARCHAR(255) UNIQUE NOT NULL,
    invited_by      UUID NOT NULL REFERENCES users(id),
    expires_at      TIMESTAMPTZ NOT NULL,
    accepted_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- TARGETS & SCANS
-- ============================================================

CREATE TABLE targets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by      UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(50) NOT NULL,  -- url, ip, domain, cidr
    value           TEXT NOT NULL,         -- URL ou IP encriptado
    description     TEXT,
    tags            TEXT[] DEFAULT '{}',
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE, -- ownership verified
    verification_token VARCHAR(255),
    last_scanned_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);

CREATE INDEX idx_targets_workspace ON targets(workspace_id) WHERE deleted_at IS NULL;

CREATE TABLE scans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES targets(id) ON DELETE RESTRICT,
    created_by      UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(255),
    status          VARCHAR(50) NOT NULL DEFAULT 'queued',
        -- queued, running, paused, completed, failed, cancelled
    scan_type       VARCHAR(50) NOT NULL DEFAULT 'full',
        -- full, passive, active, custom
    config          JSONB NOT NULL DEFAULT '{}',
        -- { engines: [], depth: 2, auth: {...}, modules: [] }
    priority        SMALLINT NOT NULL DEFAULT 5,  -- 1 (urgent) to 10 (low)
    progress        SMALLINT NOT NULL DEFAULT 0,  -- 0-100
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    duration_seconds INTEGER,
    worker_id       VARCHAR(255),  -- Celery worker que processou
    error_message   TEXT,
    statistics      JSONB NOT NULL DEFAULT '{}',
        -- { total_findings: 0, critical: 0, high: 0, medium: 0, low: 0, info: 0 }
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scans_workspace ON scans(workspace_id, created_at DESC);
CREATE INDEX idx_scans_status ON scans(status) WHERE status IN ('queued', 'running');
CREATE INDEX idx_scans_target ON scans(target_id);

CREATE TABLE findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id         UUID NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    -- Identificação
    title           VARCHAR(500) NOT NULL,
    type            VARCHAR(100) NOT NULL,  -- sqli, xss, ssrf, etc.
    description     TEXT NOT NULL,
    -- Severidade
    severity        VARCHAR(20) NOT NULL,   -- critical, high, medium, low, info
    cvss_score      DECIMAL(4,1),
    cvss_vector     VARCHAR(255),
    cwe_id          VARCHAR(20),            -- ex: CWE-79
    owasp_category  VARCHAR(100),
    -- Localização
    endpoint        TEXT NOT NULL,
    method          VARCHAR(10),            -- GET, POST, etc.
    parameter       TEXT,
    evidence        TEXT,                   -- Request/response snippet encriptado
    -- Reprodução
    proof_of_concept TEXT,                  -- PoC instructions
    curl_command    TEXT,                   -- curl testável
    -- Remediação
    remediation     TEXT NOT NULL,
    remediation_code JSONB,                 -- { language: code_snippet }
    references      TEXT[],                 -- CVE, OWASP links
    -- Estado
    status          VARCHAR(50) NOT NULL DEFAULT 'open',
        -- open, confirmed, false_positive, fixed, wont_fix
    verified_at     TIMESTAMPTZ,
    verified_by     UUID REFERENCES users(id),
    fixed_at        TIMESTAMPTZ,
    assignee_id     UUID REFERENCES users(id),
    -- Metadados
    engine          VARCHAR(100),           -- nuclei, custom, ai
    template_id     VARCHAR(255),           -- Nuclei template ID
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_findings_scan ON findings(scan_id);
CREATE INDEX idx_findings_workspace_severity ON findings(workspace_id, severity);
CREATE INDEX idx_findings_status ON findings(workspace_id, status) WHERE status = 'open';

CREATE TABLE finding_comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id      UUID NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id),
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- BILLING & SUBSCRIPTIONS
-- ============================================================

CREATE TABLE plans (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL UNIQUE,  -- free, pro, team, enterprise
    display_name    VARCHAR(255) NOT NULL,
    price_monthly   DECIMAL(10,2) NOT NULL DEFAULT 0,
    price_yearly    DECIMAL(10,2) NOT NULL DEFAULT 0,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    features        JSONB NOT NULL DEFAULT '{}',
    limits          JSONB NOT NULL DEFAULT '{}',
        -- { scans_per_month: 5, targets: 1, users: 1, api_access: false }
    stripe_price_monthly_id VARCHAR(255),
    stripe_price_yearly_id  VARCHAR(255),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    plan_id         UUID NOT NULL REFERENCES plans(id),
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
        -- trialing, active, past_due, cancelled, unpaid
    billing_cycle   VARCHAR(20) NOT NULL DEFAULT 'monthly',  -- monthly, yearly
    stripe_subscription_id VARCHAR(255) UNIQUE,
    stripe_customer_id     VARCHAR(255),
    current_period_start   TIMESTAMPTZ NOT NULL,
    current_period_end     TIMESTAMPTZ NOT NULL,
    cancel_at_period_end   BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at    TIMESTAMPTZ,
    trial_end       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_stripe ON subscriptions(stripe_subscription_id);

CREATE TABLE invoices (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE RESTRICT,
    subscription_id UUID REFERENCES subscriptions(id),
    stripe_invoice_id VARCHAR(255) UNIQUE,
    amount          DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    status          VARCHAR(50) NOT NULL,  -- draft, open, paid, void, uncollectible
    pdf_url         TEXT,
    period_start    TIMESTAMPTZ,
    period_end      TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE usage_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    scans_count     INTEGER NOT NULL DEFAULT 0,
    api_calls_count INTEGER NOT NULL DEFAULT 0,
    findings_count  INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, period_start)
);

-- ============================================================
-- BUG BOUNTY
-- ============================================================

CREATE TABLE bounty_programs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT NOT NULL,
    rules           TEXT NOT NULL,
    scope           JSONB NOT NULL DEFAULT '{}',
        -- { in_scope: [...], out_of_scope: [...] }
    rewards         JSONB NOT NULL DEFAULT '{}',
        -- { critical: 5000, high: 2000, medium: 500, low: 100 }
    type            VARCHAR(20) NOT NULL DEFAULT 'public',  -- public, private
    status          VARCHAR(20) NOT NULL DEFAULT 'draft',
        -- draft, active, paused, closed
    total_paid      DECIMAL(10,2) NOT NULL DEFAULT 0,
    submissions_count INTEGER NOT NULL DEFAULT 0,
    hall_of_fame_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    disclosure_policy VARCHAR(50) DEFAULT 'coordinated',
    response_sla_hours INTEGER NOT NULL DEFAULT 72,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE bounty_submissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id      UUID NOT NULL REFERENCES bounty_programs(id) ON DELETE RESTRICT,
    researcher_id   UUID NOT NULL REFERENCES users(id),
    title           VARCHAR(500) NOT NULL,
    vulnerability_type VARCHAR(100) NOT NULL,
    severity        VARCHAR(20) NOT NULL,
    cvss_score      DECIMAL(4,1),
    description     TEXT NOT NULL,
    steps_to_reproduce TEXT NOT NULL,
    impact          TEXT NOT NULL,
    proof_of_concept TEXT,
    attachments     TEXT[],
    status          VARCHAR(50) NOT NULL DEFAULT 'new',
        -- new, triaging, needs_info, valid, duplicate, invalid,
        -- informational, resolved, paid
    reward_amount   DECIMAL(10,2),
    triaged_by      UUID REFERENCES users(id),
    triaged_at      TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    paid_at         TIMESTAMPTZ,
    platform_fee    DECIMAL(10,2),     -- 15% de fee
    disclosure_date TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE bounty_payouts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id   UUID NOT NULL REFERENCES bounty_submissions(id),
    researcher_id   UUID NOT NULL REFERENCES users(id),
    amount          DECIMAL(10,2) NOT NULL,
    platform_fee    DECIMAL(10,2) NOT NULL,
    net_amount      DECIMAL(10,2) NOT NULL,
    currency        VARCHAR(3) NOT NULL DEFAULT 'USD',
    method          VARCHAR(50) NOT NULL,  -- stripe, wire, crypto
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    transaction_id  VARCHAR(255),
    paid_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- EASM — EXTERNAL ATTACK SURFACE
-- ============================================================

CREATE TABLE easm_assets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    type            VARCHAR(50) NOT NULL,  -- subdomain, ip, port, certificate, email
    value           TEXT NOT NULL,
    parent_id       UUID REFERENCES easm_assets(id),
    source          VARCHAR(100),          -- dns, shodan, censys, ct_logs
    risk_score      SMALLINT DEFAULT 0,    -- 0-100
    is_known        BOOLEAN NOT NULL DEFAULT FALSE,  -- shadow IT detection
    metadata        JSONB NOT NULL DEFAULT '{}',
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, type, value)
);

CREATE TABLE easm_changes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    asset_id        UUID NOT NULL REFERENCES easm_assets(id) ON DELETE CASCADE,
    change_type     VARCHAR(50) NOT NULL,  -- added, removed, modified
    field_changed   VARCHAR(100),
    old_value       TEXT,
    new_value       TEXT,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- MARKETPLACE
-- ============================================================

CREATE TABLE marketplace_modules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id       UUID NOT NULL REFERENCES users(id),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT NOT NULL,
    category        VARCHAR(100) NOT NULL,
    tags            TEXT[] DEFAULT '{}',
    version         VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    price           DECIMAL(10,2) NOT NULL DEFAULT 0,  -- 0 = free
    is_certified    BOOLEAN NOT NULL DEFAULT FALSE,
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, approved, rejected, deprecated
    downloads_count INTEGER NOT NULL DEFAULT 0,
    rating_avg      DECIMAL(3,2),
    rating_count    INTEGER NOT NULL DEFAULT 0,
    repository_url  TEXT,
    documentation_url TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE module_installations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    module_id       UUID NOT NULL REFERENCES marketplace_modules(id),
    installed_by    UUID NOT NULL REFERENCES users(id),
    version         VARCHAR(20) NOT NULL,
    license_key     VARCHAR(255),
    installed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, module_id)
);

-- ============================================================
-- REPORTS
-- ============================================================

CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    scan_id         UUID REFERENCES scans(id),
    created_by      UUID NOT NULL REFERENCES users(id),
    type            VARCHAR(50) NOT NULL,   -- technical, executive, compliance
    format          VARCHAR(20) NOT NULL,   -- pdf, json, csv
    status          VARCHAR(50) NOT NULL DEFAULT 'generating',
    file_url        TEXT,                   -- MinIO/S3 URL
    file_size       BIGINT,
    expires_at      TIMESTAMPTZ,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    workspace_id    UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    type            VARCHAR(100) NOT NULL,
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    action_url      TEXT,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read, created_at DESC);
```

### 5.3 TimescaleDB — Dados de Séries Temporais

```sql
-- Hypertable para logs de scans (performance em queries temporais)
CREATE TABLE scan_events (
    time            TIMESTAMPTZ NOT NULL,
    scan_id         UUID NOT NULL,
    workspace_id    UUID NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}',
    severity        VARCHAR(20)
);

SELECT create_hypertable('scan_events', 'time');
CREATE INDEX idx_scan_events_scan ON scan_events(scan_id, time DESC);

-- Métricas de segurança por workspace ao longo do tempo
CREATE TABLE security_metrics (
    time            TIMESTAMPTZ NOT NULL,
    workspace_id    UUID NOT NULL,
    open_findings   INTEGER NOT NULL DEFAULT 0,
    critical_count  INTEGER NOT NULL DEFAULT 0,
    high_count      INTEGER NOT NULL DEFAULT 0,
    risk_score      DECIMAL(5,2) NOT NULL DEFAULT 0,
    scans_run       INTEGER NOT NULL DEFAULT 0
);

SELECT create_hypertable('security_metrics', 'time');
```

---

## 6. Especificação da API

### 6.1 Convenções

- Base URL: `https://api.hackscan.pro/v1/`
- Formato: JSON em todos os requests e responses
- Auth: `Authorization: Bearer <JWT>` ou `X-API-Key: hs_live_<key>`
- Paginação: cursor-based (`?cursor=<token>&limit=20`)
- Versionamento: prefixo na URL (`/v1/`, `/v2/`)
- Erros: RFC 7807 Problem Details

```json
// Formato de erro padrão (RFC 7807)
{
  "type": "https://api.hackscan.pro/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "The request body contains invalid data",
  "instance": "/v1/scans/",
  "errors": {
    "target_id": ["This field is required."]
  }
}
```

### 6.2 Endpoints Principais

#### Auth

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/v1/auth/register/` | Registo de nova conta |
| POST | `/v1/auth/login/` | Login (retorna access + refresh token) |
| POST | `/v1/auth/refresh/` | Renovar access token |
| POST | `/v1/auth/logout/` | Revogar refresh token |
| POST | `/v1/auth/2fa/setup/` | Setup de TOTP 2FA |
| POST | `/v1/auth/2fa/verify/` | Verificar código TOTP |
| POST | `/v1/auth/2fa/disable/` | Desactivar 2FA |
| POST | `/v1/auth/password/reset/request/` | Pedir reset de password |
| POST | `/v1/auth/password/reset/confirm/` | Confirmar reset com token |
| GET | `/v1/auth/me/` | Perfil do utilizador autenticado |

#### Scans

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/v1/scans/` | Listar scans do workspace |
| POST | `/v1/scans/` | Criar e iniciar novo scan |
| GET | `/v1/scans/{id}/` | Detalhes de um scan |
| DELETE | `/v1/scans/{id}/` | Cancelar/remover scan |
| POST | `/v1/scans/{id}/pause/` | Pausar scan em execução |
| POST | `/v1/scans/{id}/resume/` | Retomar scan pausado |
| GET | `/v1/scans/{id}/findings/` | Findings de um scan |
| GET | `/v1/scans/{id}/events/` | Eventos em tempo real (SSE) |
| POST | `/v1/scans/{id}/report/` | Gerar relatório |

#### Findings

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/v1/findings/` | Listar todos os findings do workspace |
| GET | `/v1/findings/{id}/` | Detalhes de um finding |
| PATCH | `/v1/findings/{id}/` | Actualizar status/assignee |
| POST | `/v1/findings/{id}/comments/` | Adicionar comentário |
| GET | `/v1/findings/{id}/comments/` | Listar comentários |

#### Targets

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/v1/targets/` | Listar targets do workspace |
| POST | `/v1/targets/` | Criar novo target |
| GET | `/v1/targets/{id}/` | Detalhes de um target |
| PATCH | `/v1/targets/{id}/` | Actualizar target |
| DELETE | `/v1/targets/{id}/` | Remover target |
| POST | `/v1/targets/{id}/verify/` | Verificar ownership |

#### Billing

| Method | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/v1/billing/subscription/` | Subscripção actual |
| POST | `/v1/billing/subscription/` | Criar subscripção |
| PATCH | `/v1/billing/subscription/` | Mudar plano |
| DELETE | `/v1/billing/subscription/` | Cancelar subscripção |
| GET | `/v1/billing/invoices/` | Listar invoices |
| GET | `/v1/billing/usage/` | Uso actual do período |
| POST | `/v1/billing/portal/` | URL para portal Stripe |

#### WebSocket — Real-time

```
wss://api.hackscan.pro/ws/scans/{scan_id}/
```

Eventos emitidos pelo servidor:

```json
// Progresso de scan
{ "type": "scan.progress", "data": { "progress": 45, "current_check": "XSS Detection" } }

// Novo finding encontrado
{ "type": "scan.finding", "data": { "id": "...", "severity": "high", "title": "SQLi found" } }

// Scan concluído
{ "type": "scan.completed", "data": { "duration": 142, "total_findings": 7 } }

// Linha de output (terminal simulado)
{ "type": "scan.output", "data": { "line": "[nuclei] Testing /login for SQLi..." } }
```

---

## 7. Módulos Funcionais — Spec Detalhada

### 7.1 Auth & Gestão de Utilizadores

#### Fluxo de Registo

```
1. POST /v1/auth/register/ { email, password, full_name }
2. Validar: email único, password strength (min 12 chars, 1 uppercase, 1 number, 1 special)
3. Criar User com password_hash = bcrypt(password, rounds=12)
4. Enviar email de verificação com token JWT de curta duração (24h)
5. Retornar 201 com mensagem (sem token — aguarda verificação)
6. GET /v1/auth/verify-email/?token=<jwt>
7. Activar email_verified=True, criar Workspace pessoal, criar Subscription(free)
8. Retornar access token + refresh token
```

#### JWT — Configuração

```python
# config/settings/base.py
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),  # curto — segurança
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,  # novo refresh a cada uso
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "RS256",  # RSA assimétrico — melhor que HS256
    "SIGNING_KEY": env("JWT_PRIVATE_KEY"),
    "VERIFYING_KEY": env("JWT_PUBLIC_KEY"),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "users.serializers.CustomTokenObtainSerializer",
}
```

#### 2FA — TOTP

```python
# users/services.py
import pyotp
import qrcode
from django_encrypted_fields.fields import EncryptedCharField

class TwoFactorService:
    
    @staticmethod
    def generate_secret() -> str:
        """Gera secret TOTP — armazenado encriptado."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_qr_code_url(user: User, secret: str) -> str:
        """Gera URL para QR code de setup."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(
            name=user.email,
            issuer_name="HackScan Pro"
        )
    
    @staticmethod
    def verify_code(user: User, code: str) -> bool:
        """Verifica código TOTP com janela de ±1 período."""
        if not user.totp_secret:
            return False
        totp = pyotp.TOTP(user.totp_secret)
        return totp.verify(code, valid_window=1)
    
    @staticmethod
    def verify_and_enable(user: User, code: str) -> list[str]:
        """Verifica código, activa 2FA e retorna backup codes."""
        if not TwoFactorService.verify_code(user, code):
            raise ValidationError("Código inválido.")
        backup_codes = TwoFactorService._generate_backup_codes()
        user.totp_enabled = True
        # Armazenar backup codes como hashes
        BackupCode.objects.bulk_create([
            BackupCode(user=user, code_hash=make_password(code))
            for code in backup_codes
        ])
        user.save(update_fields=["totp_enabled"])
        return backup_codes
    
    @staticmethod
    def _generate_backup_codes(count: int = 8) -> list[str]:
        """Gera códigos de backup únicos."""
        return [secrets.token_hex(4).upper() for _ in range(count)]
```

#### RBAC — Permissões

```python
# core/permissions.py
from rest_framework.permissions import BasePermission

class WorkspacePermission(BasePermission):
    """
    Verifica se o utilizador tem a role necessária no workspace.
    Uso: permission_classes = [IsAuthenticated, WorkspacePermission]
    """
    
    required_role = "member"  # Override nas views
    
    def has_permission(self, request, view) -> bool:
        workspace_id = view.kwargs.get("workspace_id") or \
                       request.data.get("workspace_id") or \
                       request.query_params.get("workspace_id")
        
        if not workspace_id:
            return False
        
        return WorkspaceMember.objects.filter(
            workspace_id=workspace_id,
            user=request.user,
            role__in=self._get_allowed_roles()
        ).exists()
    
    def _get_allowed_roles(self) -> list[str]:
        role_hierarchy = {
            "viewer": ["viewer", "member", "admin", "owner"],
            "member": ["member", "admin", "owner"],
            "admin": ["admin", "owner"],
            "owner": ["owner"],
        }
        return role_hierarchy.get(self.required_role, [])

class IsWorkspaceAdmin(WorkspacePermission):
    required_role = "admin"

class IsWorkspaceOwner(WorkspacePermission):
    required_role = "owner"
```

### 7.2 Scanner de Vulnerabilidades

#### Engine Architecture (Strategy Pattern)

```python
# scans/engines/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator

@dataclass
class ScanConfig:
    target_url: str
    scan_type: str
    depth: int = 2
    auth: dict | None = None
    modules: list[str] | None = None
    timeout_seconds: int = 300

@dataclass
class FindingResult:
    title: str
    type: str
    severity: str
    endpoint: str
    method: str | None
    parameter: str | None
    description: str
    evidence: str | None
    proof_of_concept: str | None
    curl_command: str | None
    remediation: str
    cvss_score: float | None
    cwe_id: str | None
    template_id: str | None
    metadata: dict

class BaseEngine(ABC):
    """Interface base para todos os scan engines."""
    
    name: str
    supported_types: list[str]
    
    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o engine está disponível para execução."""
        ...
    
    @abstractmethod
    def run(
        self, 
        config: ScanConfig,
    ) -> Generator[FindingResult, None, None]:
        """
        Executa o scan e yield de cada finding encontrado.
        Generator permite streaming de resultados em tempo real.
        """
        ...
    
    @abstractmethod
    def validate_config(self, config: ScanConfig) -> list[str]:
        """Retorna lista de erros de validação (vazio = válido)."""
        ...


# scans/engines/nuclei.py
import subprocess
import json
import shutil
from pathlib import Path
from .base import BaseEngine, ScanConfig, FindingResult

class NucleiEngine(BaseEngine):
    name = "nuclei"
    supported_types = ["full", "active", "custom"]
    
    SEVERITY_MAP = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "info",
        "unknown": "info",
    }
    
    def is_available(self) -> bool:
        return shutil.which("nuclei") is not None
    
    def validate_config(self, config: ScanConfig) -> list[str]:
        errors = []
        if not config.target_url.startswith(("http://", "https://")):
            errors.append("target_url deve começar com http:// ou https://")
        return errors
    
    def run(self, config: ScanConfig) -> Generator[FindingResult, None, None]:
        cmd = self._build_command(config)
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        
        for line in iter(process.stdout.readline, ""):
            if not line.strip():
                continue
            try:
                result = json.loads(line)
                finding = self._parse_result(result)
                if finding:
                    yield finding
            except json.JSONDecodeError:
                continue
        
        process.wait()
        if process.returncode not in (0, 1):  # 1 = findings found
            stderr = process.stderr.read()
            raise RuntimeError(f"Nuclei falhou: {stderr[:500]}")
    
    def _build_command(self, config: ScanConfig) -> list[str]:
        cmd = [
            "nuclei",
            "-u", config.target_url,
            "-json",
            "-silent",
            "-timeout", str(config.timeout_seconds),
            "-max-redirects", "5",
            "-no-color",
        ]
        
        # Templates por tipo de scan
        if config.scan_type == "passive":
            cmd.extend(["-tags", "passive"])
        elif config.scan_type == "full":
            cmd.extend(["-severity", "critical,high,medium,low"])
        
        # Auth se disponível
        if config.auth:
            if config.auth.get("type") == "bearer":
                cmd.extend(["-header", f"Authorization: Bearer {config.auth['token']}"])
            elif config.auth.get("type") == "cookie":
                cmd.extend(["-header", f"Cookie: {config.auth['cookie']}"])
        
        return cmd
    
    def _parse_result(self, raw: dict) -> FindingResult | None:
        info = raw.get("info", {})
        return FindingResult(
            title=info.get("name", "Unknown"),
            type=raw.get("template-id", "generic").replace("-", "_"),
            severity=self.SEVERITY_MAP.get(info.get("severity", "info"), "info"),
            endpoint=raw.get("matched-at", raw.get("host", "")),
            method=raw.get("request", {}).get("method"),
            parameter=raw.get("matcher-name"),
            description=info.get("description", ""),
            evidence=raw.get("response"),
            proof_of_concept=raw.get("request"),
            curl_command=self._build_curl(raw),
            remediation=info.get("remediation", "Consulte a documentação OWASP."),
            cvss_score=info.get("classification", {}).get("cvss-score"),
            cwe_id=self._extract_cwe(info),
            template_id=raw.get("template-id"),
            metadata={"raw": raw},
        )
    
    def _build_curl(self, raw: dict) -> str | None:
        req = raw.get("request", {})
        if not req:
            return None
        method = req.get("method", "GET")
        url = raw.get("matched-at", "")
        headers = " ".join(
            f'-H "{k}: {v}"' 
            for k, v in (req.get("headers") or {}).items()
        )
        body = f"-d '{req.get('body', '')}'" if req.get("body") else ""
        return f"curl -X {method} {headers} {body} '{url}'"
    
    def _extract_cwe(self, info: dict) -> str | None:
        cwes = info.get("classification", {}).get("cwe-id", [])
        return cwes[0] if cwes else None


# scans/engines/registry.py
class EngineRegistry:
    """Registry de todos os engines disponíveis."""
    
    _engines: dict[str, type[BaseEngine]] = {}
    
    @classmethod
    def register(cls, engine_class: type[BaseEngine]) -> type[BaseEngine]:
        """Decorator para registar engines."""
        cls._engines[engine_class.name] = engine_class
        return engine_class
    
    @classmethod
    def get(cls, name: str) -> BaseEngine:
        engine_class = cls._engines.get(name)
        if not engine_class:
            raise ValueError(f"Engine '{name}' não encontrado.")
        return engine_class()
    
    @classmethod
    def get_all_available(cls) -> list[BaseEngine]:
        return [
            engine_class() 
            for engine_class in cls._engines.values()
            if engine_class().is_available()
        ]

# Registo de engines
EngineRegistry.register(NucleiEngine)
```

#### Celery Task — Execução Assíncrona

```python
# scans/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = get_task_logger(__name__)
channel_layer = get_channel_layer()

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=1800,   # 30 min — soft kill
    time_limit=1900,         # 31 min — hard kill
    acks_late=True,          # Confirma só após conclusão
    reject_on_worker_lost=True,
)
def run_scan(self, scan_id: str) -> dict:
    """
    Task principal de execução de scan.
    Executa em container Docker isolado via subprocess.
    """
    from .models import Scan, Finding
    from .engines.registry import EngineRegistry
    
    scan = Scan.objects.select_related("target", "workspace").get(id=scan_id)
    
    # Evitar execução duplicada
    if scan.status not in ("queued", "paused"):
        logger.warning(f"Scan {scan_id} em estado {scan.status} — ignorando.")
        return {"status": "skipped"}
    
    scan.status = "running"
    scan.started_at = timezone.now()
    scan.worker_id = self.request.id
    scan.save(update_fields=["status", "started_at", "worker_id"])
    
    _publish_event(scan_id, "scan.status", {"status": "running"})
    
    try:
        config = ScanConfig(
            target_url=scan.target.value,
            scan_type=scan.scan_type,
            depth=scan.config.get("depth", 2),
            auth=scan.config.get("auth"),
            modules=scan.config.get("modules"),
            timeout_seconds=scan.config.get("timeout", 300),
        )
        
        engines = EngineRegistry.get_all_available()
        findings_created = []
        
        for engine in engines:
            errors = engine.validate_config(config)
            if errors:
                logger.warning(f"Engine {engine.name} config inválida: {errors}")
                continue
            
            _publish_event(scan_id, "scan.output", {
                "line": f"[{engine.name}] Iniciando scan..."
            })
            
            for finding_data in engine.run(config):
                finding = Finding.objects.create(
                    scan=scan,
                    workspace=scan.workspace,
                    engine=engine.name,
                    **finding_data.__dict__,
                )
                findings_created.append(finding)
                
                _publish_event(scan_id, "scan.finding", {
                    "id": str(finding.id),
                    "severity": finding.severity,
                    "title": finding.title,
                    "endpoint": finding.endpoint,
                })
        
        # Actualizar estatísticas
        stats = _calculate_statistics(findings_created)
        scan.status = "completed"
        scan.completed_at = timezone.now()
        scan.duration_seconds = int(
            (scan.completed_at - scan.started_at).total_seconds()
        )
        scan.statistics = stats
        scan.save(update_fields=[
            "status", "completed_at", "duration_seconds", "statistics"
        ])
        
        _publish_event(scan_id, "scan.completed", {
            "duration": scan.duration_seconds,
            **stats,
        })
        
        # Disparar geração de relatório assíncrono
        generate_scan_report.delay(scan_id=scan_id, report_type="technical")
        
        # Notificar utilizador
        from notifications.tasks import notify_scan_completed
        notify_scan_completed.delay(scan_id=scan_id)
        
        return {"status": "completed", "findings": len(findings_created)}
    
    except SoftTimeLimitExceeded:
        scan.status = "failed"
        scan.error_message = "Scan excedeu o tempo limite."
        scan.save(update_fields=["status", "error_message"])
        _publish_event(scan_id, "scan.failed", {"reason": "timeout"})
        raise
    
    except Exception as exc:
        logger.exception(f"Erro no scan {scan_id}: {exc}")
        
        if self.request.retries < self.max_retries:
            scan.status = "queued"
            scan.save(update_fields=["status"])
            raise self.retry(exc=exc)
        
        scan.status = "failed"
        scan.error_message = str(exc)[:500]
        scan.save(update_fields=["status", "error_message"])
        _publish_event(scan_id, "scan.failed", {"reason": str(exc)[:200]})
        raise


def _publish_event(scan_id: str, event_type: str, data: dict) -> None:
    """Publica evento no canal WebSocket do scan."""
    async_to_sync(channel_layer.group_send)(
        f"scan_{scan_id}",
        {"type": "scan_event", "event": event_type, "data": data},
    )


def _calculate_statistics(findings: list) -> dict:
    from collections import Counter
    severity_counts = Counter(f.severity for f in findings)
    return {
        "total_findings": len(findings),
        "critical": severity_counts.get("critical", 0),
        "high": severity_counts.get("high", 0),
        "medium": severity_counts.get("medium", 0),
        "low": severity_counts.get("low", 0),
        "info": severity_counts.get("info", 0),
    }
```

### 7.3 Dashboard & Real-time

#### Django Channels Consumer

```python
# scans/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class ScanConsumer(AsyncWebsocketConsumer):
    
    async def connect(self):
        self.scan_id = self.scope["url_route"]["kwargs"]["scan_id"]
        self.group_name = f"scan_{self.scan_id}"
        
        # Verificar autenticação
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return
        
        # Verificar permissão no scan
        has_permission = await self._check_permission(user, self.scan_id)
        if not has_permission:
            await self.close(code=4003)
            return
        
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Enviar estado actual do scan ao conectar
        scan_data = await self._get_scan_data()
        await self.send(text_data=json.dumps({
            "type": "scan.connected",
            "data": scan_data,
        }))
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    async def scan_event(self, event):
        """Recebe evento do grupo e envia ao WebSocket cliente."""
        await self.send(text_data=json.dumps({
            "type": event["event"],
            "data": event["data"],
        }))
    
    @database_sync_to_async
    def _check_permission(self, user, scan_id: str) -> bool:
        from .models import Scan
        return Scan.objects.filter(
            id=scan_id,
            workspace__members__user=user,
        ).exists()
    
    @database_sync_to_async
    def _get_scan_data(self) -> dict:
        from .models import Scan
        from .serializers import ScanDetailSerializer
        scan = Scan.objects.select_related("target").get(id=self.scan_id)
        return ScanDetailSerializer(scan).data
```

#### Frontend — Hook de WebSocket

```typescript
// hooks/useScanWebSocket.ts
import { useEffect, useRef, useCallback, useState } from "react";
import { ScanEvent, ScanFinding } from "@/types/scans";

interface UseScanWebSocketOptions {
  scanId: string;
  onFinding?: (finding: ScanFinding) => void;
  onCompleted?: (stats: Record<string, number>) => void;
}

export function useScanWebSocket({
  scanId,
  onFinding,
  onCompleted,
}: UseScanWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const [outputLines, setOutputLines] = useState<string[]>([]);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const maxReconnects = 5;
  const reconnectCount = useRef(0);

  const connect = useCallback(() => {
    const token = localStorage.getItem("access_token");
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/scans/${scanId}/?token=${token}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
      reconnectCount.current = 0;
    };

    ws.onmessage = (event) => {
      const message: ScanEvent = JSON.parse(event.data);
      
      switch (message.type) {
        case "scan.output":
          setOutputLines((prev) => [...prev.slice(-500), message.data.line]); // max 500 linhas
          break;
        case "scan.finding":
          onFinding?.(message.data as ScanFinding);
          break;
        case "scan.completed":
          onCompleted?.(message.data);
          break;
      }
    };

    ws.onclose = (event) => {
      setStatus("disconnected");
      // Reconectar automaticamente se não foi fechar intencional
      if (event.code !== 1000 && reconnectCount.current < maxReconnects) {
        const delay = Math.min(1000 * 2 ** reconnectCount.current, 30000);
        reconnectCount.current++;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [scanId, onFinding, onCompleted]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimeoutRef.current);
      wsRef.current?.close(1000); // fechar limpo
    };
  }, [connect]);

  return { status, outputLines };
}
```

### 7.4 Billing & Planos

#### Stripe Integration

```python
# billing/services.py
import stripe
from django.conf import settings
from .models import Subscription, Plan, Invoice

stripe.api_key = settings.STRIPE_SECRET_KEY

class BillingService:
    
    @staticmethod
    def create_checkout_session(
        workspace,
        plan: Plan,
        billing_cycle: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Cria sessão de checkout Stripe e retorna URL."""
        price_id = (
            plan.stripe_price_monthly_id 
            if billing_cycle == "monthly" 
            else plan.stripe_price_yearly_id
        )
        
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "workspace_id": str(workspace.id),
                "plan_id": str(plan.id),
                "billing_cycle": billing_cycle,
            },
            subscription_data={
                "metadata": {"workspace_id": str(workspace.id)},
            },
        )
        return session.url
    
    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> None:
        """Processa webhooks Stripe de forma idempotente."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise ValueError("Assinatura do webhook inválida.")
        
        handlers = {
            "checkout.session.completed": BillingService._handle_checkout_completed,
            "invoice.payment_succeeded": BillingService._handle_payment_succeeded,
            "invoice.payment_failed": BillingService._handle_payment_failed,
            "customer.subscription.updated": BillingService._handle_subscription_updated,
            "customer.subscription.deleted": BillingService._handle_subscription_deleted,
        }
        
        handler = handlers.get(event["type"])
        if handler:
            handler(event["data"]["object"])
    
    @staticmethod
    def _handle_checkout_completed(session: dict) -> None:
        workspace_id = session["metadata"]["workspace_id"]
        plan_id = session["metadata"]["plan_id"]
        billing_cycle = session["metadata"]["billing_cycle"]
        stripe_sub_id = session["subscription"]
        
        stripe_sub = stripe.Subscription.retrieve(stripe_sub_id)
        
        Subscription.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={
                "plan_id": plan_id,
                "status": "active",
                "billing_cycle": billing_cycle,
                "stripe_subscription_id": stripe_sub_id,
                "stripe_customer_id": session["customer"],
                "current_period_start": datetime.fromtimestamp(
                    stripe_sub["current_period_start"], tz=timezone.utc
                ),
                "current_period_end": datetime.fromtimestamp(
                    stripe_sub["current_period_end"], tz=timezone.utc
                ),
            },
        )

    @staticmethod
    def check_quota(workspace, action: str) -> tuple[bool, str]:
        """
        Verifica se o workspace pode executar a acção.
        Retorna (allowed, reason).
        """
        subscription = workspace.subscription
        plan = subscription.plan
        limits = plan.limits
        
        if action == "create_scan":
            if limits.get("scans_per_month") == -1:  # ilimitado
                return True, ""
            usage = UsageRecord.get_current_period_usage(workspace)
            if usage.scans_count >= limits["scans_per_month"]:
                return False, f"Limite de {limits['scans_per_month']} scans/mês atingido."
        
        return True, ""
```

#### Quota Middleware

```python
# core/middleware/quota.py
class QuotaCheckMixin:
    """
    Mixin para views que consomem quota.
    Adicionar em views de criação de scan.
    """
    quota_action: str = None
    
    def create(self, request, *args, **kwargs):
        workspace = self.get_workspace()
        allowed, reason = BillingService.check_quota(workspace, self.quota_action)
        
        if not allowed:
            return Response(
                {"detail": reason, "upgrade_url": "/billing/upgrade/"},
                status=status.HTTP_402_PAYMENT_REQUIRED,
            )
        
        return super().create(request, *args, **kwargs)
```

### 7.5 AI Engine

#### Claude Integration — AI Chat e Forecaster

```python
# ai/services.py
import anthropic
from django.conf import settings

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

class AIService:
    
    SYSTEM_PROMPT = """Você é um especialista em cibersegurança da HackScan Pro.
Responda sempre em Português. Seja técnico mas claro.
Para vulnerabilidades, explique: o que é, como funciona, impacto real, como corrigir.
Para payloads, forneça exemplos educativos com avisos de uso ético.
Nunca auxilie em actividades maliciosas contra sistemas sem autorização."""
    
    @staticmethod
    def explain_finding(finding) -> str:
        """Gera explicação detalhada de uma vulnerabilidade."""
        prompt = f"""Explica esta vulnerabilidade encontrada:

Título: {finding.title}
Tipo: {finding.type}
Severidade: {finding.severity}
Endpoint: {finding.endpoint}
Parâmetro: {finding.parameter or 'N/A'}
Descrição técnica: {finding.description}
Evidência: {finding.evidence[:500] if finding.evidence else 'N/A'}

Explica:
1. O que é esta vulnerabilidade
2. Como pode ser explorada (sem dar exploit completo)
3. Impacto real para o negócio
4. Como corrigir com código de exemplo
"""
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            system=AIService.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    
    @staticmethod
    def predict_attack_chains(findings: list) -> dict:
        """
        Analisa findings e prediz possíveis chains de ataque.
        Diferencial único da plataforma.
        """
        findings_summary = "\n".join([
            f"- [{f.severity.upper()}] {f.title} @ {f.endpoint}"
            for f in findings[:20]  # Limitar contexto
        ])
        
        prompt = f"""Analisa estas vulnerabilidades encontradas num scan:

{findings_summary}

Identifica:
1. Attack chains possíveis (combinação de vulns para ataque multi-step)
2. Qual seria o caminho mais crítico de um atacante
3. Probabilidade de exploração (0-100) baseada na combinação
4. Prioridade de remediação recomendada

Responde em JSON com formato:
{{
  "risk_score": 0-100,
  "attack_chains": [
    {{
      "name": "...",
      "steps": ["vuln1", "vuln2"],
      "impact": "...",
      "probability": 0-100
    }}
  ],
  "priority_fixes": ["vuln1", "vuln2"],
  "executive_summary": "..."
}}"""
        
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=AIService.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        
        import json
        try:
            return json.loads(message.content[0].text)
        except json.JSONDecodeError:
            return {"error": "Falha ao processar análise de IA"}
    
    @staticmethod
    def generate_remediation_code(finding, language: str) -> str:
        """Gera código de remediação específico para a linguagem."""
        prompt = f"""Gera código de remediação em {language} para esta vulnerabilidade:

Tipo: {finding.type}
Endpoint afectado: {finding.endpoint}
Parâmetro: {finding.parameter or 'N/A'}

Forneça:
1. Código vulnerável (exemplo simplificado)
2. Código corrigido com comentários explicativos
3. Imports/dependências necessárias
4. Testes unitários básicos para verificar a correcção

Formato: código limpo e pronto para produção."""
        
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2000,
            system=AIService.SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
```

### 7.6 Bug Bounty

#### Ciclo de Vida de uma Submissão

```
Researcher submete → NEW
       ↓
Triage automático (AI) → TRIAGING
       ↓
Validação humana (opcional)
       ↓
VALID / DUPLICATE / INVALID / INFORMATIONAL
       ↓ (se VALID)
Negociação de reward
       ↓
RESOLVED → PAID
       ↓ (opcional)
Disclosure coordenado
```

```python
# bounty/services.py
class BountyTriageService:
    
    @staticmethod
    def auto_triage(submission) -> dict:
        """
        Triage automático com IA.
        Verifica duplicatas e avalia qualidade da submissão.
        """
        # Verificar duplicatas por tipo + endpoint
        duplicate = BountySubmission.objects.filter(
            program=submission.program,
            vulnerability_type=submission.vulnerability_type,
            status__in=["valid", "resolved"],
        ).exclude(id=submission.id).first()
        
        if duplicate:
            return {
                "verdict": "duplicate",
                "duplicate_of": str(duplicate.id),
                "reason": f"Vulnerabilidade já reportada em #{duplicate.id[:8]}",
            }
        
        # Avaliar qualidade com IA
        quality_score = BountyTriageService._evaluate_quality(submission)
        
        return {
            "verdict": "needs_review" if quality_score >= 60 else "needs_info",
            "quality_score": quality_score,
            "ai_assessment": quality_score >= 60,
        }
    
    @staticmethod
    def _evaluate_quality(submission) -> int:
        """Pontua a qualidade do relatório (0-100)."""
        score = 0
        
        # Passos de reprodução presentes e detalhados
        if len(submission.steps_to_reproduce) > 100:
            score += 30
        
        # Prova de conceito
        if submission.proof_of_concept:
            score += 20
        
        # Descrição de impacto
        if len(submission.impact) > 50:
            score += 20
        
        # CVSS score fornecido
        if submission.cvss_score:
            score += 10
        
        # Descrição técnica
        if len(submission.description) > 100:
            score += 20
        
        return min(score, 100)
    
    @staticmethod
    def calculate_reward(submission, program) -> float:
        """Calcula reward baseado na severidade e qualidade."""
        base_rewards = program.rewards
        severity = submission.severity
        
        base = base_rewards.get(severity, 0)
        
        # Bónus por qualidade excepcional
        quality = BountyTriageService._evaluate_quality(submission)
        if quality >= 90:
            base *= 1.25
        
        return round(base, 2)
    
    @staticmethod
    def process_payout(submission, amount: float) -> None:
        """Processa pagamento ao researcher."""
        PLATFORM_FEE_PCT = 0.15
        platform_fee = round(amount * PLATFORM_FEE_PCT, 2)
        net_amount = amount - platform_fee
        
        payout = BountyPayout.objects.create(
            submission=submission,
            researcher=submission.researcher,
            amount=amount,
            platform_fee=platform_fee,
            net_amount=net_amount,
            currency="USD",
            method="stripe",
            status="pending",
        )
        
        # Disparar pagamento via Stripe Connect
        from .tasks import process_stripe_payout
        process_stripe_payout.delay(payout_id=str(payout.id))
```

### 7.7 EASM — Attack Surface Management

```python
# easm/services.py
import shodan
from celery import shared_task
from dns import resolver

class EASMService:
    
    @staticmethod
    def discover_subdomains(domain: str) -> list[str]:
        """Descobre subdomínios via múltiplas fontes."""
        subdomains = set()
        
        # DNS brute-force com wordlist
        subdomains.update(EASMService._dns_bruteforce(domain))
        
        # Certificate Transparency logs
        subdomains.update(EASMService._ct_logs(domain))
        
        # Shodan
        subdomains.update(EASMService._shodan_search(domain))
        
        return list(subdomains)
    
    @staticmethod
    def _ct_logs(domain: str) -> list[str]:
        """Consulta Certificate Transparency logs via crt.sh."""
        import requests
        try:
            resp = requests.get(
                f"https://crt.sh/?q=%.{domain}&output=json",
                timeout=10,
            )
            resp.raise_for_status()
            entries = resp.json()
            return list({
                entry["name_value"].strip()
                for entry in entries
                if entry.get("name_value")
            })
        except Exception:
            return []
    
    @staticmethod
    def _shodan_search(domain: str) -> list[str]:
        """Pesquisa Shodan por IPs e subdomínios relacionados."""
        if not settings.SHODAN_API_KEY:
            return []
        try:
            api = shodan.Shodan(settings.SHODAN_API_KEY)
            results = api.search(f"hostname:{domain}", limit=100)
            return [
                match["hostnames"][0]
                for match in results["matches"]
                if match.get("hostnames")
            ]
        except Exception:
            return []
    
    @staticmethod
    def detect_changes(workspace_id: str) -> list[dict]:
        """Detecta novos activos ou alterações desde última verificação."""
        # Implementação de diff entre estado actual e anterior
        pass


@shared_task
def run_easm_discovery(workspace_id: str) -> None:
    """Task periódica de descoberta de superfície de ataque."""
    from .models import EASMAsset, EASMChange
    
    workspace = Workspace.objects.get(id=workspace_id)
    targets = workspace.targets.filter(deleted_at__isnull=True)
    
    for target in targets:
        if target.type == "domain":
            subdomains = EASMService.discover_subdomains(target.value)
            
            for subdomain in subdomains:
                asset, created = EASMAsset.objects.update_or_create(
                    workspace=workspace,
                    type="subdomain",
                    value=subdomain,
                    defaults={"last_seen_at": timezone.now()},
                )
                
                if created:
                    EASMChange.objects.create(
                        workspace=workspace,
                        asset=asset,
                        change_type="added",
                        new_value=subdomain,
                    )
                    # Notificar utilizador sobre novo activo
                    from notifications.tasks import notify_new_asset
                    notify_new_asset.delay(
                        workspace_id=workspace_id,
                        asset_id=str(asset.id),
                    )
```

### 7.8 Marketplace de Módulos

#### SDK para Developers de Módulos

```python
# packages/scanner-sdk/hackscan_sdk/base.py
"""
HackScan Pro Scanner SDK
Permite criar módulos de scan customizados para o marketplace.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ModuleConfig:
    """Configuração passada ao módulo durante execução."""
    target_url: str
    auth: dict | None = None
    custom_params: dict | None = None

@dataclass  
class ModuleFinding:
    """Resultado de um finding encontrado pelo módulo."""
    title: str
    severity: str          # critical, high, medium, low, info
    description: str
    endpoint: str
    remediation: str
    evidence: str | None = None
    cvss_score: float | None = None

class BaseModule(ABC):
    """
    Classe base para módulos do marketplace.
    
    Exemplo de uso:
    
    class WordPressScanner(BaseModule):
        name = "wordpress-scanner"
        version = "1.0.0"
        description = "Scanner especializado para WordPress"
        author = "Seu Nome"
        
        def run(self, config):
            # seu código aqui
            yield ModuleFinding(...)
    """
    
    name: str
    version: str
    description: str
    author: str
    
    @abstractmethod
    def run(self, config: ModuleConfig) -> Generator[ModuleFinding, None, None]:
        """Executa o scan e yield de cada finding."""
        ...
    
    def validate(self, config: ModuleConfig) -> list[str]:
        """Validação opcional de configuração. Retorna erros."""
        return []
```

### 7.9 Relatórios & Compliance

```python
# reports/generators/pdf.py
from weasyprint import HTML, CSS
from django.template.loader import render_to_string
from .base import BaseReportGenerator

class PDFReportGenerator(BaseReportGenerator):
    
    def generate_technical_report(self, scan) -> bytes:
        """Gera relatório técnico completo em PDF."""
        findings = scan.findings.select_related("assignee").order_by(
            "severity", "type"
        )
        
        context = {
            "scan": scan,
            "target": scan.target,
            "workspace": scan.workspace,
            "findings": findings,
            "findings_by_severity": self._group_by_severity(findings),
            "statistics": scan.statistics,
            "generated_at": timezone.now(),
            "cvss_chart_data": self._prepare_cvss_data(findings),
        }
        
        html_content = render_to_string("reports/technical.html", context)
        
        return HTML(string=html_content).write_pdf(
            stylesheets=[
                CSS(filename="reports/static/report.css"),
            ]
        )
    
    def generate_executive_report(self, scan) -> bytes:
        """
        Relatório executivo — linguagem de negócio.
        Para CISOs e C-level sem jargão técnico.
        """
        ai_analysis = AIService.predict_attack_chains(
            list(scan.findings.all()[:20])
        )
        
        context = {
            "scan": scan,
            "executive_summary": ai_analysis.get("executive_summary", ""),
            "risk_score": ai_analysis.get("risk_score", 0),
            "business_impact": self._calculate_business_impact(scan),
            "top_risks": scan.findings.filter(
                severity__in=["critical", "high"]
            )[:5],
            "remediation_priority": ai_analysis.get("priority_fixes", []),
        }
        
        html_content = render_to_string("reports/executive.html", context)
        return HTML(string=html_content).write_pdf()
    
    def _calculate_business_impact(self, scan) -> dict:
        """Estima impacto financeiro baseado nas vulnerabilidades."""
        # Baseado em custos médios de data breach por severidade
        impact_costs = {
            "critical": 500000,
            "high": 100000,
            "medium": 25000,
            "low": 5000,
        }
        
        total = sum(
            impact_costs.get(f.severity, 0) * 0.1  # probabilidade de exploração
            for f in scan.findings.all()
        )
        
        return {
            "estimated_risk_usd": round(total, -3),  # arredondado a milhares
            "currency": "USD",
        }
```

### 7.10 Colaboração em Equipa

```python
# Integração Jira — envio automático de findings
# notifications/channels/jira.py
import requests
from base64 import b64encode

class JiraIntegration:
    
    def __init__(self, config: dict):
        self.base_url = config["base_url"]
        self.project_key = config["project_key"]
        credentials = b64encode(
            f"{config['email']}:{config['api_token']}".encode()
        ).decode()
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
        }
    
    def create_issue(self, finding) -> str:
        """Cria issue no Jira para um finding e retorna issue key."""
        severity_priority = {
            "critical": "Highest",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
            "info": "Lowest",
        }
        
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": f"[HackScan] {finding.severity.upper()}: {finding.title}",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "type": "text",
                            "text": f"Endpoint: {finding.endpoint}\n\n"
                                    f"Descrição: {finding.description}\n\n"
                                    f"Remediação: {finding.remediation}"
                        }]
                    }]
                },
                "issuetype": {"name": "Bug"},
                "priority": {"name": severity_priority.get(finding.severity, "Medium")},
                "labels": ["hackscan", f"severity-{finding.severity}", finding.type],
            }
        }
        
        resp = requests.post(
            f"{self.base_url}/rest/api/3/issue",
            json=payload,
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["key"]
```

---

## 8. Segurança — Arquitectura Zero-Trust

### 8.1 Principios

1. **Nunca confiar, sempre verificar** — cada request é autenticado e autorizado independentemente
2. **Menor privilégio** — utilizadores e serviços têm apenas as permissões necessárias
3. **Assumir comprometimento** — logs e alertas desenhados para detecção rápida
4. **Defense in depth** — múltiplas camadas de segurança independentes

### 8.2 Protecções Implementadas

```python
# config/settings/base.py — Security headers

SECURE_HSTS_SECONDS = 31536000         # 1 ano
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = True              # Forçar HTTPS
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Strict"
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Content Security Policy via django-csp
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_FONT_SRC = ("'self'",)
CSP_IMG_SRC = ("'self'", "data:")
CSP_CONNECT_SRC = ("'self'", "wss://api.hackscan.pro")

# CORS — apenas origens permitidas
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = ["DELETE", "GET", "PATCH", "POST", "PUT"]
```

### 8.3 Rate Limiting

```python
# core/middleware/rate_limit.py
from django_ratelimit.decorators import ratelimit

# Aplicar em views sensíveis:
# Login: 5 tentativas por 15 minutos por IP
# Register: 3 por hora por IP
# API geral: 1000/hora para plano Pro, 100/hora para Free

RATE_LIMITS = {
    "auth.login": "5/15m",
    "auth.register": "3/h",
    "auth.password_reset": "3/h",
    "auth.totp_verify": "5/15m",
    "scans.create": {
        "free": "5/month",
        "pro": "unlimited",
        "team": "unlimited",
        "enterprise": "unlimited",
    },
    "api.default": {
        "free": "100/h",
        "pro": "1000/h",
        "team": "5000/h",
        "enterprise": "unlimited",
    },
}
```

### 8.4 Sanitização de Inputs de Scan

```python
# scans/validators.py
import ipaddress
import re
from urllib.parse import urlparse

# IPs e ranges privados — nunca permitir scan
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]

BLOCKED_DOMAINS = {
    "localhost", "metadata.google.internal",
    "169.254.169.254",  # AWS/GCP metadata
    "100.100.100.200",  # Alibaba Cloud metadata
}

def validate_scan_target(target_value: str, target_type: str) -> str:
    """
    Valida e sanitiza o target de scan.
    Previne SSRF interno, scan de metadata endpoints, etc.
    Raises ValidationError se inválido.
    """
    if target_type == "url":
        parsed = urlparse(target_value)
        
        if parsed.scheme not in ("http", "https"):
            raise ValidationError("Apenas HTTP e HTTPS são suportados.")
        
        hostname = parsed.hostname
        if not hostname:
            raise ValidationError("URL inválida.")
        
        if hostname.lower() in BLOCKED_DOMAINS:
            raise ValidationError(f"Target '{hostname}' não é permitido.")
        
        # Resolver IP e verificar se é privado
        try:
            ip = ipaddress.ip_address(hostname)
            for private_range in PRIVATE_IP_RANGES:
                if ip in private_range:
                    raise ValidationError("Scan de IPs privados não é permitido.")
        except ValueError:
            pass  # É um hostname, não IP — ok
    
    elif target_type == "ip":
        try:
            ip = ipaddress.ip_address(target_value)
            for private_range in PRIVATE_IP_RANGES:
                if ip in private_range:
                    raise ValidationError("Scan de IPs privados não é permitido.")
        except ValueError:
            raise ValidationError("IP inválido.")
    
    return target_value
```

### 8.5 Encriptação de Dados Sensíveis

```python
# Instalar: pip install django-encrypted-fields
from encrypted_fields.fields import EncryptedTextField, EncryptedCharField

class Target(models.Model):
    # Encriptado em repouso — URL pode conter credenciais
    value = EncryptedTextField()

class APIKey(models.Model):
    # Apenas o hash é guardado, nunca a key original
    key_hash = models.CharField(max_length=255)
    
    @classmethod
    def create(cls, user, name: str, scopes: list) -> tuple["APIKey", str]:
        """Cria API key. Retorna o objecto e a key raw (mostrar só uma vez)."""
        import secrets, hashlib
        raw_key = f"hs_live_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        key_prefix = raw_key[:8]
        
        api_key = cls.objects.create(
            user=user,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=scopes,
        )
        return api_key, raw_key  # raw_key nunca mais é acessível
```

---

## 9. Escalabilidade e Performance

### 9.1 Kubernetes — Configuração Base

```yaml
# infra/kubernetes/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hackscan-api
  namespace: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hackscan-api
  template:
    spec:
      containers:
      - name: api
        image: hackscan/api:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready/
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        envFrom:
        - secretRef:
            name: hackscan-secrets
        - configMapRef:
            name: hackscan-config

---
# HPA — auto-scaling por CPU
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hackscan-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hackscan-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

---
# Scanner workers com HPA por tamanho da queue
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: hackscan-scanner-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: hackscan-scanner
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: External
    external:
      metric:
        name: rabbitmq_queue_messages
        selector:
          matchLabels:
            queue: "scans"
      target:
        type: AverageValue
        averageValue: "10"  # 1 worker por 10 scans na queue
```

### 9.2 Caching Strategy

```python
# Cache layers:
# L1: Django in-process cache (pequeno, rapidíssimo)
# L2: Redis (partilhado entre instâncias)
# L3: CDN (assets estáticos e respostas cacheáveis)

from django.core.cache import cache
from functools import wraps

def cache_result(key_prefix: str, timeout: int = 300):
    """Decorator para cache de resultados de funções."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Chave única baseada nos argumentos
            key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            result = cache.get(key)
            if result is None:
                result = func(*args, **kwargs)
                cache.set(key, result, timeout)
            return result
        return wrapper
    return decorator

# Invalidação de cache em cascata
def invalidate_workspace_cache(workspace_id: str) -> None:
    """Invalida todos os caches relacionados a um workspace."""
    keys = [
        f"workspace:{workspace_id}:stats",
        f"workspace:{workspace_id}:findings",
        f"workspace:{workspace_id}:scans",
    ]
    cache.delete_many(keys)
```

### 9.3 Database Optimization

```python
# Uso obrigatório de select_related e prefetch_related
# para evitar N+1 queries

# ❌ ERRADO — N+1 queries
findings = Finding.objects.filter(scan_id=scan_id)
for f in findings:
    print(f.scan.target.value)  # query extra por finding

# ✅ CORRECTO
findings = Finding.objects.select_related(
    "scan__target", "assignee"
).filter(scan_id=scan_id)

# Paginação obrigatória em todas as listagens
from rest_framework.pagination import CursorPagination

class ScanCursorPagination(CursorPagination):
    page_size = 20
    page_size_query_param = "limit"
    max_page_size = 100
    ordering = "-created_at"

# Connection pooling com pgBouncer
# DATABASE_URL = "postgresql://user:pass@pgbouncer:6432/hackscan"
# CONN_MAX_AGE = 0  # Stateless — pgBouncer gere o pool
```

### 9.4 Celery — Configuração de Queues

```python
# config/celery.py
from celery import Celery

app = Celery("hackscan")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.task_queues = {
    "urgent": {"exchange": "urgent", "routing_key": "urgent"},
    "default": {"exchange": "default", "routing_key": "default"},
    "scheduled": {"exchange": "scheduled", "routing_key": "scheduled"},
    "reports": {"exchange": "reports", "routing_key": "reports"},
    "notifications": {"exchange": "notifications", "routing_key": "notifications"},
}

app.conf.task_routes = {
    "scans.tasks.run_scan": {
        "queue": "urgent",  # Scans são prioritários
    },
    "reports.tasks.generate_report": {
        "queue": "reports",
    },
    "notifications.tasks.*": {
        "queue": "notifications",
    },
    "easm.tasks.*": {
        "queue": "scheduled",
    },
}

# Configurações de reliability
app.conf.task_acks_late = True
app.conf.worker_prefetch_multiplier = 1  # 1 task por worker (scans são pesados)
app.conf.task_reject_on_worker_lost = True
app.conf.task_serializer = "json"
app.conf.result_serializer = "json"
app.conf.accept_content = ["json"]
```

---

## 10. Padrões de Código e Clean Code

### 10.1 Python / Django

```python
# ✅ Padrão: Services para lógica de negócio (não em views/models)
# views.py — apenas orquestração HTTP
class ScanViewSet(viewsets.ModelViewSet):
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Delegar para service
        scan = ScanService.create_scan(
            workspace=self.get_workspace(),
            created_by=request.user,
            **serializer.validated_data,
        )
        return Response(
            ScanSerializer(scan).data,
            status=status.HTTP_201_CREATED,
        )

# services.py — lógica de negócio pura (testável, reutilizável)
class ScanService:
    @staticmethod
    def create_scan(workspace, created_by, target_id, **kwargs) -> Scan:
        target = get_object_or_404(Target, id=target_id, workspace=workspace)
        validate_scan_target(target.value, target.type)
        
        scan = Scan.objects.create(
            workspace=workspace,
            target=target,
            created_by=created_by,
            **kwargs,
        )
        
        # Enqueue task
        run_scan.apply_async(
            kwargs={"scan_id": str(scan.id)},
            queue=ScanService._get_queue(workspace),
            priority=scan.priority,
        )
        
        return scan
```

```python
# ✅ Type hints obrigatórios em todas as funções
def create_scan(
    workspace: Workspace,
    created_by: User,
    target_id: str,
    scan_type: str = "full",
) -> Scan:
    ...

# ✅ Docstrings em funções públicas
def calculate_risk_score(findings: QuerySet) -> float:
    """
    Calcula score de risco agregado (0-100) baseado em findings.
    
    Args:
        findings: QuerySet de Finding objects
    
    Returns:
        Score de risco entre 0 e 100, onde 100 é risco máximo.
    
    Example:
        score = calculate_risk_score(scan.findings.all())
    """
    ...

# ✅ Constantes em lugar de magic numbers
class ScanStatus(models.TextChoices):
    QUEUED = "queued", "Na fila"
    RUNNING = "running", "Em execução"
    PAUSED = "paused", "Pausado"
    COMPLETED = "completed", "Concluído"
    FAILED = "failed", "Falhado"
    CANCELLED = "cancelled", "Cancelado"

# ✅ Fail fast — validar no início das funções
def process_payout(submission_id: str) -> None:
    submission = BountySubmission.objects.get(id=submission_id)
    
    # Guardar validações no início
    if submission.status != "resolved":
        raise ValueError(f"Submissão {submission_id} não está resolvida.")
    if not submission.reward_amount:
        raise ValueError("Montante de reward não definido.")
    
    # Lógica principal aqui
    ...
```

### 10.2 TypeScript / React

```typescript
// ✅ Types explícitos — sem any
interface Finding {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low" | "info";
  type: string;
  endpoint: string;
  status: "open" | "confirmed" | "false_positive" | "fixed";
  createdAt: string;
}

// ✅ Custom hooks para lógica reutilizável
function useFindings(scanId: string) {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    
    api.scans.getFindings(scanId)
      .then((data) => {
        if (!cancelled) {
          setFindings(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err);
          setLoading(false);
        }
      });
    
    return () => { cancelled = true; };
  }, [scanId]);

  return { findings, loading, error };
}

// ✅ Componentes pequenos com responsabilidade única
// ❌ Não — componente de 500 linhas com tudo dentro
// ✅ Sim — componentes focados

function FindingCard({ finding }: { finding: Finding }) {
  return (
    <div className="finding-card">
      <FindingSeverityBadge severity={finding.severity} />
      <FindingTitle title={finding.title} />
      <FindingEndpoint endpoint={finding.endpoint} />
      <FindingActions findingId={finding.id} status={finding.status} />
    </div>
  );
}

// ✅ Error boundaries em todas as secções críticas
function ScanDashboard({ scanId }: { scanId: string }) {
  return (
    <ErrorBoundary fallback={<ScanError />}>
      <Suspense fallback={<ScanSkeleton />}>
        <ScanContent scanId={scanId} />
      </Suspense>
    </ErrorBoundary>
  );
}
```

### 10.3 Convenções de Commits (Conventional Commits)

```
feat(scans): add real-time output via WebSockets
fix(auth): correct TOTP validation window
docs(api): update scan endpoint documentation
refactor(billing): extract stripe logic to service
test(bounty): add triage service unit tests
chore(deps): upgrade nuclei to v3.2.0
perf(db): add index on findings.workspace_severity
security(auth): increase bcrypt rounds to 12
```

---

## 11. Testes — Estratégia Completa

### 11.1 Pirâmide de Testes

```
         /\
        /  \   E2E (Playwright) — fluxos críticos
       /----\
      /      \  Integration — API endpoints, DB
     /--------\
    /          \ Unit — services, validators, utils
   /------------\
  Coverage: min 80% overall, 95% em código crítico (auth, billing)
```

### 11.2 Testes Unitários (pytest)

```python
# scans/tests/test_services.py
import pytest
from unittest.mock import patch, MagicMock
from scans.services import ScanService
from scans.engines.nuclei import NucleiEngine

@pytest.mark.django_db
class TestScanService:
    
    def test_create_scan_queues_celery_task(
        self, workspace, user, target, mock_celery
    ):
        scan = ScanService.create_scan(
            workspace=workspace,
            created_by=user,
            target_id=str(target.id),
            scan_type="full",
        )
        
        assert scan.status == "queued"
        mock_celery.assert_called_once_with(
            kwargs={"scan_id": str(scan.id)},
            queue="urgent",
            priority=5,
        )
    
    def test_create_scan_blocked_for_free_plan_over_limit(
        self, workspace_free, user, target
    ):
        # Criar 5 scans para atingir limite
        for _ in range(5):
            ScanService.create_scan(workspace=workspace_free, ...)
        
        with pytest.raises(QuotaExceeded, match="Limite de 5 scans/mês"):
            ScanService.create_scan(workspace=workspace_free, ...)


class TestNucleiEngine:
    
    def test_parse_result_extracts_finding(self):
        raw = {
            "template-id": "sqli-generic",
            "info": {
                "name": "SQL Injection",
                "severity": "high",
                "description": "SQL injection found",
                "remediation": "Use prepared statements",
                "classification": {"cvss-score": 8.1, "cwe-id": ["CWE-89"]},
            },
            "matched-at": "https://example.com/login",
            "request": {"method": "POST"},
        }
        
        engine = NucleiEngine()
        finding = engine._parse_result(raw)
        
        assert finding.type == "sqli_generic"
        assert finding.severity == "high"
        assert finding.cvss_score == 8.1
        assert finding.cwe_id == "CWE-89"
    
    def test_blocks_private_ip_scan(self):
        from scans.validators import validate_scan_target
        with pytest.raises(ValidationError, match="IPs privados"):
            validate_scan_target("192.168.1.1", "ip")
    
    def test_blocks_metadata_endpoint(self):
        from scans.validators import validate_scan_target
        with pytest.raises(ValidationError, match="não é permitido"):
            validate_scan_target("http://169.254.169.254/latest/meta-data/", "url")
```

```python
# conftest.py — fixtures partilhadas
import pytest
from users.models import User
from workspaces.models import Workspace, WorkspaceMember
from billing.models import Plan, Subscription

@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@hackscan.pro",
        password="TestPassword123!",
        full_name="Test User",
        email_verified=True,
    )

@pytest.fixture
def workspace(db, user):
    ws = Workspace.objects.create(
        owner=user,
        name="Test Workspace",
        slug="test-workspace",
    )
    WorkspaceMember.objects.create(workspace=ws, user=user, role="owner")
    plan = Plan.objects.get(name="pro")
    Subscription.objects.create(
        workspace=ws,
        plan=plan,
        status="active",
        current_period_start=now(),
        current_period_end=now() + timedelta(days=30),
    )
    return ws

@pytest.fixture
def mock_celery(mocker):
    return mocker.patch("scans.services.run_scan.apply_async")
```

### 11.3 Testes de Integração (API)

```python
# scans/tests/test_api.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestScanAPI:
    
    @pytest.fixture(autouse=True)
    def setup(self, user, workspace):
        self.client = APIClient()
        self.client.force_authenticate(user=user)
        self.workspace = workspace
    
    def test_create_scan_returns_201(self, target, mock_celery):
        response = self.client.post("/api/v1/scans/", {
            "target_id": str(target.id),
            "scan_type": "full",
        })
        
        assert response.status_code == 201
        assert response.data["status"] == "queued"
        assert "id" in response.data
    
    def test_create_scan_unauthenticated_returns_401(self, target):
        client = APIClient()  # sem auth
        response = client.post("/api/v1/scans/", {"target_id": str(target.id)})
        assert response.status_code == 401
    
    def test_create_scan_wrong_workspace_returns_403(self, target, other_user):
        self.client.force_authenticate(user=other_user)
        response = self.client.post("/api/v1/scans/", {"target_id": str(target.id)})
        assert response.status_code == 403
    
    def test_list_scans_paginated(self, workspace, target, mock_celery):
        # Criar 25 scans
        for _ in range(25):
            self.client.post("/api/v1/scans/", {"target_id": str(target.id)})
        
        response = self.client.get("/api/v1/scans/?limit=20")
        assert response.status_code == 200
        assert len(response.data["results"]) == 20
        assert "next" in response.data
```

### 11.4 Testes E2E (Playwright)

```typescript
// tests/e2e/scan-flow.spec.ts
import { test, expect } from "@playwright/test";

test.describe("Scan flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "test@hackscan.pro");
    await page.fill('[name="password"]', "TestPassword123!");
    await page.click('[type="submit"]');
    await page.waitForURL("/dashboard");
  });

  test("creates and monitors a scan in real-time", async ({ page }) => {
    // Navegar para novo scan
    await page.click("text=Novo Scan");
    await page.fill('[name="target_url"]', "https://juice-shop.hackscan.pro");
    await page.selectOption('[name="scan_type"]', "full");
    await page.click("text=Iniciar Scan");

    // Verificar que terminal aparece e tem output
    await expect(page.locator(".terminal-output")).toBeVisible();
    await expect(page.locator(".scan-status")).toHaveText("Em execução", {
      timeout: 10000,
    });

    // Aguardar findings aparecerem
    await expect(page.locator(".findings-list .finding-card").first()).toBeVisible({
      timeout: 120000,
    });

    // Verificar estrutura do finding
    const firstFinding = page.locator(".finding-card").first();
    await expect(firstFinding.locator(".severity-badge")).toBeVisible();
    await expect(firstFinding.locator(".finding-title")).toBeVisible();
  });

  test("exports report as PDF", async ({ page }) => {
    // Navegar para scan existente concluído
    await page.goto("/scans/completed-scan-id");
    
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.click("text=Exportar PDF"),
    ]);
    
    expect(download.suggestedFilename()).toMatch(/hackscan-report-.*\.pdf/);
  });
});
```

---

## 12. CI/CD e DevOps

### 12.1 Pipeline GitHub Actions

```yaml
# .github/workflows/main.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  # ─── QUALITY GATES ───────────────────────────────────
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install ruff mypy
      - run: ruff check apps/api/
      - run: mypy apps/api/ --strict

  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        options: --health-cmd pg_isready
      redis:
        image: redis:7
        options: --health-cmd "redis-cli ping"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements/test.txt
      - run: pytest apps/api/ --cov=apps/api --cov-report=xml --cov-fail-under=80
      - uses: codecov/codecov-action@v4

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: cd apps/frontend && npm ci
      - run: cd apps/frontend && npm run lint
      - run: cd apps/frontend && npm run type-check
      - run: cd apps/frontend && npm run test

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trivy — vulnerability scan em dependências
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: "fs"
          scan-ref: "."
          severity: "CRITICAL,HIGH"
          exit-code: "1"
      - name: Secrets scan (gitleaks)
        uses: gitleaks/gitleaks-action@v2

  # ─── BUILD & PUSH ─────────────────────────────────────
  build:
    needs: [lint, test-backend, test-frontend, security-scan]
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=sha-
            type=ref,event=branch
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ─── DEPLOY ───────────────────────────────────────────
  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    environment: staging
    if: github.ref == 'refs/heads/develop'
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - run: |
          kubectl set image deployment/hackscan-api \
            api=${{ needs.build.outputs.image-tag }} \
            -n staging
          kubectl rollout status deployment/hackscan-api -n staging

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    environment: production
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: azure/setup-kubectl@v3
      - name: Blue-green deployment
        run: |
          # Deploy para green
          kubectl set image deployment/hackscan-api-green \
            api=${{ needs.build.outputs.image-tag }} \
            -n production
          kubectl rollout status deployment/hackscan-api-green -n production
          # Testar smoke tests no green
          ./infra/scripts/smoke-test.sh green
          # Switch traffic para green
          kubectl patch service hackscan-api \
            -p '{"spec":{"selector":{"slot":"green"}}}' \
            -n production
```

### 12.2 Estratégia de Branching

```
main        ─── produção (protegido, só via PR)
develop     ─── staging (integração contínua)
feature/*   ─── novas features (branch de feature)
fix/*       ─── bug fixes
hotfix/*    ─── fixes urgentes directamente em main
```

### 12.3 Migration Strategy

```python
# Migrações zero-downtime — padrão obrigatório
# Nunca fazer operações destrutivas em produção sem fase transitória

# Fase 1 — Adicionar coluna nullable (não breaking)
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name="finding",
            name="cvss_vector",
            field=models.CharField(max_length=255, null=True, blank=True),
        ),
    ]

# Deploy da Fase 1

# Fase 2 — Preencher dados existentes (backfill)
# Fazer em background, em lotes, sem lock na tabela

# Fase 3 — Tornar campo NOT NULL (após backfill completo)
class Migration(migrations.Migration):
    operations = [
        migrations.AlterField(
            model_name="finding",
            name="cvss_vector",
            field=models.CharField(max_length=255),
        ),
    ]
```

---

## 13. Monitoring e Observabilidade

### 13.1 Health Checks

```python
# core/views.py
from django.db import connections
from django.core.cache import cache

def health_check(request):
    """Liveness probe — responde se a app está viva."""
    return JsonResponse({"status": "ok"})

def readiness_check(request):
    """Readiness probe — verifica se pode receber tráfego."""
    checks = {}
    
    # Database
    try:
        connections["default"].cursor().execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
    
    # Redis
    try:
        cache.set("health_check", "ok", timeout=5)
        checks["cache"] = "ok"
    except Exception:
        checks["cache"] = "error"
    
    # RabbitMQ
    try:
        from kombu import Connection
        with Connection(settings.CELERY_BROKER_URL) as conn:
            conn.ensure_connection(max_retries=1)
        checks["queue"] = "ok"
    except Exception:
        checks["queue"] = "error"
    
    is_ready = all(v == "ok" for v in checks.values())
    return JsonResponse(
        {"status": "ready" if is_ready else "not_ready", "checks": checks},
        status=200 if is_ready else 503,
    )
```

### 13.2 Prometheus Metrics

```python
# core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
scans_created_total = Counter(
    "hackscan_scans_created_total",
    "Total de scans criados",
    ["scan_type", "plan"],
)
findings_detected_total = Counter(
    "hackscan_findings_detected_total",
    "Total de findings detectados",
    ["severity", "type", "engine"],
)

# Histograms
scan_duration_seconds = Histogram(
    "hackscan_scan_duration_seconds",
    "Duração de scans em segundos",
    ["scan_type"],
    buckets=[30, 60, 120, 300, 600, 1200, 1800],
)
api_request_duration = Histogram(
    "hackscan_api_request_duration_seconds",
    "Duração de requests à API",
    ["method", "endpoint", "status_code"],
)

# Gauges
active_scans = Gauge(
    "hackscan_active_scans",
    "Número de scans actualmente em execução",
)
queue_size = Gauge(
    "hackscan_queue_size",
    "Tamanho da fila de scans",
    ["queue_name"],
)
```

### 13.3 Alertas Críticos (Prometheus/Grafana)

```yaml
# infra/monitoring/alerts.yaml
groups:
- name: hackscan.critical
  rules:
  - alert: ScanQueueBacklog
    expr: hackscan_queue_size{queue_name="urgent"} > 100
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Fila de scans com backlog crítico ({{ $value }} scans)"
      
  - alert: HighErrorRate
    expr: |
      rate(hackscan_api_request_duration_count{status_code=~"5.."}[5m]) /
      rate(hackscan_api_request_duration_count[5m]) > 0.05
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Taxa de erro acima de 5% — {{ $value | humanizePercentage }}"
      
  - alert: DatabaseConnectionsExhausted
    expr: pg_stat_activity_count > 80
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Conexões à base de dados quase esgotadas: {{ $value }}"

  - alert: ScanWorkerDown
    expr: up{job="celery-scanner"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Scanner workers offline — scans parados"
```

---

## 14. Roadmap Detalhado com Tarefas

### FASE 1 — MVP (Meses 1-3) · ~$5.000

**Objectivo:** Produto funcional, primeiros clientes pagantes, validação de mercado.

#### Sprint 1 (Semanas 1-2) — Infra & Auth Base

- [ ] Setup repositório monorepo (Turborepo)
- [ ] Configurar Docker Compose para desenvolvimento local
- [ ] Setup PostgreSQL + Redis + RabbitMQ local
- [ ] Criar projeto Django com estrutura de apps definida
- [ ] Implementar modelo `User` com UUID, campos de segurança, soft delete
- [ ] Implementar auth: register, login, logout, refresh token (RS256)
- [ ] Implementar verificação de email com token
- [ ] Implementar rate limiting em endpoints de auth
- [ ] Setup Next.js 15 com App Router e Tailwind CSS
- [ ] Implementar páginas de login e registo
- [ ] Setup CI/CD pipeline básico (lint + tests)
- [ ] Escrever testes unitários: auth service (cobertura mínima 90%)

#### Sprint 2 (Semanas 3-4) — 2FA, RBAC, Workspace

- [ ] Implementar 2FA TOTP (setup, verificação, backup codes)
- [ ] Implementar password reset via email
- [ ] Implementar modelos `Workspace`, `WorkspaceMember`, `Invitation`
- [ ] Implementar RBAC (owner, admin, member, viewer)
- [ ] Implementar API de gestão de workspaces
- [ ] Implementar audit logs para todas as acções de auth
- [ ] Dashboard inicial: lista de scans recentes (vazia)
- [ ] Página de settings: perfil e segurança
- [ ] Testes de integração: auth API endpoints

#### Sprint 3 (Semanas 5-6) — Scanner Engine Core

- [ ] Integrar Nuclei como engine primário
- [ ] Implementar `BaseEngine` e `EngineRegistry`
- [ ] Implementar `NucleiEngine` com parsing de output JSON
- [ ] Implementar validação de targets (anti-SSRF, bloqueio IPs privados)
- [ ] Implementar modelo `Target` com verificação de ownership
- [ ] Implementar modelo `Scan` com estados e configuração
- [ ] Implementar modelo `Finding` com todos os campos
- [ ] Setup Celery com RabbitMQ e queues prioritárias
- [ ] Implementar Celery task `run_scan` com error handling
- [ ] Implementar Docker sandbox para scans isolados
- [ ] Testes unitários: engines, validators, tasks

#### Sprint 4 (Semanas 7-8) — Dashboard Real-time & API Completa

- [ ] Implementar Django Channels com Redis channel layer
- [ ] Implementar `ScanConsumer` (WebSocket)
- [ ] Implementar publicação de eventos durante scan
- [ ] Frontend: terminal simulado com xterm.js
- [ ] Frontend: hook `useScanWebSocket`
- [ ] Frontend: dashboard com heatmap de severidade
- [ ] Frontend: página de detalhes de finding
- [ ] API: CRUD completo de scans, targets, findings
- [ ] API: filtros e paginação em listings
- [ ] Testes E2E: fluxo completo de criação e monitoramento de scan

#### Sprint 5 (Semanas 9-10) — Billing & Planos

- [ ] Setup Stripe (conta, webhooks, produtos e preços)
- [ ] Implementar modelos `Plan`, `Subscription`, `Invoice`, `UsageRecord`
- [ ] Implementar `BillingService` com Stripe checkout
- [ ] Implementar webhook handlers (idempotentes)
- [ ] Implementar quota check middleware
- [ ] Frontend: página de upgrade de plano
- [ ] Frontend: portal de billing (Stripe customer portal)
- [ ] Frontend: badges de plano e limitações visíveis
- [ ] Testes: billing service, webhook handlers

#### Sprint 6 (Semanas 11-12) — Relatórios & Polish

- [ ] Implementar geração de PDF técnico (WeasyPrint)
- [ ] Implementar geração de PDF executivo com resumo IA
- [ ] Templates de relatório em HTML/CSS
- [ ] Export JSON e CSV de findings
- [ ] Frontend: botão de export no scan detail
- [ ] Remediação: code snippets automáticos por linguagem
- [ ] MVP UI polish: dark mode completo, animações, responsive
- [ ] Setup Sentry para error tracking
- [ ] Setup Prometheus + Grafana básico
- [ ] Health checks (liveness + readiness)
- [ ] Deploy em staging (Kubernetes)
- [ ] **Beta privado com 20-30 utilizadores angolanos**

---

### FASE 2 — Beta (Meses 4-6) · ~$15.000

**Objectivo:** Diferenciais únicos activados, comunidade inicial, MRR > $3.000.

#### Sprint 7-8 — AI Engine

- [ ] Integrar Anthropic Claude API
- [ ] Implementar `AIService.explain_finding()` em PT-BR
- [ ] Implementar `AIService.predict_attack_chains()`
- [ ] Implementar `AIService.generate_remediation_code()`
- [ ] Frontend: chat in-app no painel de finding
- [ ] Frontend: secção "AI Risk Forecaster" no dashboard
- [ ] Frontend: visualização de attack chains
- [ ] Caching de respostas AI (Redis, TTL 1h)
- [ ] Testes: AI service com mocks da API

#### Sprint 9-10 — EASM

- [ ] Integrar Shodan API e crt.sh para descoberta
- [ ] Implementar `EASMService` com descoberta de subdomínios
- [ ] Implementar modelos `EASMAsset`, `EASMChange`
- [ ] Celery beat para execução periódica (diária)
- [ ] Frontend: mapa de superfície de ataque
- [ ] Frontend: timeline de mudanças detectadas
- [ ] Notificações: email + in-app para novos activos

#### Sprint 11-12 — Bug Bounty MVP

- [ ] Implementar modelos `BountyProgram`, `BountySubmission`, `BountyPayout`
- [ ] Implementar `BountyTriageService` com auto-triage
- [ ] Setup Stripe Connect para pagamentos a researchers
- [ ] API: CRUD de programas e submissões
- [ ] Frontend: página pública de programa de bounty
- [ ] Frontend: formulário de submissão para researchers
- [ ] Frontend: dashboard de triage para empresas
- [ ] Hall of fame público por programa
- [ ] Verificação de identidade básica para researchers (email + país)

#### Sprint 13-14 — Colaboração & Marketplace v1

- [ ] Integração Jira: criar issues automáticos de findings
- [ ] Integração Slack: alerts de novos findings críticos
- [ ] Implementar assign de findings a membros da equipa
- [ ] Comentários em findings (markdown suportado)
- [ ] Implementar modelos `MarketplaceModule`, `ModuleInstallation`
- [ ] Publicar Scanner SDK (PyPI)
- [ ] Frontend: página de marketplace
- [ ] Workflow de submissão e revisão de módulos
- [ ] Deploy 2 módulos próprios como referência

---

### FASE 3 — Scale (Meses 7-12) · ~$40.000

**Objectivo:** Enterprise ready, expansão regional, múltiplos revenue streams.

#### Sprint 15-18 — Enterprise & API Pública

- [ ] API pública com documentação OpenAPI interactiva
- [ ] Webhooks configuráveis por workspace
- [ ] Integração CI/CD: GitHub Actions, GitLab CI, Jenkins
- [ ] White-label: custom domain + branding por workspace
- [ ] SLA monitoring e relatórios de uptime
- [ ] SSO: SAML 2.0 + OAuth2 (para enterprise)
- [ ] Plano Enterprise com onboarding dedicado

#### Sprint 19-20 — Attack Chain Simulation

- [ ] Visualização interactiva de kill chain (D3.js)
- [ ] IA para correlação automática de findings em chains
- [ ] PoC interativo multi-step no browser
- [ ] Relatório de simulação de ataque
- [ ] Comparação entre scans (evolução temporal)

#### Sprint 21-22 — Mobile & Expansão

- [ ] App React Native (iOS + Android)
- [ ] Scan via QR code de URL
- [ ] Push notifications para findings críticos
- [ ] Suporte a Moçambique: localização, parceiros
- [ ] Suporte ao Brasil: Pix, LGPD compliance reports
- [ ] Programa de afiliados e white-label para MSSPs
- [ ] Documentação completa em português

---

## 15. Stack de Tecnologia — Decisões e Justificativas

| Componente | Tecnologia | Versão | Justificativa |
|---|---|---|---|
| API Backend | Django + DRF | 5.x + 3.15 | Maturidade, ORM robusto, admin grátis, ecossistema |
| Real-time | Django Channels | 4.x | WebSockets nativos com Django |
| Task Queue | Celery + RabbitMQ | 5.x + 3.12 | Filas robustas, retry, prioritização |
| Scan Engine | Nuclei | 3.x | FOSS, templates comunitários, extensível |
| AI | Anthropic Claude | claude-opus-4-5 | Melhor para análise de segurança em PT |
| Frontend | Next.js 15 | 15.x | SSR, App Router, performance, SEO |
| State Mgmt | Zustand | 5.x | Simples, sem boilerplate, TypeScript nativo |
| DB Principal | PostgreSQL | 16 | ACID, JSON support, extensível |
| DB Time-series | TimescaleDB | 2.x | Extension do PG — sem overhead operacional |
| Cache/Queue | Redis | 7.x | Pub/sub para WS, cache, Celery backend |
| PDF | WeasyPrint | 62.x | HTML/CSS → PDF, sem dependências JS |
| Billing | Stripe | - | Standard global, Connect para payouts |
| Infra | Kubernetes + Terraform | - | Escalabilidade, portabilidade |
| Registry | GitHub Container Registry | - | Integrado com CI/CD |
| Monitoring | Prometheus + Grafana | - | Standard de mercado, open-source |
| Error Tracking | Sentry | - | Real-time, source maps, alertas |
| Secrets | HashiCorp Vault | - | Rotação automática, auditoria |
| WAF | Cloudflare | - | DDoS, WAF, CDN, TLS |

---

## 16. Variáveis de Ambiente e Configuração

```bash
# .env.example — copiar para .env e preencher

# ─── Django ───────────────────────────────────────
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=                          # gerar: python -c "import secrets; print(secrets.token_urlsafe(50))"
DEBUG=False
ALLOWED_HOSTS=api.hackscan.pro
CORS_ALLOWED_ORIGINS=https://hackscan.pro,https://app.hackscan.pro

# ─── JWT (RSA) ────────────────────────────────────
# Gerar: openssl genrsa -out private.pem 2048
#        openssl rsa -in private.pem -pubout -out public.pem
JWT_PRIVATE_KEY=                     # conteúdo de private.pem
JWT_PUBLIC_KEY=                      # conteúdo de public.pem

# ─── Database ─────────────────────────────────────
DATABASE_URL=postgresql://user:pass@pgbouncer:6432/hackscan
TIMESCALE_URL=postgresql://user:pass@timescale:5432/hackscan_ts

# ─── Redis ────────────────────────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=amqp://user:pass@rabbitmq:5672/hackscan

# ─── Storage ──────────────────────────────────────
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=hackscan-reports
AWS_S3_ENDPOINT_URL=                 # MinIO: http://minio:9000

# ─── Email ────────────────────────────────────────
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=                 # SendGrid API key
DEFAULT_FROM_EMAIL=noreply@hackscan.pro

# ─── Stripe ───────────────────────────────────────
STRIPE_SECRET_KEY=sk_live_
STRIPE_PUBLISHABLE_KEY=pk_live_
STRIPE_WEBHOOK_SECRET=whsec_

# ─── Anthropic / AI ───────────────────────────────
ANTHROPIC_API_KEY=

# ─── External APIs ────────────────────────────────
SHODAN_API_KEY=
CENSYS_API_KEY=
CENSYS_API_SECRET=

# ─── Vault ────────────────────────────────────────
VAULT_ADDR=https://vault.internal:8200
VAULT_TOKEN=                         # ou usar AppRole

# ─── Sentry ───────────────────────────────────────
SENTRY_DSN=

# ─── Frontend (Next.js) ───────────────────────────
NEXT_PUBLIC_API_URL=https://api.hackscan.pro
NEXT_PUBLIC_WS_URL=wss://api.hackscan.pro
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
```

---

## 17. Glossário

| Termo | Definição |
|---|---|
| **EASM** | External Attack Surface Management — monitoramento contínuo de activos expostos externamente |
| **BAS** | Breach and Attack Simulation — simulação de ataques reais para validar defesas |
| **PTaaS** | Pentest as a Service — pentest contínuo como serviço |
| **CVSS** | Common Vulnerability Scoring System — sistema de pontuação de gravidade de vulnerabilidades |
| **CWE** | Common Weakness Enumeration — classificação de tipos de vulnerabilidades |
| **SSRF** | Server-Side Request Forgery — ataque que força o servidor a fazer requests |
| **IDOR** | Insecure Direct Object Reference — acesso não autorizado a recursos por ID |
| **BOLA** | Broken Object Level Authorization — variante de IDOR em APIs REST |
| **WAF** | Web Application Firewall — firewall específico para aplicações web |
| **RBAC** | Role-Based Access Control — controlo de acesso baseado em funções |
| **HPA** | Horizontal Pod Autoscaler — auto-scaling de pods Kubernetes |
| **TOTP** | Time-based One-Time Password — 2FA baseado em tempo |
| **MRR** | Monthly Recurring Revenue — receita recorrente mensal |
| **MSSP** | Managed Security Service Provider — fornecedor de segurança gerida |
| **kill chain** | Sequência de passos de um ataque, desde recon até ao impacto final |
| **finding** | Vulnerabilidade ou problema de segurança identificado num scan |
| **engine** | Módulo de scan responsável por um tipo específico de verificação |
| **sandbox** | Ambiente isolado para execução segura de scans |
| **payload** | Dados especialmente construídos para explorar uma vulnerabilidade |
| **PoC** | Proof of Concept — demonstração reprodutível de uma vulnerabilidade |

---

*Documento Master v2.0 — HackScan Pro · Luanda, Angola · Março 2026*  
*Actualizar este documento a cada decisão técnica significativa.*  
*Próxima revisão: início da Fase 2 (mês 4).*
