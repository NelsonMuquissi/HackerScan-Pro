import logging
import subprocess
import os
import shutil
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
                cmd = [xsstrike_bin, "-u", url, "--crawl", "-l", "1", "--timeout", "10", "--seeds", "10"]
            else:
                # Fallback to python3 /opt/xsstrike/xsstrike.py if not in PATH (legacy/linux default)
                # On Windows, this will likely fail unless explicitly installed there
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
                    "--seeds", "10"
                ]
            
            self.log(scan, f"Running: {' '.join(cmd)}")
            # This can be slow, 5 min timeout
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=300)
            
            output = proc.stdout
            if "Vulnerable" in output or "XSS" in output:
                findings.append(FindingData(
                    title="Cross-Site Scripting (XSS) Detected",
                    description=f"XSStrike identified potential XSS vulnerabilities on {url}.",
                    severity=Severity.HIGH,
                    evidence=output[:2000],
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
