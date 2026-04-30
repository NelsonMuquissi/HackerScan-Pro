import logging
import subprocess
import json
import tempfile
import os
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class SQLMapStrategy(BaseScanStrategy):
    """
    SQL Injection detection using SQLMap.
    Zero Simulation: Runs the actual sqlmap tool against the target.
    """
    slug = "sqlmap_scan"
    name = "SQL Injection Audit (SQLMap)"
    description = "Advanced SQL injection detection engine using SQLMap."

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        # If target doesn't have a protocol, assume http for sqlmap
        url = host if host.startswith(("http://", "https://")) else f"http://{host}"
        
        findings = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                cmd = [
                    "sqlmap", "-u", url,
                    "--batch",
                    "--crawl=2",
                    "--forms",
                    "--risk=1",
                    "--level=1",
                    "--output-dir", tmp_dir,
                    "--threads=3"
                ]

                # Handle Credentials
                self._add_credentials_to_cmd(cmd, target)

                self.log(scan, f"Running: {' '.join([str(arg) if 'pass' not in str(arg).lower() else '********' for arg in cmd])}")
                subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)

                # SQLMap stores results in a subdirectory named after the host
                host_dir_name = url.replace("://", "_").replace("/", "_").replace(":", "_")
                target_dir = os.path.join(tmp_dir, host_dir_name)
                
                # Sometimes sqlmap uses just the hostname if it's simple
                if not os.path.exists(target_dir):
                    from urllib.parse import urlparse
                    hostname = urlparse(url).netloc.replace(":", "_")
                    target_dir = os.path.join(tmp_dir, hostname)

                log_file = os.path.join(target_dir, "log")
                
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        log_content = f.read()
                        
                    # Parse vulnerabilities from log
                    parsed_findings = self._parse_sqlmap_log(log_content, url)
                    for pf in parsed_findings:
                        # Try to generate a PoC
                        pf.poc = self._generate_poc(url, pf.evidence.get("parameter"), pf.evidence.get("payload"))
                        findings.append(pf)
                else:
                    self.log(scan, "No SQL injection points found by SQLMap.")

            except subprocess.TimeoutExpired:
                self.log(scan, "SQLMap timed out. Results may be incomplete.")
            except Exception as e:
                logger.error("SQLMap error: %s", e)
                self.log(scan, f"SQLMap error: {str(e)}")

        return findings

    def verify(self, finding: "Finding") -> bool:
        """
        Verify SQL injection by re-running sqlmap on the specific parameter.
        """
        target = finding.scan.target
        url = target.host if target.host.startswith(("http://", "https://")) else f"http://{target.host}"
        
        # Extract parameter from evidence if available
        param = finding.evidence.get("parameter")
        if not param:
            return False

        with tempfile.TemporaryDirectory() as tmp_dir:
            cmd = [
                "sqlmap", "-u", url,
                "-p", param,
                "--batch",
                "--level=1",
                "--risk=1",
                "--output-dir", tmp_dir
            ]
            self._add_credentials_to_cmd(cmd, target)
            
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
                # If "is vulnerable" is in output or log exists
                return "is vulnerable" in proc.stdout.lower() or "injection" in proc.stdout.lower()
            except Exception:
                return False

    def _add_credentials_to_cmd(self, cmd: list, target):
        from scans.models import CredentialType
        creds = target.credentials.filter(is_active=True)
        for c in creds:
            if c.cred_type == CredentialType.COOKIE:
                cookie_str = "; ".join([f"{k}={v}" for k, v in c.value.items()])
                cmd.extend(["--cookie", cookie_str])
            elif c.cred_type == CredentialType.HEADER:
                cmd.extend(["--header", f"{c.value.get('key')}: {c.value.get('value')}"])
            elif c.cred_type == CredentialType.BASIC_AUTH:
                cmd.extend(["--auth-type", "Basic", "--auth-cred", f"{c.value.get('username')}:{c.value.get('password')}"])

    def _parse_sqlmap_log(self, log_content: str, url: str) -> List[FindingData]:
        findings = []
        # SQLMap log blocks are separated by lines of '-'
        blocks = log_content.split("---")
        for block in blocks:
            if "Parameter:" in block and "Type:" in block:
                lines = [line.strip() for line in block.strip().split("\n") if line.strip()]
                data = {}
                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        data[k.strip().lower()] = v.strip()
                
                param = data.get("parameter", "unknown")
                inj_type = data.get("type", "SQL Injection")
                title = data.get("title", "SQL Injection Detected")
                payload = data.get("payload", "")

                findings.append(FindingData(
                    title=f"SQL Injection: {title}",
                    description=f"SQLMap found a {inj_type} vulnerability in parameter '{param}' at {url}.",
                    severity=Severity.CRITICAL,
                    evidence={
                        "parameter": param,
                        "type": inj_type,
                        "title": title,
                        "payload": payload,
                        "raw_block": block.strip()
                    },
                    remediation="Use parameterized queries (prepared statements) or an ORM. Never concatenate user input into SQL strings.",
                    plugin_slug=self.slug
                ))
        return findings

    def _generate_poc(self, url, parameter, payload) -> str:
        if not parameter or not payload:
            return ""
        # Simple curl PoC
        return f"curl -G '{url}' --data-urlencode '{payload}'"
