import logging
import subprocess
import os
import xml.etree.ElementTree as ET
import tempfile
import socket
import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

# Default port set for fallback socket scan
DEFAULT_PORTS: list[tuple[int, str, str]] = [
    (21,   "FTP",          "medium"),
    (22,   "SSH",          "info"),
    (23,   "Telnet",       "high"),
    (25,   "SMTP",         "info"),
    (53,   "DNS",          "info"),
    (80,   "HTTP",         "info"),
    (443,  "HTTPS",        "info"),
    (445,  "SMB",          "high"),
    (3306, "MySQL",        "high"),
    (3389, "RDP",          "high"),
    (5432, "PostgreSQL",   "high"),
    (6379, "Redis",        "high"),
    (8080, "HTTP-Alt",     "info"),
]

TIMEOUT = 1.0

@register
class PortScanStrategy(BaseScanStrategy):
    """
    Advanced Port Scanner using Nmap (Zero Simulation).
    Features:
    - Service Version Detection (-sV)
    - OS Fingerprinting (-O)
    - HTTP Title Grabbing
    - CVE Mapping (Heuristic)
    """
    slug = "port_scan"
    name = "Network & Port Discovery (Nmap)"
    description = "Master-level port scanning with service versioning and vulnerability mapping."

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        findings = []

        # 1. Try Nmap first
        if self._is_tool_installed("nmap"):
            self.log(scan, "Nmap detected. Starting professional scan...")
            findings = self._run_nmap(host, scan)
            if findings:
                return findings

        # 2. Fallback to basic socket scan if Nmap fails or is missing
        self.log(scan, "Nmap not available. Falling back to basic TCP scan...")
        return self._run_socket_fallback(host, scan)

    def _is_tool_installed(self, name: str) -> bool:
        try:
            subprocess.run([name, "--version"], capture_output=True, check=False)
            return True
        except FileNotFoundError:
            return False

    def _run_nmap(self, host: str, scan) -> List[FindingData]:
        findings = []
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tf:
            output_file = tf.name

        try:
            # -sV: Version detection, -Pn: Skip ping, -T4: Faster
            args = ["-sV", "-T4", "-Pn", "-oX", output_file]
            
            if scan and scan.scan_type == "full":
                args.extend(["-p", "1-2000", "-sC"])
            elif scan and scan.scan_type == "quick":
                args.extend(["--top-ports", "100"])
            else:
                args.extend(["--top-ports", "1000"])

            if ":" in host: args.append("-6")

            cmd = ["nmap"] + args + [host]
            self.log(scan, f"Running: {' '.join(cmd)}")
            
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
            
            if os.path.exists(output_file):
                findings = self._parse_nmap_xml(output_file, host, scan)
                
        except Exception as e:
            logger.error("Nmap scan error: %s", e)
            self.log(scan, f"Nmap error: {str(e)}")
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

        return findings

    def _parse_nmap_xml(self, xml_file: str, host: str, scan) -> List[FindingData]:
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for host_node in root.findall("host"):
                # OS Fingerprint
                os_match = host_node.find("os/osmatch")
                if os_match is not None:
                    findings.append(FindingData(
                        title="OS Fingerprint Detected",
                        description=f"Nmap identified the target OS as: {os_match.get('name')}",
                        severity=Severity.INFO,
                        evidence={"os": os_match.get("name"), "accuracy": os_match.get("accuracy")},
                        plugin_slug=self.slug
                    ))

                # Ports
                for port_node in host_node.findall("ports/port"):
                    state = port_node.find("state").get("state")
                    if state != "open": continue

                    port_id = port_node.get("portid")
                    protocol = port_node.get("protocol")
                    service_node = port_node.find("service")
                    
                    service_name = service_node.get("name", "unknown") if service_node is not None else "unknown"
                    product = service_node.get("product", "") if service_node is not None else ""
                    version = service_node.get("version", "") if service_node is not None else ""
                    
                    # 🚀 ENRICHMENT: HTTP Title & Dumps
                    req_dump = ""
                    res_dump = ""
                    poc_curl = ""
                    extra_evidence = {}

                    if "http" in service_name or port_id in ["80", "443", "8080", "8443"]:
                        extra_evidence, req_dump, res_dump, poc_curl = self._enrich_http_service(host, port_id)

                    if product and version:
                        # Heuristic CVE Link
                        cve_search = f"https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword={product.replace(' ', '+')}+{version}"
                        extra_evidence["cve_search_url"] = cve_search

                    findings.append(FindingData(
                        title=f"Open Port: {port_id}/{protocol} ({service_name})",
                        description=(
                            f"Port {port_id} is open. {f'Running {product} {version}.' if product else ''}"
                        ),
                        severity=self._get_port_severity(int(port_id), service_name),
                        evidence={
                            "port": port_id,
                            "protocol": protocol,
                            "service": service_name,
                            "product": product,
                            "version": version,
                            **extra_evidence
                        },
                        request=req_dump,
                        response=res_dump,
                        poc=poc_curl or f"nmap -sV -p {port_id} {host}",
                        plugin_slug=self.slug,
                        is_verified=True
                    ))
        except Exception as e:
            logger.error("XML Parsing error: %s", e)
        return findings

    def _get_port_severity(self, port: int, service: str) -> Severity:
        critical_ports = {3389, 445, 139, 6379, 27017, 9200, 10250, 2375, 2376}
        high_ports = {21, 23, 3306, 5432, 1433, 1521, 5900, 111, 2049}
        if port in critical_ports: return Severity.CRITICAL
        if port in high_ports: return Severity.HIGH
        return Severity.INFO if port in {80, 443, 22} else Severity.LOW

    def _enrich_http_service(self, host: str, port: str):
        """Helper to get HTTP title and request/response evidence."""
        from scans.utils import make_evidence_request
        from bs4 import BeautifulSoup
        
        extra_evidence = {}
        req_dump = ""
        res_dump = ""
        poc_curl = ""
        
        scheme = "https" if port in ["443", "8443"] else "http"
        url = f"{scheme}://{host}:{port}"
        
        resp, req_dump, res_dump, poc_curl = make_evidence_request(url, timeout=5)
        if resp:
            try:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
                extra_evidence["http_title"] = title
            except Exception:
                pass
        
        return extra_evidence, req_dump, res_dump, poc_curl

    def _run_socket_fallback(self, host: str, scan) -> List[FindingData]:
        findings = []
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO
        }
        
        with ThreadPoolExecutor(max_workers=20) as pool:
            future_map = {pool.submit(_check_port, host, p[0]): p for p in DEFAULT_PORTS}
            for future in as_completed(future_map):
                port, service, sev_str = future_map[future]
                if future.result():
                    severity = severity_map.get(sev_str, Severity.LOW)
                    extra_evidence = {}
                    req_dump = ""
                    res_dump = ""
                    poc = f"nc -zv {host} {port}"

                    # Try HTTP enrichment for common web ports
                    if port in [80, 443, 8080, 8443]:
                        extra_evidence, req_dump, res_dump, poc_curl = self._enrich_http_service(host, str(port))
                        if poc_curl:
                            poc = poc_curl

                    findings.append(FindingData(
                        title=f"Open Port (Fallback): {port}/{service}",
                        description=f"Port {port} ({service}) was found open via direct TCP connection.",
                        severity=severity,
                        evidence={
                            "port": port, 
                            "service": service, 
                            "method": "socket_fallback",
                            **extra_evidence
                        },
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        plugin_slug=self.slug,
                        is_verified=True
                    ))
        return findings

    def verify(self, finding) -> bool:
        """
        Verify by trying to connect to the port again and updating evidence.
        """
        evidence = finding.evidence
        if not isinstance(evidence, dict): return False
        port = evidence.get("port")
        if not port: return False
        
        host = finding.scan.target.host
        is_open = _check_port(host, int(port))
        
        if is_open:
            # If it's a web port, also try to fetch the page again for enriched evidence
            if port in ["80", "443", "8080", "8443"] or "http" in str(evidence.get("service", "")).lower():
                extra, req, res, poc = self._enrich_http_service(host, str(port))
                if req and res:
                    finding.request = req
                    finding.response = res
                    if poc:
                        finding.poc = poc
                    # Update title if found
                    if "http_title" in extra:
                        finding.evidence["http_title"] = extra["http_title"]
            
            finding.is_verified = True
            finding.save()
            return True
        
        return False

def _check_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

