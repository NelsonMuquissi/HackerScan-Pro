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
            output_dir = os.path.join(tmp_dir, "results")
            
            try:
                # --batch: Never ask for user input
                # --crawl=2: Crawl the target to find injection points
                # --forms: Try to test forms
                # --risk=1 --level=1: Safe default levels
                # --output-dir: Store results
                cmd = [
                    "sqlmap", "-u", url,
                    "--batch",
                    "--crawl=2",
                    "--forms",
                    "--risk=1",
                    "--level=1",
                    "--output-dir", tmp_dir
                ]

                # Handle Credentials
                from scans.models import CredentialType
                creds = target.credentials.filter(is_active=True)
                for c in creds:
                    if c.cred_type == CredentialType.COOKIE:
                        # value: {"cookie_name": "cookie_value"}
                        cookie_str = "; ".join([f"{k}={v}" for k, v in c.value.items()])
                        cmd.extend(["--cookie", cookie_str])
                    elif c.cred_type == CredentialType.HEADER:
                        # value: {"key": "Header-Name", "value": "Header-Value"}
                        cmd.extend(["--header", f"{c.value.get('key')}: {c.value.get('value')}"])
                    elif c.cred_type == CredentialType.BASIC_AUTH:
                        # value: {"username": "...", "password": "..."}
                        cmd.extend(["--auth-type", "Basic", "--auth-cred", f"{c.value.get('username')}:{c.value.get('password')}"])

                self.log(scan, f"Running: {' '.join([str(arg) if 'pass' not in str(arg).lower() else '********' for arg in cmd])}")
                # SQLMap can take a long time, we set a 10 min timeout for now
                subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)

                # SQLMap stores results in a subdirectory named after the host
                # We look for 'log' files or similar to parse findings
                target_dir = os.path.join(tmp_dir, url.replace("://", "_").replace("/", "_"))
                log_file = os.path.join(target_dir, "log")
                
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        log_content = f.read()
                        if "vulnerable" in log_content.lower() or "injection" in log_content.lower():
                            findings.append(FindingData(
                                title="SQL Injection Vulnerability Detected",
                                description=f"SQLMap identified potential SQL injection points on {url}.",
                                severity=Severity.CRITICAL,
                                evidence=log_content[:2000], # Truncate for DB
                                remediation="Use parameterized queries (prepared statements) and ORMs to prevent SQL injection. Sanitize all user input.",
                                plugin_slug=self.slug
                            ))
                else:
                    self.log(scan, "No SQL injection points found by SQLMap.")

            except subprocess.TimeoutExpired:
                self.log(scan, "SQLMap timed out. Results may be incomplete.")
            except Exception as e:
                logger.error("SQLMap error: %s", e)
                self.log(scan, f"SQLMap error: {str(e)}")

        return findings
