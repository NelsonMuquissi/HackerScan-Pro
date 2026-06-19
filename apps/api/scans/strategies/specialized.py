"""
Tactical strategies for premium security modules.
Perform real network discovery and posture checks for specialized environments.
"""
import asyncio
from typing import List, AsyncGenerator
from .base import BaseScanStrategy, FindingData, register

class NetworkDiscoveryMixin:
    """Helper for network-focused strategies."""
    async def check_ports_async(self, host: str, ports: List[int], timeout: float = 1.0) -> List[int]:
        opened = []
        
        async def _check_port(port):
            try:
                conn = asyncio.open_connection(host, port)
                _, writer = await asyncio.wait_for(conn, timeout=timeout)
                writer.close()
                await writer.wait_closed()
                return port
            except Exception:
                return None

        results = await asyncio.gather(*[_check_port(p) for p in ports])
        return [p for p in results if p is not None]

@register
class ActiveDirectoryStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "ad_tactical"
    name = "AD Tactical Audit"
    description = "Discovers Active Directory infrastructure and insecure LDAP configurations."

    async def run_async(self, target, scan) -> AsyncGenerator[FindingData, None]:
        ad_ports = {
            389: "LDAP",
            636: "LDAPS",
            88: "Kerberos",
            445: "Microsoft-DS (SMB)",
            3268: "Global Catalog",
            3269: "Global Catalog SSL"
        }
        
        self.log(scan, f"Scanning for Active Directory endpoints on {target.host}...")
        opened = await self.check_ports_async(target.host, list(ad_ports.keys()))
        
        if opened:
            yield FindingData(
                severity="info",
                title="Active Directory Infrastructure Detected",
                description=f"Discovery identified Active Directory services on {target.host}. Ports recognized: {', '.join([f'{p} ({ad_ports[p]})' for p in opened])}.",
                evidence={"open_ports": opened},
                remediation="Ensure AD services are only accessible within the internal management network.",
                plugin_slug=self.slug,
                poc=f"nmap -Pn -p {','.join(map(str, opened))} {target.host}",
                is_verified=True
            )
            
            if 389 in opened:
                # 🚀 REAL DATA EXTRACTION: Try anonymous LDAP bind and RootDSE fetch
                try:
                    import ldap3
                    server = ldap3.Server(target.host, port=389, get_info=ldap3.ALL, connect_timeout=5)
                    with ldap3.Connection(server, auto_bind=True) as conn:
                        naming_contexts = server.info.naming_contexts
                        domain_functionality = server.info.other.get('domainFunctionality')
                        forest_functionality = server.info.other.get('forestFunctionality')
                        
                        yield FindingData(
                            severity="high",
                            title="Active Directory LDAP Anonymous Bind Enabled",
                            description=f"The LDAP service on {target.host} allows anonymous binding and directory enumeration.",
                            evidence={
                                "naming_contexts": naming_contexts,
                                "domain_functionality": domain_functionality,
                                "forest_functionality": forest_functionality,
                                "raw_info": str(server.info)
                            },
                            remediation="Disable anonymous LDAP binding and enforce 'LDAP server signing'.",
                            plugin_slug=self.slug,
                            poc=f"ldapsearch -x -h {target.host} -s base namingContexts",
                            is_verified=True
                        )
                except Exception as e:
                    logger.debug(f"LDAP probe failed for {target.host}: {e}")

            if 389 in opened and 636 not in opened:
                yield FindingData(
                    severity="medium",
                    title="Insecure LDAP Directory Service",
                    description="The server is exposing LDAP (389) without visible LDAPS (636). Data sent via LDAP is unencrypted.",
                    evidence="Port 389 open, port 636 closed/filtered.",
                    remediation="Enforce LDAP Signing and transition to LDAPS.",
                    plugin_slug=self.slug,
                    poc=f"nmap -Pn -p 389,636 {target.host}",
                    is_verified=True
                )

    async def verify_async(self, finding: "Finding") -> bool:
        import asyncio
        ports = finding.evidence.get("open_ports", [])
        if not ports and "LDAP" in finding.title:
            ports = [389, 636]
        
        if not ports: return False
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        
        opened = await self.check_ports_async(target.host, ports)
        verified = False
        if "Insecure LDAP" in finding.title:
            verified = 389 in opened and 636 not in opened
        else:
            verified = len(opened) > 0
            
        if verified:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
        return False


