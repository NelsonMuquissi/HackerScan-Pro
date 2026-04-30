"""
HTTP Security Headers Check strategy.
Fetches the root URL and inspects response headers for security best practices.

Checks:
  - Strict-Transport-Security (HSTS)       → missing = medium
  - Content-Security-Policy (CSP)          → missing = medium
  - X-Frame-Options                        → missing = medium
  - X-Content-Type-Options                 → missing = low
  - Referrer-Policy                        → missing = low
  - Permissions-Policy                     → missing = info
  - X-XSS-Protection (deprecated check)   → still present? → info
  - Server header leakage                  → present = low
"""
import logging
from typing import List
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity
from scans.utils import make_evidence_request

logger = logging.getLogger(__name__)

TIMEOUT = 15

HEADER_CHECKS = [
    {
        "header":      "Strict-Transport-Security",
        "severity":    Severity.MEDIUM,
        "title":       "Missing Strict-Transport-Security (HSTS) header",
        "description": "HSTS instructs browsers to only communicate over HTTPS. Without it, users may be subject to SSL-stripping attacks.",
        "remediation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains",
        "cvss_score":  5.4,
    },
    {
        "header":      "Content-Security-Policy",
        "severity":    Severity.MEDIUM,
        "title":       "Missing Content-Security-Policy (CSP) header",
        "description": "CSP restricts which resources browsers can load. Without it, XSS attacks are easier to exploit.",
        "remediation": "Define a strict CSP policy appropriate for your application.",
        "cvss_score":  5.0,
    },
    {
        "header":      "X-Frame-Options",
        "severity":    Severity.MEDIUM,
        "title":       "Missing X-Frame-Options header",
        "description": "Without X-Frame-Options, the site may be vulnerable to clickjacking.",
        "remediation": "Add: X-Frame-Options: DENY or SAMEORIGIN",
        "cvss_score":  4.3,
    },
    {
        "header":      "X-Content-Type-Options",
        "severity":    Severity.LOW,
        "title":       "Missing X-Content-Type-Options header",
        "description": "Without this header, browsers may MIME-sniff responses, enabling content injection attacks.",
        "remediation": "Add: X-Content-Type-Options: nosniff",
        "cvss_score": 2.6,
    },
    {
        "header":      "Referrer-Policy",
        "severity":    Severity.LOW,
        "title":       "Missing Referrer-Policy header",
        "description": "Without a Referrer-Policy, sensitive URLs in the Referer header may be leaked to third parties.",
        "remediation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
        "cvss_score": 2.1,
    }
]

@register
class HeadersCheckStrategy(BaseScanStrategy):
    """
    HTTP Security Headers Check strategy.
    Audits response headers for security best practices and misconfigurations using standardized evidence.
    """
    slug = "headers_check"
    name = "HTTP Security Headers Audit"
    description = "Inspects HTTP response headers for missing security controls and sensitive information leaks."

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        url = host if host.startswith("http") else f"https://{host}"
        findings = []

        self.log(scan, f"Auditing security headers on {url}...")
        try:
            resp, req_dump, res_dump, poc = make_evidence_request(url)
            if not resp:
                # If HTTPS fails, try HTTP
                if url.startswith("https"):
                    url = url.replace("https", "http")
                    resp, req_dump, res_dump, poc = make_evidence_request(url)
            
            if not resp:
                return findings

            headers = {k.lower(): v for k, v in resp.headers.items()}
            
            # 1. Standard Checks
            for check in HEADER_CHECKS:
                h_key = check["header"].lower()
                if h_key not in headers:
                    findings.append(FindingData(
                        title=check["title"],
                        description=check["description"],
                        severity=check["severity"],
                        evidence={"url": url, "missing_header": check["header"]},
                        remediation=check["remediation"],
                        cvss_score=check.get("cvss_score"),
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc
                    ))

            # 2. CORS Check
            cors_origin = headers.get("access-control-allow-origin")
            if cors_origin == "*":
                findings.append(FindingData(
                    title="Permissive CORS Policy (Wildcard)",
                    description="The server allows any origin to access its resources (*). This can lead to sensitive data theft via CSRF-like attacks.",
                    severity=Severity.HIGH,
                    evidence={"header": "Access-Control-Allow-Origin", "value": "*"},
                    remediation="Replace '*' with specific trusted domains.",
                    cvss_score=7.1,
                    plugin_slug=self.slug,
                    request=req_dump,
                    response=res_dump,
                    poc=f"curl -I -H 'Origin: https://evil.com' {url}"
                ))

            # 3. Cookie Checks
            set_cookies = resp.headers.get("Set-Cookie", "")
            if set_cookies:
                cookies = [c.strip() for c in set_cookies.split(",")]
                for cookie in cookies:
                    issues = []
                    if "secure" not in cookie.lower() and url.startswith("https"):
                        issues.append("Secure flag missing")
                    if "httponly" not in cookie.lower():
                        issues.append("HttpOnly flag missing")
                    
                    if issues:
                        findings.append(FindingData(
                            title=f"Insecure Cookie Configuration: {cookie.split('=')[0]}",
                            description=f"Cookie '{cookie.split('=')[0]}' is missing security flags: {', '.join(issues)}.",
                            severity=Severity.MEDIUM,
                            evidence={"cookie": cookie, "issues": issues},
                            remediation="Add 'Secure' and 'HttpOnly' flags to all sensitive cookies.",
                            cvss_score=5.0,
                            plugin_slug=self.slug,
                            request=req_dump,
                            response=res_dump,
                            poc=poc
                        ))

            # 4. Information Leakage
            leaky_headers = ["server", "x-powered-by", "x-aspnet-version", "x-generator"]
            for h in leaky_headers:
                if h in headers:
                    findings.append(FindingData(
                        title=f"Information Disclosure via '{h}' header",
                        description=f"The server reveals technical stack information: {headers[h]}.",
                        severity=Severity.LOW,
                        evidence={"header": h, "value": headers[h]},
                        remediation=f"Remove or obfuscate the '{h}' header from production responses.",
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc
                    ))

        except Exception as e:
            logger.error("Headers check error: %s", e)
            self.log(scan, f"Error: {str(e)}")

        return findings

    def verify(self, finding) -> bool:
        """
        Verify by re-fetching headers and updating evidence.
        """
        target_url = finding.evidence.get("url") if isinstance(finding.evidence, dict) else None
        if not target_url:
            target_url = finding.scan.target.host
            if not target_url.startswith("http"):
                target_url = f"http://{target_url}"

        try:
            resp, req, res, poc = make_evidence_request(target_url)
            if not resp:
                return False

            headers = {k.lower(): v for k, v in resp.headers.items()}
            evidence = finding.evidence
            is_verified = False

            if "missing_header" in evidence:
                is_verified = evidence["missing_header"].lower() not in headers
            
            elif "cookie" in evidence:
                set_cookie = resp.headers.get("Set-Cookie", "")
                is_verified = evidence["cookie"].split("=")[0] in set_cookie
                
            elif "header" in evidence:
                h_name = evidence["header"].lower()
                is_verified = h_name in headers and headers[h_name] == evidence.get("value")
            
            if is_verified:
                finding.request = req
                finding.response = res
                return True
                
        except Exception:
            pass
        return False

