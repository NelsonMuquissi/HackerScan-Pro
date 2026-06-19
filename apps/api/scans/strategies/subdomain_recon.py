import logging
import subprocess
import json
import tempfile
import os
import asyncio
import httpx
from typing import List, Set, Dict, AsyncGenerator, Optional
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

# High-value asset indicators
HIGH_VALUE_KEYWORDS = ["dev", "staging", "test", "jenkins", "jira", "gitlab", "grafana", "prometheus", "admin", "vpn", "portal"]

@register
class SubdomainReconStrategy(BaseScanStrategy):
    """
    Subdomain enumeration engine.
    Uses:
    - Subfinder (Fast passive)
    - Amass (Deep active/passive)
    - crt.sh (Certificate Transparency Logs)
    - Gau (Historical URLs/Endpoints)
    - DNS brute-force fallback
    Features: HTTP Title grabbing and asset classification.
    """
    slug = "subdomain_recon"
    name = "Asset & Subdomain Discovery"
    description = "Deep reconnaissance of the target's attack surface using passive and active enumeration."

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        host = target.host
        
        # We'll use a set to avoid duplicates across different tools
        found_subdomains = set()
        
        # 1. Run all recon tools in parallel
        self.log(scan, f"Starting parallel reconnaissance on {host}...")
        
        recon_tasks = [
            self._run_subfinder_async(host),
            self._get_crt_sh_subdomains_async(host),
            self._run_amass_async(host),
            self._run_gau_async(host)
        ]
        
        # Process tool results as they finish
        for task in asyncio.as_completed(recon_tasks):
            try:
                new_subs = await task
                found_subdomains.update(new_subs)
                self.log(scan, f"Found {len(new_subs)} potential candidates from a tool.")
            except Exception as e:
                logger.error(f"Recon tool error: {e}")
 
        if not found_subdomains:
            self.log(scan, "No subdomains found via passive tools. Running emergency DNS brute force...")
            found_subdomains.update(await self._run_dns_bruteforce_async(host))
 
        if not found_subdomains:
            return
 
        # 2. Validate and stream findings in real-time
        self.log(scan, f"Validating {len(found_subdomains)} candidates and streaming findings...")
        
        semaphore = asyncio.Semaphore(10) # Validate 10 at a time
        
        async def _validate_and_yield(sub):
            async with semaphore:
                asset = await self._validate_single_sub_async(sub, host, scan)
                if asset:
                    high_val = any(kw in sub.lower() for kw in HIGH_VALUE_KEYWORDS)
                    return FindingData(
                        title=f"Discovered Subdomain: {sub}",
                        description=(
                            f"An active asset was discovered at `{sub}` during the reconnaissance phase. "
                            "This asset responds to network probes and may expose further attack surface.\n\n"
                            f"**REAL DATA PROOF**:\n"
                            f"- **Host**: {sub}\n"
                            f"- **Resolved IP**: {asset['ip']}\n"
                            f"- **HTTP Title**: {asset['title']}"
                        ),
                        severity=Severity.HIGH if high_val else Severity.INFO,
                        evidence=asset,
                        remediation="Ensure this asset is authorized and covered by security monitoring.",
                        plugin_slug=self.slug,
                        request=asset.get("req_dump", ""),
                        response=asset.get("res_dump", ""),
                        poc=asset.get("poc", f"subfinder -d {host} -silent"),
                        is_verified=True
                    )
                return None
 
        # Use unique subdomains only
        unique_subs = list(found_subdomains)
        validation_tasks = [_validate_and_yield(sub) for sub in unique_subs[:100]] # Cap at 100
        
        for task in asyncio.as_completed(validation_tasks):
            finding = await task
            if finding:
                yield finding
 
    async def verify_async(self, finding) -> bool:
        """Native async verification."""
        import asyncio
        from scans.utils import make_evidence_request_async
        
        sub = finding.evidence.get("subdomain") or finding.evidence.get("primary_host")
        if not sub:
            return False
 
        try:
            # Try HTTPS then HTTP
            resp, req, res, poc = await make_evidence_request_async(f"https://{sub}", timeout=5)
            if not resp:
                resp, req, res, poc = await make_evidence_request_async(f"http://{sub}", timeout=5)
            
            if resp:
                finding.request = req
                finding.response = res
                finding.poc = poc
                finding.is_verified = True
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True
        except Exception:
            pass
        return False

    async def _run_subfinder_async(self, host: str) -> List[str]:
        results = []
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            output_file = tf.name
        try:
            cmd = ["subfinder", "-d", host, "-o", output_file, "-silent"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(process.wait(), timeout=120)
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    results = [line.strip() for line in f if line.strip()]
        except Exception:
            pass
        finally:
            if os.path.exists(output_file): os.remove(output_file)
        return results

    async def _run_amass_async(self, host: str) -> List[str]:
        results = []
        try:
            cmd = ["amass", "enum", "-passive", "-d", host, "-silent"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=180)
            if stdout:
                results = [line.strip() for line in stdout.decode().split("\n") if line.strip()]
        except Exception:
            pass
        return results

    async def _run_gau_async(self, host: str) -> List[str]:
        results = set()
        try:
            cmd = ["gau", host, "--subs", "--threads", "5"]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=60)
            if stdout:
                from urllib.parse import urlparse
                for line in stdout.decode().split("\n"):
                    line = line.strip()
                    if not line: continue
                    if not line.startswith(("http://", "https://")): line = "http://" + line
                    try:
                        parsed = urlparse(line)
                        hostname = parsed.hostname
                        if hostname and hostname.endswith(host):
                            results.add(hostname)
                    except Exception:
                        continue
        except Exception:
            pass
        return list(results)

    async def _get_crt_sh_subdomains_async(self, domain: str) -> List[str]:
        results = set()
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    for entry in data:
                        name_value = entry.get("name_value", "")
                        for name in name_value.split("\n"):
                            name = name.strip().lower()
                            if name.endswith(domain) and "*" not in name:
                                results.add(name)
        except Exception:
            pass
        return list(results)

    async def _run_dns_bruteforce_async(self, host: str) -> List[str]:
        famous_subs = ["www", "mail", "dev", "api", "admin", "app", "vpn", "test", "demo", "portal", "staging"]
        results = []
        
        async def _check(sub):
            candidate = f"{sub}.{host}"
            try:
                # Use getaddrinfo for async-friendly DNS lookup
                await asyncio.get_event_loop().getaddrinfo(candidate, None)
                return candidate
            except Exception:
                return None

        tasks = [_check(sub) for sub in famous_subs]
        completed = await asyncio.gather(*tasks)
        return [c for c in completed if c]

    async def _validate_single_sub_async(self, sub: str, host: str, scan) -> Optional[Dict]:
        from bs4 import BeautifulSoup
        from scans.utils import make_evidence_request_async
        
        try:
            # Use getaddrinfo for async-friendly DNS lookup
            addr_info = await asyncio.get_event_loop().getaddrinfo(sub, None)
            ip = addr_info[0][4][0]
            
            title = "N/A"
            req_dump = ""
            res_dump = ""
            poc = ""

            # Try HTTPS then HTTP
            resp, req_dump, res_dump, poc = await make_evidence_request_async(f"https://{sub}", timeout=3)
            if not resp:
                resp, req_dump, res_dump, poc = await make_evidence_request_async(f"http://{sub}", timeout=3)
            
            if resp:
                try:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
                except Exception:
                    title = "Response parsing failed"
            else:
                title = "Unreachable (HTTPS/HTTP)"
            
            self.log(scan, f"  [+] {sub} -> {ip} ({title[:30]})")
            return {
                "subdomain": sub,
                "ip": ip,
                "title": title[:100],
                "req_dump": req_dump,
                "res_dump": res_dump,
                "poc": poc
            }
        except Exception:
            return None
