import logging
import re
from typing import List, AsyncGenerator, Optional
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity
from scans.utils import make_evidence_request_async, make_evidence_request, take_screenshot_async

logger = logging.getLogger(__name__)

# "Famous" critical files to actively probe for (Industry Standard + Advanced)
_CRITICAL_PROBE_FILES = [
    # Environment & Secrets
    ".env", ".env.local", ".env.production", ".env.staging", ".env.bak", ".env.old", ".env.example", ".env.dist",
    ".aws/credentials", ".aws/config",
    ".ssh/id_rsa", ".ssh/id_dsa", ".ssh/id_ecdsa", ".ssh/authorized_keys",
    "docker-compose.yml", "docker-compose.yaml", "Dockerfile", "docker-stack.yml",
    
    # Version Control
    ".git/config", ".git/index", ".git/HEAD", ".git/logs/HEAD",
    ".svn/entries", ".svn/all-wcprops",
    ".hg/requires", ".hg/hgrc",
    
    # Config & DB
    "config.php.bak", "config.php~", "config.php.old", "config.inc.php", "config.php.dist",
    "web.config", "phpinfo.php", "php.ini", "web.xml",
    "database.sql", "db.sql", "dump.sql", "backup.sql", "database.sqlite", "db.sqlite3",
    "config.json", "settings.json", "firebase.json", "config/database.yml",
    
    # Web Frameworks
    "wp-config.php.save", "wp-config.php.bak", "wp-config.php.swp",
    "composer.json", "package.json", "yarn.lock", "package-lock.json",
    ".npmrc", ".yarnrc", "Procfile",
    "storage/logs/laravel.log", "logs/error.log", "logs/access.log", "debug.log",
    
    # CMS & Admin
    "robots.txt", "sitemap.xml", ".well-known/security.txt",
    "server-status", "server-info",
    "admin/", "administrator/", "dashboard/", "console/", "wp-admin/",
    
    # IDE & System
    ".vscode/sftp.json", ".idea/workspace.xml",
    ".DS_Store", "Thumbs.db", "ehthumbs.db",
    "backup.zip", "site.zip", "www.zip", "backup.sql.gz"
]

