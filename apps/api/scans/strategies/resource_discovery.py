import logging
import requests
import re
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

# Suspicious file patterns to look for in HTML
_SENSITIVE_PATTERNS = [
    ".env", ".git", ".svn", "backup", "config", "admin",
    "wp-login", "phpinfo", ".htaccess", "web.config", "database", "sql",
    "docker-compose", "yarn.lock", "package-lock.json", ".npmrc"
]

# "Famous" critical files to actively probe for (Industry Standard)
_CRITICAL_PROBE_FILES = [
    ".env",
    ".git/config",
    "robots.txt",
    "sitemap.xml",
    ".well-known/security.txt",
    "server-status",
    "phpinfo.php",
    "config.php.bak",
    ".aws/credentials",
    ".ssh/id_rsa"
]


@register
class ResourceDiscoveryStrategy(BaseScanStrategy):
    """
    Resource discovery engine using requests + BeautifulSoup.
    Identifies sensitive server headers, metadata, and linked resources.
    """
    slug = "resource_discovery"
    name = "Resource Discovery"

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        # target.host is the correct field on ScanTarget (target.address does not exist)
        host = target.host
        url = host if host.startswith("http") else f"http://{host}"

        try:
            response = requests.get(
                url, timeout=10, allow_redirects=True,
                headers={"User-Agent": "HackerScan-Pro/1.0 (Security Audit)"},
            )
            # 3. Links to sensitive resources in the HTML
            all_links = []
            try:
                from bs4 import BeautifulSoup # noqa: PLC0415
                soup = BeautifulSoup(response.text, "html.parser")
                all_links = [
                    a.get("href", "") for a in soup.find_all("a", href=True)
                ] + [
                    link.get("href", "") for link in soup.find_all("link", href=True)
                ] + [
                    script.get("src", "") for script in soup.find_all("script", src=True)
                ]
            except ImportError:
                # RegEx fallback for environments without BeautifulSoup
                logger.info("BS4 missing, falling back to Regex for link extraction")
                all_links = re.findall(r'href=["\'](.*?)["\']', response.text, re.IGNORECASE)
                all_links += re.findall(r'src=["\'](.*?)["\']', response.text, re.IGNORECASE)

            # 1. Server header disclosure
            server_header = response.headers.get("Server")
            if server_header:
                findings.append(FindingData(
                    title="Server Header Exposed",
                    description=(
                        f"The server at {host} discloses its software version via the "
                        f"'Server' HTTP header: '{server_header}'. "
                        "This information can help attackers fingerprint the server."
                    ),
                    severity=Severity.INFO,
                    evidence=f"Server: {server_header}",
                    remediation=(
                        "Configure your web server to suppress or minimize the 'Server' header. "
                        "For Nginx: `server_tokens off;`. For Apache: `ServerTokens Prod`."
                    ),
                ))

            # 2. X-Powered-By disclosure
            powered_by = response.headers.get("X-Powered-By")
            if powered_by:
                findings.append(FindingData(
                    title="X-Powered-By Header Exposed",
                    description=(
                        f"The server discloses its technology stack via 'X-Powered-By': "
                        f"'{powered_by}'."
                    ),
                    severity=Severity.INFO,
                    evidence=f"X-Powered-By: {powered_by}",
                    remediation=(
                        "Remove the 'X-Powered-By' header. "
                        "In Express.js: `app.disable('x-powered-by');`. "
                        "In PHP: `expose_php = Off` in php.ini."
                    ),
                ))

            sensitive_links = []
            for link in all_links:
                if any(pattern in link.lower() for pattern in _SENSITIVE_PATTERNS):
                    sensitive_links.append(link)

            if sensitive_links:
                findings.append(FindingData(
                    title=f"Sensitive Resource Links Found ({len(sensitive_links)})",
                    description=(
                        f"The page at {url} contains {len(sensitive_links)} links to "
                        "potentially sensitive paths (config files, admin panels, backups, etc.)."
                    ),
                    severity=Severity.MEDIUM,
                    evidence="\n".join(sensitive_links[:20]),  # Cap to 20
                    remediation=(
                        "Review the listed URLs and ensure they are not publicly accessible. "
                        "Remove references to admin/config pages from public HTML."
                    ),
                ))

            # 5. Active Probing for "Famous" Files (Industry Standard)
            active_probes = []
            for probe_file in _CRITICAL_PROBE_FILES:
                try:
                    probe_url = f"{url.rstrip('/')}/{probe_file}"
                    probe_resp = requests.get(
                        probe_url, timeout=5, allow_redirects=False,
                        headers={"User-Agent": "HackerScan-Pro/1.0 (Security Audit Check)"}
                    )
                    if probe_resp.status_code == 200:
                        # Check for false positives (some servers return 200 for everything)
                        if len(probe_resp.text) > 10 and "<html" not in probe_resp.text.lower():
                            active_probes.append(f"{probe_file} (Found!)")
                except Exception:
                    continue

            if active_probes:
                findings.append(FindingData(
                    title="Sensitive Files Discovered via Active Probing",
                    description=(
                        f"The scanner successfully accessed {len(active_probes)} sensitive files "
                        "on the server that should not be publicly accessible."
                    ),
                    severity=Severity.HIGH if any(".env" in p or ".git" in p for p in active_probes) else Severity.MEDIUM,
                    evidence="\n".join(active_probes),
                    remediation=(
                        "Restrict access to these files using .htaccess, web.config, or server-level "
                        "permissions. Move sensitive configuration outside the web root."
                    ),
                ))

            # 6. Fallback: always report a successful discovery run
            if not findings:
                findings.append(FindingData(
                    title="Resource Discovery Completed",
                    description=f"No sensitive resources or header disclosures found on {host}.",
                    severity=Severity.INFO,
                    evidence=f"HTTP {response.status_code} at {url}",
                    remediation="No action required.",
                ))

        except requests.exceptions.ConnectionError:
            logger.warning("Resource discovery: connection refused to %s", url)
            findings.append(FindingData(
                title="Target Unreachable",
                description=f"Could not connect to {url} over HTTP.",
                severity=Severity.INFO,
                remediation="Verify the target is accessible over HTTP or HTTPS.",
            ))
        except requests.exceptions.Timeout:
            logger.warning("Resource discovery: timeout for %s", url)
        except Exception as e:
            logger.error("ResourceDiscoveryStrategy error: %s", e)

        return findings
