import logging
import asyncio
import os
from pathlib import Path
from typing import List, Optional, AsyncGenerator

from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity
from ..utils import make_evidence_request_async

logger = logging.getLogger(__name__)

# Resolve the wordlist path relative to this file
_STRATEGY_DIR = Path(__file__).resolve().parent
_DEFAULT_WORDLIST = _STRATEGY_DIR.parent / "wordlists" / "common.txt"

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

    async def run_async(self, target: "ScanTarget", scan: "Scan" = None) -> AsyncGenerator[FindingData, None]:
        url = target.url

        import shutil
        gobuster_path = shutil.which("gobuster")

        if gobuster_path:
            self.log(scan, "Gobuster detected. Starting directory fuzzing...")
            async for finding in self._run_gobuster_async(gobuster_path, url, scan):
                yield finding
        else:
            self.log(scan, "Gobuster not found. Using built-in async fuzzer...")
            async for finding in self._run_fallback_fuzzer_async(url, scan):
                yield finding

    async def _run_gobuster_async(self, gobuster_path: str, url: str, scan: "Scan") -> AsyncGenerator[FindingData, None]:
        wordlist = str(_DEFAULT_WORDLIST)
        if not os.path.exists(wordlist):
            self.log(scan, f"Wordlist not found at {wordlist}. Skipping.")
            return

        try:
            cmd = [
                gobuster_path,
                "dir",
                "-u", url,
                "-w", wordlist,
                "-z",  # No progress bar
                "-q",  # Quiet
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            for line in stdout.decode().splitlines():
                if "(Status: 200)" in line or "(Status: 301)" in line or "(Status: 302)" in line:
                    path = line.split(" ")[0].strip()
                    full_url = f"{url.rstrip('/')}/{path.lstrip('/')}"
                    
                    # Enrich with a real request for evidence
                    resp, req, res, poc = await make_evidence_request_async(full_url, timeout=5, follow_redirects=True)
                    
                    finding = self._process_path_result(path, full_url, resp.status_code if resp else 200, req, res, poc)
                    if finding:
                        yield finding

        except Exception as e:
            logger.error(f"Gobuster error: {e}")
            self.log(scan, f"Engine error: {str(e)}")

    async def _run_fallback_fuzzer_async(self, base_url: str, scan: "Scan") -> AsyncGenerator[FindingData, None]:
        wordlist_path = str(_DEFAULT_WORDLIST)
        if not os.path.exists(wordlist_path):
            return

        with open(wordlist_path, 'r') as f:
            words = [line.strip() for line in f if line.strip()]

        semaphore = asyncio.Semaphore(10)

        async def _check_path(path):
            async with semaphore:
                full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(full_url, timeout=5, follow_redirects=True)
                    if resp and resp.status_code < 400:
                        return self._process_path_result(path, full_url, resp.status_code, req, res, poc)
                except Exception:
                    pass
                return None

        tasks = [asyncio.create_task(_check_path(word)) for word in words[:200]] # Limit built-in scan
        for task in asyncio.as_completed(tasks):
            finding = await task
            if finding:
                yield finding

    def _process_path_result(self, path: str, full_url: str, status: int, request_dump: str, response_dump: str, poc: str) -> FindingData:
        severity = Severity.INFO
        title = f"Discovered Path: {path}"
        description = (
            f"Automated fuzzing identified an accessible path at `{full_url}`.\n\n"
            f"**REAL DATA PROOF**: The server returned a successful response for this path."
        )
        
        # Check for sensitive patterns
        for pattern, sev in self.SENSITIVE_PATTERNS.items():
            if pattern in path.lower():
                severity = sev
                title = f"Sensitive Resource Exposed: {path}"
                description = (
                    f"A potentially sensitive resource `{path}` was found exposed on the server.\n\n"
                    f"**REAL DATA PROOF**: Resource accessible at `{full_url}` (HTTP {status})."
                )
                break

        return FindingData(
            title=title,
            description=description,
            severity=severity,
            evidence={
                "path": path, 
                "full_url": full_url, 
                "status_code": status,
                "method": "GET"
            },
            request=request_dump,
            response=response_dump,
            poc=poc or f"curl -i {full_url}",
            remediation="Restrict access to this path or remove the file if it is not necessary for production.",
            plugin_slug=self.slug,
            is_verified=True
        )

    async def verify_async(self, finding: "Finding") -> bool:
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
            
        full_url = evidence.get("full_url")
        if not full_url:
            return False
            
        try:
            resp, req, res, poc = await make_evidence_request_async(
                full_url, 
                method=evidence.get("method", "GET"),
                follow_redirects=True,
                timeout=10
            )
            
            if resp and resp.status_code < 400:
                finding.request = req
                finding.response = res
                finding.poc = poc
                
                # Use executor for DB save to avoid blocking
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                
                if ".env" in full_url.lower():
                    if "DB_" in resp.text or "API_" in resp.text:
                        return True
                return True
        except Exception as e:
            logger.error(f"Verification error for DirFuzzing: {e}")
            
        return False