@register
class ResourceDiscoveryStrategy(BaseScanStrategy):
    """
    Resource discovery engine.
    Identifies sensitive files, server headers, and metadata using standardized evidence collection.
    """
    slug = "resource_discovery"
    name = "Resource Discovery"

    async def run_async(self, target, scan=None):
        """
        Natively asynchronous implementation of resource discovery.
        Runs probes in parallel for high performance.
        """
        url = target.url
        
        # 1. Header Checks (Initial)
        resp, req_dump, res_dump, poc = await make_evidence_request_async(url)
        if resp:
            # Server header disclosure
            server_header = resp.headers.get("Server")
            if server_header:
                yield FindingData(
                    title="Server Header Exposed",
                    description=f"The server at {host} discloses its software version: '{server_header}'.",
                    severity=Severity.INFO,
                    evidence={"header": "Server", "value": server_header},
                    plugin_slug=self.slug,
                    request=req_dump, response=res_dump, poc=poc
                )

        # 2. Parallel Probing for Critical Files
        import asyncio
        semaphore = asyncio.Semaphore(15)

        async def probe_file(probe_name):
            async with semaphore:
                probe_url = f"{url.rstrip('/')}/{probe_name}"
                try:
                    p_resp, p_req, p_res, p_poc = await make_evidence_request_async(probe_url, follow_redirects=False)
                    
                    if p_resp and p_resp.status_code == 200:
                        content = p_resp.text
                        
                        # Soft-404 / WAF detection
                        if self._is_soft_404(content, probe_name):
                            return []
                            
                        # 🔍 Scan for Secrets in content
                        secret_findings = self._scan_for_secrets(content, probe_url, p_req, p_res, p_poc)
                        
                        # Base finding for the file itself
                        severity = self._get_file_severity(probe_name)
                        proof_text = self._get_masked_snippet(content, severity)

                        # 🚀 Visual Proof for sensitive directories
                        visual_proof = None
                        if any(x in probe_name.lower() for x in ["admin", "dashboard", "console", "portal", "/"]):
                            visual_proof = await take_screenshot_async(probe_url)

                        main_finding = FindingData(
                            title=f"Sensitive Resource Discovered: {probe_name}",
                            description=f"The scanner successfully accessed {probe_name} at {probe_url}.\n\n**REAL DATA PROOF**: Content Snippet: `{proof_text[:100]}...`",
                            severity=severity,
                            evidence={
                                "url": probe_url, 
                                "size": len(content), 
                                "snippet": proof_text[:800],
                                "visual_proof_b64": visual_proof
                            },
                            request=p_req, response=p_res, poc=p_poc,
                            plugin_slug=self.slug, is_verified=True
                        )
                        return [main_finding] + secret_findings
                except Exception:
                    return []
                return []

        # Execute all probes in parallel
        tasks = [probe_file(f) for f in _CRITICAL_PROBE_FILES]
        for completed_task in asyncio.as_completed(tasks):
            findings = await completed_task
            for f in findings:
                yield f

    def _is_soft_404(self, content: str, filename: str) -> bool:
        content_lower = content.lower()
        is_html = "<html" in content_lower or "<!doctype" in content_lower
        is_generic_404 = any(x in content_lower for x in ["404 not found", "page not found", "cannot find"])
        is_waf_block = any(x in content_lower for x in ["access denied", "waf", "forbidden", "captcha", "security check"])
        should_be_html = filename.endswith((".html", ".htm", "/"))
        return (is_html or is_generic_404 or is_waf_block) and not should_be_html

    def _get_file_severity(self, filename: str) -> Severity:
        if any(x in filename for x in [".env", ".aws", ".ssh", "config.php", "database.sql"]):
            return Severity.CRITICAL
        if any(x in filename for x in [".git", "docker-compose", ".npmrc"]):
            return Severity.HIGH
        return Severity.MEDIUM

    def _get_masked_snippet(self, content: str, severity: Severity) -> str:
        proof_text = "\n".join(content.splitlines()[:15])
        if severity == Severity.CRITICAL:
            proof_text = re.sub(r"([A-Z0-9_]*(?:KEY|SECRET|PASSWORD|TOKEN|AUTH|PWD)[A-Z0-9_]*\s*[=:]\s*).*(\n|$)", r"\1 [REDACTED]\2", proof_text, flags=re.IGNORECASE)
        return proof_text

    def _scan_for_secrets(self, content: str, url: str, req, res, poc) -> List[FindingData]:
        """Scans file content for leaked API keys and secrets with validation."""
        patterns = {
            "AWS Access Key": r"AKIA[0-9A-Z]{16}",
            "AWS Secret Key": r"([^A-Z0-9/+=][A-Z0-9/+=]{40}[^A-Z0-9/+=])",
            "Google API Key": r"AIza[0-9A-Za-z\\-_]{35}",
            "Stripe API Key": r"sk_live_[0-9a-zA-Z]{24}",
            "GitHub Personal Access Token": r"ghp_[0-9a-zA-Z]{36}",
            "Firebase URL": r"https://[a-z0-9-]+\.firebaseio\.com",
            "Slack Webhook": r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+",
            "Generic Private Key": r"-----BEGIN [A-Z ]+ PRIVATE KEY-----",
        }
        
        findings = []
        for name, pattern in patterns.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                secret = match.group(0)
                findings.append(FindingData(
                    title=f"Leaked Secret Found: {name}",
                    description=f"A {name} was found in the content of {url}. This represents a severe security risk.\n\n**REAL DATA PROOF**: Found `{secret[:10]}...` in resource content.",
                    severity=Severity.CRITICAL,
                    evidence={
                        "secret_type": name, 
                        "url": url,
                        "raw_secret_internal": secret, # For verification validation
                        "snippet": content[max(0, match.start()-50):min(len(content), match.end()+50)].strip()
                    },
                    remediation=f"1. **Revoke**: Immediately revoke the leaked {name}.\n2. **Rotate**: Generate a new secret and update your configuration.",
                    request=req, response=res, poc=poc,
                    plugin_slug=self.slug, is_verified=False
                ))
        
        # 🚀 REAL DATA EXTRACTION for Specific Files
        if ".git/config" in url:
            remotes = re.findall(r"url\s*=\s*(.*)", content)
            if remotes:
                findings.append(FindingData(
                    title="Git Remote URL Exposure",
                    description=f"The internal Git configuration is exposed at {url}, revealing the repository source and potential developer usernames.\n\n**REAL DATA PROOF**: Remote: {remotes[0]}",
                    severity=Severity.HIGH,
                    evidence={"remotes": remotes, "url": url},
                    remediation="Block access to the .git directory in your web server configuration.",
                    request=req, response=res, poc=poc,
                    plugin_slug=self.slug, is_verified=True
                ))

        if ".git/HEAD" in url:
            branch = re.findall(r"ref:\s*refs/heads/(.*)", content)
            if branch:
                findings.append(FindingData(
                    title="Git Branch Disclosure",
                    description=f"The active Git branch is exposed.\n\n**REAL DATA PROOF**: Branch: **{branch[0]}**",
                    severity=Severity.LOW,
                    evidence={"branch": branch[0], "url": url},
                    plugin_slug=self.slug, is_verified=True
                ))

        if ".env" in url:
            # Extract non-sensitive but proving keys for "Real Data Proof"
            proving_keys = ["APP_NAME", "APP_ENV", "DB_DATABASE", "DB_USERNAME", "DB_HOST", "DB_USER", "MAIL_HOST"]
            found_vars = {}
            for k in proving_keys:
                match = re.search(rf"^{k}\s*=\s*(.*)", content, re.M)
                if match:
                    found_vars[k.lower()] = match.group(1).strip()
            
            if found_vars:
                findings.append(FindingData(
                    title="Sensitive Resource Discovered: Database Credentials in .env",
                    description=f"Sensitive environment variables leaked at {url}. Verified by extracting real configuration keys.\n\n**REAL DATA PROOF**: Database Host: {found_vars.get('db_host', 'N/A')}, User: {found_vars.get('db_user', 'N/A')}",
                    severity=Severity.CRITICAL,
                    evidence={**found_vars, "url": url, "extracted_vars": found_vars},
                    remediation="Remove .env from public root and use server-level environment variables.",
                    request=req, response=res, poc=poc,
                    plugin_slug=self.slug, is_verified=True
                ))
            else:
                findings.append(FindingData(
                    title="Environment Configuration Leak (.env)",
                    description=f"The .env file is publicly accessible at {url}.",
                    severity=Severity.CRITICAL,
                    evidence={"url": url},
                    remediation="Remove .env from public root and use server-level environment variables.",
                    request=req, response=res, poc=poc,
                    plugin_slug=self.slug, is_verified=True
                ))

        if "phpinfo" in url:
            os_info = re.search(r"System\s*</td><td class=\"v\">(.*?)</td>", content, re.I)
            php_ver = re.search(r"PHP Version\s*</td><td class=\"v\">(.*?)</td>", content, re.I)
            if os_info or php_ver:
                findings.append(FindingData(
                    title="PHPInfo Disclosure with System Metadata",
                    description=f"Exposed phpinfo() at {url} discloses detailed server configuration.",
                    severity=Severity.MEDIUM,
                    evidence={
                        "os": os_info.group(1) if os_info else "Unknown",
                        "php_version": php_ver.group(1) if php_ver else "Unknown"
                    },
                    remediation="Delete phpinfo() files from production environments.",
                    request=req, response=res, poc=poc,
                    plugin_slug=self.slug, is_verified=True
                ))

        return findings

    async def _validate_secret_async(self, name: str, secret: str) -> Optional[str]:
        """Shared validation logic (similar to JSSecretStrategy)."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5, verify=False) as client:
                if name == "GitHub Personal Access Token":
                    resp = await client.get("https://api.github.com/user", headers={"Authorization": f"token {secret}"})
                    if resp.status_code == 200: return f"VALID: GitHub User: {resp.json().get('login')}"
                elif name == "Google API Key":
                    url = f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?location=-33,151&radius=1&key={secret}"
                    resp = await client.get(url)
                    if resp.status_code == 200 and "error_message" not in resp.text: return "VALID: Google Maps API key is active."
                elif name == "Stripe API Key":
                    resp = await client.get("https://api.stripe.com/v1/account", auth=(secret, ""))
                    if resp.status_code == 200: return f"VALID: Stripe Account: {resp.json().get('id')}"
        except: pass
        return None

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Re-verify by checking if the sensitive file is still accessible and contains expected data.
        Updates evidence if verified.
        """
        import asyncio
        url = finding.evidence.get("url") if isinstance(finding.evidence, dict) else None
        
        if not url:
            # Maybe it was a header check
            header_data = finding.evidence if isinstance(finding.evidence, dict) else {}
            if "header" in header_data:
                from asgiref.sync import sync_to_async
                scan = await sync_to_async(lambda: finding.scan)()
                target = await sync_to_async(lambda: scan.target)()

                target_url = target.host
                if not target_url.startswith("http"):
                    target_url = f"http://{target_url}"
                resp, req, res, poc = await make_evidence_request_async(target_url)
                if resp:
                    h_name = header_data.get("header")
                    if h_name in resp.headers:
                        finding.request = req
                        finding.response = res
                        
                        # Save finding
                        from asgiref.sync import sync_to_async
                        await sync_to_async(finding.save)()
                        return True
                return False
            return False
            
        try:
            resp, req, res, poc = await make_evidence_request_async(url, follow_redirects=False)
            
            if resp and resp.status_code == 200:
                is_html = "<html" in resp.text.lower()
                is_file = not url.endswith((".html", ".htm", "/"))
                
                if is_file and is_html:
                    return False # Now a soft-404 or masked
                
                # Update evidence
                finding.request = req
                finding.response = res
                
                # 🚀 Active Validation if secret was found
                raw_secret = finding.evidence.get("raw_secret_internal")
                secret_type = finding.evidence.get("secret_type")
                if raw_secret and secret_type:
                    proof = await self._validate_secret_async(secret_type, raw_secret)
                    if proof:
                        finding.description += f"\n\n**REAL DATA PROOF**: {proof}"
                        finding.evidence["validation_proof"] = proof
                
                finding.is_verified = True
                
                # Save finding
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True
        except Exception as e:
            logger.error(f"Verification error for ResourceDiscovery: {e}")
            return False
            
        return False
