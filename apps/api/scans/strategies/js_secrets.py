import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

# Enhanced regex patterns for secrets and sensitive data
SECRET_PATTERNS = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "Google API Key": r"AIza[0-9A-Za-z-_]{35}",
    "Slack Token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
    "GitHub Personal Access Token": r"ghp_[a-zA-Z0-9]{36}",
    "Stripe API Key": r"(?:r|s)k_(?:live|test)_[0-9a-zA-Z]{24}",
    "Mailgun API Key": r"key-[0-9a-zA-Z]{32}",
    "Firebase Config": r"apiKey: ['\"]([a-zA-Z0-9_-]{35,})['\"]",
    "Heroku API Key": r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
    "Mailchimp API Key": r"[0-9a-fA-F]{32}-us[0-9]{1,2}",
    "Twilio Account SID": r"AC[a-f0-9]{32}",
    "Twilio Auth Token": r"[a-f0-9]{32}",
    "Private Key": r"-----BEGIN (?:RSA|OPENSSH|DSA|EC) PRIVATE KEY-----",
    "Cloudflare API Token": r"[a-zA-Z0-9_-]{40}",
    "JSON Web Token (JWT)": r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}",
    "Generic Secret": r"(?i)(api_key|apikey|secret|password|token|auth|credentials)\s*[:=]\s*['\"]([a-zA-Z0-9_-]{16,})['\"]",
}

# Patterns for discovering hidden infrastructure
INFRA_PATTERNS = {
    "Subdomain Discovery": r"[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(?::[0-9]{1,5})?",
    "Internal Endpoint": r"(['\"])\/(api|v1|v2|v3|graphql|admin|dev|staging)\/([a-zA-Z0-9\-\_\/\.\?\&\%]+)\1",
}

@register
class JSSecretScanStrategy(BaseScanStrategy):
    """
    Scans JavaScript files for hardcoded secrets, API keys, and sensitive data.
    Also extracts subdomains and internal endpoints found in the JS code.
    """
    slug = "js_secrets"
    name = "JS Secret & Endpoint Scraper"
    description = "Analyzes JS files for secrets, hardcoded API endpoints, and potential subdomains."

    def run(self, target, scan=None) -> List[FindingData]:
        from scans.utils import make_evidence_request
        host = target.host
        findings = []

        if target.target_type == "url" and "://" in host:
            start_url = host
        else:
            start_url = f"https://{host}"
        
        self.log(scan, f"Starting JS analysis on {start_url}...")

        try:
            # 🎯 Initial request to find scripts
            resp, req_dump, res_dump, _ = make_evidence_request(start_url)

            if not resp or resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            script_tags = soup.find_all("script")
            
            js_urls = []
            for s in script_tags:
                if s.get("src"):
                    js_urls.append(urljoin(start_url, s["src"]))
                elif s.string:
                    # Analyze inline content directly
                    findings.extend(self._analyze_js_content(s.string, start_url, req_dump, res_dump))

            for js_url in set(js_urls):
                parsed_js = urlparse(js_url)
                skip_domains = ["google-analytics.com", "googletagmanager.com", "facebook.net", "stripe.com"]
                if any(d in parsed_js.netloc for d in skip_domains):
                    continue

                try:
                    js_res, js_req_dump, js_res_dump, _ = make_evidence_request(js_url)
                    if js_res and js_res.status_code == 200:
                        findings.extend(self._analyze_js_content(js_res.text, js_url, js_req_dump, js_res_dump))
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"JS Analysis error: {e}")

        return findings

    def _analyze_js_content(self, content: str, source_url: str, req_dump: str, res_dump: str) -> List[FindingData]:
        findings = []
        
        # 1. Secrets Extraction
        for name, pattern in SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                secret = match.group(0)
                severity = Severity.HIGH
                if name in ["Generic Secret", "Firebase Config"]: severity = Severity.MEDIUM
                if name in ["Private Key", "AWS Access Key", "Stripe API Key"]: severity = Severity.CRITICAL

                # Construct a more specific response dump for the finding
                context_start = max(0, match.start() - 100)
                context_end = min(len(content), match.end() + 100)
                snippet = content[context_start:context_end]
                
                findings.append(FindingData(
                    title=f"Hardcoded {name} Found",
                    description=f"A sensitive {name} was detected in a JavaScript file at {source_url}.",
                    severity=severity,
                    evidence={
                        "type": "secret",
                        "pattern_name": name,
                        "source": source_url,
                        "match": secret[:6] + "..." + secret[-4:] if len(secret) > 10 else "****",
                        "context": content[max(0, match.start()-60):min(len(content), match.end()+60)].strip(),
                        "raw_secret_internal": secret 
                    },
                    plugin_slug=self.slug,
                    remediation="Revoke the secret and move it to a secure server-side vault.",
                    request=req_dump,
                    response=res_dump + "\n\n--- JS SNIPPET ---\n\n" + snippet,
                    poc=f"curl -s '{source_url}' | grep -E '{pattern}'",
                    is_verified=True
                ))

        # 2. Infrastructure Discovery (Subdomains & Endpoints)
        target_domain = urlparse(source_url).netloc.split(':')[0]
        subdomain_matches = re.findall(INFRA_PATTERNS["Subdomain Discovery"], content)
        found_subs = {s[0] for s in subdomain_matches if target_domain in s[0] and s[0] != target_domain}
        
        if found_subs:
            findings.append(FindingData(
                title="Hidden Subdomains Discovered in JS",
                description=f"Analysis of JS code revealed subdomains related to {target_domain}.",
                severity=Severity.INFO,
                evidence={"subdomains": list(found_subs), "source": source_url},
                plugin_slug=self.slug,
                request=req_dump,
                response=res_dump[:1000]
            ))

        return findings

    def verify(self, finding) -> bool:
        """
        Verify the finding by re-requesting the JS file and checking for the secret.
        """
        from scans.utils import make_evidence_request
        
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
            
        source_url = evidence.get("source")
        raw_secret = evidence.get("raw_secret_internal")
        
        if not source_url:
            return False
            
        try:
            resp, req, res, poc = make_evidence_request(source_url)
            
            if resp and resp.status_code == 200:
                # Update finding with fresh dumps
                finding.request = req
                finding.response = res
                finding.poc = poc
                
                if raw_secret:
                    return raw_secret in resp.text
                return True
        except Exception as e:
            logger.error(f"Verification error for JSSecret: {e}")
            
        return False
