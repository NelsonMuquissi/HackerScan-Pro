import logging
import re
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity
from scans.utils import make_evidence_request

logger = logging.getLogger(__name__)

# "Famous" critical files to actively probe for (Industry Standard + Advanced)
_CRITICAL_PROBE_FILES = [
    # Environment & Secrets
    ".env", ".env.local", ".env.production", ".env.staging", ".env.bak", ".env.old",
    ".aws/credentials", ".aws/config",
    ".ssh/id_rsa", ".ssh/id_dsa", ".ssh/id_ecdsa", ".ssh/authorized_keys",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    
    # Version Control
    ".git/config", ".git/index", ".git/HEAD", ".git/logs/HEAD",
    ".svn/entries", ".svn/all-wcprops",
    
    # Config & DB
    "config.php.bak", "config.php~", "config.php.old", "config.inc.php",
    "web.config", "phpinfo.php", "php.ini",
    "database.sql", "db.sql", "dump.sql", "backup.sql",
    "config.json", "settings.json", "firebase.json",
    
    # Web Frameworks
    "wp-config.php.save", "wp-config.php.bak", "wp-config.php.swp",
    "composer.json", "package.json", "yarn.lock", "package-lock.json",
    ".npmrc", ".yarnrc",
    
    # CMS & Admin
    "robots.txt", "sitemap.xml", ".well-known/security.txt",
    "server-status", "server-info",
    "admin/", "administrator/", "dashboard/", "console/",
    
    # IDE & System
    ".vscode/sftp.json", ".idea/workspace.xml",
    ".DS_Store", "Thumbs.db"
]

@register
class ResourceDiscoveryStrategy(BaseScanStrategy):
    """
    Resource discovery engine.
    Identifies sensitive files, server headers, and metadata using standardized evidence collection.
    """
    slug = "resource_discovery"
    name = "Resource Discovery"

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        host = target.host
        url = host if host.startswith("http") else f"http://{host}"

        try:
            # 1. Check Root URL for Headers
            resp, req_dump, res_dump, poc = make_evidence_request(url)
            if resp:
                # Server header disclosure
                server_header = resp.headers.get("Server")
                if server_header:
                    findings.append(FindingData(
                        title="Server Header Exposed",
                        description=(
                            f"The server at {host} discloses its software version via the "
                            f"'Server' HTTP header: '{server_header}'. "
                            "Attackers can use this to research known vulnerabilities for that specific version."
                        ),
                        severity=Severity.INFO,
                        evidence={"header": "Server", "value": server_header},
                        remediation="Configure your web server to suppress or minimize the 'Server' header (e.g., 'ServerTokens Prod' in Apache).",
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        plugin_slug=self.slug
                    ))

                # X-Powered-By disclosure
                powered_by = resp.headers.get("X-Powered-By")
                if powered_by:
                    findings.append(FindingData(
                        title="X-Powered-By Header Exposed",
                        description=f"The technology stack is exposed via the 'X-Powered-By' header: '{powered_by}'.",
                        severity=Severity.INFO,
                        evidence={"header": "X-Powered-By", "value": powered_by},
                        remediation="Remove the X-Powered-By header from server responses.",
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        plugin_slug=self.slug
                    ))

            # 2. Active Probing for Critical Files
            for probe_file in _CRITICAL_PROBE_FILES:
                try:
                    probe_url = f"{url.rstrip('/')}/{probe_file}"
                    p_resp, p_req, p_res, p_poc = make_evidence_request(probe_url, follow_redirects=False)
                    
                    if p_resp and p_resp.status_code == 200:
                        # Advanced False Positive Detection
                        # 1. Check if it's just a custom 404 page returning 200
                        is_html = "<html" in p_resp.text.lower() or "<!doctype" in p_resp.text.lower()
                        should_be_html = probe_file.endswith((".html", ".htm", "/"))
                        
                        if is_html and not should_be_html:
                            continue # Likely a soft-404
                            
                        # 2. Check for minimum size
                        content = p_resp.text
                        if len(content) < 5:
                            continue
                            
                        # Identify severity based on content/filename
                        severity = Severity.MEDIUM
                        if any(x in probe_file for x in [".env", ".aws", ".ssh", "config.php", "database.sql"]):
                            severity = Severity.CRITICAL
                        elif any(x in probe_file for x in [".git", "docker-compose", ".npmrc"]):
                            severity = Severity.HIGH

                        # Extract Proof (Masked)
                        proof_lines = content.splitlines()[:10]
                        proof_text = "\n".join(proof_lines)
                        if severity == Severity.CRITICAL:
                            proof_text = re.sub(r"(=|:)\s*.*", r"\1 [REDACTED]", proof_text)

                        findings.append(FindingData(
                            title=f"Sensitive Resource Discovered: {probe_file}",
                            description=(
                                f"The scanner successfully accessed {probe_file} at {probe_url}. "
                                "This file contains sensitive configuration or metadata that should not be publicly accessible."
                            ),
                            severity=severity,
                            evidence={
                                "url": probe_url,
                                "status": 200,
                                "size": len(content),
                                "snippet": proof_text[:500]
                            },
                            remediation=(
                                "1. Remove the file if it is not needed on the production server.\n"
                                "2. Restrict access using firewall rules or web server configuration (.htaccess, nginx.conf).\n"
                                "3. Ensure sensitive files are included in .gitignore."
                            ),
                            request=p_req,
                            response=p_res,
                            poc=p_poc,
                            plugin_slug=self.slug,
                            is_verified=True
                        ))
                except Exception:
                    continue

        except Exception as e:
            logger.error("ResourceDiscoveryStrategy error: %s", e)

        return findings

    def verify(self, finding: "Finding") -> bool:
        """
        Re-verify by checking if the sensitive file is still accessible and contains expected data.
        Updates evidence if verified.
        """
        url = finding.evidence.get("url") if isinstance(finding.evidence, dict) else None
        if not url:
            # Maybe it was a header check
            header_data = finding.evidence if isinstance(finding.evidence, dict) else {}
            if "header" in header_data:
                target_url = finding.scan.target.host
                if not target_url.startswith("http"):
                    target_url = f"http://{target_url}"
                resp, req, res, poc = make_evidence_request(target_url)
                if resp:
                    h_name = header_data.get("header")
                    if h_name in resp.headers:
                        finding.request = req
                        finding.response = res
                        return True
                return False
            return False
            
        try:
            resp, req, res, poc = make_evidence_request(url, follow_redirects=False)
            
            if resp and resp.status_code == 200:
                is_html = "<html" in resp.text.lower()
                is_file = not url.endswith((".html", ".htm", "/"))
                
                if is_file and is_html:
                    return False # Now a soft-404 or masked
                
                # Update evidence
                finding.request = req
                finding.response = res
                return True
        except Exception:
            return False
            
        return False
