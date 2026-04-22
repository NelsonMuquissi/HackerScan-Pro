import logging
import socket
import requests
from typing import List, Optional
import urllib.parse

from .base import BaseScanStrategy, FindingData, register

logger = logging.getLogger(__name__)


@register
class ContainerSecurityStrategy(BaseScanStrategy):
    """
    ContainerSecurityStrategy checks for exposed Container and Kubernetes management ports
    and unauthenticated API endpoints (Docker Socket, Kubelet, K8s API, etcd).
    """
    name = "Container Security Check"
    slug = "container_security"
    description = "Checks for exposed container management ports."


    def run(self, target: "ScanTarget", scan: "Scan") -> List[FindingData]:
        findings = []
        target_host = target.host
        parsed = urllib.parse.urlparse(target_host)
        host = parsed.netloc.split(":")[0] if parsed.netloc else target_host.split(":")[0]
        
        # Ports to check: 
        # 2375 (Docker HTTP), 2376 (Docker HTTPS)
        # 6443 (K8s API HTTPS), 8080 (K8s API HTTP)
        # 10250 (Kubelet HTTPS), 10255 (Kubelet HTTP Read-Only)
        # 2379 (etcd client)
        ports_to_check = [2375, 2376, 6443, 8080, 10250, 10255, 2379]
        
        open_ports = self._scan_ports(host, ports_to_check)
        
        for port in open_ports:
            findings.extend(self._analyze_port(host, port))
            
        return findings

    def _scan_ports(self, host: str, ports: List[int]) -> List[int]:
        open_ports = []
        for port in ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    if s.connect_ex((host, port)) == 0:
                        open_ports.append(port)
            except Exception as e:
                logger.debug(f"Error scanning port {port} on {host}: {e}")
        return open_ports

    def _analyze_port(self, host: str, port: int) -> List[FindingData]:
        findings = []
        
        # Docker API Check
        if port in [2375, 2376]:
            proto = "https" if port == 2376 else "http"
            url = f"{proto}://{host}:{port}/containers/json"
            try:
                resp = requests.get(url, timeout=3, verify=False)
                if resp.status_code == 200 and "Id" in resp.text and "Names" in resp.text:
                    findings.append(FindingData(
                        title="Unauthenticated Docker API Exposed",
                        description=f"The Docker API is exposed without authentication at {url}. An attacker can take full control of the Docker host.",
                        severity="CRITICAL",
                        category="Container Security",
                        evidence={"url": url, "response_snippet": resp.text[:200]},
                        confidence=100
                    ))
            except requests.RequestException:
                pass
                
        # Kubernetes API Check
        if port in [6443, 8080]:
            proto = "https" if port == 6443 else "http"
            url = f"{proto}://{host}:{port}/api/v1/namespaces"
            try:
                resp = requests.get(url, timeout=3, verify=False)
                if resp.status_code in [200, 403]: # 403 means it's there but requires auth
                    severity = "CRITICAL" if resp.status_code == 200 else "INFO"
                    title_suffix = "(Unauthenticated)" if resp.status_code == 200 else "(Requires Auth)"
                    desc = "Unauthenticated access to Kubernetes API is allowed!" if resp.status_code == 200 else "Kubernetes API endpoint exposed."
                    findings.append(FindingData(
                        title=f"Kubernetes API Exposed {title_suffix}",
                        description=f"{desc} URL: {url}",
                        severity=severity,
                        category="Container Security",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=100
                    ))
            except requests.RequestException:
                pass

        # Kubelet Check
        if port in [10250, 10255]:
            proto = "https" if port == 10250 else "http"
            url = f"{proto}://{host}:{port}/pods"
            try:
                resp = requests.get(url, timeout=3, verify=False)
                if resp.status_code == 200 and "items" in resp.text:
                    findings.append(FindingData(
                        title="Unauthenticated Kubelet Read-Only API",
                        description=f"The Kubelet API is exposed at {url}, revealing pod information.",
                        severity="HIGH",
                        category="Container Security",
                        evidence={"url": url, "response_snippet": resp.text[:200]},
                        confidence=100
                    ))
                elif resp.status_code in [401, 403]:
                    findings.append(FindingData(
                        title="Kubelet API Exposed (Requires Auth)",
                        description=f"The Kubelet API is exposed at {url} but requires authentication.",
                        severity="INFO",
                        category="Container Security",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=90
                    ))
            except requests.RequestException:
                pass
                
        # Etcd Check
        if port == 2379:
            url = f"http://{host}:{port}/v2/keys"
            try:
                resp = requests.get(url, timeout=3)
                if resp.status_code == 200 or "errorCode" in resp.text:
                    findings.append(FindingData(
                        title="Etcd API Exposed",
                        description=f"An Etcd API endpoint is exposed at {url}. This might leak critical cluster state and secrets.",
                        severity="CRITICAL",
                        category="Container Security",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=100
                    ))
            except requests.RequestException:
                pass

        return findings
