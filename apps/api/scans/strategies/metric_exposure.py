import logging
import re
from typing import AsyncGenerator, List, Optional
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class MetricExposureStrategy(BaseScanStrategy):
    slug = "metric_exposure"
    name = "Metric & Monitoring Exposure Check"
    description = "Checks for exposed monitoring endpoints like Prometheus, Grafana, and Spring Boot Actuator."

    async def run_async(self, target, scan) -> AsyncGenerator[FindingData, None]:
        from scans.utils import make_evidence_request_async
        
        # Common monitoring paths
        paths = [
            "/metrics",
            "/prometheus",
            "/actuator/prometheus",
            "/actuator/metrics",
            "/actuator/info",
            "/actuator/env",
            "/grafana/",
            "/grafana/login",
            "/dashboard/",
            "/netdata/",
            "/zabbix/"
        ]
        
        self.log(scan, f"Probing {len(paths)} monitoring paths...")
        
        for path in paths:
            url = f"http://{target.host}{path}"
            try:
                resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
                if not resp or resp.status_code != 200:
                    continue
                
                # Check for Prometheus metrics
                if "# HELP" in resp.text and "# TYPE" in resp.text:
                    # 🚀 REAL DATA EXTRACTION: Extract some system metadata from metrics
                    node_info = re.search(r'node_uname_info\{.*?release="(.*?)".*?version="(.*?)".*?\}', resp.text)
                    cpu_count = re.search(r'node_cpu_seconds_total\{.*?\}', resp.text)
                    
                    data_proof = ""
                    if node_info:
                        data_proof += f"Node Release: {node_info.group(1)}, Version: {node_info.group(2)}\n"
                    
                    yield FindingData(
                        severity=Severity.HIGH,
                        title="Exposed Prometheus Metrics Endpoint",
                        description=(
                            f"A Prometheus metrics endpoint is exposed at `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Found live metrics data with HELP/TYPE annotations.\n"
                            f"{data_proof}"
                        ),
                        evidence={"url": url, "snippet": resp.text[:500]},
                        remediation="Restrict access to metrics endpoints using basic auth or a firewall.",
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        is_verified=True
                    )
                
                # Check for Spring Boot Actuator
                elif ("/actuator" in path or '"_links"' in resp.text):
                    # Try to get extra info as proof
                    info_url = f"http://{target.host}/actuator/info"
                    info_resp, _, _, _ = await make_evidence_request_async(info_url, timeout=3)
                    info_proof = info_resp.text if (info_resp and info_resp.status_code == 200) else "Info endpoint restricted"

                    yield FindingData(
                        severity=Severity.HIGH,
                        title="Spring Boot Actuator Exposed",
                        description=(
                            f"Spring Boot Actuator endpoints are exposed at `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Info endpoint returned: `{info_proof[:100]}...`"
                        ),
                        evidence={"url": url, "response": resp.json() if "json" in resp.headers.get("Content-Type", "") else resp.text[:500], "info": info_proof},
                        remediation="Secure actuator endpoints with Spring Security.",
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        is_verified=True
                    )
                
                # Check for Grafana
                elif "Grafana" in resp.text:
                    # Extract version from sub-string like "version":"v10.1.0"
                    version_match = re.search(r'"version":"(v?\d+\.\d+\.\d+)"', resp.text)
                    version = version_match.group(1) if version_match else "Unknown"
                    
                    yield FindingData(
                        severity=Severity.INFO,
                        title="Grafana Dashboard Detected",
                        description=(
                            f"A Grafana monitoring dashboard was found at `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Version identified: `{version}`"
                        ),
                        evidence={"url": url, "version": version},
                        plugin_slug=self.slug,
                        request=req_dump,
                        response=res_dump,
                        poc=poc,
                        is_verified=True
                    )
                    
            except Exception:
                continue


    async def verify_async(self, finding) -> bool:
        from scans.utils import make_evidence_request_async
        url = finding.evidence.get("url")
        if not url: return False
        try:
            resp, _, _, _ = await make_evidence_request_async(url, timeout=5)
            return resp and resp.status_code == 200
        except:
            return False
