import logging
import requests
import urllib.parse
from typing import List, Optional
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class CloudExposureStrategy(BaseScanStrategy):
    """
    Advanced CloudExposureStrategy checks for exposed Cloud Storage buckets
    (AWS S3, Azure Blob, GCP Storage) with smarter permutations and content analysis.
    """
    name = "Cloud Exposure Enum"
    slug = "cloud_exposure"
    description = "Checks for exposed Cloud Storage buckets (S3, Azure, GCP)."

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        target_host = target.host
        domain = urllib.parse.urlparse(target_host).netloc or target_host
        domain_parts = domain.split('.')
        base_name = domain_parts[0] if domain_parts else domain
        
        # Advanced bucket name permutations
        permutations = [
            base_name,
            domain.replace('.', '-'),
            f"{base_name}-assets",
            f"{base_name}-public",
            f"{base_name}-prod",
            f"{base_name}-production",
            f"{base_name}-staging",
            f"{base_name}-dev",
            f"{base_name}-internal",
            f"{base_name}-data",
            f"{base_name}-backup",
            f"{base_name}-logs",
            f"{base_name}-files"
        ]
        
        self.log(scan, f"Running cloud enumeration for {len(permutations)} permutations...")
        
        findings.extend(self._check_aws_s3(permutations, scan))
        findings.extend(self._check_azure_blob(permutations, scan))
        findings.extend(self._check_gcp_bucket(permutations, scan))
        
        return findings

    def _check_aws_s3(self, permutations: List[str], scan) -> List[FindingData]:
        findings = []
        for name in permutations:
            url = f"https://{name}.s3.amazonaws.com"
            try:
                resp = requests.get(url, timeout=5)
                # 200 means public listable
                if resp.status_code == 200:
                    # Content Analysis: Check for sensitive file extensions in the XML
                    sensitive_hits = re.findall(r"<Key>(.*?\.(?:sql|zip|bak|env|pdf|docx|xlsx))</Key>", resp.text, re.I)
                    
                    description = f"An AWS S3 bucket named '{name}' is publicly listable at {url}."
                    severity = Severity.HIGH
                    if sensitive_hits:
                        severity = Severity.CRITICAL
                        description += f"\n\n**CRITICAL**: Found {len(sensitive_hits)} potentially sensitive files in the bucket index: {', '.join(sensitive_hits[:5])}..."

                    findings.append(FindingData(
                        title=f"Public AWS S3 Bucket Exposed: {name}",
                        description=description,
                        severity=severity,
                        category="Cloud Exposure",
                        evidence={
                            "url": url, 
                            "status_code": resp.status_code, 
                            "sensitive_files": sensitive_hits[:10],
                            "headers": dict(resp.headers)
                        },
                        request=f"GET / HTTP/1.1\nHost: {name}.s3.amazonaws.com",
                        response=f"HTTP/1.1 200 OK\n\n{resp.text[:500]}...",
                        poc=f"aws s3 ls s3://{name} --no-sign-request",
                        plugin_slug=self.slug,
                        confidence=100,
                        is_verified=True
                    ))
                elif resp.status_code == 403:
                    # Bucket exists but list is forbidden. Still interesting.
                    findings.append(FindingData(
                        title=f"AWS S3 Bucket Found (Forbidden): {name}",
                        description=f"An AWS S3 bucket named '{name}' exists but listing is forbidden. It may still contain public objects if individual ACLs are weak.",
                        severity=Severity.INFO,
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": 403},
                        plugin_slug=self.slug,
                        confidence=90
                    ))
            except Exception:
                continue
        return findings

    def _check_azure_blob(self, permutations: List[str], scan) -> List[FindingData]:
        findings = []
        containers = ["public", "assets", "backup", "files", "uploads", "logs", "internal"]
        for name in permutations:
            for container in containers:
                url = f"https://{name}.blob.core.windows.net/{container}?restype=container&comp=list"
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        findings.append(FindingData(
                            title=f"Public Azure Blob Container Exposed: {name}/{container}",
                            description=f"An Azure Blob container '{container}' in storage account '{name}' is publicly listable.",
                            severity=Severity.HIGH,
                            category="Cloud Exposure",
                            evidence={"url": url, "status_code": resp.status_code},
                            request=f"GET /{container}?restype=container&comp=list HTTP/1.1\nHost: {name}.blob.core.windows.net",
                            response=f"HTTP/1.1 200 OK\n\n{resp.text[:500]}...",
                            poc=f"curl -i '{url}'",
                            plugin_slug=self.slug,
                            confidence=100,
                            is_verified=True
                        ))
                except Exception:
                    continue
        return findings

    def _check_gcp_bucket(self, permutations: List[str], scan) -> List[FindingData]:
        findings = []
        for name in permutations:
            url = f"https://storage.googleapis.com/{name}"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    findings.append(FindingData(
                        title=f"Public GCP Bucket Exposed: {name}",
                        description=f"A GCP Storage bucket named '{name}' is publicly accessible and listable.",
                        severity=Severity.HIGH,
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": resp.status_code},
                        request=f"GET / HTTP/1.1\nHost: storage.googleapis.com\nPath: /{name}",
                        response=f"HTTP/1.1 200 OK\n\n{resp.text[:500]}...",
                        poc=f"gsutil ls gs://{name}",
                        plugin_slug=self.slug,
                        confidence=100,
                        is_verified=True
                    ))
            except Exception:
                continue
        return findings

    def verify(self, finding: "Finding") -> bool:
        """Simple re-check of the bucket status."""
        url = finding.evidence.get("url")
        if not url: return False
        try:
            resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except:
            return False
