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
import urllib.request
import urllib.error

from .base import BaseScanStrategy, FindingData, register

TIMEOUT = 10  # seconds

HEADER_CHECKS = [
    {
        "header":      "Strict-Transport-Security",
        "severity":    "medium",
        "title":       "Missing Strict-Transport-Security (HSTS) header",
        "description": "HSTS instructs browsers to only communicate over HTTPS. "
                       "Without it, users may be subject to SSL-stripping attacks.",
        "remediation": "Add: Strict-Transport-Security: max-age=31536000; includeSubDomains",
        "cvss_score":  5.4,
    },
    {
        "header":      "Content-Security-Policy",
        "severity":    "medium",
        "title":       "Missing Content-Security-Policy (CSP) header",
        "description": "CSP restricts which resources browsers can load. "
                       "Without it, XSS attacks are easier to exploit.",
        "remediation": "Define a strict CSP policy appropriate for your application.",
        "cvss_score":  5.0,
    },
    {
        "header":      "X-Frame-Options",
        "severity":    "medium",
        "title":       "Missing X-Frame-Options header",
        "description": "Without X-Frame-Options, the site may be vulnerable to clickjacking.",
        "remediation": "Add: X-Frame-Options: DENY or SAMEORIGIN",
        "cvss_score":  4.3,
    },
    {
        "header":      "X-Content-Type-Options",
        "severity":    "low",
        "title":       "Missing X-Content-Type-Options header",
        "description": "Without this header, browsers may MIME-sniff responses, "
                       "enabling content injection attacks.",
        "remediation": "Add: X-Content-Type-Options: nosniff",
    },
    {
        "header":      "Referrer-Policy",
        "severity":    "low",
        "title":       "Missing Referrer-Policy header",
        "description": "Without a Referrer-Policy, sensitive URLs in the Referer header "
                       "may be leaked to third parties.",
        "remediation": "Add: Referrer-Policy: strict-origin-when-cross-origin",
    },
    {
        "header":      "Permissions-Policy",
        "severity":    "info",
        "title":       "Missing Permissions-Policy header",
        "description": "This header controls which browser features the page can use. "
                       "Its absence is not immediately dangerous but is a best practice.",
        "remediation": "Add a Permissions-Policy header to restrict unused browser capabilities.",
    },
]


@register
class HeadersCheckStrategy(BaseScanStrategy):
    name        = "HTTP Security Headers Check"
    slug        = "headers_check"
    description = "Fetches the target URL and audits HTTP response headers for security best practices."

    def run(self, target, scan) -> list[FindingData]:
        host     = target.host
        scheme   = scan.config.get("scheme", "https")
        url      = f"{scheme}://{host}"
        findings: list[FindingData] = []

        self.log(scan, f"Fetching HTTP headers from {url}...")
        try:
            # Try HEAD first for efficiency
            req = urllib.request.Request(url, headers={"User-Agent": "HackScanPro/1.0"}, method="HEAD")
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                headers = {k.lower(): v for k, v in resp.headers.items()}
                self.log(scan, f"Connection successful (HEAD). Received {len(headers)} headers.")
        except urllib.error.HTTPError as exc:
            if exc.code in (405, 501):  # Method Not Allowed or Not Implemented
                self.log(scan, f"HEAD request not allowed (HTTP {exc.code}), falling back to GET...")
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "HackScanPro/1.0"}, method="GET")
                    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                        headers = {k.lower(): v for k, v in resp.headers.items()}
                        self.log(scan, f"Connection successful (GET). Received {len(headers)} headers.")
                except urllib.error.URLError as exc2:
                    return self._handle_error(url, exc2, findings)
            else:
                return self._handle_error(url, exc, findings)
        except urllib.error.URLError as exc:
            return self._handle_error(url, exc, findings)

        self.log(scan, "Auditing security headers...")

        # Check each expected header
        for check in HEADER_CHECKS:
            header_key = check["header"].lower()
            if header_key not in headers:
                self.log(scan, f"MISSING: {check['header']} ({check['severity']})")
                findings.append(FindingData(
                    plugin_slug=self.slug,
                    severity=check["severity"],
                    title=check["title"],
                    description=check["description"],
                    remediation=check["remediation"],
                    cvss_score=check.get("cvss_score"),
                    evidence={"url": url, "missing_header": check["header"]},
                ))
            else:
                self.log(scan, f"PRESENT: {check['header']}")

        # Server header leakage
        if "server" in headers:
            self.log(scan, f"LEAK: Server header found: {headers['server']}")
            findings.append(FindingData(
                plugin_slug=self.slug,
                severity="low",
                title="Server version disclosure via Server header",
                description=f"The Server header reveals: {headers['server']}. "
                             "This information aids attackers in fingerprinting the stack.",
                remediation="Configure the server to return a generic or no Server header.",
                evidence={"url": url, "server_header": headers["server"]},
            ))

        if not findings:
            self.log(scan, "SUCCESS: No major security header issues found.")
            findings.append(FindingData(
                plugin_slug=self.slug,
                severity="info",
                title="All expected security headers present",
                description=f"No missing security headers detected on {url}.",
                evidence={"url": url},
            ))

        self.log(scan, "HTTP security headers check completed.")
        return findings
