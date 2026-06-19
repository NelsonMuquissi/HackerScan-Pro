import logging
import socket
import requests
from typing import List, Optional, AsyncGenerator
import urllib.parse

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

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


    async def run_async(self, target: "ScanTarget", scan: "Scan") -> AsyncGenerator[FindingData, None]:
        """
        Native async implementation for improved performance.
        Yields FindingData as they are identified.
        """
        import asyncio
        target_host = target.host
        parsed = urllib.parse.urlparse(target_host)
        host = parsed.netloc.split(":")[0] if parsed.netloc else target_host.split(":")[0]
        
        # Ports to check: 
        # 2375/2376 (Docker HTTP/HTTPS), 5000 (Docker Registry)
        # 6443 (K8s API HTTPS), 8080 (K8s API HTTP)
        # 10250 (Kubelet HTTPS), 10255 (Kubelet HTTP Read-Only)
        # 2379 (etcd client)
        # 44134 (Helm Tiller — K8s < 3.0)
        ports_to_check = [2375, 2376, 5000, 6443, 8080, 10250, 10255, 2379, 44134]
        
        self.log(scan, f"Scanning {len(ports_to_check)} container-related ports on {host}...")
        
        open_ports = await self._scan_ports_async(host, ports_to_check)
        
        if not open_ports:
            self.log(scan, "No exposed container management ports found.")
            return
 
        # Analyze open ports concurrently
        analysis_tasks = [self._analyze_port_async(host, port, scan) for port in open_ports]
        for future in asyncio.as_completed(analysis_tasks):
            findings = await future
            for f in findings:
                yield f
 
    async def _scan_ports_async(self, host: str, ports: List[int]) -> List[int]:
        import asyncio
        open_ports = []
        
        async def _check_port(port):
            try:
                # Use wait_for to enforce a timeout on the connection attempt
                conn = asyncio.open_connection(host, port)
                _, writer = await asyncio.wait_for(conn, timeout=2.0)
                writer.close()
                await writer.wait_closed()
                return port
            except Exception:
                return None
 
        # Scan all ports in parallel
        results = await asyncio.gather(*[_check_port(p) for p in ports])
        return [p for p in results if p is not None]
 
    async def _analyze_port_async(self, host: str, port: int, scan) -> List[FindingData]:
        findings = []
        
        # Docker API Check
        if port in [2375, 2376]:
            finding = await self._audit_docker_api(host, port)
            if finding:
                findings.append(finding)

        # Docker Registry Check
        if port == 5000:
            finding = await self._audit_docker_registry(host, port)
            if finding:
                findings.append(finding)
                
        # Kubernetes API Check
        if port in [6443, 8080]:
            finding = await self._audit_k8s_api(host, port)
            if finding:
                findings.append(finding)
 
        # Kubelet Check
        if port in [10250, 10255]:
            finding = await self._audit_kubelet(host, port)
            if finding:
                findings.append(finding)
                
        # Etcd Check
        if port == 2379:
            finding = await self._audit_etcd(host, port)
            if finding:
                findings.append(finding)

        # Helm Tiller Check
        if port == 44134:
            finding = await self._audit_helm_tiller(host, port)
            if finding:
                findings.append(finding)
 
        return findings

    async def _audit_docker_api(self, host: str, port: int) -> Optional[FindingData]:
        from scans.utils import make_evidence_request_async
        proto = "https" if port == 2376 else "http"
        url = f"{proto}://{host}:{port}/containers/json"
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5, verify=False)
            if resp and resp.status_code == 200 and ("Id" in resp.text or "Names" in resp.text):
                # 🚀 REAL DATA EXTRACTION: Get Version and Info
                version_info = {}
                try:
                    v_resp, _, _, _ = await make_evidence_request_async(f"{proto}://{host}:{port}/version", timeout=5, verify=False)
                    if v_resp and v_resp.status_code == 200:
                        version_info = v_resp.json()
                except: pass

                return FindingData(
                    title="Unauthenticated Docker API Exposed",
                    description=f"The Docker API is exposed without authentication at {url}. An attacker can take full control of the Docker host.\n\n**REAL DATA PROOF**: Docker Version: {version_info.get('Version', 'Unknown')}, OS: {version_info.get('Os', 'Unknown')}",
                    severity=Severity.CRITICAL,
                    category="Container Security",
                    evidence={
                        "url": url, 
                        "version": version_info,
                        "containers_count": len(resp.json()) if resp.status_code == 200 else 0
                    },
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=f"docker -H {host}:{port} ps",
                    plugin_slug=self.slug,
                    is_verified=True
                )
        except Exception:
            pass
        return None

    async def _audit_k8s_api(self, host: str, port: int) -> Optional[FindingData]:
        from scans.utils import make_evidence_request_async
        proto = "https" if port == 6443 else "http"
        url = f"{proto}://{host}:{port}/api/v1/namespaces"
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5, verify=False)
            if resp and resp.status_code in [200, 403]: # 403 means it's there but requires auth
                severity = Severity.CRITICAL if resp.status_code == 200 else Severity.INFO
                title_suffix = "(Unauthenticated)" if resp.status_code == 200 else "(Requires Auth)"
                desc = "Unauthenticated access to Kubernetes API is allowed!" if resp.status_code == 200 else "Kubernetes API endpoint exposed."
                return FindingData(
                    title=f"Kubernetes API Exposed {title_suffix}",
                    description=f"{desc} URL: {url}\n\n**REAL DATA PROOF**: Status Code: {resp.status_code}",
                    severity=severity,
                    category="Container Security",
                    evidence={"url": url, "status_code": resp.status_code},
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=poc,
                    plugin_slug=self.slug,
                    is_verified=resp.status_code == 200
                )
        except Exception:
            pass
        return None

    async def _audit_kubelet(self, host: str, port: int) -> Optional[FindingData]:
        from scans.utils import make_evidence_request_async
        proto = "https" if port == 10250 else "http"
        url = f"{proto}://{host}:{port}/pods"
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5, verify=False)
            if resp and resp.status_code == 200 and "items" in resp.text:
                return FindingData(
                    title="Unauthenticated Kubelet Read-Only API",
                    description=f"The Kubelet API is exposed at {url}, revealing pod information.\n\n**REAL DATA PROOF**: Pods Snippet: `{resp.text[:100]}...`",
                    severity=Severity.HIGH,
                    category="Container Security",
                    evidence={"url": url, "response_snippet": resp.text[:200]},
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=poc,
                    plugin_slug=self.slug,
                    is_verified=True
                )
            elif resp and resp.status_code in [401, 403]:
                return FindingData(
                    title="Kubelet API Exposed (Requires Auth)",
                    description=f"The Kubelet API is exposed at {url} but requires authentication.",
                    severity=Severity.INFO,
                    category="Container Security",
                    evidence={"url": url, "status_code": resp.status_code},
                    confidence=90,
                    request=req_dump,
                    response=res_dump,
                    poc=poc,
                    plugin_slug=self.slug
                )
        except Exception:
            pass
        return None

    async def _audit_etcd(self, host: str, port: int) -> Optional[FindingData]:
        from scans.utils import make_evidence_request_async
        url = f"http://{host}:{port}/v2/keys"
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
            if resp and (resp.status_code == 200 or "errorCode" in resp.text):
                return FindingData(
                    title="Etcd API Exposed",
                    description=f"An Etcd API endpoint is exposed at {url}. This might leak critical cluster state and secrets.\n\n**REAL DATA PROOF**: Status Code: {resp.status_code}, Response: `{resp.text[:50]}...`",
                    severity=Severity.CRITICAL,
                    category="Container Security",
                    evidence={"url": url, "status_code": resp.status_code},
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=poc,
                    plugin_slug=self.slug,
                    is_verified=resp.status_code == 200
                )
        except Exception:
            pass
        return None

    async def _audit_docker_registry(self, host: str, port: int) -> Optional[FindingData]:
        """Check for unauthenticated Docker Registry (V2 API)."""
        from scans.utils import make_evidence_request_async
        url = f"http://{host}:{port}/v2/_catalog"
        try:
            resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
            if resp and resp.status_code == 200 and "repositories" in resp.text:
                repos = []
                try:
                    repos = resp.json().get("repositories", [])
                except Exception:
                    pass
                return FindingData(
                    title="Unauthenticated Docker Registry Exposed",
                    description=(
                        f"The Docker Registry V2 API at `{url}` is accessible without authentication. "
                        f"An attacker can pull, inspect, or push Docker images.\n\n"
                        f"**REAL DATA PROOF**: Repository list: {repos[:5]}"
                    ),
                    severity=Severity.CRITICAL,
                    category="Container Security",
                    evidence={"url": url, "repositories": repos},
                    confidence=100,
                    request=req_dump,
                    response=res_dump,
                    poc=f"curl -s {url} | python3 -m json.tool",
                    plugin_slug=self.slug,
                    is_verified=True,
                )
        except Exception:
            pass
        return None

    async def _audit_helm_tiller(self, host: str, port: int) -> Optional[FindingData]:
        """Check for exposed Helm Tiller (gRPC port 44134)."""
        import asyncio
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=3
            )
            writer.close()
            await writer.wait_closed()
            return FindingData(
                title="Helm Tiller Port Exposed (44134)",
                description=(
                    f"Port 44134 (Helm Tiller gRPC) is open on `{host}`. "
                    "In Helm 2.x, an unauthenticated Tiller allows full cluster compromise via `helm` commands.\n\n"
                    "**REAL DATA PROOF**: TCP connection to port 44134 succeeded."
                ),
                severity=Severity.CRITICAL,
                category="Container Security",
                evidence={"host": host, "port": port},
                confidence=85,
                poc=f"helm --host {host}:44134 version",
                plugin_slug=self.slug,
            )
        except Exception:
            pass
        return None

    async def verify_async(self, finding: "Finding") -> bool:
        """Native async verification."""
        import asyncio
        from scans.utils import make_evidence_request_async
        evidence = finding.evidence
        if not isinstance(evidence, dict) or "url" not in evidence:
            return False
            
        url = evidence["url"]
        try:
            resp, req, res, poc = await make_evidence_request_async(url, timeout=5, verify=False)
            if resp:
                verified = False
                # If it was unauthenticated (200), check if still 200
                if "Unauthenticated" in finding.title or finding.severity == Severity.CRITICAL:
                    if resp.status_code == 200:
                        finding.request = req
                        finding.response = res
                        verified = True
                # If it just needed to be exposed
                elif resp.status_code in [200, 401, 403]:
                    finding.request = req
                    finding.response = res
                    verified = True
                
                if verified:
                    finding.is_verified = True
                    from asgiref.sync import sync_to_async
                    await sync_to_async(finding.save)()
                    return True
        except Exception:
            pass
        return False

