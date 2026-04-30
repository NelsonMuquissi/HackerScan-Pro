import logging
import subprocess
import os
import requests
from pathlib import Path
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

# Resolve the wordlist path relative to this file
_STRATEGY_DIR = Path(__file__).resolve().parent
_DEFAULT_WORDLIST = _STRATEGY_DIR / "wordlists" / "common.txt"

@register
class DirFuzzingStrategy(BaseScanStrategy):
    """
    Directory fuzzing engine using gobuster.
    Checks for sensitive directories and files.
    """
    slug = "dir_fuzzing"
    name = "Directory Fuzzing"

    SENSITIVE_PATTERNS = {
        ".env": Severity.CRITICAL,
        ".git": Severity.HIGH,
        "config.php": Severity.MEDIUM,
        "wp-config.php": Severity.HIGH,
        "backup": Severity.MEDIUM,
        ".sql": Severity.HIGH,
        ".zip": Severity.MEDIUM,
        ".tar.gz": Severity.MEDIUM,
        "id_rsa": Severity.CRITICAL,
        ".aws": Severity.CRITICAL,
        "admin": Severity.LOW,
        "login": Severity.LOW,
        "dashboard": Severity.LOW,
    }

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        host = target.host
        url = host if host.startswith("http") else f"http://{host}"

        wordlist = str(_DEFAULT_WORDLIST)
        if not os.path.exists(wordlist):
            self.log(scan, f"Wordlist not found at {wordlist}. Skipping.")
            return findings

        try:
            cmd = [
                "gobuster",
                "dir",
                "-u", url,
                "-w", wordlist,
                "-z",  # No progress bar
                "-q",  # Quiet
            ]

            self.log(scan, f"Running: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)

            discovered_paths = []
            for line in proc.stdout.splitlines():
                # Line format usually: /admin (Status: 200) [Size: 123]
                if "(Status: 200)" in line or "(Status: 301)" in line:
                    path = line.split(" ")[0].strip()
                    discovered_paths.append(path)

            for path in discovered_paths:
                severity = Severity.INFO
                full_url = f"{url.rstrip('/')}/{path.lstrip('/')}"
                title = f"Discovered Path: {path}"
                description = f"Automated fuzzing identified an accessible path at {full_url}"
                
                # Check for sensitive patterns
                for pattern, sev in self.SENSITIVE_PATTERNS.items():
                    if pattern in path.lower():
                        severity = sev
                        title = f"Sensitive Resource Exposed: {path}"
                        description = f"A potentially sensitive file or directory was found at {full_url}. This could lead to information disclosure."
                        break

                findings.append(FindingData(
                    title=title,
                    description=description,
                    severity=severity,
                    evidence={
                        "path": path, 
                        "full_url": full_url, 
                        "raw_line": line,
                        "method": "GET"
                    },
                    poc=f"curl -I {full_url}",
                    remediation="Restrict access to this path or remove the file if it is not necessary for production.",
                    plugin_slug=self.slug
                ))

            if not discovered_paths:
                self.log(scan, "No interesting paths discovered.")

        except FileNotFoundError:
            self.log(scan, "gobuster not found. Skipping.")
        except subprocess.TimeoutExpired:
            self.log(scan, "gobuster timed out.")
        except Exception as e:
            logger.error("DirFuzzingStrategy error: %s", e)

        return findings

    def verify(self, finding) -> bool:
        """
        Verify the finding by checking if the path is still accessible.
        """
        from scans.utils import make_evidence_request
        
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
            
        full_url = evidence.get("full_url")
        if not full_url:
            return False
            
        try:
            # 🎯 Standardized verification with evidence capture
            resp, req, res, poc = make_evidence_request(
                full_url, 
                method=evidence.get("method", "GET"),
                follow_redirects=True,
                timeout=10
            )
            
            if resp and resp.status_code < 400:
                # Update finding with fresh dumps
                finding.request = req
                finding.response = res
                finding.poc = poc
                
                # Extra "hidden" check: if it's a .env, check for common keys
                if ".env" in full_url.lower():
                    if "DB_" in resp.text or "API_" in resp.text:
                        return True
                return True
        except Exception as e:
            logger.error(f"Verification error for DirFuzzing: {e}")
            
        return False

