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
    "default": {
        "explanation": "Esta vulnerabilidade requer atenção imediata para prevenir possíveis explorações.",
        "risk": "O risco acumulado de falhas de segurança pode levar ao comprometimento da integridade e confidencialidade dos dados.",
        "remediation": "Revisar o código seguindo as diretrizes do OWASP e aplicar correções baseadas em princípios de 'Defense in Depth'.",
    }
}

# ── Model Configuration ─────────────────────────────────────────────────
ANTHROPIC_MODEL_ID = "claude-3-5-sonnet-20241022"
GEMINI_MODEL_ID = "gemini-2.0-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


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
        self.active_engine = None  # Track which engine is active

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

    def _call_anthropic(self, user_prompt: str, max_tokens: int = 1024) -> str | None:
        """
        Chama o Claude via Anthropic SDK.
        Retorna o texto da resposta ou None em caso de erro.
        """
        if not self.anthropic_client:
            return None
        try:
            response = self.anthropic_client.messages.create(
                model=ANTHROPIC_MODEL_ID,
                max_tokens=max_tokens,
                system=SYSTEM_PROMPT_PT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"❌ Erro na chamada ao Claude ({ANTHROPIC_MODEL_ID}): {e}")
            return None

    def _call_gemini(self, user_prompt: str, max_tokens: int = 1024) -> str | None:
        """
        Chama o Gemini via REST API (sem SDK pesado).
        Retorna o texto da resposta ou None em caso de erro.
        """
        if not self.gemini_api_key:
            return None
        try:
            url = f"{GEMINI_API_URL}/{GEMINI_MODEL_ID}:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{SYSTEM_PROMPT_PT}\n\n---\n\n{user_prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": max_tokens,
                    "temperature": 0.3,
                }
            }
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()

            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
            logger.warning(f"⚠️ Gemini retornou resposta vazia: {data}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro na chamada ao Gemini ({GEMINI_MODEL_ID}): {e}")
            return None
    def _call_llm(self, user_prompt: str, max_tokens: int = 1024) -> tuple[str | None, object]:
        """
        Wrapper centralizado: tenta Anthropic primeiro, depois Gemini.
        Retorna (texto_resposta, usage_object).
        """
        usage = SimpleNamespace(input_tokens=0, output_tokens=0)
        
        # Try primary engine first
        if self.anthropic_client:
            try:
                response = self.anthropic_client.messages.create(
                    model=ANTHROPIC_MODEL_ID,
                    max_tokens=max_tokens,
                    system=SYSTEM_PROMPT_PT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                res_text = response.content[0].text
                usage.input_tokens = getattr(response.usage, "input_tokens", 0)
                usage.output_tokens = getattr(response.usage, "output_tokens", 0)
                return res_text, usage
            except Exception as e:
                logger.error(f"❌ Erro na chamada ao Claude: {e}")
                logger.warning("⚠️ Anthropic falhou, tentando Gemini como fallback...")

        # Fallback to Gemini
        if self.gemini_api_key:
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
                        res_text = parts[0].get("text", "")
                        # Gemini usage metadata
                        meta = data.get("usageMetadata", {})
                        usage.input_tokens = meta.get("promptTokenCount", 0)
                        usage.output_tokens = meta.get("candidatesTokenCount", 0)
                        return res_text, usage
                logger.warning(f"⚠️ Gemini retornou resposta vazia: {data}")
            except Exception as e:
                logger.error(f"❌ Erro na chamada ao Gemini: {e}")

        return None, usage

    # ── 1. explain_finding ──────────────────────────────────────────────

    @ai_action(action="explain_finding", cache_ttl=3600)
    def explain_finding(self, finding_title: str, description: str, severity: str) -> tuple[str, object]:
        """Gera explicação detalhada de uma vulnerabilidade em PT-BR."""
        safe_title = self._redact_pii(finding_title)
        safe_desc = self._redact_pii(description)

        if not self.has_ai:
            return self._fallback_explanation(safe_title, severity), SimpleNamespace(input_tokens=0, output_tokens=0)

        prompt = (
            f"Explique detalhadamente a seguinte vulnerabilidade encontrada pelo HackerScan Pro.\n\n"
            f"Título: {safe_title}\n"
            f"Severidade: {severity}\n"
            f"Descrição Original: {safe_desc}\n\n"
            "Estruture a resposta em:\n"
            "1. O que é esta vulnerabilidade?\n"
            "2. Qual o risco real para o negócio?\n"
            "3. Como um atacante exploraria isso?"
        )

        result, usage = self._call_llm(prompt, max_tokens=1000)
        if result:
            return result, usage
        return self._fallback_explanation(safe_title, severity), usage

    # ── 2. generate_remediation_code ───────────────────────────────────

    @ai_action(action="remediation_code", cache_ttl=86400)
    def generate_remediation_code(self, finding_title: str, description: str) -> tuple[str, object]:
        """Gera guia de correção passo a passo com exemplos de código em PT-BR."""
        safe_title = self._redact_pii(finding_title)
        safe_desc = self._redact_pii(description)

        if not self.has_ai:
            return self._fallback_remediation(safe_title), SimpleNamespace(input_tokens=0, output_tokens=0)

        prompt = (
            f"Forneça um guia de correção passo a passo para a seguinte falha de segurança.\n\n"
            f"Título: {safe_title}\n"
            f"Descrição: {safe_desc}\n\n"
            "Inclua:\n"
            "- Passos imediatos de correção.\n"
            "- Exemplos de código seguro (antes/depois).\n"
            "- Como verificar se a correção funcionou.\n"
            "- Melhores práticas para prevenção futura."
        )

        result, usage = self._call_llm(prompt, max_tokens=1200)
        if result:
            return result, usage
        return self._fallback_remediation(safe_title), usage

    # ── 3. predict_attack_chains ────────────────────────────────────────

    @ai_action(action="attack_chains", cache_ttl=3600)
    def predict_attack_chains(self, findings: list[dict]) -> tuple[str, object]:
        """Recebe uma lista de findings e prevê cadeias de ataque combinadas."""
        if not findings:
            return "Nenhuma vulnerabilidade fornecida.", SimpleNamespace(input_tokens=0, output_tokens=0)

        if not self.has_ai:
            return self._fallback_attack_chain(findings), SimpleNamespace(input_tokens=0, output_tokens=0)

        findings_text = "\n".join(
            f"- [{f.get('severity', 'N/A')}] {f.get('title', 'Sem título')}: {f.get('description', '')[:200]}"
            for f in findings
        )

        prompt = (
            "Com base nas vulnerabilidades listadas abaixo, preveja possíveis cadeias de ataque...\n"
            f"Vulnerabilidades encontradas:\n{findings_text}\n\n"
            "Para cada cadeia de ataque identificada, descreva:\n"
            "1. Sequência de exploração (passo a passo).\n"
            "2. Impacto potencial no negócio.\n"
            "3. Probabilidade estimada (Alta / Média / Baixa).\n"
            "4. Mitigação prioritária recomendada."
        )

        result, usage = self._call_llm(prompt, max_tokens=1500)
        if result:
            return result, usage
        return self._fallback_attack_chain(findings), usage

    # ── Fallbacks (sempre em PT, nunca raise) ───────────────────────────

    def _get_kb_entry(self, title: str) -> dict:
        """Tenta encontrar uma entrada correspondente na base de conhecimento estática."""
        t = title.lower()
        if "sql" in t: return VULNERABILITY_KB["sql_injection"]
        if "xss" in t or "scripting" in t: return VULNERABILITY_KB["xss"]
        if "auth" in t or "login" in t or "password" in t: return VULNERABILITY_KB["broken_auth"]
        if "idor" in t or "direct object" in t: return VULNERABILITY_KB["idor"]
        if "info" in t or "exposure" in t or "leak" in t: return VULNERABILITY_KB["info_exposure"]
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
