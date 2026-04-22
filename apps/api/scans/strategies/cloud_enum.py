import logging
import requests
import urllib.parse
from typing import List, Optional
from datetime import datetime

from .base import BaseScanStrategy, FindingData, register

logger = logging.getLogger(__name__)


@register
class CloudExposureStrategy(BaseScanStrategy):
    """
    CloudExposureStrategy checks for exposed Cloud Storage buckets
    (AWS S3, Azure Blob, GCP Storage) based on the target domain permutations.
    """
    name = "Cloud Exposure Enum"
    slug = "cloud_exposure"
    description = "Checks for exposed Cloud Storage buckets."

        
    def run(self, target, scan) -> List[FindingData]:
        findings = []
        target_host = target.host
        domain = urllib.parse.urlparse(target_host).netloc or target_host
        domain_parts = domain.split('.')
        base_name = domain_parts[0] if domain_parts else domain
        
        # Generates common bucket name permutations
        permutations = [
            base_name,
            domain.replace('.', '-'),
            f"{base_name}-assets",
            f"{base_name}-public",
            f"{base_name}-prod",
            f"{base_name}-dev",
            f"{base_name}-backup"
        ]
        
        findings.extend(self._check_aws_s3(permutations))
        findings.extend(self._check_azure_blob(permutations))
        findings.extend(self._check_gcp_bucket(permutations))
        
        return findings

    def _check_aws_s3(self, permutations: List[str]) -> List[FindingData]:
        findings = []
        for name in permutations:
            url = f"https://{name}.s3.amazonaws.com"
            try:
                # Use a fast HEAD or GET request
                resp = requests.get(url, timeout=5)
                # 200 means public listable, 403 means it exists but forbidden (still good to know), 404 is not found
                if resp.status_code == 200:
                    findings.append(FindingData(
                        title=f"Public AWS S3 Bucket Exposed: {name}",
                        description=f"An AWS S3 bucket named '{name}' is publicly accessible and listable at {url}.",
                        severity="HIGH",
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": resp.status_code, "headers": dict(resp.headers)},
                        confidence=100
                    ))
                elif resp.status_code == 403:
                    findings.append(FindingData(
                        title=f"AWS S3 Bucket Found (Access Denied): {name}",
                        description=f"An AWS S3 bucket named '{name}' exists but listing is forbidden. It may still contain public objects.",
                        severity="INFO",
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=90
                    ))
            except requests.RequestException as e:
                logger.debug(f"CloudExposure check failed for {url}: {e}")
        return findings

    def _check_azure_blob(self, permutations: List[str]) -> List[FindingData]:
        findings = []
        for name in permutations:
            # Check common container names like 'public', 'assets', 'backup' within the storage account
            containers = ["public", "assets", "backup", "files"]
            for container in containers:
                url = f"https://{name}.blob.core.windows.net/{container}?restype=container&comp=list"
                try:
                    resp = requests.get(url, timeout=5)
                    if resp.status_code == 200:
                        findings.append(FindingData(
                            title=f"Public Azure Blob Container Exposed: {name}/{container}",
                            description=f"An Azure Blob container '{container}' in storage account '{name}' is publicly listable.",
                            severity="HIGH",
                            category="Cloud Exposure",
                            evidence={"url": url, "status_code": resp.status_code},
                            confidence=100
                        ))
                except requests.RequestException as e:
                    logger.debug(f"CloudExposure check failed for Azure {url}: {e}")
        return findings

    def _check_gcp_bucket(self, permutations: List[str]) -> List[FindingData]:
        findings = []
        for name in permutations:
            url = f"https://storage.googleapis.com/{name}"
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    findings.append(FindingData(
                        title=f"Public GCP Bucket Exposed: {name}",
                        description=f"A GCP Storage bucket named '{name}' is publicly accessible and listable.",
                        severity="HIGH",
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=100
                    ))
                elif resp.status_code == 403:
                    findings.append(FindingData(
                        title=f"GCP Bucket Found (Access Denied): {name}",
                        description=f"A GCP Storage bucket named '{name}' exists but listing is forbidden.",
                        severity="INFO",
                        category="Cloud Exposure",
                        evidence={"url": url, "status_code": resp.status_code},
                        confidence=90
                    ))
            except requests.RequestException as e:
                logger.debug(f"CloudExposure check failed for GCP {url}: {e}")
        return findings
