import logging
import os
import shutil
import subprocess
import urllib.parse
import requests
from typing import List, Optional

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

# Intelligent wordlist categorized by value
API_WORDLIST = {
    "High": ["actuator/env", "actuator/heapdump", ".env", "config/databases.yml", ".git/config", "backup.zip", "admin/config", "firebase.json", ".npmrc"],
    "Medium": ["swagger.json", "swagger-ui.html", "docs", "api-docs", "v1/swagger.json", "graphql", "playground", "graphiql", "actuator/health"],
    "Standard": ["api", "api/v1", "api/v2", "rest", "v1", "v2", "v3", "health", "metrics", "status", "debug", "admin/api", "wp-json"]
}

@register
class APIFuzzingStrategy(BaseScanStrategy):
    """
    APIFuzzingStrategy attempts to discover hidden API endpoints using `ffuf` if available.
    Falls back to a robust Python-based fuzzer if `ffuf` is not available.
    Features: Swagger detection, Actuator discovery, and sensitive file fuzzing.
    """
    slug = "api_fuzzer"
    name = "Advanced API & Endpoint Fuzzer"
    description = "Discovers hidden API endpoints, Swagger documentation, and sensitive configuration files using high-performance fuzzing."

    def run(self, target: "ScanTarget", scan: "Scan" = None) -> List[FindingData]:
        findings = []
        host = target.host
        
        if target.target_type == "url" and "://" in host:
            base_url = host.rstrip('/')
        else:
            base_url = f"https://{host}"
        
        self.log(scan, f"Starting API discovery on {base_url}...")
        
        ffuf_path = shutil.which("ffuf")
        
        if ffuf_path:
            self.log(scan, "High-performance fuzzer (ffuf) detected. Initializing engine...")
            findings.extend(self._run_ffuf(ffuf_path, base_url, scan))
        else:
            self.log(scan, "Using built-in multi-threaded fuzzer engine...")
            findings.extend(self._run_fallback_fuzzer(base_url, scan))
            
        return findings

    def _run_ffuf(self, ffuf_path: str, base_url: str, scan: "Scan") -> List[FindingData]:
        findings = []
        wordlist_path = os.path.join(os.getcwd(), f"wordlist_{scan.id if scan else 'temp'}.txt")
        self._create_wordlist(wordlist_path)
        
        target_url = f"{base_url}/FUZZ"
        output_file = os.path.join(os.getcwd(), f"ffuf_{scan.id if scan else 'temp'}.json")
        
        try:
            cmd = [
                ffuf_path,
                "-u", target_url,
                "-w", wordlist_path,
                "-o", output_file,
                "-of", "json",
                "-mc", "200,201,301,302,401,403", 
                "-t", "20",
                "-H", "User-Agent: Mozilla/5.0 (HackerScanPro/1.0)",
                "-timeout", "5"
            ]
            
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)
            
            if os.path.exists(output_file):
                import json
                with open(output_file, 'r') as f:
                    data = json.load(f)
                    
                for result in data.get("results", []):
                    # For ffuf results, we can't easily get the body without another request
                    # so we fetch it briefly for findings that look sensitive
                    f = self._process_fuzz_result(
                        url=result.get("url"),
                        payload=result.get("input", {}).get("FUZZ", ""),
                        status=result.get("status"),
                        length=result.get("length")
                    )
                    if f: findings.append(f)
        except Exception as e:
            logger.error(f"FFUF error: {e}")
            self.log(scan, f"Engine error: {str(e)}")
        finally:
            for p in [wordlist_path, output_file]:
                if os.path.exists(p): os.remove(p)
                
        return [f for f in findings if f]

    def _run_fallback_fuzzer(self, base_url: str, scan: "Scan") -> List[FindingData]:
        from scans.utils import make_evidence_request
        findings = []
        all_words = []
        for cat in API_WORDLIST.values(): all_words.extend(cat)
        
        for ep in all_words:
            url = f"{base_url.rstrip('/')}/{ep.lstrip('/')}"
            try:
                # 🎯 Standardized request capture
                resp, req, res, poc = make_evidence_request(url, timeout=5, follow_redirects=False)
                
                if resp and resp.status_code in [200, 201, 301, 302, 401, 403]:
                    f = self._process_fuzz_result(url, ep, resp.status_code, len(resp.content), req, res, poc)
                    if f: findings.append(f)
            except Exception:
                pass
                
        return findings

    def _process_fuzz_result(self, url: str, payload: str, status: int, length: int, 
                             request_dump: str = "", response_dump: str = "", poc: str = "") -> Optional[FindingData]:
        """Classifies the finding and includes proof (request/response)."""
        title = f"API Endpoint Discovered: /{payload}"
        severity = Severity.INFO
        description = f"Found a potential API endpoint at {url} with status {status}."
        remediation = "Ensure the endpoint is properly secured with authentication and authorization."

        # Special Classifications
        if "swagger" in payload.lower() or "api-docs" in payload.lower():
            title = "API Documentation (Swagger/OpenAPI) Exposed"
            severity = Severity.MEDIUM
            description = f"Publicly accessible API documentation was found at {url}. This leaks the entire API structure to attackers."
            remediation = "Restrict access to API documentation to authorized users only."

        elif any(x in payload.lower() for x in ["actuator", ".env", ".git", "config"]):
            severity = Severity.HIGH
            if status == 200:
                severity = Severity.CRITICAL
                title = f"Sensitive Information Leak: /{payload}"
                description = f"A critical system endpoint was found at {url}. This leaks database credentials, environment variables, or internal details."
                remediation = "IMMEDIATELY restrict access to this path or disable the endpoint in production."

        return FindingData(
            title=title,
            description=description,
            severity=severity,
            evidence={
                "endpoint": payload,
                "url": url,
                "status_code": status,
                "length": length
            },
            plugin_slug=self.slug,
            remediation=remediation,
            request=request_dump,
            response=response_dump,
            poc=poc or f"curl -i '{url}'",
            is_verified=(status == 200)
        )

    def verify(self, finding: "Finding") -> bool:
        """
        Verify the finding by re-requesting the endpoint and checking if it's still accessible.
        """
        from scans.utils import make_evidence_request
        
        url = finding.evidence.get("url")
        if not url:
            return False
            
        try:
            # 🎯 Standardized verification with evidence capture
            resp, req, res, poc = make_evidence_request(url, timeout=10, follow_redirects=False)
            
            if resp and resp.status_code == finding.evidence.get("status_code"):
                # Update finding with fresh dumps
                finding.request = req
                finding.response = res
                finding.poc = poc
                return True
        except Exception as e:
            logger.error(f"Verification error for APIFuzzer: {e}")
            
        return False

    def _create_wordlist(self, filepath: str):
        with open(filepath, 'w') as f:
            for cat in API_WORDLIST.values():
                for ep in cat:
                    f.write(f"{ep}\n")
