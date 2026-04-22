import logging
import subprocess
import json
import tempfile
import os
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class NucleiVulnStrategy(BaseScanStrategy):
    """
    Nuclei vulnerability scan engine.
    Focuses on CVEs, critical exposures, and misconfigurations.
    """
    slug = "nuclei_vuln"
    name = "Nuclei Vulnerability Scan"

    def run(self, target, scan=None) -> List[FindingData]:
        return self._run_nuclei(target, tags="cve,vuln,critical,high")

    def _run_nuclei(self, target, tags=None, templates=None) -> List[FindingData]:
        findings = []
        # target.host is the correct field on ScanTarget (target.address does not exist)
        host = target.host
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            output_file = tf.name

        try:
            cmd = [
                "nuclei",
                "-target", host,
                "-json-export", output_file,
                "-silent",
                "-no-update-check"
            ]
            if tags:
                cmd.extend(["-tags", tags])
            if templates:
                cmd.extend(["-t", templates])

            logger.info("Running nuclei: %s", " ".join(cmd))
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)

            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            findings.append(FindingData(
                                title=data.get("info", {}).get("name", "Nuclei Finding"),
                                description=data.get("info", {}).get("description", ""),
                                severity=self._map_severity(data.get("info", {}).get("severity", "info")),
                                evidence=f"Matched: {data.get('matched-at', '')}\nTemplate: {data.get('template-id', '')}",
                                remediation=data.get("info", {}).get("remediation", ""),
                                cvss_score=data.get("info", {}).get("classification", {}).get("cvss-score")
                            ))
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            logger.warning("nuclei not found in PATH — skipping vuln scan.")
            findings.append(FindingData(
                title="Nuclei Vulnerability Scan Unavailable",
                description="The nuclei scanning engine is not installed or not in PATH on this server.",
                severity=Severity.INFO,
                remediation="Install nuclei to enable advanced vulnerability research and CVE detection.",
            ))
        except Exception as e:
            logger.error("Nuclei strategy error: %s", e)
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

        return findings

    def _map_severity(self, nuclei_sev: str) -> Severity:
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
        }
        return mapping.get(nuclei_sev.lower(), Severity.INFO)


@register
class NucleiFullStrategy(NucleiVulnStrategy):
    """
    Nuclei full scan engine.
    Runs all available templates.
    """
    slug = "nuclei_full"
    name = "Nuclei Full Scan"

    def run(self, target, scan=None) -> List[FindingData]:
        return self._run_nuclei(target)  # No tags = all templates
