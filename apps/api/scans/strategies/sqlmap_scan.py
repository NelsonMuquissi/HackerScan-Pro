import asyncio
import logging
import tempfile
import os
import re
import subprocess
from typing import List, AsyncGenerator
from asgiref.sync import sync_to_async
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity, CredentialType

logger = logging.getLogger(__name__)

@register
class SQLMapStrategy(BaseScanStrategy):
    """
    SQL Injection detection using SQLMap.
    Zero Simulation: Runs the actual sqlmap tool against the target.
    Native async implementation for improved integration.
    """
    slug = "sqlmap_scan"
    name = "SQL Injection Audit (SQLMap)"
    description = "Advanced SQL injection detection engine using SQLMap."
    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        """
        Native async implementation using asyncio.subprocess.
        """
        host = target.host
        # If target doesn't have a protocol, assume http for sqlmap
        url = host if host.startswith(("http://", "https://")) else f"http://{host}"
        
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
                await self._add_credentials_to_cmd(cmd, target)

                self.log(scan, f"Running: sqlmap {' '.join([str(arg) if 'pass' not in str(arg).lower() else '********' for arg in cmd])}")
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                try:
                    await asyncio.wait_for(process.wait(), timeout=600)
                except asyncio.TimeoutError:
                    self.log(scan, "SQLMap timed out. Results may be incomplete.")
                    if process.returncode is None:
                        process.terminate()

                # SQLMap stores results in a subdirectory named after the host
                host_dir_name = url.replace("://", "_").replace("/", "_").replace(":", "_")
                target_dir = os.path.join(tmp_dir, host_dir_name)
                
                if not os.path.exists(target_dir):
                    from urllib.parse import urlparse
                    hostname = urlparse(url).netloc.replace(":", "_")
                    target_dir = os.path.join(tmp_dir, hostname)

                log_file = os.path.join(target_dir, "log")
                
                if os.path.exists(log_file):
                    with open(log_file, "r") as f:
                        log_content = f.read()
                        
                    parsed_findings = self._parse_sqlmap_log(log_content, url)
                    
                    # 🚀 ENRICHMENT: If findings are found, try to extract real data
                    if parsed_findings:
                        self.log(scan, "Injection found! Extracting real database metadata...")
                        enrich_cmd = cmd + ["--dbs", "--current-db", "--current-user", "--hostname"]
                        try:
                            enrich_proc = await asyncio.create_subprocess_exec(
                                *enrich_cmd,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            await asyncio.wait_for(enrich_proc.wait(), timeout=120)
                            
                            # Read results from log file again (or session file)
                            if os.path.exists(log_file):
                                with open(log_file, "r") as f:
                                    enriched_log = f.read()
                                    self._apply_enrichment(parsed_findings, enriched_log)
                        except Exception as e:
                            logger.error(f"SQLMap enrichment error: {e}")

                    for pf in parsed_findings:
                        pf.poc = self._generate_poc(url, pf.evidence.get("parameter"), pf.evidence.get("payload"))
                        yield pf
                else:
                    self.log(scan, "No SQL injection points found by SQLMap.")

            except Exception as e:
                logger.error("SQLMap error: %s", e)
                self.log(scan, f"SQLMap error: {str(e)}")
    def _apply_enrichment(self, findings: List[FindingData], log_content: str):
        """
        Extracts real data from enriched log content and adds it to findings.
        """
        dbs = re.findall(r"available databases \[\d+\]:\n(.*?)(?:\n\n|\n\[|\Z)", log_content, re.S)
        curr_db = re.findall(r"current database:\s+'([^']+)'", log_content)
        curr_user = re.findall(r"current user:\s+'([^']+)'", log_content)
        hostname = re.findall(r"hostname:\s+'([^']+)'", log_content)

        for f in findings:
            if dbs: f.evidence["databases"] = [d.strip() for d in dbs[0].split("\n") if d.strip()]
            if curr_db: f.evidence["current_database"] = curr_db[0]
            if curr_user: f.evidence["current_user"] = curr_user[0]
            if hostname: f.evidence["hostname"] = hostname[0]
            
            # Update description with proof (avoiding duplication)
            proof_lines = []
            if curr_db: proof_lines.append(f"- Current Database: `{curr_db[0]}`")
            if curr_user: proof_lines.append(f"- Current User: `{curr_user[0]}`")
            if hostname: proof_lines.append(f"- Hostname: `{hostname[0]}`")
            
            if proof_lines and "**REAL DATA PROOF**" not in f.description:
                f.description += f"\n\n**REAL DATA PROOF**:\n" + "\n".join(proof_lines)


    async def verify_async(self, finding: "Finding") -> bool:
        """
        Verify SQL injection by re-running sqlmap on the specific parameter (async).
        """
        import asyncio
        # We must use sync_to_async for relation access in an async context
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()
        url = target.host if target.host.startswith(("http://", "https://")) else f"http://{target.host}"
        
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
                "--output-dir", tmp_dir,
                "--current-db", "--current-user" # Enrich during verification
            ]
            await self._add_credentials_to_cmd(cmd, target)
            
            try:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=300)
                output = stdout.decode()
                
                is_vulnerable = "is vulnerable" in output.lower() or "injection" in output.lower()
                if is_vulnerable:
                    finding.is_verified = True
                    
                    # Extract proof from verification output
                    curr_db = re.findall(r"current database:\s+'([^']+)'", output)
                    curr_user = re.findall(r"current user:\s+'([^']+)'", output)
                    
                    proof_lines = []
                    if curr_db:
                        finding.evidence["verified_database"] = curr_db[0]
                        proof_lines.append(f"- Verified Database: `{curr_db[0]}`")
                    if curr_user:
                        finding.evidence["verified_user"] = curr_user[0]
                        proof_lines.append(f"- Verified User: `{curr_user[0]}`")
                    
                    if proof_lines and "**VERIFICATION PROOF**" not in finding.description:
                        finding.description += f"\n\n**VERIFICATION PROOF**:\n" + "\n".join(proof_lines)

                    from asgiref.sync import sync_to_async
                    await sync_to_async(finding.save)()
                    return True
                return False
            except Exception as e:
                logger.error(f"SQLMap verification error: {e}")
                return False


    async def _add_credentials_to_cmd(self, cmd: list, target):
        # We must use sync_to_async for ORM access in an async context
        def get_creds():
            return list(target.credentials.filter(is_active=True))
            
        creds = await sync_to_async(get_creds)()
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
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            k, v = parts
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
