import logging
import os
import shutil
import subprocess
import urllib.parse
from typing import List, Optional

from .base import BaseScanStrategy, FindingData, register

logger = logging.getLogger(__name__)

@register
class APIFuzzingStrategy(BaseScanStrategy):
    """
    APIFuzzingStrategy attempts to discover hidden API endpoints using `ffuf` if available.
    Falls back to a basic Python-based fuzzer if `ffuf` is not in the system PATH.
    """
    name = "API Fuzzer"
    slug = "api_fuzzer"
    description = "Discovers hidden API endpoints using fuzzing."


    def run(self, target: "ScanTarget", scan: "Scan") -> List[FindingData]:
        findings = []
        target_host = target.host
        parsed = urllib.parse.urlparse(target_host)
        base_url = f"{parsed.scheme or 'http'}://{parsed.netloc or target_host}"
        
        # We append a common API base path or just fuzz the root
        target_url = f"{base_url}/FUZZ"
        
        ffuf_path = shutil.which("ffuf")
        
        if ffuf_path:
            logger.info("ffuf found. Executing ffuf for API fuzzing.")
            findings.extend(self._run_ffuf(ffuf_path, target_url))
        else:
            logger.warning("ffuf not found in PATH. Falling back to basic Python fuzzer.")
            findings.extend(self._run_fallback_fuzzer(base_url))
            
        return findings

    def _run_ffuf(self, ffuf_path: str, target_url: str) -> List[FindingData]:
        findings = []
        # Fallback to a common wordlist. For real-world, a parameter should provide this.
        # But for zero simulation, we create a small temporary wordlist.
        wordlist_path = os.path.join(os.getcwd(), "api_wordlist.txt")
        self._create_wordlist(wordlist_path)
        
        output_file = os.path.join(os.getcwd(), "ffuf_output.json")
        
        try:
            cmd = [
                ffuf_path,
                "-u", target_url,
                "-w", wordlist_path,
                "-o", output_file,
                "-of", "json",
                "-mc", "200,201,301,302,401,403", # match statuses
                "-t", "10" # threads
            ]
            
            logger.info(f"Running ffuf: {' '.join(cmd)}")
            subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)
            
            if os.path.exists(output_file):
                import json
                with open(output_file, 'r') as f:
                    data = json.load(f)
                    
                for result in data.get("results", []):
                    endpoint = result.get("url")
                    status = result.get("status")
                    if endpoint:
                        findings.append(FindingData(
                            title=f"API Endpoint Discovered: {result.get('input', {}).get('FUZZ', 'Unknown')}",
                            description=f"Found a potential API endpoint at {endpoint} with status {status}.",
                            severity="INFO" if status in [301, 302, 401, 403] else "LOW",
                            category="API Fuzzing",
                            evidence={"url": endpoint, "status_code": status, "content_length": result.get("length")},
                            confidence=90
                        ))
        except subprocess.TimeoutExpired:
            logger.warning("ffuf timed out.")
        except Exception as e:
            logger.error(f"Error running ffuf: {e}")
        finally:
            if os.path.exists(wordlist_path):
                os.remove(wordlist_path)
            if os.path.exists(output_file):
                os.remove(output_file)
                
        return findings

    def _run_fallback_fuzzer(self, base_url: str) -> List[FindingData]:
        import requests
        findings = []
        endpoints = self._get_wordlist_entries()
        
        for ep in endpoints:
            url = f"{base_url}/{ep}"
            try:
                resp = requests.get(url, timeout=3, allow_redirects=False)
                if resp.status_code in [200, 201, 301, 302, 401, 403]:
                    findings.append(FindingData(
                        title=f"API Endpoint Discovered: {ep}",
                        description=f"Found a potential API endpoint at {url} with status {resp.status_code}.",
                        severity="INFO" if resp.status_code in [301, 302, 401, 403] else "LOW",
                        category="API Fuzzing",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=80
                    ))
            except requests.RequestException:
                pass
                
        return findings
        
    def _create_wordlist(self, filepath: str):
        with open(filepath, 'w') as f:
            for ep in self._get_wordlist_entries():
                f.write(f"{ep}\n")
                
    def _get_wordlist_entries(self) -> List[str]:
        return [
            "api", "api/v1", "api/v2", "api/v3", "graphql", "swagger", "swagger-ui", "docs",
            "api-docs", "v1", "v2", "v3", "rest", "rest/api", "wp-json", "metrics", "health",
            "actuator/health", "actuator/env", "env", "config", "status", "debug", "admin/api"
        ]
