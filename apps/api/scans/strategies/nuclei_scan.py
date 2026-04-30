import logging
import subprocess
import json
import tempfile
import os
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity
from scans.external.cvss_calculator import CVSS31Calculator

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
                "-include-rr",
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
                            
                            # 🚀 ENRICHED EVIDENCE
                            evidence_dict = {
                                "matched_at": data.get("matched-at", ""),
                                "template_id": data.get("template-id", ""),
                                "matcher_name": data.get("matcher-name", ""),
                                "extracted_results": data.get("extracted-results", []),
                                "type": data.get("type", "unknown")
                            }
                            
                            # Add interaction data if available (for OAST)
                            if data.get("interaction"):
                                evidence_dict["interaction"] = data.get("interaction")

                            # 🎯 DYNAMIC SCORING (CVSS v3.1)
                            classification = data.get("info", {}).get("classification", {})
                            cvss_score = classification.get("cvss-score")
                            cvss_vector = classification.get("cvss-metrics")

                            if cvss_vector and "CVSS:3.1" in cvss_vector:
                                calc_score = CVSS31Calculator.calculate(cvss_vector)
                                if calc_score > 0:
                                    cvss_score = calc_score

                            findings.append(FindingData(
                                title=data.get("info", {}).get("name", "Nuclei Finding"),
                                description=data.get("info", {}).get("description", ""),
                                severity=self._map_severity(data.get("info", {}).get("severity", "info")),
                                evidence=evidence_dict,
                                remediation=data.get("info", {}).get("remediation", ""),
                                cvss_score=cvss_score,
                                request=data.get("request", ""),
                                response=data.get("response", ""),
                                poc=f"nuclei -u {host} -id {data.get('template-id')}"
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

    def verify(self, finding: "Finding") -> bool:
        """
        Re-verify by running the specific template that found this vulnerability.
        """
        template_id = finding.evidence.get("template_id")
        if not template_id:
            return False
            
        results = self._run_nuclei(finding.scan.target, templates=template_id)
        
        # If any result matches the template_id, it's verified
        is_found = any(r.evidence.get("template_id") == template_id for r in results)
        
        if is_found:
            # Update request/response with fresh ones
            for r in results:
                if r.evidence.get("template_id") == template_id:
                    finding.request = r.request
                    finding.response = r.response
                    break
            return True
            
        return False

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


@register
class NucleiTechStrategy(NucleiVulnStrategy):
    """
    Nuclei technology detection engine.
    Used in Phase 1 to identify the stack (WAF, CMS, Framework).
    """
    slug = "nuclei_tech"
    name = "Nuclei Technology Detection"

    def run(self, target, scan=None) -> List[FindingData]:
        # 'tech' tag is fast and identifies many frameworks/CMS
        return self._run_nuclei(target, tags="tech,waf,detect")
