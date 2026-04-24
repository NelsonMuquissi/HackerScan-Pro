# HackScan Pro — Modelo de Monetização por IA
## Documento Master de Estratégia, Psicologia e Implementação

> **Classificação:** Estratégia de Produto — Confidencial  
> **Versão:** 2.0 God Mode · **Data:** Março 2026  
> **Referências reais:** OpenAI · Anthropic · Cursor · Perplexity · Midjourney  
> · GitHub Copilot · Notion AI · Vercel · Linear · Jasper · Copy.ai  

---

## Por que este documento existe

Tens um produto que funciona. Tens scans reais. Tens utilizadores reais.  
O que te falta é o **mecanismo que transforma valor em dinheiro de forma viciante**.

Este documento é o manual completo desse mecanismo — a estratégia, a psicologia, os números, o código e o roadmap para implementar. Cada decisão aqui tem referência em produtos reais que geram dezenas de milhões por ano.

---

## Índice

1. [A Tese — Porquê Tokens e Não Apenas Planos](#1-a-tese)
2. [Análise dos Modelos que Realmente Funcionam](#2-análise-dos-modelos-que-realmente-funcionam)
3. [A Psicologia do Pagamento Voluntário](#3-a-psicologia-do-pagamento-voluntário)
4. [Arquitectura do Modelo HackScan](#4-arquitectura-do-modelo-hackscan)
5. [Tabela de Preços e Créditos](#5-tabela-de-preços-e-créditos)
6. [As 12 Mecânicas de Retenção](#6-as-12-mecânicas-de-retenção)
7. [Fluxos de Upsell Automático](#7-fluxos-de-upsell-automático)
8. [Schema de Base de Dados Completo](#8-schema-de-base-de-dados-completo)
9. [Implementação Técnica Completa](#9-implementação-técnica-completa)
10. [Frontend — Experiência que Converte](#10-frontend--experiência-que-converte)
11. [Stripe — Pagamentos e Webhooks](#11-stripe--pagamentos-e-webhooks)
12. [Analytics e Métricas de Monetização](#12-analytics-e-métricas-de-monetização)
13. [Projecções Financeiras Detalhadas](#13-projecções-financeiras-detalhadas)
14. [Roadmap de Implementação](#14-roadmap-de-implementação)
15. [Prompt para Claude Code](#15-prompt-para-claude-code)

---

## 1. A Tese

### O problema dos planos fixos

Um plano de $29/mês tem um problema matemático:

```
Utilizador A:  usa 2 vezes/mês   → paga $29  → valor percebido: baixo
Utilizador B:  usa 200 vezes/mês → paga $29  → valor percebido: alto
               tu perdes margem  ←──────────────── desequilíbrio
```

Os produtos mais rentáveis do mundo resolveram isto com uma fórmula simples:

```
RECEITA = Plano Base (previsível) + Consumo Variável (escalável)
```

O Plano Base cobre a infra. O Consumo Variável captura valor ilimitado dos utilizadores de alto uso. Juntos, criam MRR previsível + upside ilimitado.

### Porquê funciona especificamente em segurança

No mundo da cibersegurança, o valor de uma explicação é **assimétrico**:

```
O teu custo para explicar um SQL Injection:  $0.03 (tokens Anthropic)
O valor para o CISO que recebe a explicação: $10.000+ (danos prevenidos)
O preço que cobras:                          $0.10 (10 créditos)

Margem bruta: 70%
Valor capturado vs. valor criado: 0.001%  ← podes cobrar muito mais
```

O utilizador nunca vai comparar $0.10 com o custo real. Vai comparar com o valor recebido. E o valor recebido é sempre ordens de magnitude superior.

---

## 2. Análise dos Modelos que Realmente Funcionam

### 2.1 Cursor — $200M ARR em 2 anos

**O modelo:** Plano Pro $20/mês inclui 500 "fast requests". Cada fast request adicional custa $0.04. Utilizadores heavy users pagam $50-100/mês na prática.

**O que copiar:**
- Nomenclatura de "requests" em vez de "tokens" — o utilizador entende melhor
- Contador sempre visível no canto da interface
- "Slow mode" grátis vs. "Fast mode" pago — cria dois tiers naturais
- Usage dashboard com breakdown por tipo de acção

**O que adaptar para HackScan:**
```
"Fast scan" (Nuclei completo)    → consome créditos
"Quick scan" (headers + ports)  → sempre grátis
"AI explain"                    → consome créditos
"Basic findings list"           → sempre grátis
```

### 2.2 Perplexity — $73M ARR, 15M utilizadores

**O modelo:** Free dá 5 "Pro searches" por dia. Pro $20/mês dá ilimitado. A limitação diária é suficiente para criar hábito mas não para uso real.

**O que copiar:**
- Limitação diária em vez de mensal → urgência mais frequente
- "Pro search" como nome premium → o utilizador sente que está a obter algo especial
- Mostrar o que a Pro search faz a mais (fontes extra, análise mais profunda)

**O que adaptar:**
```
Free: 3 "AI explanations" por dia (não por mês)
Pro: Ilimitado com créditos mensais
→ O utilizador Free atinge o limite todos os dias → converte mais rápido
```

### 2.3 Midjourney — $200M ARR com produto simples

**O modelo:** Planos por GPU hours, não por imagens. Utilizadores intensivos pagam proporcionalmente mais. Bónus de horas extra em planos maiores.

**O que copiar:**
- Métrica de consumo real (GPU time / tokens) em vez de acções abstractas
- Bónus percentuais em pacotes maiores (20% extra no plano anual)
- Fast vs. Relax mode — modo rápido prioritário, modo lento gratuito mas demorado

**O que adaptar:**
```
HackScan "Express AI" → resposta em <3s (consome 2x créditos)
HackScan "Standard AI" → resposta em <30s (créditos normais)
→ Utilizadores em deadline pagam a taxa express
```

### 2.4 GitHub Copilot — 1.8M utilizadores pagantes, $400M ARR

**O modelo:** $10/mês individual, $19/mês business. Nenhuma limitação de uso — totalmente ilimitado. A retenção vem do hábito, não da limitação.

**O que aprender:**
- Para alguns produtos, a limitação prejudica a adoção
- O hábito criado pelo uso ilimitado converte melhor que a urgência da limitação
- Para o HackScan: scans ilimitados (sem limite), IA com créditos (com limite)

### 2.5 Notion AI — $16/mês add-on sobre o plano base

**O modelo:** O plano Notion é separado do Notion AI. Utilizadores que adoram o Notion pagam $8/mês. Se quiserem IA, pagam mais $16/mês. Revenue por utilizador duplicou.

**O que copiar:**
- IA como add-on explícito, não feature incluída
- O preço do add-on parece razoável comparado com o plano base
- Utilizadores que não usam IA não pagam por ela (maior adoption do plano base)

**O que adaptar:**
```
HackScan Pro $29/mês     → scanner ilimitado, sem IA
HackScan Pro + AI $39/mês → scanner + 500 créditos/mês
→ Utilizadores que só querem o scanner pagam menos
→ Utilizadores que querem IA percebem o valor extra
```

### 2.6 Linear — $8/mês, 99% de retenção

**O modelo:** Preço simples, produto excepcional, zero friction no pagamento. A retenção não vem de lock-in mas de qualidade.

**O que copiar:**
- Interface de pagamento em menos de 30 segundos
- Sem confirmações desnecessárias
- Auto-renovação por defeito, cancelamento em 1 clique
- Email de confirmação de compra com o que o utilizador "ganhou"

---

## 3. A Psicologia do Pagamento Voluntário

### 3.1 O Princípio da Reciprocidade (Cialdini)

Quando dás valor primeiro, o utilizador sente-se obrigado a retribuir. O primeiro uso de IA grátis não é generosidade — é investimento na conversão.

```
Fluxo de reciprocidade HackScan:
1. Utilizador faz scan → encontra 9 findings
2. Clica em "Explicar com IA" → recebe explicação GRÁTIS (primeira vez)
3. Lê a explicação detalhada em português
4. Entende o risco real pela primeira vez
5. Sente que a plataforma "ajudou-o"
6. Na segunda vulnerability → compra créditos sem hesitar

Taxa de conversão após primeiro uso grátis: 35-45% (benchmark SaaS)
Taxa de conversão sem primeiro uso grátis: 8-12%
```

### 3.2 O Efeito de Posse (Thaler — Nobel de Economia)

As pessoas valorizam mais o que já possuem. Créditos não usados são percebidos como "dinheiro que vou perder".

```
Mecânicas de posse no HackScan:
- Welcome credits: 100 créditos no registo → "já tenho créditos"
- Achievements: créditos ganhos → "ganhei isto, não vou desperdiçar"
- Créditos comprados nunca expiram → "estão lá quando precisar"
- Créditos do plano expiram → urgência de usar antes de perder
```

### 3.3 Anchoring — O Preço que Nunca Compras mas que Muda Tudo

```
❌ Mostrar do mais barato para o mais caro:
   $5 → $20 → $50 → $100
   → Utilizador compara $5 com $20 e vê $20 como caro

✅ Mostrar do mais caro para o mais barato (Cursor, Notion):
   $100 → $50 → $20 → $5
   → Utilizador compara $100 com $50 e vê $50 como razoável
   → Compra o $50 em vez do $20
   → Receita por transacção 2.5x maior
```

O pacote que mais vende nunca é o mais barato nem o mais caro. É sempre o segundo mais caro — com bónus suficientes para parecer o melhor deal.

### 3.4 A Aversão à Perda (Kahneman)

A dor de perder €1 é 2x maior que o prazer de ganhar €1. Usa isto:

```
❌ "Compra 2.200 créditos por $20"
✅ "Não percas acesso à IA — os teus 45 créditos acabam hoje"

❌ "Upgrade para Pro"
✅ "Perdes 455 créditos mensais grátis se não fizeres upgrade"

❌ "Relatório disponível no plano Pro"
✅ "O teu relatório está pronto mas está bloqueado — 
    desbloqueia agora por $5 em créditos"
```

### 3.5 O Compromisso e Consistência (Cialdini)

Uma vez que o utilizador pagou qualquer quantia, a probabilidade de pagar de novo é 5x maior. O primeiro pagamento é o mais difícil.

```
Funil de compromisso:
1. Registo grátis              → sem fricção
2. Primeiro scan grátis        → sem fricção
3. IA grátis (1 vez)           → sem fricção
4. Compra de $5 Starter pack   → PRIMEIRO PAGAMENTO (crítico)
5. Recarga de $20              → 5x mais provável
6. Upgrade para Pro ($29/mês)  → 10x mais provável
7. Team ($99/mês)              → muito provável

→ O Starter pack de $5 existe para criar o primeiro pagamento,
  não para gerar receita significativa
```

### 3.6 FOMO e Escassez Social

```
Notificações que disparam FOMO:
"3 empresas angolanas fizeram upgrade esta semana"
"O teu competidor kacifos.com tem 0 vulnerabilidades críticas abertas"
"15 utilizadores estão a ver relatórios AI esta tarde"

Escassez de acesso (não de produto):
"AI Forecaster disponível apenas para utilizadores Pro e superiores"
"Acesso prioritário ao Nuclei engine — fila de espera para Free"
```

---

## 4. Arquitectura do Modelo HackScan

### A Estrutura em Camadas

```
┌─────────────────────────────────────────────────────┐
│                  CAMADA GRATUITA                     │
│  Scanner básico (ports, headers, SSL)                │
│  5 scans/mês · Ver findings · Dashboard básico       │
│  OBJECTIVO: Criar hábito e dependência               │
└─────────────────────────┬───────────────────────────┘
                          │ Utilizador quer mais valor
                          ▼
┌─────────────────────────────────────────────────────┐
│              CAMADA DE SUBSCRIPÇÃO                   │
│  Scans ilimitados · Nuclei · Subfinder · Gobuster    │
│  Pro $29 · Team $99 · Enterprise $299                │
│  OBJECTIVO: MRR previsível                           │
└─────────────────────────┬───────────────────────────┘
                          │ Utilizador usa IA
                          ▼
┌─────────────────────────────────────────────────────┐
│              CAMADA DE CRÉDITOS IA                   │
│  Explicações · Relatórios · Forecaster · Chat        │
│  Créditos incluídos no plano + compra adicional      │
│  OBJECTIVO: Revenue variável, margem 80%+            │
└─────────────────────────┬───────────────────────────┘
                          │ Utilizador quer mais escala
                          ▼
┌─────────────────────────────────────────────────────┐
│              CAMADA ENTERPRISE                       │
│  API · White-label · Bug Bounty · EASM               │
│  Contratos anuais · SLA · Suporte dedicado           │
│  OBJECTIVO: ACV alto, churning rate próximo de 0     │
└─────────────────────────────────────────────────────┘
```

### O Que é Sempre Grátis (Âncora da Plataforma)

```
✅ Criar conta e workspace
✅ Scans básicos (até ao limite do plano)
✅ Ver lista de findings
✅ Dashboard com métricas básicas
✅ 1 explicação AI por dia (não por mês — urgência diária)
✅ Relatório PDF básico (primeiras 2 páginas)
✅ Participar em programas de Bug Bounty públicos
```

### O Que Sempre Custa Créditos

```
💳 Explicações AI completas (após o 1 diário grátis)
💳 Relatórios PDF completos
💳 AI Forecaster / Attack Chains
💳 Remediation code em múltiplas linguagens
💳 Relatórios de compliance (LGPD, ISO, PCI-DSS)
💳 Chat AI ilimitado (após 5 mensagens/dia grátis)
💳 Análise de findings históricos
💳 Export com AI insights incluídos
```

---

## 5. Tabela de Preços e Créditos

### Planos de Subscripção

| | **Free** | **Pro** | **Team** | **Enterprise** |
|---|---|---|---|---|
| **Preço/mês** | $0 | $29 | $99 | $299 |
| **Preço/ano** | $0 | $290 (-17%) | $990 (-17%) | $2.990 (-17%) |
| **Créditos IA/mês** | 30 (diário: 1 explain) | 600 | 2.500 | 12.000 |
| **Scans/mês** | 5 | Ilimitado | Ilimitado | Ilimitado |
| **Targets** | 1 | 10 | 50 | Ilimitado |
| **Utilizadores** | 1 | 1 | 5 | Ilimitado |
| **Nuclei engine** | ❌ | ✅ | ✅ | ✅ |
| **Subfinder/Gobuster** | ❌ | ✅ | ✅ | ✅ |
| **Relatório PDF** | Parcial (2 pág.) | Completo | Completo | Completo + branded |
| **API access** | ❌ | ❌ | Rate limited | Ilimitado |
| **Bug Bounty** | Participar | Participar | Criar programas | White-label |
| **Suporte** | Community | Email | Priority email | Dedicated CSM |
| **SLA** | Nenhum | Nenhum | 99.5% | 99.9% |

### Créditos de Boas-Vindas por Plano

```
Novo registo Free:        30 créditos (expira em 7 dias → urgência)
Primeiro upgrade Pro:    +300 créditos de bónus (one-time)
Primeiro upgrade Team:   +1.000 créditos de bónus (one-time)
Referral bem-sucedido:   +500 créditos para ti + 100 para o convidado
Achievement desbloqueado: +25 a +200 créditos
```

### Pacotes de Créditos Adicionais

| Pacote | Créditos Base | Bónus | Total | Preço | $/crédito | Destacado |
|--------|-------------|-------|-------|-------|-----------|-----------|
| **Micro** | 100 | 0 | 100 | $1.99 | $0.0199 | — |
| **Starter** | 500 | 0 | 500 | $5 | $0.0100 | — |
| **Growth** | 2.000 | 200 | 2.200 | $20 | $0.0091 | ⭐ POPULAR |
| **Power** | 5.000 | 1.000 | 6.000 | $50 | $0.0083 | — |
| **Ultra** | 10.000 | 5.000 | 15.000 | $100 | $0.0067 | MELHOR VALOR |

> **Porquê o pacote Micro de $1.99:**  
> O primeiro pagamento é o mais difícil. $1.99 é uma barreira psicológica quase inexistente. Uma vez que o utilizador paga $1.99, a probabilidade de comprar $20 aumenta 5x. É um mecanismo de activação, não de receita.

### Custo Real vs. Preço Cobrado

| Acção | Créditos Cobrados | Custo Anthropic | Receita | Margem |
|-------|-----------------|----------------|---------|--------|
| Explain finding (curto) | 10 | $0.018 | $0.10 | 82% |
| Explain finding (detalhado) | 20 | $0.035 | $0.20 | 83% |
| Relatório PDF técnico | 60 | $0.095 | $0.60 | 84% |
| Relatório PDF executivo | 90 | $0.140 | $0.90 | 84% |
| AI Forecaster | 35 | $0.055 | $0.35 | 84% |
| Attack chains analysis | 50 | $0.080 | $0.50 | 84% |
| Remediation code | 15 | $0.025 | $0.15 | 83% |
| Chat message | 5 | $0.008 | $0.05 | 84% |
| Compliance report (LGPD) | 150 | $0.240 | $1.50 | 84% |
| Compliance report (ISO 27001) | 200 | $0.320 | $2.00 | 84% |

**Margem bruta média: 83.5%** — uma das mais altas possíveis em SaaS

---

## 6. As 12 Mecânicas de Retenção

Cada mecânica tem referência em produto real. Nenhuma é inventada.

### Mecânica 1 — O Primeiro Uso Grátis (Perplexity, Cursor)

```python
def explain_finding(finding, workspace, user):
    # Verificar se é literalmente o primeiro uso de AI deste user
    is_first_time = not AITransaction.objects.filter(
        workspace=workspace,
        type="debit",
        action__startswith="explain"
    ).exists()
    
    if is_first_time:
        result = call_claude(prompt)
        # Registar como grátis mas marcar claramente
        AITransaction.objects.create(
            action="explain_finding_first_use",
            amount=0,
            metadata={"first_time_bonus": True}
        )
        # Mostrar ao utilizador que foi grátis
        return result, {"was_free": True, "reason": "first_use_bonus"}
    
    # A partir da segunda vez → cobra normalmente
    return explain_with_credits(finding, workspace, user)
```

**UI após o primeiro uso grátis:**
```
✅ Explicação gerada com sucesso
⚡ Esta foi a tua primeira explicação AI — grátis!
   As próximas custam 10 créditos cada.
   [Comprar 500 créditos por $5] [Continuar sem IA]
```

### Mecânica 2 — O Limite Diário em Vez de Mensal (Duolingo)

```
❌ Mensal: utilizador usa 30 créditos em 2 dias → 28 dias sem urgência
✅ Diário:  utilizador usa 1 explain grátis → amanhã tem outro
           mas HOJE, neste momento, se quiser mais → compra créditos

O limite diário cria 30 momentos de urgência por mês
O limite mensal cria 1 momento (quando o saldo acaba)
```

### Mecânica 3 — A Barra de Progresso de Créditos (Linear, Vercel)

```
Sempre visível no header:
⚡ [████████░░] 340/600 créditos
               ↑ barra visual + número exacto

Quando abaixo de 20%:
⚡ [█░░░░░░░░░] 87/600 créditos  ← vermelho + pulse animation
   "Créditos baixos — Recarrega"
```

### Mecânica 4 — Os Créditos que Expiram vs. os que Ficam (Airlines)

```
Créditos do plano mensal: expiram no dia de renovação
→ Cria urgência: "tenho de usar os meus créditos antes do dia 15"
→ Utilizador usa mais o produto → cria hábito

Créditos comprados: nunca expiram
→ Remove friction na compra: "não vou perder o que paguei"
→ Utilizador compra mais sem medo

Esta assimetria é intencional e psicologicamente poderosa.
```

### Mecânica 5 — O Auto-Reload (Uber, Google Ads)

```
Configuração simples no dashboard:
"Quando o saldo baixar de 100 créditos, recarregar automaticamente $20"

Efeito: utilizador nunca fica sem IA durante um scan importante
Resultado: pagamentos automáticos mensais adicionais ao plano
Revenue per user aumenta 40% com auto-reload activado (benchmark: Google Ads)
```

### Mecânica 6 — O Relatório Parcial que Força Upgrade (Scribd, Medium)

```
PDF gerado para Free users:
┌────────────────────────────────────┐
│ HACKSCAN PRO                       │
│ Relatório de Segurança             │
│ selenium.ao — 25 Mar 2026          │
│                                    │
│ Executive Summary          ✅ visível
│ Risk Score: 67/100         ✅ visível
│ Top 3 Vulnerabilidades     ✅ visível
│                                    │
│ ████████████████████████   🔒 blur
│ █████████ Findings ██████   🔒 blur
│ ████ Detalhes técnicos ███   🔒 blur
│ ████ Remediação ██████████   🔒 blur
│                                    │
│ [Desbloquear relatório — 60 créditos]
└────────────────────────────────────┘
```

### Mecânica 7 — Os Achievements que Dão Créditos (Duolingo)

```python
ACHIEVEMENTS = {
    "first_scan": {
        "name": "Primeiro Scan",
        "description": "Completaste o teu primeiro scan",
        "credits": 50,
        "icon": "🔍",
    },
    "five_scans": {
        "name": "Caçador de Vulns",
        "credits": 100,
        "icon": "🎯",
    },
    "first_critical": {
        "name": "Alerta Crítico",
        "description": "Encontraste a tua primeira vulnerabilidade crítica",
        "credits": 150,
        "icon": "🚨",
    },
    "first_report": {
        "name": "Primeiro Relatório",
        "credits": 75,
        "icon": "📄",
    },
    "invite_teammate": {
        "name": "Team Player",
        "credits": 200,
        "icon": "👥",
    },
    "thirty_day_streak": {
        "name": "Streak 30 dias",
        "description": "Usaste HackScan 30 dias consecutivos",
        "credits": 500,
        "icon": "🔥",
    },
    "first_bounty": {
        "name": "Bug Hunter",
        "description": "Submeteste o teu primeiro bug bounty",
        "credits": 300,
        "icon": "💰",
    },
}
```

### Mecânica 8 — O Trial de Upgrade que Converte (Dropbox, Figma)

```
Quando utilizador Pro tenta acção Enterprise:

┌─────────────────────────────────────────┐
│  🔐 Funcionalidade Enterprise            │
│                                          │
│  Relatório de compliance ISO 27001       │
│  requer o plano Enterprise.              │
│                                          │
│  Activa o teu trial de 7 dias — grátis. │
│  Sem cartão adicional necessário.        │
│                                          │
│  Durante o trial tens acesso a:          │
│  ✅ Compliance reports ilimitados        │
│  ✅ EASM avançado                        │
│  ✅ API enterprise                       │
│  ✅ White-label                          │
│  ✅ Suporte prioritário                  │
│                                          │
│  [Activar Trial Enterprise — Grátis]    │
│  [Não, obrigado]                         │
└─────────────────────────────────────────┘

Taxa de conversão trial → pago: 25-40% (benchmark B2B SaaS)
```

### Mecânica 9 — O Referral com Créditos (Dropbox original)

```
Dropbox cresceu 3900% com referral. O HackScan replica:

Tu convidas → link único de referral
Convidado regista → convidado recebe 100 créditos
Convidado faz upgrade → TU recebes 500 créditos

Notificação quando o convidado faz upgrade:
"🎉 O João Baptista que convidaste fez upgrade para Pro!
 Acabaste de ganhar 500 créditos AI."

Efeito: cada utilizador tem incentivo de venda para ti.
        Custo de aquisição = 500 créditos = $5 (em vez de $50+ em ads)
```

### Mecânica 10 — O "Loyalty Rollover" para Clientes Antigos (Airlines)

```
Utilizadores com subscripção activa há mais de 6 meses:
→ 20% dos créditos mensais não usados acumulam para o mês seguinte
→ Máximo de acumulação: 1 mês de créditos

Porquê retém: cancelar a subscripção significa perder os créditos acumulados.
É o mesmo mecanismo das milhas de avião — quanto mais tempo és cliente,
mais "perdes" se cancelares.
```

### Mecânica 11 — O Relatório de "O Que Perdeste" (Grammarly)

```
Email semanal automático para Free users:

Assunto: "3 vulnerabilidades críticas encontradas — 
          mas não podes ver os detalhes"

Corpo:
"Na semana passada, 47 scans foram feitos por utilizadores Pro.
Em média, encontraram 12 findings cada, incluindo:

🔴 2.3 vulnerabilidades críticas por scan
🟠 4.1 vulnerabilidades altas por scan

Os utilizadores Pro receberam explicações AI detalhadas
e relatórios PDF completos para corrigir tudo.

Os utilizadores Free como tu vêem apenas os títulos.

[Desbloquear tudo por $29/mês →]"
```

### Mecânica 12 — O "Express Mode" com Custo Duplo (Midjourney)

```python
# Dois modos de IA:
# Express: resposta em <3 segundos (2x créditos)
# Standard: resposta em <30 segundos (créditos normais)

AI_MODES = {
    "standard": {"multiplier": 1.0, "max_seconds": 30},
    "express":  {"multiplier": 2.0, "max_seconds": 3},
}

# Utilizador em situação urgente (deadline de segurança) paga express
# Utilizador relaxado usa standard
# Cria dois segmentos de preço naturais sem complexidade artificial
```

---

## 7. Fluxos de Upsell Automático

### Fluxo 1 — Créditos a zero durante scan

```
[Utilizador corre scan] → [Scan completo: 9 findings]
→ [Clica "Explicar todos com IA"]
→ [Sistema: 0 créditos disponíveis]
→ [Modal]: 
   "Os teus créditos acabaram a meio do scan.
    Os findings 1-3 foram explicados.
    Para receber os findings 4-9:
    [Comprar 500 créditos — $5] [Só quero os primeiros 3]"
→ [Se comprar]: continua automaticamente do finding 4
→ [Conversão]: alta — já está envolvido no processo
```

### Fluxo 2 — Limite de utilizadores no plano Team

```
[Team owner tenta adicionar 6º utilizador]
→ [Sistema: plano Team = máx 5 utilizadores]
→ [Banner contextual]:
   "O teu plano Team suporta até 5 utilizadores.
    Tens actualmente 5/5.
    
    Para adicionar mais membros, faz upgrade para Enterprise.
    
    💡 Com 4+ utilizadores activos, o Enterprise paga-se sozinho.
    
    [Ver plano Enterprise] [Gerir utilizadores actuais]"
```

### Fluxo 3 — Fim do trial de Enterprise

```
Dia 7 do trial (último dia):
Email: "O teu trial Enterprise termina hoje às 23:59"

Dia 8 (trial expirado):
[Utilizador tenta gerar compliance report]
→ [Modal]:
   "O teu trial Enterprise expirou ontem.
    Durante os 7 dias, geraste 3 relatórios de compliance,
    fizeste 12 scans com Nuclei e encontraste
    2 vulnerabilidades críticas via EASM.
    
    Para manter este nível de segurança:
    [Activar Enterprise — $299/mês] [Voltar ao plano Pro]"
```

### Fluxo 4 — Scan encontra vulnerabilidade crítica em Free

```
[Free user faz scan] → [Nuclei encontra RCE crítico]
→ [Dashboard mostra]: 🔴 1 VULNERABILIDADE CRÍTICA ENCONTRADA
→ [Finding card]: título visível, detalhes bloqueados
→ [CTA urgente]:
   "⚠️ RISCO CRÍTICO DETECTADO
    O teu sistema tem uma vulnerabilidade que permite
    execução remota de código.
    
    Esta vulnerabilidade pode comprometer completamente
    o teu servidor em menos de 5 minutos se explorada.
    
    Desbloqueia os detalhes e a remediação:
    [Ver detalhes — 10 créditos] [Upgrade Pro — ilimitado]"

→ A urgência de uma vuln crítica converte melhor que qualquer copy
```

---

## 8. Schema de Base de Dados Completo

```sql
-- ============================================================
-- AI WALLETS — Carteira principal de créditos
-- ============================================================
CREATE TABLE ai_wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID UNIQUE NOT NULL 
        REFERENCES workspaces(id) ON DELETE CASCADE,
    
    -- Saldos separados por origem
    balance_subscription  INTEGER NOT NULL DEFAULT 0 CHECK (balance_subscription >= 0),
    balance_purchased     INTEGER NOT NULL DEFAULT 0 CHECK (balance_purchased >= 0),
    balance_bonus         INTEGER NOT NULL DEFAULT 0 CHECK (balance_bonus >= 0),
    
    -- Saldo total (computed)
    balance_total INTEGER GENERATED ALWAYS AS 
        (balance_subscription + balance_purchased + balance_bonus) STORED,
    
    -- Métricas de lifetime
    lifetime_credits_granted INTEGER NOT NULL DEFAULT 0,
    lifetime_credits_used    INTEGER NOT NULL DEFAULT 0,
    lifetime_revenue_usd     DECIMAL(10,2) NOT NULL DEFAULT 0,
    
    -- Auto-reload
    auto_reload_enabled   BOOLEAN NOT NULL DEFAULT FALSE,
    auto_reload_threshold INTEGER NOT NULL DEFAULT 100,
    auto_reload_package   VARCHAR(50),  -- slug do pacote
    auto_reload_stripe_pm VARCHAR(255), -- payment method ID
    
    -- Estado de alertas
    low_balance_alert_sent_at TIMESTAMPTZ,
    zero_balance_alert_sent_at TIMESTAMPTZ,
    
    -- Loyalty
    consecutive_months_active INTEGER NOT NULL DEFAULT 0,
    rollover_credits          INTEGER NOT NULL DEFAULT 0,
    
    -- Express mode
    express_mode_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_wallets_workspace ON ai_wallets(workspace_id);
CREATE INDEX idx_ai_wallets_balance ON ai_wallets(balance_total) 
    WHERE balance_total < 100;


-- ============================================================
-- AI TRANSACTIONS — Cada movimento de créditos
-- ============================================================
CREATE TABLE ai_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id      UUID REFERENCES users(id) ON DELETE SET NULL,
    
    -- Tipo e categorização
    type    VARCHAR(20) NOT NULL CHECK (type IN ('credit', 'debit')),
    action  VARCHAR(100) NOT NULL,
    -- CREDIT actions: purchase, monthly_grant, bonus_achievement,
    --                 referral_reward, welcome_bonus, auto_reload,
    --                 rollover, refund, admin_grant
    -- DEBIT actions:  explain_finding, explain_finding_first_use,
    --                 generate_report_pdf, generate_report_executive,
    --                 ai_forecaster, attack_chains, remediation_code,
    --                 chat_message, compliance_report, express_surcharge
    
    -- Origem dos créditos debitados (ordem de consumo)
    debit_from_subscription INTEGER NOT NULL DEFAULT 0,
    debit_from_purchased    INTEGER NOT NULL DEFAULT 0,
    debit_from_bonus        INTEGER NOT NULL DEFAULT 0,
    
    -- Valores
    amount         INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after  INTEGER NOT NULL,
    
    -- Modo de execução
    mode          VARCHAR(20) DEFAULT 'standard' 
        CHECK (mode IN ('standard', 'express')),
    mode_multiplier DECIMAL(3,1) DEFAULT 1.0,
    
    -- Métricas de IA
    tokens_input  INTEGER,
    tokens_output INTEGER,
    model_used    VARCHAR(100),
    
    -- Financeiro (interno — nunca exposto ao cliente)
    cost_usd    DECIMAL(10,6),
    revenue_usd DECIMAL(10,6),
    margin_pct  DECIMAL(5,2),
    
    -- Cache
    was_cached    BOOLEAN NOT NULL DEFAULT FALSE,
    cache_hit_key VARCHAR(255),
    
    -- Referência ao recurso
    reference_type VARCHAR(100),
    reference_id   UUID,
    
    -- Stripe (para compras)
    stripe_payment_intent_id VARCHAR(255),
    stripe_charge_id         VARCHAR(255),
    
    -- Metadata adicional
    metadata JSONB NOT NULL DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ai_transactions_workspace_date 
    ON ai_transactions(workspace_id, created_at DESC);
CREATE INDEX idx_ai_transactions_type_action 
    ON ai_transactions(type, action);
CREATE INDEX idx_ai_transactions_reference 
    ON ai_transactions(reference_type, reference_id) 
    WHERE reference_id IS NOT NULL;
CREATE INDEX idx_ai_transactions_stripe 
    ON ai_transactions(stripe_payment_intent_id) 
    WHERE stripe_payment_intent_id IS NOT NULL;


-- ============================================================
-- CREDIT PACKAGES — Pacotes disponíveis para compra
-- ============================================================
CREATE TABLE credit_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name          VARCHAR(100) NOT NULL,
    slug          VARCHAR(50) UNIQUE NOT NULL,
    tagline       VARCHAR(255),              -- "Perfeito para começar"
    
    credits       INTEGER NOT NULL,
    bonus_credits INTEGER NOT NULL DEFAULT 0,
    total_credits INTEGER GENERATED ALWAYS AS (credits + bonus_credits) STORED,
    
    price_usd        DECIMAL(10,2) NOT NULL,
    price_per_credit DECIMAL(10,6) GENERATED ALWAYS AS 
        (price_usd / (credits + bonus_credits + 0.000001)) STORED,
    
    stripe_price_id VARCHAR(255),
    
    -- Apresentação
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE, -- destaque "Popular"
    badge_text  VARCHAR(50),                    -- "Melhor valor"
    sort_order  INTEGER NOT NULL DEFAULT 0,
    
    -- Limites de compra (prevenção de fraude)
    max_per_workspace_per_month INTEGER DEFAULT 5,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO credit_packages 
    (name, slug, tagline, credits, bonus_credits, price_usd, 
     is_featured, badge_text, sort_order) VALUES
    ('Micro',   'micro',   'Para experimentar',         100,   0,    1.99,  FALSE, NULL,           0),
    ('Starter', 'starter', 'Para uso ocasional',         500,   0,    5.00,  FALSE, NULL,           1),
    ('Growth',  'growth',  'O mais popular',            2000, 200,   20.00,  TRUE,  '⭐ Popular',   2),
    ('Power',   'power',   'Para equipas activas',      5000, 1000,  50.00,  FALSE, '+20% bónus',   3),
    ('Ultra',   'ultra',   'Melhor custo-benefício',   10000, 5000, 100.00,  FALSE, 'Melhor valor', 4);


-- ============================================================
-- ACHIEVEMENTS — Conquistas que dão créditos
-- ============================================================
CREATE TABLE achievements (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug        VARCHAR(100) UNIQUE NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    icon        VARCHAR(10),
    credits     INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workspace_achievements (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id   UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    achievement_id UUID NOT NULL REFERENCES achievements(id),
    unlocked_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    credits_awarded INTEGER NOT NULL,
    UNIQUE(workspace_id, achievement_id)
);

INSERT INTO achievements (slug, name, description, icon, credits) VALUES
    ('first_scan',         'Primeiro Scan',     'Completaste o teu primeiro scan',          '🔍', 50),
    ('five_scans',         'Caçador de Vulns',  'Completaste 5 scans',                      '🎯', 100),
    ('twenty_scans',       'Scanner Profissional','Completaste 20 scans',                   '⚡', 200),
    ('first_critical',     'Alerta Máximo',     'Encontraste uma vulnerabilidade crítica',  '🚨', 150),
    ('first_report',       'Primeiro Relatório','Geraste o teu primeiro relatório PDF',     '📄', 75),
    ('invite_teammate',    'Team Player',       'Convidaste um membro para a equipa',       '👥', 200),
    ('thirty_day_streak',  'Streak 30 dias',    'Usaste HackScan 30 dias consecutivos',     '🔥', 500),
    ('first_bounty',       'Bug Hunter',        'Submeteste o teu primeiro bug bounty',     '💰', 300),
    ('first_fix',          'Remediation Hero',  'Marcaste um finding como corrigido',       '✅', 50),
    ('referral_success',   'Embaixador',        'O teu referral fez upgrade para pago',     '🌟', 500);


-- ============================================================
-- MONTHLY GRANTS — Concessões mensais do plano (auditoria)
-- ============================================================
CREATE TABLE monthly_credit_grants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id),
    period_start    TIMESTAMPTZ NOT NULL,
    period_end      TIMESTAMPTZ NOT NULL,
    credits_granted INTEGER NOT NULL,
    rollover_added  INTEGER NOT NULL DEFAULT 0,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, period_start)
);


-- ============================================================
-- REFERRALS — Programa de referral
-- ============================================================
CREATE TABLE referrals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id     UUID NOT NULL REFERENCES users(id),
    referred_id     UUID REFERENCES users(id),
    referral_code   VARCHAR(20) UNIQUE NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    -- pending, signed_up, upgraded, rewarded
    credits_awarded INTEGER NOT NULL DEFAULT 0,
    upgraded_at     TIMESTAMPTZ,
    rewarded_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_referrals_code ON referrals(referral_code);
CREATE INDEX idx_referrals_referrer ON referrals(referrer_id);
```

---

## 9. Implementação Técnica Completa

### 9.1 Credit Service

```python
# ai/credit_service.py
import logging
import secrets
from decimal import Decimal
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    def __init__(self, needed: int, available: int, action: str):
        self.needed = needed
        self.available = available
        self.action = action
        self.shortfall = needed - available
        super().__init__(
            f"Créditos insuficientes para '{action}': "
            f"necessário {needed}, disponível {available}"
        )


class CreditService:

    # Custo base por acção (créditos)
    COSTS = {
        "explain_finding":             10,
        "explain_finding_first_use":    0,   # grátis
        "explain_finding_express":     20,   # 2x em express mode
        "generate_report_pdf":         60,
        "generate_report_executive":   90,
        "ai_forecaster":               35,
        "attack_chains":               50,
        "remediation_code":            15,
        "chat_message":                 5,
        "chat_message_express":        10,
        "compliance_report_lgpd":     150,
        "compliance_report_iso":      200,
        "compliance_report_pci":      180,
    }

    # Custo Anthropic por 1M tokens
    ANTHROPIC_INPUT_CPM  = Decimal("3.00")
    ANTHROPIC_OUTPUT_CPM = Decimal("15.00")

    # Receita por crédito
    REVENUE_PER_CREDIT = Decimal("0.01")

    @classmethod
    def get_cost(cls, action: str, express: bool = False) -> int:
        """Retorna custo em créditos. Express = 2x para acções elegíveis."""
        if express and f"{action}_express" in cls.COSTS:
            return cls.COSTS[f"{action}_express"]
        return cls.COSTS.get(action, 10)

    @classmethod
    def check_balance(
        cls,
        workspace,
        action: str,
        express: bool = False,
    ) -> tuple[bool, int, int]:
        """
        Verifica saldo.
        Returns: (has_balance, cost, current_balance)
        """
        cost = cls.get_cost(action, express)
        if cost == 0:
            return True, 0, 0

        try:
            wallet = AIWallet.objects.get(workspace=workspace)
            return wallet.balance_total >= cost, cost, wallet.balance_total
        except AIWallet.DoesNotExist:
            return False, cost, 0

    @classmethod
    @transaction.atomic
    def debit(
        cls,
        workspace,
        user,
        action: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        model_used: str = "claude-opus-4-5",
        reference_type: str = None,
        reference_id=None,
        was_cached: bool = False,
        express: bool = False,
        cache_key: str = None,
    ) -> "AITransaction":
        """
        Debita créditos de forma atómica.
        Ordem de consumo: subscription → purchased → bonus
        """
        cost = 0 if was_cached else cls.get_cost(action, express)

        wallet = AIWallet.objects.select_for_update().get_or_create(
            workspace=workspace,
            defaults={"balance_subscription": 0, "balance_purchased": 0}
        )[0]

        if not was_cached and wallet.balance_total < cost:
            raise InsufficientCreditsError(cost, wallet.balance_total, action)

        balance_before = wallet.balance_total

        # Consumir na ordem correcta: subscription → purchased → bonus
        debit_sub = debit_purch = debit_bonus = 0
        if not was_cached and cost > 0:
            remaining = cost
            # 1. Consumir créditos de subscripção primeiro (expiram)
            use_sub = min(remaining, wallet.balance_subscription)
            wallet.balance_subscription -= use_sub
            debit_sub = use_sub
            remaining -= use_sub
            # 2. Consumir créditos comprados (nunca expiram)
            if remaining > 0:
                use_purch = min(remaining, wallet.balance_purchased)
                wallet.balance_purchased -= use_purch
                debit_purch = use_purch
                remaining -= use_purch
            # 3. Consumir bónus por último
            if remaining > 0:
                use_bonus = min(remaining, wallet.balance_bonus)
                wallet.balance_bonus -= use_bonus
                debit_bonus = use_bonus

            wallet.lifetime_credits_used += cost
            wallet.save(update_fields=[
                "balance_subscription", "balance_purchased",
                "balance_bonus", "lifetime_credits_used", "updated_at"
            ])

        # Calcular métricas financeiras
        cost_usd = (
            Decimal(tokens_input) * cls.ANTHROPIC_INPUT_CPM +
            Decimal(tokens_output) * cls.ANTHROPIC_OUTPUT_CPM
        ) / Decimal("1000000")

        revenue_usd = Decimal(cost) * cls.REVENUE_PER_CREDIT
        margin_pct = (
            (revenue_usd - cost_usd) / revenue_usd * 100
            if revenue_usd > 0 else Decimal("0")
        )

        tx = AITransaction.objects.create(
            workspace=workspace,
            user=user,
            type="debit",
            action=action,
            amount=cost,
            balance_before=balance_before,
            balance_after=wallet.balance_total,
            debit_from_subscription=debit_sub,
            debit_from_purchased=debit_purch,
            debit_from_bonus=debit_bonus,
            mode="express" if express else "standard",
            mode_multiplier=Decimal("2.0") if express else Decimal("1.0"),
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_used=model_used,
            cost_usd=cost_usd,
            revenue_usd=revenue_usd,
            margin_pct=margin_pct,
            was_cached=was_cached,
            cache_hit_key=cache_key if was_cached else None,
            reference_type=reference_type,
            reference_id=reference_id,
        )

        # Actualizar revenue lifetime
        if not was_cached:
            wallet.lifetime_revenue_usd += revenue_usd
            wallet.save(update_fields=["lifetime_revenue_usd"])

        # Verificar alertas de saldo baixo
        if not was_cached:
            cls._check_alerts(workspace, wallet)

        logger.info("ai.credit.debit",
            workspace_id=str(workspace.id),
            action=action, cost=cost,
            balance_after=wallet.balance_total,
            margin_pct=float(margin_pct),
            was_cached=was_cached,
        )

        return tx

    @classmethod
    @transaction.atomic
    def credit(
        cls,
        workspace,
        amount: int,
        action: str,
        credit_type: str = "bonus",  # subscription, purchased, bonus
        user=None,
        stripe_payment_intent_id: str = None,
    ) -> "AITransaction":
        """Adiciona créditos ao wallet."""
        wallet, _ = AIWallet.objects.select_for_update().get_or_create(
            workspace=workspace,
            defaults={}
        )

        balance_before = wallet.balance_total

        if credit_type == "subscription":
            wallet.balance_subscription += amount
        elif credit_type == "purchased":
            wallet.balance_purchased += amount
        else:
            wallet.balance_bonus += amount

        wallet.lifetime_credits_granted += amount
        wallet.low_balance_alert_sent_at = None   # reset alertas
        wallet.zero_balance_alert_sent_at = None
        wallet.save()

        tx = AITransaction.objects.create(
            workspace=workspace,
            user=user,
            type="credit",
            action=action,
            amount=amount,
            balance_before=balance_before,
            balance_after=wallet.balance_total,
            stripe_payment_intent_id=stripe_payment_intent_id,
        )

        logger.info("ai.credit.credit",
            workspace_id=str(workspace.id),
            action=action, amount=amount,
            balance_after=wallet.balance_total,
        )

        return tx

    @classmethod
    def is_first_use(cls, workspace, action: str) -> bool:
        """Verifica se é o primeiro uso desta acção no workspace."""
        return not AITransaction.objects.filter(
            workspace=workspace,
            type="debit",
            action=action,
        ).exclude(action=f"{action}_first_use").exists()

    @classmethod
    def grant_achievement(cls, workspace, achievement_slug: str) -> bool:
        """
        Concede achievement se ainda não desbloqueado.
        Retorna True se foi desbloqueado agora.
        """
        achievement = Achievement.objects.filter(
            slug=achievement_slug, is_active=True
        ).first()
        if not achievement:
            return False

        _, created = WorkspaceAchievement.objects.get_or_create(
            workspace=workspace,
            achievement=achievement,
            defaults={"credits_awarded": achievement.credits}
        )

        if created and achievement.credits > 0:
            cls.credit(
                workspace=workspace,
                amount=achievement.credits,
                action=f"bonus_achievement_{achievement_slug}",
                credit_type="bonus",
            )
            # Notificar utilizador
            from notifications.tasks import notify_achievement_unlocked
            notify_achievement_unlocked.delay(
                workspace_id=str(workspace.id),
                achievement_slug=achievement_slug,
            )

        return created

    @classmethod
    def _check_alerts(cls, workspace, wallet) -> None:
        """Verifica e dispara alertas de saldo baixo."""
        from notifications.tasks import notify_low_credits, notify_zero_credits
        from billing.models import Plan

        plan = getattr(
            getattr(workspace, 'subscription', None), 'plan', None
        )
        monthly = plan.features.get("ai_credits_monthly", 600) if plan else 600
        threshold = int(monthly * 0.20)

        now = timezone.now()

        if wallet.balance_total == 0 and not wallet.zero_balance_alert_sent_at:
            notify_zero_credits.delay(workspace_id=str(workspace.id))
            wallet.zero_balance_alert_sent_at = now
            wallet.save(update_fields=["zero_balance_alert_sent_at"])

        elif (
            wallet.balance_total <= threshold
            and not wallet.low_balance_alert_sent_at
        ):
            notify_low_credits.delay(
                workspace_id=str(workspace.id),
                balance=wallet.balance_total,
                threshold=threshold,
            )
            wallet.low_balance_alert_sent_at = now
            wallet.save(update_fields=["low_balance_alert_sent_at"])


### 9.2 Decorator para AI Actions

def ai_action(action: str, cache_ttl: int = 3600, allow_express: bool = True):
    """
    Decorator que gere todo o ciclo de vida de uma chamada IA:
    cache → saldo → execução → debit → cache store
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, workspace=None, user=None,
                    express: bool = False, **kwargs):
            
            # Cache key baseada nos argumentos
            import hashlib
            key_data = f"{action}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = f"ai:{hashlib.md5(key_data.encode()).hexdigest()}"

            # 1. Verificar cache
            cached = cache.get(cache_key)
            if cached is not None:
                CreditService.debit(
                    workspace=workspace, user=user,
                    action=action, was_cached=True, cache_key=cache_key,
                )
                return cached

            # 2. Verificar se é primeiro uso (grátis)
            is_first = CreditService.is_first_use(workspace, action)
            effective_action = f"{action}_first_use" if is_first else action

            # 3. Verificar saldo
            has_balance, cost, balance = CreditService.check_balance(
                workspace, effective_action, express
            )
            if not has_balance:
                raise InsufficientCreditsError(cost, balance, effective_action)

            # 4. Executar função de IA
            result, usage = func(*args, **kwargs)

            # 5. Debitar com tokens reais
            CreditService.debit(
                workspace=workspace,
                user=user,
                action=effective_action,
                tokens_input=getattr(usage, 'input_tokens', 0),
                tokens_output=getattr(usage, 'output_tokens', 0),
                express=express,
            )

            # 6. Guardar em cache
            cache.set(cache_key, result, cache_ttl)

            # 7. Verificar achievements após uso
            from ai.tasks import check_achievements_after_ai_use
            check_achievements_after_ai_use.delay(
                workspace_id=str(workspace.id)
            )

            return result

        return wrapper
    return decorator
```

---

## 10. Frontend — Experiência que Converte

### Componente de Saldo no Header

```typescript
// components/ai/CreditsBadge.tsx
"use client"
import { useWallet } from "@/hooks/useWallet"
import { cn } from "@/lib/utils"
import Link from "next/link"

export function CreditsBadge() {
  const { data: wallet, isLoading } = useWallet()
  
  if (isLoading) return <div className="w-24 h-6 bg-gray-800 animate-pulse rounded" />
  
  const balance = wallet?.balance_total ?? 0
  const isLow = balance < 100
  const isEmpty = balance === 0

  return (
    <Link href="/billing/credits">
      <div className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-md border",
        "text-xs font-mono transition-all cursor-pointer",
        isEmpty  && "border-red-500/50 bg-red-500/10 text-red-400 animate-pulse",
        isLow && !isEmpty && "border-yellow-500/50 bg-yellow-500/10 text-yellow-400",
        !isLow   && "border-green-500/30 bg-green-500/5 text-green-400",
      )}>
        <span className="text-base leading-none">⚡</span>
        <span className="font-bold">{balance.toLocaleString()}</span>
        <span className="text-gray-600">crd</span>
        {isEmpty && (
          <span className="ml-1 text-red-400 text-[10px] font-bold">
            RECARREGAR
          </span>
        )}
      </div>
    </Link>
  )
}
```

### Modal de Créditos Insuficientes

```typescript
// components/ai/InsufficientCreditsModal.tsx
const ACTION_LABELS: Record<string, string> = {
  explain_finding:           "explicar esta vulnerabilidade",
  generate_report_pdf:       "gerar o relatório PDF",
  generate_report_executive: "gerar o relatório executivo",
  ai_forecaster:             "analisar attack chains",
  attack_chains:             "prever cadeia de ataques",
  remediation_code:          "gerar código de remediação",
  compliance_report_lgpd:    "gerar relatório LGPD",
}

export function InsufficientCreditsModal({
  action,
  needed,
  available,
  onClose,
}: {
  action: string
  needed: number
  available: number
  onClose: () => void
}) {
  const router = useRouter()
  const shortfall = needed - available

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm
                    flex items-center justify-center z-50 p-4">
      <div className="border border-red-500/40 bg-gray-950 rounded-xl
                      p-6 max-w-sm w-full shadow-2xl shadow-red-500/10">
        
        {/* Header */}
        <div className="flex items-start gap-3 mb-5">
          <div className="w-10 h-10 rounded-full bg-red-500/20 
                          flex items-center justify-center flex-shrink-0">
            <span className="text-xl">⚡</span>
          </div>
          <div>
            <h3 className="font-mono text-white font-bold">
              Créditos insuficientes
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {needed} necessários · {available} disponíveis
            </p>
          </div>
        </div>

        {/* Corpo */}
        <p className="text-gray-400 text-sm mb-2">
          Para {ACTION_LABELS[action] ?? action}, precisas de{" "}
          <span className="text-white font-mono font-bold">{needed}</span>{" "}
          créditos.
        </p>
        <p className="text-gray-500 text-sm mb-6">
          Faltam apenas{" "}
          <span className="text-yellow-400 font-mono">{shortfall}</span>{" "}
          créditos. O pacote Micro de{" "}
          <span className="text-green-400">$1.99</span> resolve isso.
        </p>

        {/* Quick buy sugerido */}
        <div className="border border-green-500/30 rounded-lg p-3 mb-4 
                        bg-green-500/5 cursor-pointer hover:bg-green-500/10
                        transition-colors"
             onClick={() => router.push("/billing/credits?package=micro")}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-400 font-mono font-bold text-sm">
                Micro — 100 créditos
              </p>
              <p className="text-gray-500 text-xs">
                Suficiente para {Math.floor(100 / needed)} acções
              </p>
            </div>
            <div className="text-right">
              <p className="text-white font-bold">$1.99</p>
              <p className="text-gray-600 text-xs">pagamento único</p>
            </div>
          </div>
        </div>

        {/* CTAs */}
        <button
          className="w-full py-2.5 bg-green-500 text-black font-bold
                     font-mono rounded-lg hover:bg-green-400 transition-colors mb-2"
          onClick={() => router.push("/billing/credits")}
        >
          Ver todos os pacotes →
        </button>
        <button
          className="w-full py-2 text-gray-600 text-sm hover:text-gray-400
                     transition-colors"
          onClick={onClose}
        >
          Cancelar
        </button>
      </div>
    </div>
  )
}
```

### Hook de AI com gestão de créditos

```typescript
// hooks/useAI.ts
import { useState } from "react"
import { api } from "@/lib/api"
import { useWallet } from "./useWallet"

interface AIActionOptions {
  express?: boolean
  onInsufficientCredits?: (needed: number, available: number) => void
}

export function useAI() {
  const [loading, setLoading] = useState(false)
  const { refetch: refetchWallet } = useWallet()

  const explainFinding = async (
    findingId: string,
    options: AIActionOptions = {}
  ) => {
    setLoading(true)
    try {
      const result = await api.ai.explainFinding(findingId, {
        express: options.express,
      })
      
      // Actualizar saldo após uso
      await refetchWallet()
      
      return result
    } catch (error: any) {
      if (error.status === 402) {
        // Créditos insuficientes
        options.onInsufficientCredits?.(
          error.data.credits_needed,
          error.data.credits_available,
        )
        return null
      }
      throw error
    } finally {
      setLoading(false)
    }
  }

  return { explainFinding, loading }
}
```

---

## 11. Stripe — Pagamentos e Webhooks

```python
# billing/services.py — compra de créditos

class BillingService:

    @staticmethod
    def create_credits_checkout(
        workspace,
        package: CreditPackage,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Checkout Stripe para compra pontual de créditos."""
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            customer_email=workspace.owner.email,
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"HackScan Pro — {package.total_credits:,} créditos AI",
                        "description": (
                            f"{package.credits:,} créditos base"
                            + (f" + {package.bonus_credits:,} créditos bónus"
                               if package.bonus_credits else "")
                        ),
                        "images": ["https://hackerscan.pro/og/credits.png"],
                    },
                    "unit_amount": int(package.price_usd * 100),
                },
                "quantity": 1,
            }],
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "type": "credit_purchase",
                "workspace_id": str(workspace.id),
                "package_id": str(package.id),
                "package_slug": package.slug,
                "credits": str(package.total_credits),
            },
            payment_intent_data={
                "metadata": {
                    "workspace_id": str(workspace.id),
                    "package_slug": package.slug,
                }
            },
        )
        return session.url

    @staticmethod
    def handle_credit_purchase_webhook(session: dict) -> None:
        """
        Webhook handler para compra de créditos.
        IDEMPOTENTE — usa payment_intent_id como chave.
        """
        if session.get("metadata", {}).get("type") != "credit_purchase":
            return

        payment_intent_id = session.get("payment_intent")
        if not payment_intent_id:
            return

        # IDEMPOTÊNCIA
        if AITransaction.objects.filter(
            stripe_payment_intent_id=payment_intent_id,
            type="credit",
            action="purchase",
        ).exists():
            logger.warning("credit_purchase.duplicate_webhook",
                           payment_intent_id=payment_intent_id)
            return

        workspace_id = session["metadata"]["workspace_id"]
        credits = int(session["metadata"]["credits"])
        package_slug = session["metadata"]["package_slug"]

        workspace = Workspace.objects.get(id=workspace_id)

        CreditService.credit(
            workspace=workspace,
            amount=credits,
            action="purchase",
            credit_type="purchased",   # nunca expiram
            stripe_payment_intent_id=payment_intent_id,
        )

        # Notificar utilizador
        from notifications.tasks import notify_credits_purchased
        notify_credits_purchased.delay(
            workspace_id=workspace_id,
            credits=credits,
            package_slug=package_slug,
        )

        # Verificar achievement "first purchase"
        if not AITransaction.objects.filter(
            workspace=workspace,
            type="credit",
            action="purchase",
        ).exclude(stripe_payment_intent_id=payment_intent_id).exists():
            CreditService.grant_achievement(workspace, "first_purchase")

        logger.info("credit_purchase.processed",
                    workspace_id=workspace_id,
                    credits=credits,
                    package=package_slug)
```

---

## 12. Analytics e Métricas de Monetização

### Dashboard interno de revenue por acção

```python
# analytics/credit_analytics.py

class CreditAnalytics:
    
    @staticmethod
    def revenue_by_action(days: int = 30) -> list[dict]:
        """Revenue gerado por cada tipo de acção IA."""
        from django.db.models import Sum, Count, Avg
        since = timezone.now() - timedelta(days=days)
        
        return list(
            AITransaction.objects.filter(
                type="debit",
                was_cached=False,
                created_at__gte=since,
            ).values("action").annotate(
                total_revenue=Sum("revenue_usd"),
                total_cost=Sum("cost_usd"),
                total_actions=Count("id"),
                avg_margin=Avg("margin_pct"),
                total_tokens=Sum("tokens_input") + Sum("tokens_output"),
            ).order_by("-total_revenue")
        )

    @staticmethod
    def conversion_funnel() -> dict:
        """
        Métricas do funil de conversão de créditos.
        Onde os utilizadores estão no funil?
        """
        total_workspaces = Workspace.objects.count()
        
        used_free_ai = AITransaction.objects.filter(
            action="explain_finding_first_use"
        ).values("workspace_id").distinct().count()
        
        made_first_purchase = AITransaction.objects.filter(
            type="credit", action="purchase"
        ).values("workspace_id").distinct().count()
        
        recurring_buyers = (
            AITransaction.objects.filter(type="credit", action="purchase")
            .values("workspace_id")
            .annotate(purchases=Count("id"))
            .filter(purchases__gte=2)
            .count()
        )
        
        return {
            "total_workspaces": total_workspaces,
            "used_free_ai": used_free_ai,
            "free_ai_rate": used_free_ai / total_workspaces * 100,
            "made_first_purchase": made_first_purchase,
            "first_purchase_rate": made_first_purchase / used_free_ai * 100,
            "recurring_buyers": recurring_buyers,
            "recurring_rate": recurring_buyers / made_first_purchase * 100,
        }
```

### KPIs a monitorizar semanalmente

```
Métrica                    Meta inicial    Meta 6 meses
────────────────────────────────────────────────────────
Credit ARPU (médio)        $3/mês         $8/mês
Free → primeiro pagamento  5%             15%
Retenção de compradores    40%            65%
Margem bruta créditos      80%            83%
Auto-reload activado       5%             25%
Cache hit rate             30%            60%  ← reduz custo
Revenue per AI action      $0.12          $0.18
```

---

## 13. Projecções Financeiras Detalhadas

### Cenário Base — Angola + Mercado Lusófono

```
MESES 1-3: Lançamento e traction inicial
────────────────────────────────────────
Utilizadores Free:        50  → $0 subscripção
                              → $1.50/mês em créditos (avg)
                              → $75/mês

Utilizadores Pro:         10  → $290/mês subscripção
                              → $12/mês em créditos extra
                              → $410/mês

MRR Total mês 3:  ~$485/mês
Custo Anthropic:  ~$50/mês  (10% da receita IA)
Custo infra:      ~$150/mês (Docker, VPS)
Margem:           ~$285/mês


MESES 4-6: Crescimento e primeiros Enterprise
─────────────────────────────────────────────
Free:        200 utilizadores  → $300/mês créditos
Pro:          40 utilizadores  → $1.160/mês sub + $480/mês créditos
Team:          8 utilizadores  → $792/mês sub + $320/mês créditos
Enterprise:    2 clientes      → $598/mês sub

MRR Total mês 6:   ~$3.650/mês
Custo Anthropic:   ~$280/mês
Custo infra:       ~$250/mês
Lucro líquido:     ~$3.120/mês  ← €3.120 MENSAIS em Angola


MESES 7-12: Escala e expansão
──────────────────────────────
Free:        1.000 utilizadores → $1.500/mês créditos
Pro:          120 utilizadores  → $3.480/mês sub + $1.440/mês créditos
Team:          25 utilizadores  → $2.475/mês sub + $1.000/mês créditos
Enterprise:     8 clientes      → $2.392/mês sub

MRR Total mês 12:  ~$12.287/mês
ARR:               ~$147.000/ano
Custo Anthropic:   ~$980/mês
Custo infra:       ~$600/mês
Lucro líquido:     ~$10.707/mês  ← quase $11.000/mês no ano 1
```

### Comparação com modelo sem créditos IA

```
Modelo só subscripção (sem créditos):
  Mês 12 MRR:  ~$8.700/mês

Modelo subscripção + créditos:
  Mês 12 MRR:  ~$12.287/mês

Diferença: +41% de revenue com o mesmo número de utilizadores
```

---

## 14. Roadmap de Implementação

### Sprint A — Backend (Semana 1)

```
Dia 1: Migrations (ai_wallets, ai_transactions, credit_packages, achievements)
Dia 2: CreditService completo (check_balance, debit, credit, grant_achievement)
Dia 3: Decorator @ai_action + integração em AIService
Dia 4: Endpoints API (wallet, packages, transaction history, purchase)
Dia 5: Webhook Stripe para compra de créditos (idempotente)
Dia 6: Grant mensal via webhook invoice.payment_succeeded
Dia 7: Testes (thread safety, idempotência, edge cases)

Modelos: Sonnet para services/endpoints · Opus para decorator e idempotência
```

### Sprint B — Frontend (Semana 2)

```
Dia 1: CreditsBadge no Header + useWallet hook
Dia 2: /billing/credits page (saldo + pacotes + historial)
Dia 3: InsufficientCreditsModal + useAI hook
Dia 4: Integração nos botões de AI (explain, report, forecaster)
Dia 5: Auto-reload settings
Dia 6: Achievements UI (lista + notificação de desbloqueio)
Dia 7: Testes E2E (compra, uso, modal, recarga)

Modelos: Gemini Pro Low para todo o frontend
```

### Sprint C — Retenção (Semana 3)

```
Dia 1: Welcome credits no registo (100 créditos, 7 dias expiração)
Dia 2: Primeiro uso grátis (lógica + UI "foi grátis!")
Dia 3: Alertas de saldo baixo (email + in-app + push)
Dia 4: Referral program (código único + rastreio)
Dia 5: Achievements automáticos via signals Django
Dia 6: Email semanal "O que perdeste" para Free users
Dia 7: A/B test nos preços dos pacotes

Modelos: Sonnet para backend · Gemini Low para emails HTML
```

---

## 15. Prompt

Copia este prompt:

```
Tens o projecto HackScan Pro em /apps/api/ (Django) e /apps/web/ (Next.js).

Implementa o sistema completo de créditos de IA seguindo este plano:

FASE 1 — Base de dados:
Cria as migrations para estas tabelas novas:
- ai_wallets (com balance_subscription, balance_purchased, balance_bonus separados)
- ai_transactions (com todas as métricas financeiras)
- credit_packages (com os 5 pacotes: micro $1.99, starter $5, growth $20, power $50, ultra $100)
- achievements (com os 10 achievements definidos)
- workspace_achievements
- monthly_credit_grants

FASE 2 — CreditService:
Cria apps/api/ai/credit_service.py com:
- check_balance(workspace, action, express=False) → tuple[bool, int, int]
- debit(workspace, user, action, tokens_input, tokens_output, ...) → AITransaction
- credit(workspace, amount, action, credit_type, ...) → AITransaction
- is_first_use(workspace, action) → bool
- grant_achievement(workspace, achievement_slug) → bool
- grant_monthly_credits(workspace, subscription) → None
- _check_alerts(workspace, wallet) → None
Tudo atómico (SELECT FOR UPDATE). Ordem de consumo: subscription → purchased → bonus.

FASE 3 — Decorator @ai_action:
Cria o decorator que gere cache → saldo → execução → debit → cache store.
Integra em todos os métodos de AIService (explain_finding, predict_attack_chains, 
generate_remediation_code, compliance_report).

FASE 4 — API endpoints:
Cria apps/api/ai/views.py com:
- GET /v1/ai/wallet/ → saldo e breakdown por tipo
- GET /v1/ai/packages/ → lista de pacotes
- GET /v1/ai/transactions/ → historial paginado
- POST /v1/billing/credits/checkout/ → criar sessão Stripe
- GET /v1/ai/achievements/ → achievements do workspace

FASE 5 — Webhook Stripe:
Em apps/api/billing/services.py adiciona handle_credit_purchase_webhook()
IDEMPOTENTE via stripe_payment_intent_id.
Debita créditos do tipo "purchased" (nunca expiram).

FASE 6 — Grant mensal:
No handler de invoice.payment_succeeded, chama CreditService.grant_monthly_credits()
com os créditos do plano (Plan.features["ai_credits_monthly"]).
Garante idempotência via monthly_credit_grants.

FASE 7 — Testes:
Cria testes para: thread safety do debit, idempotência do webhook,
ordem de consumo (subscription primeiro), primeiro uso grátis,
grant mensal não duplicado.

Após cada fase, corre: python manage.py test ai.tests -v2
Corrige erros antes de avançar para a fase seguinte.

Usa SELECT FOR UPDATE em todas as operações de wallet.
Usa structlog para todos os logs.
Nunca expões os campos cost_usd, revenue_usd, margin_pct na API pública.
```

---

## Resumo Executivo

O modelo de créditos de IA é a decisão de produto mais importante do HackScan Pro pelos seguintes motivos:

**1. Alinha preço com valor** — quem usa mais, paga mais. Quem usa pouco, paga pouco. Todos ficam satisfeitos.

**2. 83% de margem bruta** — cada $1 cobrado em créditos custa $0.17. É uma das margens mais altas possíveis em tecnologia.

**3. Cria urgência sem pressão** — o saldo a diminuir é visível, natural e auto-explicativo. Não precisas de pushs agressivos.

**4. O primeiro pagamento é o mais difícil** — o pacote Micro de $1.99 existe para ultrapassar essa barreira. Uma vez que pagou $1.99, paga $20 sem pensar.

**5. Os créditos comprados não expiram** — remove o medo de "perder dinheiro" e aumenta o ticket médio por transacção.

**6. Escalável sem custo marginal** — quando tens 1.000 utilizadores a usar IA, o custo escala linearmente mas a receita escala com a margem. Nunca pagas mais do que recebes.

**7. Angola é o mercado perfeito para pioneiro** — nenhum concorrente tem presença, suporte em português ou preços adaptados. O utilizador angolano que descobrir o HackScan vai recomendar aos colegas porque não há alternativa.

A combinação de scanner grátis + IA paga é o modelo que transformou o Cursor de zero para $200M ARR em 24 meses. No mercado africano de cibersegurança, com zero concorrência local, o potencial é ainda maior.

---

*HackScan Pro · Luanda, Angola · 2026*  
*"The best security platform you've never heard of — yet."*
