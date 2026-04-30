import os
import re
import logging
import json
import httpx
from types import SimpleNamespace
from django.conf import settings
from django.core.cache import cache
from .decorators import ai_action

logger = logging.getLogger(__name__)

# ── System prompt em Português ──────────────────────────────────────────
SYSTEM_PROMPT_PT = (
    "Você é o motor de inteligência artificial do HackerScan Pro, uma plataforma "
    "profissional de auditoria de segurança cibernética. Todas as suas respostas "
    "devem ser em Português do Brasil, com linguagem técnica mas acessível. "
    "Nunca invente CVEs ou dados que não lhe foram fornecidos. Quando aplicável, "
    "inclua exemplos de código seguro e referências ao OWASP Top 10."
)

# ── Base de Conhecimento de Fallback (PT-BR) ───────────────────────────
VULNERABILITY_KB = {
    "sql_injection": {
        "explanation": "Injeção de SQL ocorre quando dados não confiáveis são inseridos em uma consulta SQL, permitindo que um atacante manipule a lógica do banco de dados.",
        "risk": "Acesso total ao banco de dados, bypass de autenticação, vazamento de dados sensíveis e destruição de informações.",
        "remediation": "Utilizar 'Prepared Statements' (consultas parametrizadas) e ORMs seguros. Nunca concatenar strings em consultas SQL.",
    },
    "xss": {
        "explanation": "Cross-Site Scripting (XSS) permite a execução de scripts maliciosos no navegador de outros usuários através da injeção de scripts em páginas web.",
        "risk": "Roubo de sessões (cookies), redirecionamentos maliciosos e captura de dados de formulários.",
        "remediation": "Validar e sanitizar todas as entradas. Utilizar escape de HTML na saída (Output Encoding) e implementar Content Security Policy (CSP).",
    },
    "broken_auth": {
        "explanation": "Falhas em mecanismos de autenticação e gerenciamento de sessão permitem que atacantes comprometam senhas ou tokens de sessão.",
        "risk": "Invasão de contas de usuários e administradores, comprometendo todo o sistema.",
        "remediation": "Implementar Multi-Factor Authentication (MFA), políticas de senha forte e utilizar gerenciamento de sessão seguro (SameSite, Secure, HttpOnly).",
    },
    "idor": {
        "explanation": "Insecure Direct Object Reference (IDOR) ocorre quando uma aplicação utiliza um identificador para acessar um objeto sem uma verificação de autorização adequada.",
        "risk": "Acesso não autorizado a dados de outros usuários, modificação ou exclusão de registros sensíveis.",
        "remediation": "Implementar verificações de autorização rigorosas a nível de objeto. Usar identificadores não previsíveis (UUIDs).",
    },
    "info_exposure": {
        "explanation": "A exposição de dados sensíveis ocorre quando informações como PII, segredos ou erros técnicos são revelados indevidamente.",
        "risk": "Violação de privacidade (LGPD), auxílio em ataques direcionados e perda de confiança do cliente.",
        "remediation": "Criptografar dados sensíveis em repouso e em trânsito. Desativar logs detalhados em produção e mascarar dados sensíveis.",
    },
    "csp": {
        "explanation": "A falta do cabeçalho Content-Security-Policy (CSP) deixa a aplicação vulnerável a ataques de injeção de conteúdo, como XSS e Clickjacking.",
        "risk": "Execução de scripts não autorizados, roubo de dados e manipulação da interface do usuário.",
        "remediation": "Implementar uma política CSP restritiva através do cabeçalho HTTP 'Content-Security-Policy'.",
    },
    "hsts": {
        "explanation": "O cabeçalho HTTP Strict Transport Security (HSTS) não está configurado, o que pode permitir ataques de downgrade de protocolo (HTTP em vez de HTTPS).",
        "risk": "Interceptação de tráfego em ataques Man-in-the-Middle (MitM) e roubo de cookies de sessão.",
        "remediation": "Adicionar o cabeçalho 'Strict-Transport-Security' com um tempo de 'max-age' longo e a diretiva 'includeSubDomains'.",
    },
    "clickjacking": {
        "explanation": "A ausência de proteção contra Clickjacking (como X-Frame-Options ou diretiva frame-ancestors do CSP) permite que o site seja carregado dentro de um iframe em sites maliciosos.",
        "risk": "Usuários podem ser induzidos a clicar em elementos invisíveis, realizando ações indesejadas em seu nome.",
        "remediation": "Configurar o cabeçalho 'X-Frame-Options: DENY' ou 'SAMEORIGIN', ou utilizar a diretiva 'frame-ancestors' no CSP.",
    },
    "tls_version": {
        "explanation": "O servidor suporta versões obsoletas e inseguras do protocolo TLS (como 1.0 ou 1.1).",
        "risk": "Criptografia fraca que pode ser quebrada por atacantes, expondo dados em trânsito.",
        "remediation": "Desativar suporte para TLS 1.0 e 1.1. Manter apenas TLS 1.2 e 1.3 com cifras fortes.",
    },
    "open_port": {
        "explanation": "Uma porta de rede foi encontrada aberta sem uma justificativa clara de serviço público.",
        "risk": "Aumento da superfície de ataque. Portas desnecessárias podem expor serviços vulneráveis ou painéis administrativos.",
        "remediation": "Fechar todas as portas que não são estritamente necessárias. Utilizar VPN ou listas brancas de IP para serviços internos.",
    },
    "default": {
        "explanation": "Esta vulnerabilidade requer atenção imediata para prevenir possíveis explorações.",
        "risk": "O risco acumulado de falhas de segurança pode levar ao comprometimento da integridade e confidencialidade dos dados.",
        "remediation": "Revisar o código seguindo as diretrizes do OWASP e aplicar correções baseadas em princípios de 'Defense in Depth'.",
    }
}

