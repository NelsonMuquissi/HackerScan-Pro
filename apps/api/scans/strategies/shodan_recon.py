import logging
import os
import requests
import socket
import urllib.parse
from typing import List, Optional

from .base import BaseScanStrategy, FindingData, register

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


    def run(self, target: "ScanTarget", scan: "Scan") -> List[FindingData]:
        findings = []
        api_key = os.environ.get("SHODAN_API_KEY")
        
        if not api_key:
            logger.warning("SHODAN_API_KEY not set. Shodan reconnaissance will be skipped.")
            findings.append(FindingData(
                title="Shodan Scan Skipped",
                description="SHODAN_API_KEY is not configured in the environment.",
                severity="INFO",
                category="OSINT Reconnaissance",
                evidence={"reason": "Missing API Key"},
                confidence=100
            ))
            return findings

        target_host = target.host
        parsed = urllib.parse.urlparse(target_host)
        host = parsed.netloc.split(":")[0] if parsed.netloc else target_host.split(":")[0]
        
        try:
            # Resolve to IP since Shodan works best with IPs
            ip_address = socket.gethostbyname(host)
            logger.info(f"Resolved {host} to {ip_address} for Shodan lookup.")
            
            url = f"https://api.shodan.io/shodan/host/{ip_address}?key={api_key}"
            resp = requests.get(url, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                ports = data.get("ports", [])
                vulns = data.get("vulns", [])
                org = data.get("org", "Unknown")
                
                if ports:
                    findings.append(FindingData(
                        title=f"Shodan Intelligence: Open Ports on {ip_address}",
                        description=f"Shodan reports the following open ports for organization '{org}': {', '.join(map(str, ports))}",
                        severity="INFO",
                        category="OSINT Reconnaissance",
                        evidence={"ports": ports, "org": org, "ip": ip_address},
                        confidence=100
                    ))
                    
                for vuln in vulns:
                    findings.append(FindingData(
                        title=f"Shodan CVE Intelligence: {vuln}",
                        description=f"Shodan indicates {ip_address} is vulnerable to {vuln}.",
                        severity="HIGH", # Shodan vulns are generally serious
                        category="Vulnerability Intelligence",
                        evidence={"cve": vuln, "ip": ip_address},
                        confidence=80 # High but not 100 since Shodan caches state
                    ))
            elif resp.status_code == 404:
                findings.append(FindingData(
                    title="Shodan Intelligence: No Data",
                    description=f"Shodan does not have any records for {ip_address}.",
                    severity="INFO",
                    category="OSINT Reconnaissance",
                    evidence={"ip": ip_address},
                    confidence=100
                ))
            else:
                logger.warning(f"Shodan API returned status code {resp.status_code}")
                
        except socket.gaierror:
            logger.error(f"Could not resolve host {host} for Shodan lookup.")
        except requests.RequestException as e:
            logger.error(f"Shodan API request failed: {e}")
            
        return findings
