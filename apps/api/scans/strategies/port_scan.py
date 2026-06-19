import logging
import subprocess
import os
import xml.etree.ElementTree as ET
import tempfile
import socket
import re
import asyncio
from typing import List, Optional, AsyncGenerator

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity
from ..utils import make_evidence_request_async

logger = logging.getLogger(__name__)

# Comprehensive port configuration for severity mapping and fallback scanning
PORT_CONFIG = {
    21:    {"service": "FTP",             "severity": Severity.HIGH},
    22:    {"service": "SSH",             "severity": Severity.INFO},
    23:    {"service": "Telnet",          "severity": Severity.HIGH},
    25:    {"service": "SMTP",            "severity": Severity.INFO},
    53:    {"service": "DNS",             "severity": Severity.INFO},
    69:    {"service": "TFTP",            "severity": Severity.MEDIUM},
    80:    {"service": "HTTP",            "severity": Severity.INFO},
    110:   {"service": "POP3",            "severity": Severity.INFO},
    111:   {"service": "RPC",             "severity": Severity.MEDIUM},
    139:   {"service": "NetBIOS",         "severity": Severity.HIGH},
    143:   {"service": "IMAP",            "severity": Severity.INFO},
    161:   {"service": "SNMP",            "severity": Severity.HIGH},
    389:   {"service": "LDAP",            "severity": Severity.MEDIUM},
    443:   {"service": "HTTPS",           "severity": Severity.INFO},
    445:   {"service": "SMB",             "severity": Severity.CRITICAL},
    465:   {"service": "SMTPS",           "severity": Severity.INFO},
    512:   {"service": "rexec",           "severity": Severity.HIGH},
    513:   {"service": "rlogin",          "severity": Severity.HIGH},
    514:   {"service": "rsh",             "severity": Severity.HIGH},
    636:   {"service": "LDAPS",           "severity": Severity.INFO},
    873:   {"service": "rsync",           "severity": Severity.MEDIUM},
    993:   {"service": "IMAPS",           "severity": Severity.INFO},
    995:   {"service": "POP3S",           "severity": Severity.INFO},
    1433:  {"service": "MSSQL",           "severity": Severity.HIGH},
    1521:  {"service": "Oracle",          "severity": Severity.HIGH},
    2049:  {"service": "NFS",             "severity": Severity.HIGH},
    2375:  {"service": "Docker-API",      "severity": Severity.CRITICAL},
    2376:  {"service": "Docker-TLS",      "severity": Severity.HIGH},
    3306:  {"service": "MySQL",           "severity": Severity.HIGH},
    3389:  {"service": "RDP",             "severity": Severity.CRITICAL},
    4369:  {"service": "RabbitMQ-epmd",   "severity": Severity.MEDIUM},
    5432:  {"service": "PostgreSQL",      "severity": Severity.HIGH},
    5672:  {"service": "RabbitMQ",        "severity": Severity.MEDIUM},
    5900:  {"service": "VNC",             "severity": Severity.HIGH},
    6379:  {"service": "Redis",           "severity": Severity.CRITICAL},
    7001:  {"service": "WebLogic",        "severity": Severity.HIGH},
    8080:  {"service": "HTTP-Alt",        "severity": Severity.INFO},
    8443:  {"service": "HTTPS-Alt",       "severity": Severity.INFO},
    8888:  {"service": "Jupyter",         "severity": Severity.HIGH},
    9000:  {"service": "SonarQube/PHP-FPM", "severity": Severity.MEDIUM},
    9200:  {"service": "Elasticsearch",   "severity": Severity.CRITICAL},
    9300:  {"service": "Elasticsearch-TCP","severity": Severity.HIGH},
    11211: {"service": "Memcached",       "severity": Severity.HIGH},
    15672: {"service": "RabbitMQ-Mgmt",   "severity": Severity.MEDIUM},
    27017: {"service": "MongoDB",         "severity": Severity.CRITICAL},
    27018: {"service": "MongoDB-Shard",   "severity": Severity.HIGH},
    50000: {"service": "DB2",             "severity": Severity.HIGH},
}

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

    async def run_async(self, target: "ScanTarget", scan: "Scan" = None) -> AsyncGenerator[FindingData, None]:
        host = target.host

        # 1. Try Nmap first
        if self._is_tool_installed("nmap"):
            self.log(scan, "Nmap detected. Starting professional scan...")
            async for finding in self._run_nmap_async(host, scan):
                yield finding
            return

        # 2. Fallback to basic socket scan if Nmap fails or is missing
        self.log(scan, "Nmap not available. Falling back to basic TCP scan...")
        async for finding in self._run_socket_fallback_async(host, scan):
            yield finding

    async def _run_nmap_async(self, host: str, scan: "Scan") -> AsyncGenerator[FindingData, None]:
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tf:
            output_file = tf.name

        try:
            # -sV: Version detection, -Pn: Skip ping, -T4: Faster
            args = ["-sV", "-T4", "-Pn", "-oX", output_file]
            
            if scan and scan.scan_type == "full":
                # Full scan: ports 1-10000 + critical high-value ports above 10000
                critical_high = "27017,27018,50000,11211,15672"
                args.extend(["-p", f"1-10000,{critical_high}", "-sC"])
            elif scan and scan.scan_type == "quick":
                args.extend(["--top-ports", "100"])
            else:
                args.extend(["--top-ports", "500"])

            if ":" in host: args.append("-6")

            self.log(scan, f"Running: nmap {' '.join(args)} {host}")
            
            process = await asyncio.create_subprocess_exec(
                "nmap", *args, host,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(process.wait(), timeout=600)
            
            if os.path.exists(output_file):
                async for finding in self._parse_nmap_xml_async(output_file, host, scan):
                    yield finding
                
        except asyncio.TimeoutError:
            self.log(scan, "Nmap scan timed out.")
        except Exception as e:
            logger.error("Nmap scan error: %s", e)
            self.log(scan, f"Nmap error: {str(e)}")
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    async def _parse_nmap_xml_async(self, xml_file: str, host: str, scan: "Scan") -> AsyncGenerator[FindingData, None]:
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for host_node in root.findall("host"):
                # OS Fingerprint
                os_match = host_node.find("os/osmatch")
                if os_match is not None:
                    yield FindingData(
                        title="OS Fingerprint Detected",
                        description=f"Nmap identified the target OS as: {os_match.get('name')}",
                        severity=Severity.INFO,
                        evidence={"os": os_match.get("name"), "accuracy": os_match.get("accuracy")},
                        plugin_slug=self.slug
                    )

                # Ports
                for port_node in host_node.findall("ports/port"):
                    state_node = port_node.find("state")
                    if state_node is None or state_node.get("state") != "open":
                        continue

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
                        extra_evidence, req_dump, res_dump, poc_curl = await self._enrich_http_service_async(host, port_id)

                    if product and version:
                        # Heuristic CVE Link
                        cve_search = f"https://cve.mitre.org/cgi-bin/cvekey.cgi?keyword={product.replace(' ', '+')}+{version}"
                        extra_evidence["cve_search_url"] = cve_search

                    proof = f"Port {port_id} responded to connection."
                    if product: proof += f" Service identified: `{product} {version}`."
                    if extra_evidence.get("http_title"): proof += f" HTTP Title: `{extra_evidence['http_title']}`."

                    yield FindingData(
                        title=f"Open Port: {port_id}/{protocol} ({service_name})",
                        description=(
                            f"Port {port_id} is open and active on the target host.\n\n"
                            f"**REAL DATA PROOF**: {proof}"
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
                    )
        except Exception as e:
            logger.error("XML Parsing error: %s", e)

    def _get_port_severity(self, port: int, service: str) -> Severity:
        if port in PORT_CONFIG:
            return PORT_CONFIG[port]["severity"]
        
        # Heuristic for unknown ports
        if service.lower() in ["mysql", "postgresql", "redis", "mongodb"]:
            return Severity.CRITICAL
        
        return Severity.INFO

    async def _enrich_http_service_async(self, host: str, port: str):
        """Helper to get HTTP title and request/response evidence asynchronously."""
        from bs4 import BeautifulSoup
        
        extra_evidence = {}
        req_dump = ""
        res_dump = ""
        poc_curl = ""
        
        scheme = "https" if port in ["443", "8443"] else "http"
        url = f"{scheme}://{host}:{port}"
        
        response, req_dump, res_dump, poc_curl = await make_evidence_request_async(url, timeout=5)
        if response:
            try:
                soup = BeautifulSoup(response.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
                extra_evidence["http_title"] = title
            except Exception:
                pass
        
        return extra_evidence, req_dump, res_dump, poc_curl

    async def _run_socket_fallback_async(self, host: str, scan: "Scan") -> AsyncGenerator[FindingData, None]:
        severity_map = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO
        }
        
        semaphore = asyncio.Semaphore(20)

        async def _check_and_enrich(port, service, severity):
            async with semaphore:
                is_open = await self._async_check_port(host, port)
                if not is_open:
                    return None
                extra_evidence = {}
                req_dump = ""
                res_dump = ""
                poc = f"nc -zv {host} {port}"

                # Try HTTP enrichment for common web ports
                if port in [80, 443, 8080, 8443]:
                    extra_evidence, req_dump, res_dump, poc_curl = await self._enrich_http_service_async(host, str(port))
                    if poc_curl:
                        poc = poc_curl

                proof = f"Direct TCP connection to port {port} established."
                if extra_evidence.get("http_title"):
                    proof += f" HTTP Title detected: `{extra_evidence['http_title']}`."

                return FindingData(
                    title=f"Open Port (Fallback): {port}/{service}",
                    description=(
                        f"Port {port} ({service}) was found open via direct TCP connection.\n\n"
                        f"**REAL DATA PROOF**: {proof}"
                    ),
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
                )

        tasks = [
            asyncio.create_task(_check_and_enrich(port, cfg["service"], cfg["severity"])) 
            for port, cfg in PORT_CONFIG.items()
        ]
        
        for task in asyncio.as_completed(tasks):
            finding = await task
            if finding:
                yield finding

    async def _async_check_port(self, host: str, port: int, timeout: float = 2.0) -> bool:
        try:
            conn = asyncio.open_connection(host, port)
            _, writer = await asyncio.wait_for(conn, timeout=timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Verify by trying to connect to the port again and updating evidence asynchronously.
        """
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
        port = evidence.get("port")
        if not port:
            return False
        
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        host = target.host
        is_open = await self._async_check_port(host, int(port))
        
        if is_open:
            # If it's a web port, also try to fetch the page again for enriched evidence
            if str(port) in ["80", "443", "8080", "8443"] or "http" in str(evidence.get("service", "")).lower():
                extra, req, res, poc = await self._enrich_http_service_async(host, str(port))
                if req and res:
                    finding.request = req
                    finding.response = res
                    if poc:
                        finding.poc = poc
                    # Update title if found
                    if "http_title" in extra:
                        finding.evidence["http_title"] = extra["http_title"]
            
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
        
        return False

    def _is_tool_installed(self, name: str) -> bool:
        try:
            subprocess.run([name, "--version"], capture_output=True, check=False)
            return True
        except FileNotFoundError:
            return False

