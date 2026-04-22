import logging
import subprocess
import os
import xml.etree.ElementTree as ET
import tempfile
import socket
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


def _check_port(host: str, port: int, timeout: float = TIMEOUT) -> bool:
    """Returns True if TCP connection succeeds (Fallback)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError, TimeoutError):
        return False


@register
class PortScanStrategy(BaseScanStrategy):
    """
    Advanced Port Scanner using Nmap (Zero Simulation).
    Features:
    - Service Version Detection (-sV)
    - OS Fingerprinting (-O)
    - Stealth Scan support
    - XML Parsing for high-fidelity results
    """
    slug = "port_scan"
    name = "Network & Port Discovery (Nmap)"
    description = "Master-level port scanning with service versioning and OS detection."

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
            # Base arguments
            # -sV: Service version detection
            # -T4: Faster execution
            # -Pn: Treat all hosts as online
            # -oX: XML output
            args = ["-sV", "-T4", "-Pn", "-oX", output_file]
            
            # 1. Determine port range and scan type based on ScanType
            if scan and scan.scan_type == "full":
                self.log(scan, "Full scan requested: scanning all 65535 ports...")
                args.extend(["-p-", "-sS", "-sU"]) # SYN + UDP (requires root for -sS and -sU)
            elif scan and scan.scan_type == "quick":
                args.extend(["--top-ports", "1000"])
            else:
                args.extend(["--top-ports", "2000"])

            # 2. Add OS Detection
            args.append("-O")

            # 3. Handle IPv6
            if ":" in host:
                args.append("-6")

            cmd = ["nmap"] + args + [host]
            
            # Note: On some systems, nmap -sS, -sU, and -O require sudo.
            # In a containerized scanner, we usually run as root.
            
            self.log(scan, f"Running: {' '.join(cmd)}")
            # Increased timeout for full scans
            timeout = 3600 if "-p-" in args else 600
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)

            if os.path.exists(output_file):
                findings = self._parse_nmap_xml(output_file, host)
        except Exception as e:
            logger.error("Nmap scan error: %s", e)
            self.log(scan, f"Nmap error: {str(e)}")
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

        return findings

    def _parse_nmap_xml(self, xml_file: str, host: str) -> List[FindingData]:
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for host_node in root.findall("host"):
                # Handle OS matches
                os_match = host_node.find("os/osmatch")
                if os_match is not None:
                    findings.append(FindingData(
                        title="OS Fingerprint Detected",
                        description=f"Nmap identified the target OS as: {os_match.get('name')}",
                        severity=Severity.INFO,
                        evidence={"os": os_match.get("name"), "accuracy": os_match.get("accuracy")},
                        plugin_slug=self.slug
                    ))

                # Handle Ports
                for port_node in host_node.findall("ports/port"):
                    state = port_node.find("state").get("state")
                    if state != "open":
                        continue

                    port_id = port_node.get("portid")
                    protocol = port_node.get("protocol")
                    service_node = port_node.find("service")
                    
                    service_name = "unknown"
                    product = ""
                    version = ""
                    if service_node is not None:
                        service_name = service_node.get("name", "unknown")
                        product = service_node.get("product", "")
                        version = service_node.get("version", "")

                    findings.append(FindingData(
                        title=f"Open Port: {port_id}/{protocol} ({service_name})",
                        description=(
                            f"Port {port_id} is open. Service: {service_name}. "
                            f"{f'Product: {product} {version}' if product else ''}"
                        ),
                        severity=self._get_port_severity(int(port_id), service_name),
                        evidence={
                            "port": port_id,
                            "protocol": protocol,
                            "service": service_name,
                            "product": product,
                            "version": version
                        },
                        plugin_slug=self.slug,
                        remediation="Verify if this port needs to be publicly accessible. Use a firewall to restrict access if not."
                    ))
        except Exception as e:
            logger.error("XML Parsing error: %s", e)
        return findings

    def _get_port_severity(self, port: int, service: str) -> Severity:
        critical_ports = {3389, 445, 139, 6379, 27017, 9200}
        high_ports = {21, 23, 3306, 5432, 1433, 1521, 5900}
        
        if port in critical_ports:
            return Severity.CRITICAL
        if port in high_ports or "telnet" in service.lower() or "ftp" in service.lower():
            return Severity.HIGH
        return Severity.INFO

    def _run_socket_fallback(self, host: str, scan) -> List[FindingData]:
        findings = []
        ports = DEFAULT_PORTS
        
        with ThreadPoolExecutor(max_workers=20) as pool:
            future_map = {pool.submit(_check_port, host, p[0]): p for p in ports}
            for future in as_completed(future_map):
                port, service, sev_str = future_map[future]
                if future.result():
                    findings.append(FindingData(
                        title=f"Open Port (Fallback): {port}/{service}",
                        description=f"Port {port} ({service}) was found open via direct TCP connection.",
                        severity=sev_str,
                        evidence={"port": port, "service": service, "method": "socket_fallback"},
                        plugin_slug=self.slug
                    ))
        return findings
indings
