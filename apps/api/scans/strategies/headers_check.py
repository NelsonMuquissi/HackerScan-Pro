"""
HTTP Security Headers Check strategy — v2.
Fetches the root URL and inspects response headers for security best practices.

Checks:
  - Strict-Transport-Security (HSTS)       → missing or weak max-age = medium
  - Content-Security-Policy (CSP)          → missing OR insecure directives = medium/high
  - X-Frame-Options                        → missing = medium
  - X-Content-Type-Options                 → missing = low
  - Referrer-Policy                        → missing = low
  - Permissions-Policy                     → missing = info
  - CORS wildcard                          → high
  - Insecure cookies (Secure/HttpOnly/SameSite) → medium
  - Server / X-Powered-By leakage         → low
  - Cache-Control on sensitive resources   → low
"""
import logging
import re
from typing import List, AsyncGenerator
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

TIMEOUT = 15

# Headers that must be PRESENT
HEADER_CHECKS = [
    {
        "header":      "Strict-Transport-Security",
        "severity":    Severity.MEDIUM,
        "title":       "Missing Strict-Transport-Security (HSTS) header",
        "description": "HSTS instructs browsers to only communicate over HTTPS. Without it, users may be subject to SSL-stripping attacks.",
        "remediation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
        "cvss_score":  5.4,
    },
    {
        "header":      "Content-Security-Policy",
        "severity":    Severity.MEDIUM,
        "title":       "Missing Content-Security-Policy (CSP) header",
        "description": "CSP restricts which resources browsers can load. Without it, XSS attacks are easier to exploit.",
        "remediation": "Define a strict CSP policy. Start with: Content-Security-Policy: default-src 'self'",
        "cvss_score":  5.0,
    },
    {
        "header":      "X-Frame-Options",
        "severity":    Severity.MEDIUM,
        "title":       "Missing X-Frame-Options header",
        "description": "Without X-Frame-Options, the site may be vulnerable to clickjacking attacks.",
        "remediation": "Add: X-Frame-Options: DENY  (or SAMEORIGIN if framing by same domain is required)",
        "cvss_score":  4.3,
    },
    {
        "header":      "X-Content-Type-Options",
        "severity":    Severity.LOW,
        "title":       "Missing X-Content-Type-Options header",
        "description": "Without this header, browsers may MIME-sniff responses, enabling content injection attacks.",
        "remediation": "Add: X-Content-Type-Options: nosniff",
        "cvss_score":  2.6,
    },
    {
        "header":      "Referrer-Policy",
        "severity":    Severity.LOW,
        "title":       "Missing Referrer-Policy header",
        "description": "Without a Referrer-Policy, sensitive URLs in the Referer header may be leaked to third parties.",
        "remediation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
        "cvss_score":  2.1,
    },
    {
        "header":      "Permissions-Policy",
        "severity":    Severity.INFO,
        "title":       "Missing Permissions-Policy header",
        "description": "Permissions-Policy controls which browser features the page can use. Missing it allows unrestricted feature access.",
        "remediation": "Add: Permissions-Policy: geolocation=(), microphone=(), camera=()",
        "cvss_score":  1.0,
    },
]

# CSP directives that make the policy insecure even when the header is present
INSECURE_CSP_PATTERNS = [
    (r"'unsafe-inline'",  Severity.HIGH,   "CSP allows 'unsafe-inline' — XSS protection is effectively bypassed"),
    (r"'unsafe-eval'",    Severity.HIGH,   "CSP allows 'unsafe-eval' — execution of arbitrary JS strings is permitted"),
    (r"(?:^|;)\s*default-src\s+\*",  Severity.HIGH, "CSP default-src wildcard (*) allows resources from any origin"),
    (r"(?:^|;)\s*script-src\s+[^;]*\*",  Severity.HIGH, "CSP script-src contains wildcard — script injection possible"),
    (r"http:",            Severity.MEDIUM, "CSP policy allows loading resources over plain HTTP"),
    (r"data:",            Severity.MEDIUM, "CSP allows 'data:' URIs — can be used for XSS in some browsers"),
]


