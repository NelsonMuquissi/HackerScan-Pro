import logging
import subprocess
import json
import tempfile
import os
import httpx
from typing import List, Set
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

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
    """
    slug = "subdomain_recon"
    name = "Subdomain & Asset Recon"

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        # Use a set to avoid duplicates
        subdomains: Set[str] = set()

        # 1. Try Subfinder
        self.log(scan, f"Running Subfinder on {host}...")
        subfinder_results = self._run_subfinder(host)
        subdomains.update(subfinder_results)

        # 2. Try Amass (Deep)
        self.log(scan, f"Running Amass deep enum on {host}...")
        amass_results = self._run_amass(host)
        subdomains.update(amass_results)

        # 3. Try crt.sh (Certificate Transparency)
        self.log(scan, f"Querying Certificate Transparency logs for {host}...")
        crt_results = self._get_crt_sh_subdomains(host)
        subdomains.update(crt_results)

        # 4. Try Gau (Historical)
        self.log(scan, f"Fetching historical endpoints via Gau for {host}...")
        gau_results = self._run_gau(host)
        subdomains.update(gau_results)

        # 5. Fallback if still empty
        if not subdomains:
            self.log(scan, "No subdomains found via tools. Running emergency DNS brute force...")
            subdomains.update(self._run_dns_bruteforce(host))

        if not subdomains:
            return []

        # 6. Validate findings (Live Check)
        self.log(scan, f"Validating {len(subdomains)} candidates...")
        active_findings = self._validate_subdomains(list(subdomains), host)

        findings = [FindingData(
            title=f"Discovered {len(subdomains)} Assets/Subdomains",
            description=f"Automated recon identified these assets for {host}. Includes CRT transparency logs and active discovery.",
            severity=Severity.INFO,
            evidence="\n".join(active_findings),
            remediation="Review discovered assets for legacy environments or shadow IT.",
            plugin_slug=self.slug
        )]

        return findings

    def _run_subfinder(self, host: str) -> List[str]:
        results = []
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
            output_file = tf.name
        try:
            cmd = ["subfinder", "-d", host, "-o", output_file, "-silent"]
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    results = [line.strip() for line in f if line.strip()]
        except Exception as e:
            logger.warning("Subfinder failed: %s", e)
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)
        return results

    def _run_amass(self, host: str) -> List[str]:
        results = []
        try:
            # -passive: Fast mode without active DNS resolution/brute
            cmd = ["amass", "enum", "-passive", "-d", host, "-silent"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
            if proc.stdout:
                results = [line.strip() for line in proc.stdout.split("\n") if line.strip()]
        except Exception as e:
            logger.warning("Amass failed: %s", e)
        return results

    def _run_gau(self, host: str) -> List[str]:
        results = []
        try:
            cmd = ["gau", host, "--subs", "--threads", "10"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            if proc.stdout:
                # Gau returns URLs, we need to extract hostnames
                from urllib.parse import urlparse
                for line in proc.stdout.split("\n"):
                    line = line.strip()
                    if not line: continue
                    # line might be "sub.domain.com/path" or "http://sub.domain.com"
                    if not line.startswith(("http://", "https://")):
                        line = "http://" + line
                    parsed = urlparse(line)
                    hostname = parsed.hostname
                    if hostname and hostname.endswith(host):
                        results.append(hostname)
        except Exception as e:
            logger.warning("Gau failed: %s", e)
        return list(set(results))

    def _get_crt_sh_subdomains(self, domain: str) -> List[str]:
        """Query crt.sh for subdomains found in certificates."""
        results = []
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            response = httpx.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for entry in data:
                    name_value = entry.get("name_value", "")
                    # crt.sh can return multiple names per entry (separated by \n)
                    for name in name_value.split("\n"):
                        name = name.strip().lower()
                        if name.endswith(domain) and "*" not in name:
                            results.append(name)
        except Exception as e:
            logger.error("crt.sh error: %s", e)
        return list(set(results))

    def _run_dns_bruteforce(self, host: str) -> List[str]:
        famous_subs = ["www", "mail", "dev", "api", "admin", "app", "vpn", "test", "demo", "portal"]
        results = []
        import socket
        for sub in famous_subs:
            candidate = f"{sub}.{host}"
            try:
                socket.gethostbyname(candidate)
                results.append(candidate)
            except socket.gaierror:
                continue
        return results

    def _validate_subdomains(self, subdomains: List[str], host: str) -> List[str]:
        import socket
        validated = []
        # Limit to top 100 for performance
        for sub in sorted(subdomains)[:100]:
            try:
                ip = socket.gethostbyname(sub)
                validated.append(f"{sub} ({ip}) [ACTIVE]")
            except socket.gaierror:
                validated.append(f"{sub} [DNS ONLY]")
        return validated
