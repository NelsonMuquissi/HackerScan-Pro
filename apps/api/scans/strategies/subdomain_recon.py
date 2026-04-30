import logging
import subprocess
import json
import tempfile
import os
import httpx
from typing import List, Set, Dict
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

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        subdomains: Set[str] = set()

        # 1. Try Subfinder
        self.log(scan, f"Running Subfinder on {host}...")
        subdomains.update(self._run_subfinder(host))

        # 2. Try crt.sh (Always works, very fast)
        self.log(scan, f"Querying Certificate Transparency logs for {host}...")
        subdomains.update(self._get_crt_sh_subdomains(host))

        # 3. Try Amass (Deep)
        self.log(scan, f"Running Amass passive enum on {host}...")
        subdomains.update(self._run_amass(host))

        # 4. Try Gau (Historical)
        self.log(scan, f"Fetching historical endpoints via Gau for {host}...")
        subdomains.update(self._run_gau(host))

        # 5. Fallback if still empty
        if not subdomains:
            self.log(scan, "No subdomains found via passive tools. Running emergency DNS brute force...")
            subdomains.update(self._run_dns_bruteforce(host))

        if not subdomains:
            return []

        # 6. Validate findings & Grab Titles (The "Proof")
        self.log(scan, f"Validating {len(subdomains)} candidates and grabbing HTTP titles...")
        assets = self._validate_and_fingerprint(list(subdomains), host, scan)

        if not assets:
            return []

        # Categorize for the finding
        high_value = [a for a in assets if any(kw in a['subdomain'].lower() for kw in HIGH_VALUE_KEYWORDS)]
        
        finding_desc = f"Automated reconnaissance discovered {len(assets)} active subdomains/assets for {host}."
        if high_value:
            finding_desc += "\n\n### High-Value Assets Detected:\n" + "\n".join([f"- {a['subdomain']} ({a['ip']})" for a in high_value[:5]])

        # We take the first active asset as a "representative" for the request/response evidence
        primary_asset = high_value[0] if high_value else assets[0]

        findings = [FindingData(
            title=f"Subdomain Discovery: {len(assets)} Active Assets Found",
            description=finding_desc,
            severity=Severity.HIGH if high_value else Severity.INFO,
            evidence={
                "assets": assets[:100], # Limit UI payload
                "total_count": len(assets),
                "primary_host": primary_asset["subdomain"]
            },
            remediation="1. Review discovered subdomains for unauthorized or legacy environments (Shadow IT).\n2. Decommission unused subdomains and DNS records (prevent Subdomain Takeover).\n3. Ensure all discovered assets are covered by standard security monitoring.",
            plugin_slug=self.slug,
            request=primary_asset.get("req_dump", ""),
            response=primary_asset.get("res_dump", ""),
            poc=primary_asset.get("poc", f"subfinder -d {host} -silent"),
            is_verified=True
        )]

        return findings

    def verify(self, finding: "Finding") -> bool:
        """Verify by checking if at least one of the discovered subdomains still resolves and responds."""
        from scans.utils import make_evidence_request
        
        assets = finding.evidence.get("assets", [])
        if not assets:
            primary = finding.evidence.get("primary_host")
            if primary:
                assets = [{"subdomain": primary}]
            else:
                return False

        # Check up to 3 subdomains for verification
        for asset in assets[:3]:
            sub = asset.get("subdomain")
            if not sub: continue
            
            try:
                # Try HTTPS then HTTP
                resp, req, res, poc = make_evidence_request(f"https://{sub}", timeout=5)
                if not resp:
                    resp, req, res, poc = make_evidence_request(f"http://{sub}", timeout=5)
                
                if resp:
                    # Update the finding with fresh dumps from one successful check
                    finding.request = req
                    finding.response = res
                    finding.poc = poc
                    return True
            except Exception:
                continue
        return False

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
        except Exception:
            pass
        finally:
            if os.path.exists(output_file): os.remove(output_file)
        return results

    def _run_amass(self, host: str) -> List[str]:
        results = []
        try:
            cmd = ["amass", "enum", "-passive", "-d", host, "-silent"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
            if proc.stdout:
                results = [line.strip() for line in proc.stdout.split("\n") if line.strip()]
        except Exception:
            pass
        return results

    def _run_gau(self, host: str) -> List[str]:
        results = set()
        try:
            cmd = ["gau", host, "--subs", "--threads", "5"]
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            if proc.stdout:
                from urllib.parse import urlparse
                for line in proc.stdout.split("\n"):
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

    def _get_crt_sh_subdomains(self, domain: str) -> List[str]:
        results = set()
        try:
            url = f"https://crt.sh/?q=%.{domain}&output=json"
            response = httpx.get(url, timeout=20)
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

    def _run_dns_bruteforce(self, host: str) -> List[str]:
        famous_subs = ["www", "mail", "dev", "api", "admin", "app", "vpn", "test", "demo", "portal", "staging"]
        results = []
        import socket
        for sub in famous_subs:
            candidate = f"{sub}.{host}"
            try:
                socket.gethostbyname(candidate)
                results.append(candidate)
            except Exception:
                continue
        return results

    def _validate_and_fingerprint(self, subdomains: List[str], host: str, scan) -> List[Dict]:
        import socket
        from bs4 import BeautifulSoup
        from scans.utils import make_evidence_request
        assets = []
        
        # Limit to top 50 for performance
        seen = set()
        unique_subs = [s for s in subdomains if not (s in seen or seen.add(s))]
        
        for sub in unique_subs[:50]:
            try:
                ip = socket.gethostbyname(sub)
                title = "N/A"
                req_dump = ""
                res_dump = ""
                poc = ""

                # Try HTTPS then HTTP
                resp, req_dump, res_dump, poc = make_evidence_request(f"https://{sub}", timeout=3)
                if not resp:
                    resp, req_dump, res_dump, poc = make_evidence_request(f"http://{sub}", timeout=3)
                
                if resp:
                    try:
                        soup = BeautifulSoup(resp.text, "html.parser")
                        title = soup.title.string.strip() if soup.title else "No Title"
                    except Exception:
                        title = "Response parsing failed"
                else:
                    title = "Unreachable (HTTPS/HTTP)"
                
                assets.append({
                    "subdomain": sub,
                    "ip": ip,
                    "title": title[:100],
                    "req_dump": req_dump,
                    "res_dump": res_dump,
                    "poc": poc
                })
                self.log(scan, f"  [+] {sub} -> {ip} ({title[:30]})")
            except Exception:
                continue
        return assets
