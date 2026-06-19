import asyncio
import json
import os
import tempfile
import logging
from typing import List, AsyncGenerator
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

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        async for finding in self._run_nuclei_async(target, tags="cve,vuln,critical,high"):
            yield finding


    async def _run_nuclei_async(self, target, tags=None, templates=None) -> AsyncGenerator[FindingData, None]:
        # Use standardized URL
        url = target.url
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            output_file = tf.name

        try:
            args = [
                "-target", url,
                "-json-export", output_file,
                "-silent",
                "-include-rr",
                "-no-update-check"
            ]
            if tags:
                args.extend(["-tags", tags])
            if templates:
                args.extend(["-t", templates])

            logger.info("Running nuclei: nuclei %s", " ".join(args))
            
            process = await asyncio.create_subprocess_exec(
                "nuclei", *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await asyncio.wait_for(process.wait(), timeout=300)

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

                            if cvss_vector and ("CVSS:3.1" in cvss_vector or "CVSS:3.0" in cvss_vector):
                                try:
                                    calc_score = CVSS31Calculator.calculate(cvss_vector)
                                    if calc_score > 0:
                                        cvss_score = calc_score
                                except Exception as e:
                                    logger.debug(f"CVSS calculation failed for {cvss_vector}: {e}")

                            description = data.get("info", {}).get("description", "")
                            
                            # 🚀 REAL DATA PROOF: Add extraction or matcher details
                            extracted = data.get("extracted-results", [])
                            matcher = data.get("matcher-name", "")
                            if extracted:
                                description += f"\n\n**REAL DATA PROOF**:\n- Extracted values: `{', '.join(extracted)}`"
                            elif matcher:
                                description += f"\n\n**REAL DATA PROOF**:\n- Matcher `{matcher}` triggered in response."

                            yield FindingData(
                                title=data.get("info", {}).get("name", "Nuclei Finding"),
                                description=description,
                                severity=self._map_severity(data.get("info", {}).get("severity", "info")),
                                evidence=evidence_dict,
                                remediation=data.get("info", {}).get("remediation", ""),
                                cvss_score=cvss_score,
                                request=data.get("request", ""),
                                response=data.get("response", ""),
                                poc=f"nuclei -u {url} -id {data.get('template-id')}"
                            )
                        except json.JSONDecodeError:
                            continue
        except FileNotFoundError:
            logger.warning("nuclei not found in PATH — skipping vuln scan.")
            yield FindingData(
                title="Nuclei Vulnerability Scan Unavailable",
                description="The nuclei scanning engine is not installed or not in PATH on this server.",
                severity=Severity.INFO,
                remediation="Install nuclei to enable advanced vulnerability research and CVE detection.",
            )
        except Exception as e:
            logger.error("Nuclei strategy error: %s", e)
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Re-verify by running the specific template that found this vulnerability (async).
        """
        import asyncio
        template_id = finding.evidence.get("template_id")
        if not template_id:
            return False
            
        results = []
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()
        async for f in self._run_nuclei_async(target, templates=template_id):
            results.append(f)
        
        # If any result matches the template_id, it's verified
        is_found = any(r.evidence.get("template_id") == template_id for r in results)
        
        if is_found:
            # Update request/response with fresh ones
            for r in results:
                if r.evidence.get("template_id") == template_id:
                    finding.request = r.request
                    finding.response = r.response
                    finding.is_verified = True
                    break
            
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
            
        return False

    def _map_severity(self, nuclei_sev: str) -> Severity:
        mapping = {
            "critical": Severity.CRITICAL,
            "high": Severity.HIGH,
            "medium": Severity.MEDIUM,
            "low": Severity.LOW,
            "info": Severity.INFO,
            "unknown": Severity.INFO
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

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        async for finding in self._run_nuclei_async(target):  # No tags = all templates
            yield finding



@register
class NucleiTechStrategy(NucleiVulnStrategy):
    """
    Nuclei technology detection engine.
    Used in Phase 1 to identify the stack (WAF, CMS, Framework).
    """
    slug = "nuclei_tech"
    name = "Nuclei Technology Detection"

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        # 'tech' tag is fast and identifies many frameworks/CMS
        async for finding in self._run_nuclei_async(target, tags="tech,waf,detect"):
            yield finding

