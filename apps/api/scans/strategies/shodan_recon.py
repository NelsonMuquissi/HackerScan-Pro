import logging
import os
import asyncio
import socket
import urllib.parse
from typing import List, Optional, AsyncGenerator

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity
from ..utils import make_evidence_request_async

logger = logging.getLogger(__name__)


@register
class ShodanReconStrategy(BaseScanStrategy):
    """
    ShodanReconStrategy queries the Shodan REST API for intelligence about the target host.
    Requires SHODAN_API_KEY environment variable.
    """
    name = "Shodan Reconnaissance"
    slug = "shodan_recon"
    description = "Queries Shodan API for OSINT and vulnerabilities."

    async def run_async(self, target: "ScanTarget", scan: "Scan") -> AsyncGenerator[FindingData, None]:
        api_key = os.environ.get("SHODAN_API_KEY")
        
        if not api_key:
            self.log(scan, "SHODAN_API_KEY not set. Skipping Shodan reconnaissance.")
            yield FindingData(
                title="Shodan Scan Skipped",
                description="SHODAN_API_KEY is not configured in the environment.\n\n**REAL DATA PROOF**: API key missing in scanner environment.",
                severity=Severity.INFO,
                category="OSINT Reconnaissance",
                evidence={"reason": "Missing API Key"},
                confidence=100
            )
            return

        target_host = target.host
        parsed = urllib.parse.urlparse(target_host)
        host = parsed.netloc.split(":")[0] if parsed.netloc else target_host.split(":")[0]
        
        try:
            # Resolve to IP since Shodan works best with IPs
            self.log(scan, f"Resolving {host} to IP address...")
            loop = asyncio.get_event_loop()
            addrinfo = await loop.getaddrinfo(host, None)
            ip_address = addrinfo[0][4][0]
            
            self.log(scan, f"Shodan lookup for {ip_address}...")
            url = f"https://api.shodan.io/shodan/host/{ip_address}?key={api_key}"
            
            response, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=15)
            
            if response and response.status_code == 200:
                data = response.json()
                ports = data.get("ports", [])
                vulns = data.get("vulns", [])
                org = data.get("org", "Unknown")
                
                if ports:
                    yield FindingData(
                        title=f"Shodan Intelligence: Open Ports on {ip_address}",
                        description=(
                            f"Shodan reports the following open ports for organization '{org}': {', '.join(map(str, ports))}.\n\n"
                            f"**REAL DATA PROOF**: Shodan API returned live scan data for `{ip_address}`."
                        ),
                        severity=Severity.INFO,
                        category="OSINT Reconnaissance",
                        evidence={"ports": ports, "org": org, "ip": ip_address},
                        confidence=100,
                        request=req_dump,
                        response=res_dump,
                        poc=poc
                    )
                    
                for vuln in vulns:
                    yield FindingData(
                        title=f"Shodan CVE Intelligence: {vuln}",
                        description=(
                            f"Shodan indicates {ip_address} is vulnerable to {vuln}.\n\n"
                            f"**REAL DATA PROOF**: CVE {vuln} flagged by Shodan's vulnerability database."
                        ),
                        severity=Severity.HIGH,
                        category="Vulnerability Intelligence",
                        evidence={"cve": vuln, "ip": ip_address},
                        confidence=80,
                        request=req_dump,
                        response=res_dump,
                        poc=poc
                    )
            elif response and response.status_code == 404:
                yield FindingData(
                    title="Shodan Intelligence: No Data",
                    description=(
                        f"Shodan does not have any records for {ip_address}.\n\n"
                        f"**REAL DATA PROOF**: API response returned 404 (Not Found)."
                    ),
                    severity=Severity.INFO,
                    category="OSINT Reconnaissance",
                    evidence={"ip": ip_address},
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=poc
                )
            else:
                status = response.status_code if response else "Error"
                self.log(scan, f"Shodan API returned status code {status}")
                
        except (socket.gaierror, IndexError):
            self.log(scan, f"Could not resolve host {host} for Shodan lookup.")
            logger.error(f"Could not resolve host {host} for Shodan lookup.")
        except Exception as e:
            self.log(scan, f"Shodan API error: {str(e)}")
            logger.error(f"Shodan API request failed: {e}")

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Re-verify Shodan findings by querying the API again (async).
        """
        # Since Shodan is OSINT, verification means re-checking the data source
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        async for f in self.run_async(target, scan):
            if f.title == finding.title:
                finding.is_verified = True
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True
        return False