# ── Model Configuration ─────────────────────────────────────────────────
ANTHROPIC_MODEL_ID = "claude-sonnet-4-20250514"
GEMINI_MODEL_ID = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GITHUB_MODELS_URL = "https://models.inference.ai.azure.com/chat/completions"
GITHUB_MODEL_ID = "gpt-4o" # Motor redundante via GitHub Models


class AIService:
    """
    Dual-engine AI service for HackerScan Pro security analysis.

    Primary engine: Anthropic Claude (claude-sonnet-4-20250514)
    Fallback engine: Google Gemini (gemini-2.0-flash)

    Caches results per method, and never raises exceptions
    — always retorna uma string de fallback em Português.
    """

    def __init__(self):
        self.anthropic_client = None
        self.gemini_api_key = None
        self.github_token = None
        self.active_engine = None  

        # ── 1. Try Anthropic (Primary) ──────────────────────────────────
        anthropic_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.getenv('ANTHROPIC_API_KEY', '')
        if anthropic_key and not anthropic_key.startswith('sk-ant-manual'):
            try:
                from anthropic import Anthropic
                self.anthropic_client = Anthropic(api_key=anthropic_key)
                self.active_engine = "anthropic"
                logger.info("✅ Motor IA primário (Anthropic Claude) inicializado com sucesso.")
            except Exception as e:
                self.anthropic_client = None
                logger.error(f"❌ Falha ao inicializar cliente Anthropic: {e}")

        # ── 2. Try Gemini (Fallback) ────────────────────────────────────
        gemini_key = getattr(settings, 'GEMINI_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')
        if gemini_key:
            self.gemini_api_key = gemini_key
            if not self.active_engine:
                self.active_engine = "gemini"
                logger.info("✅ Motor IA fallback (Google Gemini) ativado como primário.")
            else:
                logger.info("✅ Motor IA fallback (Google Gemini) disponível como secundário.")

        # ── 3. Try GitHub Models (Redundant) ───────────────────────────
        github_token = getattr(settings, 'GITHUB_TOKEN', '') or os.getenv('GITHUB_TOKEN', '')
        if github_token:
            self.github_token = github_token
            if not self.active_engine:
                self.active_engine = "github"
                logger.info("✅ Motor IA redundante (GitHub Models) ativado como primário.")
            else:
                logger.info("✅ Motor IA redundante (GitHub Models) disponível.")

        if not self.active_engine:
            logger.warning("⚠️ Nenhuma chave de IA configurada. Serviço em modo fallback estático.")

        # PII / Token Redaction Regex
        self.redact_patterns = [
            (re.compile(r'(?i)(api[_-]?key|secret|password|token|auth|credential|pwd)["\s:=]+[a-z0-9_\-\.]{10,}', re.IGNORECASE), "[REDACTED_SENSITIVE]"),
            (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), "[REDACTED_IP]"),
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), "[REDACTED_EMAIL]"),
        ]

    # ── Engine Status ──────────────────────────────────────────────────

    @property
    def has_ai(self) -> bool:
        """Retorna True se algum motor de IA está disponível."""
        return self.active_engine is not None

    def get_engine_status(self) -> dict:
        """Retorna o status de cada motor de IA."""
        return {
            "anthropic": "active" if self.anthropic_client else "unavailable",
            "gemini": "active" if self.gemini_api_key else "unavailable",
            "github": "active" if self.github_token else "unavailable",
            "primary_engine": self.active_engine or "fallback_static",
        }

    # ── Helpers privados ────────────────────────────────────────────────

    def _redact_pii(self, text: str) -> str:
        """Remove dados sensíveis antes de enviar ao LLM."""
        if not text:
            return ""
        for pattern, replacement in self.redact_patterns:
            text = pattern.sub(replacement, text)
        return text

    def _call_anthropic(self, user_prompt: str, max_tokens: int = 1024) -> tuple[str | None, object]:
        """Chama o Claude via Anthropic SDK."""
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        if not self.anthropic_client:
            return None, usage
        try:
            response = self.anthropic_client.messages.create(
                model=ANTHROPIC_MODEL_ID,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT_PT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            usage.input_tokens = getattr(response.usage, "input_tokens", 0)
            usage.output_tokens = getattr(response.usage, "output_tokens", 0)
            return response.content[0].text, usage
        except Exception as e:
            logger.error(f"❌ Erro na chamada ao Claude ({ANTHROPIC_MODEL_ID}): {e}")
            raise e # Raise to be handled by retry logic in _call_llm

    def _call_gemini(self, user_prompt: str, max_tokens: int = 1024) -> tuple[str | None, object]:
        """Chama o Gemini via REST API."""
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        if not self.gemini_api_key:
            return None, usage
        try:
            url = f"{GEMINI_API_URL}/{GEMINI_MODEL_ID}:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT_PT}\n\n---\n\n{user_prompt}"}]}],
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3}
            }
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    meta = data.get("usageMetadata", {})
                    usage.input_tokens = meta.get("promptTokenCount", 0)
                    usage.output_tokens = meta.get("candidatesTokenCount", 0)
                    return parts[0].get("text", ""), usage
            return None, usage
        except Exception as e:
            logger.error(f"❌ Erro na chamada ao Gemini ({GEMINI_MODEL_ID}): {e}")
            raise e

    def _call_github_models(self, user_prompt: str, max_tokens: int = 1024) -> tuple[str | None, object]:
        """Chama o GitHub Models (Azure AI Inference API)."""
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        if not self.github_token:
            return None, usage
        try:
            headers = {
                "Authorization": f"Bearer {self.github_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_PT},
                    {"role": "user", "content": user_prompt}
                ],
                "model": GITHUB_MODEL_ID,
                "max_tokens": max_tokens,
                "temperature": 0.3
            }
            with httpx.Client(timeout=60.0) as client:
                response = client.post(GITHUB_MODELS_URL, headers=headers, json=payload)
                response.raise_for_status()

            data = response.json()
            choices = data.get("choices", [])
            if choices:
                res_text = choices[0].get("message", {}).get("content", "")
                meta = data.get("usage", {})
                usage.input_tokens = meta.get("prompt_tokens", 0)
                usage.output_tokens = meta.get("completion_tokens", 0)
                return res_text, usage
            return None, usage
        except Exception as e:
            logger.error(f"❌ Erro na chamada ao GitHub Models ({GITHUB_MODEL_ID}): {e}")
            raise e
    def _call_llm(self, user_prompt: str, max_tokens: int = 1024) -> tuple[str | None, object]:
        """
        Wrapper centralizado com Fallback Multi-Modelo e Retry Automático.
        """
        import time
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        
        # Engines em ordem de prioridade (respeitando engine ativa se forçada)
        all_engines = [
            ("anthropic", self._call_anthropic),
            ("gemini", self._call_gemini),
            ("github", self._call_github_models),
        ]
        
        # Se houver uma engine ativa, movemos para o topo da lista
        engines = []
        if self.active_engine:
            active = next((e for e in all_engines if e[0] == self.active_engine), None)
            if active:
                engines.append(active)
        
        for e in all_engines:
            if e not in engines:
                engines.append(e)

        for engine_name, engine_func in engines:
            # Tenta até 3 vezes com backoff exponencial se houver erro de Rate Limit (429)
            for attempt in range(3):
                try:
                    result, engine_usage = engine_func(user_prompt, max_tokens)
                    if result:
                        usage.input_tokens = getattr(engine_usage, "input_tokens", 0)
                        usage.output_tokens = getattr(engine_usage, "output_tokens", 0)
                        return result, usage
                except Exception as e:
                    # Se for 429 (Rate Limit) ou 503 (Overloaded), espera e tenta novamente
                    error_msg = str(e)
                    if "429" in error_msg or "503" in error_msg or "overloaded" in error_msg.lower():
                        wait_time = (2 ** attempt) + 1
                        logger.warning(f"⚠️ {engine_name} congestionado. Aguardando {wait_time}s (Tentativa {attempt+1}/3)...")
                        time.sleep(wait_time)
                        continue
                    
                    logger.error(f"❌ Motor {engine_name} falhou: {error_msg}")
                    break # Pula para o próximo motor

        return None, usage

    # ── 1. explain_finding ──────────────────────────────────────────────

    @ai_action(action="explain_finding", cache_ttl=3600)
    def explain_finding(self, finding_title: str, description: str, severity: str, evidence: dict = None, **kwargs) -> tuple[str, object]:
        """Gera explicação detalhada de uma vulnerabilidade em PT-BR."""
        safe_title = self._redact_pii(finding_title)
        safe_desc = self._redact_pii(description)
        
        # Serialize evidence for the prompt
        evidence_str = ""
        if evidence:
            try:
                evidence_str = json.dumps(evidence, indent=2)
                evidence_str = self._redact_pii(evidence_str)
            except Exception:
                evidence_str = str(evidence)

        if not self.has_ai:
            return self._fallback_explanation(safe_title, severity), SimpleNamespace(input_tokens=0, output_tokens=0)

        prompt = (
            f"Como um Especialista Sênior em Segurança Cibernética, forneça uma análise técnica profunda "
            f"sobre a seguinte vulnerabilidade detectada pelo HackerScan Pro.\n\n"
            f"Título: {safe_title}\n"
            f"Severidade: {severity}\n"
            f"Descrição Técnica: {safe_desc}\n"
            f"Evidência Técnica (RAW DATA): {evidence_str}\n\n"
            "Sua resposta deve ser exaustiva e estruturada da seguinte forma:\n"
            "1. **Análise de Causa Raiz**: Explique tecnicamente por que esta falha ocorre a nível de código ou configuração, analisando os dados fornecidos na evidência.\n"
            "2. **Vetores de Ataque**: Descreva múltiplos cenários de como um atacante persistente (APT) ou oportunista poderia explorar esta falha específica.\n"
            "3. **Impacto Estratégico**: Detalhe o impacto não apenas técnico, mas também jurídico (ex: LGPD), financeiro e de reputação.\n"
            "4. **Relação com OWASP/MITRE**: Cite as categorias específicas do OWASP Top 10 ou técnicas do MITRE ATT&CK relacionadas."
        )

        result, usage = self._call_llm(prompt, max_tokens=1000)
        if result:
            return result, usage
        return self._fallback_explanation(safe_title, severity), usage

    # ── 2. generate_remediation_code ───────────────────────────────────

    @ai_action(action="remediation_code", cache_ttl=86400)
    def generate_remediation_code(self, finding_title: str, description: str, evidence: dict = None, **kwargs) -> tuple[str, object]:
        """Gera guia de correção passo a passo com exemplos de código em PT-BR."""
        safe_title = self._redact_pii(finding_title)
        safe_desc = self._redact_pii(description)
        
        evidence_str = ""
        if evidence:
            try:
                evidence_str = json.dumps(evidence, indent=2)
                evidence_str = self._redact_pii(evidence_str)
            except Exception:
                evidence_str = str(evidence)

        if not self.has_ai:
            return self._fallback_remediation(safe_title), SimpleNamespace(input_tokens=0, output_tokens=0)

        prompt = (
            f"Gere um Plano de Remediação detalhado e acionável para a seguinte falha de segurança.\n\n"
            f"Título: {safe_title}\n"
            f"Contexto: {safe_desc}\n"
            f"Evidência Técnica: {evidence_str}\n\n"
            "O plano deve incluir:\n"
            "1. **Ação Imediata (Quick Fix)**: Como mitigar o risco nas próximas 2 horas, considerando os detalhes técnicos da evidência.\n"
            "2. **Correção Definitiva**: Instruções passo a passo para resolver a causa raiz.\n"
            "3. **Exemplos de Código Seguro**: Forneça blocos de código 'Vulnerável' vs 'Protegido' (Clean Code) aplicáveis ao contexto.\n"
            "4. **Verificação de Eficácia**: Comandos ou testes específicos para validar se a correção foi bem-sucedida.\n"
            "5. **Controles Compensatórios**: Sugestões de WAF rules, monitoramento ou hardening adicional."
        )

        result, usage = self._call_llm(prompt, max_tokens=1200)
        if result:
            return result, usage
        return self._fallback_remediation(safe_title), usage

    # ── 3. predict_attack_chains ────────────────────────────────────────

    @ai_action(action="attack_chains", cache_ttl=3600)
    def predict_attack_chains(self, findings: list[dict], **kwargs) -> tuple[str, object]:
        """Recebe uma lista de findings e prevê cadeias de ataque combinadas."""
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        
        if not findings:
            # 🚀 NEW: Even with no findings, we can provide a Posture Analysis
            if not self.has_ai:
                return "Análise de Postura: Nenhuma vulnerabilidade crítica detectada na superfície exposta.", usage
            
            prompt = (
                "O scan não detectou vulnerabilidades ativas (findings). "
                "Como um Especialista em Defesa Cibernética, forneça uma 'Análise de Postura Preventiva'.\n\n"
                "Sua análise deve:\n"
                "1. **Resumo de Higiene Cibernética**: Explique que a ausência de findings é um sinal positivo de configuração inicial.\n"
                "2. **Monitoramento Contínuo**: Por que o monitoramento constante é necessário mesmo sem falhas imediatas.\n"
                "3. **Vetores de Shadow IT**: Mencione o risco de serviços ocultos que podem surgir.\n"
                "4. **Recomendação Proativa**: Sugira a implementação de Zero Trust ou Hardening adicional."
            )
            result, usage = self._call_llm(prompt, max_tokens=800)
            return result or "Postura de segurança sólida. Continue monitorando.", usage

        if not self.has_ai:
            return self._fallback_attack_chain(findings), usage

        findings_text = "\n".join(
            f"- [{f.get('severity', 'N/A')}] {f.get('title', 'Sem título')}: {f.get('description', '')[:200]}\n  Evidência: {json.dumps(f.get('evidence', {}))[:150]}"
            for f in findings
        )

        prompt = (
            "Como um Analista de Threat Intelligence (Red Team), realize uma correlação avançada entre as vulnerabilidades "
            "listadas abaixo para prever cadeias de ataque (Kill Chains) complexas.\n\n"
            f"Inventário de Vulnerabilidades:\n{findings_text}\n\n"
            "Sua análise deve conter:\n"
            "1. **Cadeias de Exploração Combinadas**: Explique como as falhas detectadas podem ser encadeadas (Attack Chaining). Use uma abordagem de 'Caminho Crítico'.\n"
            "2. **Ponto de Entrada Crítico**: Identifique o 'paciente zero' (vetor inicial) para o comprometimento total.\n"
            "3. **Movimentação Lateral & Escalação**: Preveja como um atacante se moveria dentro da rede ou escalaria privilégios.\n"
            "4. **Visualização de Risco (Grafo)**: Descreva o fluxo do ataque passo a passo (ex: Passo 1 -> Passo 2 -> Objetivo Final).\n"
            "5. **Estratégia de Interrupção**: Qual o ponto exato da cadeia que, se corrigido, interrompe todo o fluxo de ataque."
        )

        result, usage = self._call_llm(prompt, max_tokens=1500)
        if result:
            return result, usage
        return self._fallback_attack_chain(findings), usage

    # ── 4. suggest_scan_strategy ───────────────────────────────────────

    @ai_action(action="suggest_strategy", cache_ttl=3600)
    def suggest_scan_strategy(self, recon_findings: list[dict], available_strategies: list[str]) -> tuple[dict, object]:
        """
        Analyze recon findings and suggest which targeted strategies to run.
        Returns a JSON-formatted dict with 'recommended_strategies' and 'nuclei_tags'.
        """
        if not recon_findings:
            return {"recommended_strategies": [], "nuclei_tags": "cve,vuln"}, SimpleNamespace(input_tokens=0, output_tokens=0)

        findings_text = "\n".join(
            f"- {f.get('title', 'Finding')}: {f.get('description', '')} (Evidence: {json.dumps(f.get('evidence', {}))})"
            for f in recon_findings
        )

        prompt = (
            "Como um Especialista em Red Teaming, analise os resultados da fase de Reconhecimento abaixo "
            "e decida quais estratégias de ataque e auditoria devem ser priorizadas.\n\n"
            f"Resultados de Reconhecimento:\n{findings_text}\n\n"
            f"Estratégias Disponíveis:\n{', '.join(available_strategies)}\n\n"
            "Sua resposta deve ser EXCLUSIVAMENTE um objeto JSON válido no seguinte formato:\n"
            "{\n"
            "  \"recommended_strategies\": [\"slug1\", \"slug2\"],\n"
            "  \"nuclei_tags\": \"comma,separated,tags\",\n"
            "  \"reasoning\": \"Breve explicação técnica em Português\"\n"
            "}\n"
            "Priorize estratégias que façam sentido para os serviços encontrados (ex: sqlmap se houver DB, dir_fuzzing se houver Web)."
        )

        result, usage = self._call_llm(prompt, max_tokens=500)
        if result:
            try:
                # Basic JSON cleaning in case of markdown blocks
                json_str = result.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                return json.loads(json_str), usage
            except (json.JSONDecodeError, IndexError):
                logger.error("AI returned invalid JSON for suggest_scan_strategy")
        
        return {"recommended_strategies": available_strategies[:3], "nuclei_tags": "cve,vuln"}, usage

    # ── 5. analyze_false_positive ──────────────────────────────────────
    
    @ai_action(action="analyze_fp", cache_ttl=3600)
    def analyze_false_positive(self, finding_title: str, description: str, evidence: dict | str) -> tuple[dict, object]:
        """
        Analisa se uma descoberta (finding) é um falso positivo com base na evidência técnica.
        Retorna um dicionário com 'is_false_positive' (bool), 'confidence' (float) e 'reasoning'.
        """
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        
        safe_title = self._redact_pii(finding_title)
        safe_desc = self._redact_pii(description)
        
        evidence_str = ""
        if isinstance(evidence, dict):
            try:
                evidence_str = json.dumps(evidence, indent=2)
                evidence_str = self._redact_pii(evidence_str)
            except Exception:
                evidence_str = str(evidence)
        else:
            evidence_str = self._redact_pii(str(evidence))

        if not self.has_ai:
            return {"is_false_positive": False, "confidence": 0.0, "reasoning": "IA indisponível para validação."}, usage

        prompt = (
            "Como um Auditor de Segurança Sênior, analise a seguinte descoberta para determinar se ela é um Falso Positivo.\n\n"
            f"Título: {safe_title}\n"
            f"Descrição: {safe_desc}\n"
            f"Evidência Técnica (RAW DATA): {evidence_str}\n\n"
            "Sua tarefa é verificar se a evidência realmente confirma a vulnerabilidade ou se o scanner se enganou "
            "(ex: erro HTTP 404 interpretado como falha, cabeçalhos de simulação, respostas de honeypot).\n\n"
            "Sua resposta deve ser EXCLUSIVAMENTE um objeto JSON válido no seguinte formato:\n"
            "{\n"
            "  \"is_false_positive\": true/false,\n"
            "  \"confidence\": 0.0 a 1.0,\n"
            "  \"reasoning\": \"Explicação técnica concisa em Português\"\n"
            "}"
        )

        result, usage = self._call_llm(prompt, max_tokens=500)
        if result:
            try:
                json_str = result.strip()
                if "```json" in json_str:
                    json_str = json_str.split("```json")[1].split("```")[0].strip()
                elif "```" in json_str:
                    json_str = json_str.split("```")[1].split("```")[0].strip()
                
                return json.loads(json_str), usage
            except (json.JSONDecodeError, IndexError):
                logger.error("AI returned invalid JSON for analyze_false_positive")
        
        return {"is_false_positive": False, "confidence": 0.0, "reasoning": "Erro ao processar resposta da IA."}, usage

    # ── Fallbacks (sempre em PT, nunca raise) ───────────────────────────

    def _get_kb_entry(self, title: str) -> dict:
        """Tenta encontrar uma entrada correspondente na base de conhecimento estática."""
        t = title.lower()
        
        # 1. Specific Web Headers (Check these before "port" to avoid "Transport" match)
        if "content-security-policy" in t or "csp" in t: return VULNERABILITY_KB["csp"]
        if "strict-transport-security" in t or "hsts" in t: return VULNERABILITY_KB["hsts"]
        if "frame-options" in t or "clickjacking" in t or "x-frame" in t: return VULNERABILITY_KB["clickjacking"]
        
        # 2. Network / Ports (Use regex for word boundary)
        if re.search(r"\b(port|porta)\b", t): return VULNERABILITY_KB["open_port"]
        
        # 3. Injection
        if "sql" in t: return VULNERABILITY_KB["sql_injection"]
        if "xss" in t or "scripting" in t: return VULNERABILITY_KB["xss"]
        
        # 4. Auth / IDOR
        if "auth" in t or "login" in t or "password" in t: return VULNERABILITY_KB["broken_auth"]
        if "idor" in t or "direct object" in t: return VULNERABILITY_KB["idor"]
        
        # 5. Info / Encryption
        if "info" in t or "exposure" in t or "leak" in t: return VULNERABILITY_KB["info_exposure"]
        if "tls" in t or "ssl" in t or "cryptography" in t: return VULNERABILITY_KB["tls_version"]
        
        return VULNERABILITY_KB["default"]

    def _fallback_explanation(self, title: str, severity: str) -> str:
        kb = self._get_kb_entry(title)
        return (
            f"### [Análise de Segurança - Modo Fallback]\n\n"
            f"**O que é esta vulnerabilidade?**\n{kb['explanation']}\n\n"
            f"**Risco para o negócio:**\n{kb['risk']}\n\n"
            f"---\n*Nota: O serviço de IA avançado está em modo de segurança simplificado.*"
        )

    def _fallback_remediation(self, title: str) -> str:
        kb = self._get_kb_entry(title)
        return (
            f"### [Guia de Correção - Modo Fallback]\n\n"
            f"**Passos recomendados:**\n"
            f"1. {kb['remediation']}\n"
            f"2. Realizar testes de regressão após a aplicação do patch.\n"
            f"3. Validar a entrada de dados em todas as camadas da aplicação.\n\n"
            f"*Consulte o manual do HackerScan Pro para guias de código específicos por linguagem.*"
        )

    def _fallback_attack_chain(self, findings: list[dict]) -> str:
        titles = ", ".join(f.get("title", "?") for f in findings[:3])
        return (
            f"### [Cadeia de Ataque - Modo Fallback]\n\n"
            f"Foi identificada uma possível combinação crítica entre: **{titles}**.\n\n"
            f"**Sequência provável:** Um atacante pode utilizar as falhas de menor severidade para escalar "
            f"privilégios e eventualmente explorar as vulnerabilidades mais críticas listadas no relatório.\n\n"
            f"**Prioridade:** Corrigir primeiro as vulnerabilidades de severidade 'Critical' e 'High'."
        )


ai_service = AIService()
