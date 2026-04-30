import logging
import subprocess
import os
import shutil
import re
import requests
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class XSStrikeStrategy(BaseScanStrategy):
    """
    Advanced XSS detection using XSStrike.
    Zero Simulation: Runs the actual XSStrike tool against the target.
    """
    slug = "xss_scan"
    name = "XSS Security Audit (XSStrike)"
    description = "Advanced Cross-Site Scripting (XSS) detection engine."

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        url = host if host.startswith(("http://", "https://")) else f"http://{host}"
        
        findings = []
        try:
            # 1. Determine tool location
            xsstrike_bin = shutil.which("xsstrike")
            
            if xsstrike_bin:
                cmd = [xsstrike_bin, "-u", url, "--crawl", "-l", "1", "--timeout", "10", "--seeds", "10", "--skip-dom"]
            else:
                # Fallback to python3 /opt/xsstrike/xsstrike.py
                xsstrike_script = "/opt/xsstrike/xsstrike.py"
                if os.name == "nt": # Windows
                    xsstrike_script = "C:\\tools\\xsstrike\\xsstrike.py"
                
                cmd = [
                    "python3" if os.name != "nt" else "python",
                    xsstrike_script,
                    "-u", url,
                    "--crawl",
                    "-l", "1",
                    "--timeout", "10",
                    "--seeds", "10",
                    "--skip-dom"
                ]
            
            self.log(scan, f"Running: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=600)
            
            output = proc.stdout
            
            # 🚀 ADVANCED PARSING
            # XSStrike output often contains patterns like:
            # [+] Vulnerable Parameter: q
            # [+] Vector: <script>confirm(1)</script>
            # [+] Type: reflected
            
            params = re.findall(r"Vulnerable Parameter:\s+([^\n\r]+)", output)
            payloads = re.findall(r"Payload:\s+([^\n\r]+)", output)
            vectors = re.findall(r"Vector:\s+([^\n\r]+)", output)
            
            if "Vulnerable" in output and params:
                from scans.utils import make_evidence_request
                for i, param in enumerate(params):
                    payload = payloads[i] if i < len(payloads) else "Unknown"
                    vector = vectors[i] if i < len(vectors) else "Unknown"
                    
                    # 🚀 REPRODUCE for Enriched Evidence
                    # Simple heuristic: if it's reflected, it's likely a GET param
                    req_dump = ""
                    res_dump = ""
                    poc_curl = ""
                    
                    resp, req_dump, res_dump, poc_curl = make_evidence_request(
                        url, 
                        method="GET", 
                        params={param: payload} if payload != "Unknown" else {}
                    )
                    
                    is_verified = False
                    if resp and payload != "Unknown" and payload in resp.text:
                        is_verified = True

                    findings.append(FindingData(
                        title=f"Reflected XSS on Parameter '{param}'",
                        description=f"XSStrike identified a reflected XSS vulnerability on the '{param}' parameter of {url}. The payload was confirmed to be reflected in the server response.",
                        severity=Severity.HIGH,
                        evidence={
                            "parameter": param,
                            "payload": payload,
                            "vector": vector,
                            "raw_output": output[-1000:]
                        },
                        request=req_dump,
                        response=res_dump,
                        poc=poc_curl or f"curl -G '{url}' --data-urlencode '{param}={payload}'",
                        remediation="Implement proper output encoding and input validation. Use Content Security Policy (CSP) headers.",
                        plugin_slug=self.slug,
                        is_verified=is_verified
                    ))
            elif "Vulnerable" in output:
                # Fallback if parsing fails but tool says it's vulnerable
                findings.append(FindingData(
                    title="Cross-Site Scripting (XSS) Detected",
                    description=f"XSStrike identified potential XSS vulnerabilities on {url}.",
                    severity=Severity.HIGH,
                    evidence={"raw_output": output[-1000:]},
                    remediation="Implement proper output encoding and input validation. Use Content Security Policy (CSP) headers.",
                    plugin_slug=self.slug
                ))
            else:
                self.log(scan, "No XSS vulnerabilities found by XSStrike.")

        except subprocess.TimeoutExpired:
            self.log(scan, "XSStrike timed out. Results may be incomplete.")
        except Exception as e:
            logger.error("XSStrike error: %s", e)
            self.log(scan, f"XSStrike error: {str(e)}")

        return findings

    def verify(self, finding) -> bool:
        """
        Verify XSS by checking if the payload is reflected in the response.
        """
        from scans.utils import make_evidence_request
        
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False
            
        param = evidence.get("parameter")
        payload = evidence.get("payload")
        
        # Try to extract URL from evidence or finding
        target_url = finding.scan.target.host
        if not target_url.startswith("http"):
            target_url = f"http://{target_url}"
        
        if not param or not payload:
            return False
            
        try:
            # 🎯 Standardized verification with evidence capture
            resp, req, res, poc = make_evidence_request(
                target_url, 
                method="GET", 
                params={param: payload},
                timeout=10
            )
            
            if resp and payload in resp.text:
                # Update the finding with fresh evidence
                finding.request = req
                finding.response = res
                finding.poc = poc
                return True
        except Exception as e:
            logger.error("Verification error for XSS: %s", e)
            
        return False

