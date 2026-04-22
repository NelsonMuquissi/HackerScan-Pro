"""
Tactical strategies for premium security modules.
Perform real network discovery and posture checks for specialized environments.
"""
import socket
from typing import List
from .base import BaseScanStrategy, FindingData, register

class NetworkDiscoveryMixin:
    """Helper for network-focused strategies."""
    def check_ports(self, host: str, ports: List[int], timeout: float = 1.0) -> List[int]:
        opened = []
        for port in ports:
            try:
                with socket.create_connection((host, port), timeout=timeout):
                    opened.append(port)
            except (OSError, ConnectionRefusedError, TimeoutError):
                continue
        return opened

@register
class ActiveDirectoryStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "ad_tactical"
    name = "AD Tactical Audit"
    description = "Discovers Active Directory infrastructure and insecure LDAP configurations."

    def run(self, target, scan) -> List[FindingData]:
        findings = []
        ad_ports = {
            389: "LDAP",
            636: "LDAPS",
            88: "Kerberos",
            445: "Microsoft-DS (SMB)",
            3268: "Global Catalog",
            3269: "Global Catalog SSL"
        }
        
        self.log(scan, f"Scanning for Active Directory endpoints on {target.host}...")
        opened = self.check_ports(target.host, list(ad_ports.keys()))
        
        if opened:
            findings.append(FindingData(
                severity="info",
                title="Active Directory Infrastructure Detected",
                description=f"Discovery identified Active Directory services on {target.host}. Ports recognized: {', '.join([f'{p} ({ad_ports[p]})' for p in opened])}.",
                evidence={"open_ports": opened},
                remediation="Ensure AD services are only accessible within the internal management network."
            ))
            
            if 389 in opened and 636 not in opened:
                findings.append(FindingData(
                    severity="medium",
                    title="Insecure LDAP Directory Service",
                    description="The server is exposing LDAP (389) without visible LDAPS (636).",
                    evidence="Port 389 open, port 636 closed/filtered.",
                    remediation="Enforce LDAP Signing and transition to LDAPS."
                ))
        
        return findings

@register
class KubernetesSecurityStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "k8s_hardening"
    name = "K8s Hardening Check"
    description = "Checks for exposed Kubernetes control plane and node components."

    def run(self, target, scan) -> List[FindingData]:
        findings = []
        k8s_ports = {
            6443: "Kubernetes API Server",
            10250: "Kubelet API",
            2379: "Etcd Client API",
            10255: "Read-only Kubelet"
        }
        
        self.log(scan, "Performing K8s control plane discovery...")
        opened = self.check_ports(target.host, list(k8s_ports.keys()))
        
        if opened:
            findings.append(FindingData(
                severity="high",
                title="Kubernetes Control Plane Exposed",
                description=f"Control plane components were detected on {target.host}.",
                evidence={"detected_ports": opened},
                remediation="Restrict k8s API access using network policies or firewall rules."
            ))
        
        return findings

@register
class SAPSpecializedStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "sap_recon"
    name = "SAP Ecosystem Recon"
    description = "Identifies SAP-specific services and potential gateway exposures."

    def run(self, target, scan) -> List[FindingData]:
        findings = []
        sap_ports = {
            3200: "SAP Dispatcher",
            3600: "SAP Message Server",
            3300: "SAP Gateway",
            3900: "SAP NI Broker",
            8000: "SAP Web Dispatcher (HTTP)"
        }
        
        self.log(scan, "Scanning for SAP application layer services...")
        opened = self.check_ports(target.host, list(sap_ports.keys()))
        
        if opened:
            findings.append(FindingData(
                severity="medium",
                title="SAP Specialized Environment Detected",
                description=f"Identified SAP-specific services on {target.host}.",
                evidence={"sap_ports": opened},
                remediation="Apply SAP security notes and restrict dispatcher access."
            ))
            
        return findings
