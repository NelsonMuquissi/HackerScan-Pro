import logging
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

# Common regex patterns for secrets
SECRET_PATTERNS = {
    "AWS Access Key": r"AKIA[0-9A-Z]{16}",
    "Google API Key": r"AIza[0-9A-Za-z-_]{35}",
    "Slack Token": r"xox[baprs]-[0-9a-zA-Z]{10,48}",
    "GitHub Personal Access Token": r"ghp_[a-zA-Z0-9]{36}",
    "Stripe API Key": r"(?:r|s)k_(?:live|test)_[0-9a-zA-Z]{24}",
    "Mailgun API Key": r"key-[0-9a-zA-Z]{32}",
    "Generic Secret": r"(?i)(api_key|apikey|secret|password|token|auth)\s*[:=]\s*['\"]([a-zA-Z0-9_-]{16,})['\"]",
}

@register
class JSSecretScanStrategy(BaseScanStrategy):
    """
    Scans JavaScript files for hardcoded secrets, API keys, and sensitive data.
    """
    slug = "js_secrets"
    name = "JS Secret Scraper"
    description = "Crawls the target for JavaScript files and extracts hardcoded secrets using regex."

    def run(self, target, scan=None) -> List[FindingData]:
        host = target.host
        findings = []

        # Determine start URL
        if target.target_type == "url":
            start_url = host
        else:
            # Try HTTPS first, fallback to HTTP
            start_url = f"https://{host}"
        
        self.log(scan, f"Starting JS secret scan on {start_url}...")

        try:
            # 1. Fetch homepage
            response = requests.get(start_url, timeout=15, verify=False)
            if response.status_code != 200:
                # Try HTTP
                if start_url.startswith("https"):
                    start_url = f"http://{host}"
                    response = requests.get(start_url, timeout=15, verify=False)
            
            if response.status_code != 200:
                self.log(scan, f"Failed to reach target: {response.status_code}")
                return []

            # 2. Find JS files
            soup = BeautifulSoup(response.text, "html.parser")
            script_tags = soup.find_all("script", src=True)
            js_urls = [urljoin(start_url, s["src"]) for s in script_tags]
            
            # Filter for internal JS or common CDNs if we want, but let's check all for now
            self.log(scan, f"Found {len(js_urls)} script tags. Analyzing...")

            # 3. Analyze each JS file
            for js_url in set(js_urls):
                try:
                    js_res = requests.get(js_url, timeout=10, verify=False)
                    if js_res.status_code == 200:
                        file_findings = self._scan_content(js_res.text, js_url)
                        findings.extend(file_findings)
                except Exception as e:
                    logger.warning(f"Failed to fetch JS {js_url}: {e}")

            # 4. Also scan the main page text
            findings.extend(self._scan_content(response.text, start_url))

        except Exception as e:
            logger.error(f"JS Secret Scan error: {e}")
            self.log(scan, f"Error: {str(e)}")

        return findings

    def _scan_content(self, content: str, source_url: str) -> List[FindingData]:
        findings = []
        for name, pattern in SECRET_PATTERNS.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                secret = match.group(0)
                # Obfuscate secret for safety in description
                obfuscated = secret[:4] + "*" * (len(secret) - 8) + secret[-4:] if len(secret) > 8 else "****"
                
                findings.append(FindingData(
                    title=f"Potential {name} Exposed",
                    description=f"A potential {name} was found hardcoded in {source_url}.",
                    severity=Severity.HIGH if name != "Generic Secret" else Severity.MEDIUM,
                    evidence={
                        "pattern_name": name,
                        "source": source_url,
                        "match_snippet": obfuscated,
                        "context": content[max(0, match.start()-50):min(len(content), match.end()+50)].strip()
                    },
                    plugin_slug=self.slug,
                    remediation="Revoke the exposed key/secret immediately and move it to a secure backend environment variable or vault."
                ))
        return findings