@register
class KubernetesSecurityStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "k8s_hardening"
    name = "K8s Hardening Check"
    description = "Checks for exposed Kubernetes control plane and node components."

    async def run_async(self, target, scan) -> AsyncGenerator[FindingData, None]:
        k8s_ports = {
            6443: "Kubernetes API Server",
            10250: "Kubelet API",
            2379: "Etcd Client API",
            10255: "Read-only Kubelet"
        }
        
        self.log(scan, "Performing K8s control plane discovery...")
        opened = await self.check_ports_async(target.host, list(k8s_ports.keys()))
        
        if opened:
            main_finding = FindingData(
                severity="high",
                title="Kubernetes Control Plane Exposed",
                description=f"Control plane components were detected on {target.host}. This may expose sensitive cluster configuration.",
                evidence={"detected_ports": opened},
                remediation="Restrict k8s API access using network policies or firewall rules. Disable public access to the control plane.",
                plugin_slug=self.slug,
                poc=f"nmap -Pn -p {','.join(map(str, opened))} {target.host}",
            )
            
            # 🚀 REAL DATA EXTRACTION: Try to fetch k8s version
            if 6443 in opened:
                try:
                    import httpx
                    url = f"https://{target.host}:6443/version"
                    async with httpx.AsyncClient(verify=False, timeout=5) as client:
                        resp = await client.get(url)
                        if resp.status_code == 200:
                            v_data = resp.json()
                            main_finding.severity = "critical"
                            main_finding.title = "Exposed Kubernetes API Server with Version Leak"
                            main_finding.description += f"\n\n**REAL DATA PROOF**: K8s Version: {v_data.get('gitVersion')} (Platform: {v_data.get('platform')})"
                            main_finding.evidence["k8s_version"] = v_data
                            main_finding.is_verified = True
                except Exception:
                    pass
            
            yield main_finding

    async def verify_async(self, finding: "Finding") -> bool:
        import asyncio
        ports = finding.evidence.get("detected_ports", [])
        if not ports: return False
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        opened = await self.check_ports_async(target.host, ports)
        if len(opened) > 0:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
        return False

@register
class SAPSpecializedStrategy(BaseScanStrategy, NetworkDiscoveryMixin):
    slug = "sap_recon"
    name = "SAP Ecosystem Recon"
    description = "Identifies SAP-specific services and potential gateway exposures."

    async def run_async(self, target, scan) -> AsyncGenerator[FindingData, None]:
        sap_ports = {
            3200: "SAP Dispatcher",
            3600: "SAP Message Server",
            3300: "SAP Gateway",
            3900: "SAP NI Broker",
            8000: "SAP Web Dispatcher (HTTP)",
            50000: "SAP NetWeaver (HTTP)",
            50013: "SAP Host Control"
        }
        
        self.log(scan, "Scanning for SAP application layer services...")
        opened = await self.check_ports_async(target.host, list(sap_ports.keys()))
        
        if opened:
            main_finding = FindingData(
                severity="medium",
                title="SAP Specialized Environment Detected",
                description=f"Identified SAP-specific services on {target.host}. Ports recognized: {', '.join([f'{p} ({sap_ports[p]})' for p in opened])}.",
                evidence={"sap_ports": opened},
                remediation="Apply SAP security notes and restrict dispatcher access to trusted networks.",
                plugin_slug=self.slug,
                poc=f"nmap -Pn -p {','.join(map(str, opened))} {target.host}",
            )

            # 🚀 REAL DATA EXTRACTION: Try to fetch SAP System Info via Web Dispatcher or NetWeaver
            http_ports = [p for p in opened if p in [8000, 50000]]
            if http_ports:
                import httpx
                for port in http_ports:
                    url = f"http://{target.host}:{port}/sap/public/icman?Action=ShowStatistics"
                    try:
                        async with httpx.AsyncClient(verify=False, timeout=5) as client:
                            resp = await client.get(url)
                            if resp.status_code == 200 and "SAP Web Dispatcher" in resp.text:
                                main_finding.severity = "high"
                                main_finding.title = "Exposed SAP Web Dispatcher Statistics"
                                main_finding.description += f"\n\n**REAL DATA PROOF**: Successfully accessed SAP Web Dispatcher statistics at {url}. This reveals internal server topology and workload."
                                main_finding.evidence["sap_stats_url"] = url
                                main_finding.is_verified = True
                                break
                    except Exception:
                        pass
            
            yield main_finding

    async def verify_async(self, finding: "Finding") -> bool:
        import asyncio
        ports = finding.evidence.get("sap_ports", [])
        if not ports: return False
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        opened = await self.check_ports_async(target.host, ports)
        if len(opened) > 0:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
        return False


