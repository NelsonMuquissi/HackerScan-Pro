import subprocess
import logging
import re
from typing import List

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class DNSAuditStrategy(BaseScanStrategy):
    """
    DNS Security Audit Strategy.
    Checks for:
    - DNS Zone Transfer (AXFR)
    - Name Server discovery
    - Common DNS records analysis
    """
    slug = "dns_audit"
    name = "DNS Security Audit"
    description = "Analyzes DNS records and attempts zone transfers to identify information disclosure."

    def run(self, target, scan=None) -> List[FindingData]:
        if target.target_type != "domain":
            self.log(scan, "Target is not a domain, skipping DNS audit.")
            return []

        domain = target.host
        findings = []

        self.log(scan, f"Starting DNS audit for {domain}...")

        # 1. Get Name Servers
        ns_servers = self._get_name_servers(domain, scan)
        if not ns_servers:
            self.log(scan, "No name servers found.")
            return []

        # 2. Attempt AXFR on each NS
        for ns in ns_servers:
            self.log(scan, f"Attempting zone transfer (AXFR) on {ns}...")
            axfr_findings = self._attempt_axfr(domain, ns, scan)
            findings.extend(axfr_findings)

        # 3. Basic Record Analysis (TXT, MX)
        findings.extend(self._analyze_txt_records(domain, scan))

        return findings

    def _get_name_servers(self, domain: str, scan) -> List[str]:
        try:
            cmd = ["dig", "+short", "NS", domain]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            servers = [s.strip() for s in result.stdout.splitlines() if s.strip()]
            # Remove trailing dots
            return [s[:-1] if s.endswith(".") else s for s in servers]
        except Exception as e:
            logger.error(f"Error getting NS: {e}")
            return []

    def _attempt_axfr(self, domain: str, ns: str, scan) -> List[FindingData]:
        findings = []
        try:
            cmd = ["dig", "AXFR", f"@{ns}", domain]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=20)
            
            output = result.stdout
            # If AXFR was successful, it will contain many records and "Transfer completed"
            if "Transfer failed" not in output and len(output.splitlines()) > 10:
                findings.append(FindingData(
                    title="DNS Zone Transfer (AXFR) Possible",
                    description=(
                        f"The name server {ns} allowed a full zone transfer for {domain}. "
                        "This leaks all subdomains and internal IP addresses."
                    ),
                    severity=Severity.HIGH,
                    evidence={"ns": ns, "output_preview": output[:1000]},
                    plugin_slug=self.slug,
                    remediation="Configure the name server to disallow AXFR requests except from trusted slave servers."
                ))
        except Exception as e:
            logger.error(f"AXFR error: {e}")
        return findings

    def _analyze_txt_records(self, domain: str, scan) -> List[FindingData]:
        findings = []
        try:
            cmd = ["dig", "+short", "TXT", domain]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=10)
            records = result.stdout.splitlines()
            
            for record in records:
                # Check for SPF issues
                if "v=spf1" in record:
                    if "~all" in record or "?all" in record:
                        findings.append(FindingData(
                            title="Weak SPF Policy",
                            description=f"SPF record '{record}' uses a softfail (~all) or neutral (?all) policy.",
                            severity=Severity.LOW,
                            evidence={"record": record},
                            plugin_slug=self.slug,
                            remediation="Change the SPF policy to -all (hardfail) for better spoofing protection."
                        ))
                
                # Check for exposed services in TXT (e.g. verification tokens)
                if any(x in record for x in ["google-site-verification", "msVerify", "facebook-domain-verification"]):
                    findings.append(FindingData(
                        title="DNS Verification Token Exposed",
                        description=f"Found a site verification token in DNS: {record}",
                        severity=Severity.INFO,
                        evidence={"record": record},
                        plugin_slug=self.slug
                    ))
        except Exception as e:
            logger.error(f"TXT analysis error: {e}")
        return findings
    def verify(self, finding: "Finding") -> bool:
        """
        Verify DNS findings by re-running the specific dig command.
        """
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
            
        domain = finding.scan.target.host
        
        # Determine what to verify based on title or evidence
        if "AXFR" in finding.title:
            ns = evidence.get("ns")
            if not ns: return False
            results = self._attempt_axfr(domain, ns, None)
            return len(results) > 0
            
        elif "SPF" in finding.title or "Verification Token" in finding.title:
            results = self._analyze_txt_records(domain, None)
            # Check if any result has the same title
            return any(r.title == finding.title for r in results)
            
        return False