@register
class HeadersCheckStrategy(BaseScanStrategy):
    """
    HTTP Security Headers Check strategy v2.
    Audits response headers for missing controls, insecure configurations,
    and cookie security issues using standardised evidence.
    """
    slug = "headers_check"
    name = "HTTP Security Headers Audit"
    description = "Inspects HTTP response headers for missing security controls and sensitive information leaks."

    async def run_async(self, target, scan=None):
        """Native async implementation — yields FindingData as identified."""
        from scans.utils import make_evidence_request_async
        host = target.host.strip()
        url  = host if host.startswith("http") else f"https://{host}"

        self.log(scan, f"Auditing security headers on {url}...")
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=TIMEOUT)
            if not resp:
                if url.startswith("https"):
                    url = url.replace("https://", "http://")
                    resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=TIMEOUT)

            if not resp:
                self.log(scan, "Could not connect to target. Aborting headers check.")
                return

            headers = {k.lower(): v for k, v in resp.headers.items()}

            # ── 1. Standard presence checks ──────────────────────────────────
            for check in HEADER_CHECKS:
                h_key = check["header"].lower()
                if h_key not in headers:
                    yield FindingData(
                        title=check["title"],
                        description=(
                            f"{check['description']}\n\n"
                            f"**REAL DATA PROOF**: The `{check['header']}` header was not present "
                            f"in the HTTP response from `{url}`."
                        ),
                        severity=check["severity"],
                        evidence={"url": url, "missing_header": check["header"]},
                        remediation=check["remediation"],
                        cvss_score=check.get("cvss_score"),
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                    )

            # ── 2. HSTS quality check (header present but weak) ──────────────
            hsts_val = headers.get("strict-transport-security", "")
            if hsts_val:
                max_age_match = re.search(r"max-age\s*=\s*(\d+)", hsts_val)
                if max_age_match:
                    max_age = int(max_age_match.group(1))
                    if max_age < 31536000:  # less than 1 year
                        yield FindingData(
                            title="HSTS max-age is too short",
                            description=(
                                f"The HSTS header is present but `max-age={max_age}` is below the recommended "
                                f"minimum of 31536000 (1 year). Short max-age values reduce the effectiveness "
                                f"of HSTS protection.\n\n"
                                f"**REAL DATA PROOF**: `Strict-Transport-Security: {hsts_val}`"
                            ),
                            severity=Severity.LOW,
                            evidence={"url": url, "hsts_value": hsts_val, "max_age": max_age},
                            remediation="Set max-age to at least 31536000 and add 'includeSubDomains; preload'.",
                            cvss_score=3.1,
                            plugin_slug=self.slug,
                            request=req_dump,
                            response=res_dump,
                            poc=poc,
                        )
                if "includesubdomains" not in hsts_val.lower():
                    yield FindingData(
                        title="HSTS missing 'includeSubDomains' directive",
                        description=(
                            f"The HSTS header does not include `includeSubDomains`, leaving subdomains "
                            f"unprotected against SSL-stripping.\n\n"
                            f"**REAL DATA PROOF**: `Strict-Transport-Security: {hsts_val}`"
                        ),
                        severity=Severity.INFO,
                        evidence={"url": url, "hsts_value": hsts_val},
                        remediation="Update to: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload",
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                    )

            # ── 3. CSP quality check (header present but insecure) ───────────
            csp_val = headers.get("content-security-policy", "")
            if csp_val:
                for pattern, sev, label in INSECURE_CSP_PATTERNS:
                    if re.search(pattern, csp_val, re.IGNORECASE):
                        yield FindingData(
                            title=f"Insecure CSP Directive: {label}",
                            description=(
                                f"The Content-Security-Policy header is present but contains an insecure directive.\n\n"
                                f"**Issue**: {label}\n\n"
                                f"**REAL DATA PROOF** (Full CSP):\n```\n{csp_val}\n```"
                            ),
                            severity=sev,
                            evidence={"url": url, "csp_value": csp_val, "pattern": pattern},
                            remediation=(
                                "Remove 'unsafe-inline' and 'unsafe-eval'. Use nonces or hashes instead. "
                                "Avoid wildcard sources. Never allow http: or data: in script-src."
                            ),
                            cvss_score=6.5 if sev == Severity.HIGH else 4.0,
                            plugin_slug=self.slug,
                            request=req_dump,
                            response=res_dump,
                            poc=poc,
                        )

            # ── 4. CORS check ─────────────────────────────────────────────────
            cors_origin = headers.get("access-control-allow-origin", "")
            if cors_origin == "*":
                yield FindingData(
                    title="Permissive CORS Policy (Wildcard Origin)",
                    description=(
                        "The server responds with `Access-Control-Allow-Origin: *`, allowing any origin "
                        "to make cross-origin requests. Combined with sensitive endpoints, this can lead to "
                        "cross-site data theft.\n\n"
                        "**REAL DATA PROOF** (Extracted Header): `Access-Control-Allow-Origin: *`"
                    ),
                    severity=Severity.HIGH,
                    evidence={"header": "Access-Control-Allow-Origin", "value": "*", "url": url},
                    remediation="Replace '*' with specific trusted domains in Access-Control-Allow-Origin.",
                    cvss_score=7.1,
                    plugin_slug=self.slug,
                    request=req_dump,
                    response=res_dump,
                    poc=f"curl -I -H 'Origin: https://evil.com' {url}",
                )

            # ── 5. Cookie security checks ─────────────────────────────────────
            # Use the raw headers list to handle multiple Set-Cookie headers correctly
            # (httpx stores multiple Set-Cookie as a list in resp.headers.get_list)
            raw_set_cookies = []
            for raw_header_name, raw_header_val in resp.headers.items():
                if raw_header_name.lower() == "set-cookie":
                    raw_set_cookies.append(raw_header_val)

            for cookie_header in raw_set_cookies:
                cookie_name = cookie_header.split("=")[0].strip()
                cookie_lower = cookie_header.lower()
                issues = []

                if "secure" not in cookie_lower and url.startswith("https"):
                    issues.append("Missing `Secure` flag — cookie may be transmitted over HTTP")
                if "httponly" not in cookie_lower:
                    issues.append("Missing `HttpOnly` flag — cookie accessible via JavaScript (XSS risk)")
                if "samesite" not in cookie_lower:
                    issues.append("Missing `SameSite` flag — cookie sent on cross-site requests (CSRF risk)")
                elif "samesite=none" in cookie_lower and "secure" not in cookie_lower:
                    issues.append("`SameSite=None` requires the `Secure` flag — currently missing")

                if issues:
                    yield FindingData(
                        title=f"Insecure Cookie Configuration: {cookie_name}",
                        description=(
                            f"The cookie `{cookie_name}` has security configuration issues:\n"
                            + "\n".join(f"- {i}" for i in issues)
                            + f"\n\n**REAL DATA PROOF** (Raw Set-Cookie header):\n`{cookie_header}`"
                        ),
                        severity=Severity.MEDIUM,
                        evidence={"cookie_name": cookie_name, "cookie_header": cookie_header, "issues": issues},
                        remediation=(
                            f"Update the cookie: Set-Cookie: {cookie_name}=<value>; Secure; HttpOnly; SameSite=Strict"
                        ),
                        cvss_score=5.0,
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                    )

            # ── 6. Information leakage headers ───────────────────────────────
            leaky_headers = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"]
            for h in leaky_headers:
                if h in headers:
                    yield FindingData(
                        title=f"Server Information Disclosure via '{h}' header",
                        description=(
                            f"The server reveals technology information via the `{h}` header. "
                            f"This helps attackers fingerprint the stack and search for known CVEs.\n\n"
                            f"**REAL DATA PROOF** (Extracted Header): `{h}: {headers[h]}`"
                        ),
                        severity=Severity.LOW,
                        evidence={"header": h, "value": headers[h], "url": url},
                        remediation=f"Remove or obfuscate the `{h}` header from all production responses.",
                        cvss_score=2.6,
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                    )

            # ── 7. Cache-Control check ────────────────────────────────────────
            cache_control = headers.get("cache-control", "")
            if not cache_control or ("no-store" not in cache_control and "private" not in cache_control):
                # Only flag if page seems sensitive (auth-related)
                if any(kw in url.lower() for kw in ["/login", "/admin", "/account", "/profile", "/dashboard"]):
                    yield FindingData(
                        title="Sensitive Page Without Cache-Control: no-store",
                        description=(
                            f"The page at `{url}` appears to be sensitive but does not set `Cache-Control: no-store`. "
                            f"This may cause browsers or intermediary proxies to cache sensitive content.\n\n"
                            f"**REAL DATA PROOF**: `Cache-Control: {cache_control or '(missing)'}`"
                        ),
                        severity=Severity.LOW,
                        evidence={"url": url, "cache_control": cache_control},
                        remediation="Add `Cache-Control: no-store, no-cache, must-revalidate` to authenticated/sensitive pages.",
                        cvss_score=2.0,
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                    )

        except Exception as e:
            logger.error("Headers check error: %s", e)
            self.log(scan, f"Error during headers audit: {str(e)}")

    async def verify_async(self, finding) -> bool:
        """Native async verification."""
        from scans.utils import make_evidence_request_async
        evidence = finding.evidence if isinstance(finding.evidence, dict) else {}
        target_url = evidence.get("url")

        if not target_url:
            from asgiref.sync import sync_to_async
            scan   = await sync_to_async(lambda: finding.scan)()
            target = await sync_to_async(lambda: scan.target)()
            target_url = target.host
            if not target_url.startswith("http"):
                target_url = f"https://{target_url}"

        try:
            resp, req, res, poc = await make_evidence_request_async(target_url, timeout=TIMEOUT)
            if not resp:
                return False

            headers      = {k.lower(): v for k, v in resp.headers.items()}
            is_verified  = False

            if "missing_header" in evidence:
                is_verified = evidence["missing_header"].lower() not in headers

            elif "cookie_name" in evidence:
                raw_cookies = [v for k, v in resp.headers.items() if k.lower() == "set-cookie"]
                is_verified = any(evidence["cookie_name"] in c for c in raw_cookies)

            elif "header" in evidence:
                h_name      = evidence["header"].lower()
                is_verified = h_name in headers and headers[h_name] == evidence.get("value")

            elif "csp_value" in evidence:
                csp_val     = headers.get("content-security-policy", "")
                is_verified = bool(csp_val) and re.search(evidence.get("pattern", ""), csp_val, re.IGNORECASE)

            elif "hsts_value" in evidence:
                hsts_val    = headers.get("strict-transport-security", "")
                is_verified = bool(hsts_val)

            if is_verified:
                finding.request     = req
                finding.response    = res
                finding.is_verified = True
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True

        except Exception:
            pass
        return False
