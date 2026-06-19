import logging
import urllib.parse
import re
import asyncio
from typing import List, Optional, AsyncGenerator
from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

@register
class CloudExposureStrategy(BaseScanStrategy):
    """
    Advanced CloudExposureStrategy checks for exposed Cloud Storage buckets
    (AWS S3, Azure Blob, GCP Storage) with smarter permutations and content analysis.
    Native async implementation for massive concurrency.
    """
    name = "Cloud Exposure Enum"
    slug = "cloud_exposure"
    description = "Checks for exposed Cloud Storage buckets (S3, Azure, GCP)."


    async def run_async(self, target, scan=None):
        """
        Native async implementation for improved performance.
        Yields FindingData as they are identified.
        """
        from scans.utils import check_dns_resolution_async
        
        target_host = target.host
        domain = urllib.parse.urlparse(target_host).netloc or target_host
        domain_parts = domain.split('.')
        base_name = domain_parts[0] if domain_parts else domain
        
        # Advanced but balanced bucket name permutations
        # Reduced to most critical ones to prevent DNS saturation
        suffixes = [
            "assets", "public", "prod", "staging", "dev", "test",
            "internal", "data", "backup", "logs", "files", "storage",
            "db", "config", "secrets", "uploads"
        ]
        
        permutations = [base_name, domain.replace('.', '-')]
        for s in suffixes:
            permutations.append(f"{base_name}-{s}")
        
        self.log(scan, f"Running cloud enumeration for {len(permutations)} permutations (with DNS pre-checks)...")
        
        # Concurrency limit
        semaphore = asyncio.Semaphore(15)
        
        tasks = []
        for name in permutations:
            tasks.append(self._check_aws_s3_async(name, semaphore, scan))
            tasks.append(self._check_azure_blob_async(name, semaphore, scan))
            tasks.append(self._check_gcp_bucket_async(name, semaphore, scan))
            
        for task in asyncio.as_completed(tasks):
            try:
                results = await task
                if results:
                    for finding in results:
                        yield finding
            except Exception as e:
                logger.error(f"Cloud enum task error: {e}")

    async def _check_aws_s3_async(self, name: str, semaphore, scan) -> List[FindingData]:
        from scans.utils import make_evidence_request_async, check_dns_resolution_async
        findings = []
        hostname = f"{name}.s3.amazonaws.com"
        url = f"https://{hostname}"
        
        async with semaphore:
            # 🎯 DNS Pre-check to avoid massive connection timeouts
            if not await check_dns_resolution_async(hostname):
                return []

            try:
                resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
                if not resp:
                    return []
                
                # 200 means public listable
                if resp.status_code == 200:
                    sensitive_hits = re.findall(r"<Key>(.*?\.(?:sql|zip|bak|env|pdf|docx|xlsx))</Key>", resp.text, re.I)
                    
                    description = f"An AWS S3 bucket named '{name}' is publicly listable at {url}."
                    severity = Severity.HIGH
                    proof_snippet = ""
                    
                    if sensitive_hits:
                        severity = Severity.CRITICAL
                        description += f"\n\n**CRITICAL**: Found {len(sensitive_hits)} potentially sensitive files."
                        # 🚀 REAL DATA PROOF: Download a snippet of the first sensitive file
                        proof_snippet = await self._get_proof_snippet_async(url, sensitive_hits[0])
                        if proof_snippet:
                            description += f"\n\n**REAL DATA PROOF** (from {sensitive_hits[0]}):\n```\n{proof_snippet}\n```"

                    findings.append(FindingData(
                        title=f"Public AWS S3 Bucket Exposed: {name}",
                        description=description,
                        severity=severity,
                        category="Cloud Exposure",
                        evidence={
                            "url": url, 
                            "status_code": resp.status_code, 
                            "sensitive_files": sensitive_hits[:10],
                            "proof_snippet": proof_snippet,
                            "headers": dict(resp.headers)
                        },
                        request=req_dump,
                        response=res_dump,
                        poc=f"aws s3 ls s3://{name} --no-sign-request",
                        plugin_slug=self.slug,
                        confidence=100,
                        is_verified=True
                    ))

                elif resp.status_code == 403:
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
                pass
        return findings

    async def _check_azure_blob_async(self, name: str, semaphore, scan) -> List[FindingData]:
        from scans.utils import make_evidence_request_async, check_dns_resolution_async
        findings = []
        if not re.match(r"^[a-z0-9]{3,24}$", name):
            return []
            
        hostname = f"{name}.blob.core.windows.net"
        
        async with semaphore:
            # 🎯 DNS Pre-check
            if not await check_dns_resolution_async(hostname):
                return []

            containers = ["public", "assets", "backup", "files", "uploads", "logs", "internal", "data", "conf", "config"]
            
            for container in containers:
                url = f"https://{hostname}/{container}?restype=container&comp=list"
                try:
                    resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
                    if not resp or resp.status_code != 200:
                        continue
                        
                    sensitive_hits = self._get_sensitive_files(resp.text)
                    
                    description = f"An Azure Blob container '{container}' in storage account '{name}' is publicly listable."
                    severity = Severity.HIGH
                    proof_snippet = ""
                    
                    if sensitive_hits:
                        severity = Severity.CRITICAL
                        description += f"\n\n**CRITICAL**: Found {len(sensitive_hits)} potentially sensitive files."
                        # 🚀 REAL DATA PROOF: Download a snippet
                        proof_snippet = await self._get_proof_snippet_async(f"https://{hostname}/{container}", sensitive_hits[0])
                        if proof_snippet:
                            description += f"\n\n**REAL DATA PROOF** (from {sensitive_hits[0]}):\n```\n{proof_snippet}\n```"

                    findings.append(FindingData(
                        title=f"Public Azure Blob Container Exposed: {name}/{container}",
                        description=description,
                        severity=severity,
                        category="Cloud Exposure",
                        evidence={
                            "url": url, 
                            "status_code": resp.status_code,
                            "sensitive_files": sensitive_hits[:20],
                            "proof_snippet": proof_snippet,
                            "provider": "Azure"
                        },
                        request=req_dump,
                        response=res_dump,
                        poc=f"curl -i '{url}'",
                        plugin_slug=self.slug,
                        is_verified=True
                    ))
                except Exception:
                    continue
        return findings

    async def _check_gcp_bucket_async(self, name: str, semaphore, scan) -> List[FindingData]:
        from scans.utils import make_evidence_request_async
        findings = []
        url = f"https://storage.googleapis.com/{name}"
        async with semaphore:
            try:
                resp, req_dump, res_dump, poc = await make_evidence_request_async(url, timeout=5)
                if not resp or resp.status_code != 200:
                    return []
                    
                sensitive_hits = self._get_sensitive_files(resp.text)
                
                description = f"A GCP Storage bucket named '{name}' is publicly accessible and listable."
                severity = Severity.HIGH
                proof_snippet = ""
                
                if sensitive_hits:
                    severity = Severity.CRITICAL
                    description += f"\n\n**CRITICAL**: Found {len(sensitive_hits)} potentially sensitive files."
                    # 🚀 REAL DATA PROOF: Download a snippet
                    proof_snippet = await self._get_proof_snippet_async(url, sensitive_hits[0])
                    if proof_snippet:
                        description += f"\n\n**REAL DATA PROOF** (from {sensitive_hits[0]}):\n```\n{proof_snippet}\n```"

                findings.append(FindingData(
                    title=f"Public GCP Bucket Exposed: {name}",
                    description=description,
                    severity=severity,
                    category="Cloud Exposure",
                    evidence={
                        "url": url, 
                        "status_code": resp.status_code,
                        "sensitive_files": sensitive_hits[:20],
                        "proof_snippet": proof_snippet,
                        "provider": "GCP"
                    },
                    request=req_dump,
                    response=res_dump,
                    poc=f"gsutil ls gs://{name}",
                    plugin_slug=self.slug,
                    is_verified=True
                ))
            except Exception:
                pass
        return findings

    def _get_sensitive_files(self, text: str) -> List[str]:
        return re.findall(r"<Key>(.*?\.(?:sql|zip|bak|env|pdf|docx|xlsx))</Key>", text, re.I)

    async def _get_proof_snippet_async(self, bucket_url: str, file_key: str) -> Optional[str]:
        """Downloads a small snippet of a sensitive file to prove exposure."""
        from scans.utils import make_evidence_request_async
        url = f"{bucket_url.rstrip('/')}/{file_key}"
        try:
            resp, _, _, _ = await make_evidence_request_async(url, timeout=5)
            if resp and resp.status_code == 200:
                content = resp.text
                return content[:500] + ("..." if len(content) > 500 else "")
        except:
            pass
        return None

    async def verify_async(self, finding) -> bool:
        """Async re-check of the bucket status and data proof."""
        from scans.utils import make_evidence_request_async
        url = finding.evidence.get("url")
        sensitive_files = finding.evidence.get("sensitive_files", [])
        
        if not url: return False
        try:
            resp, req, res, poc = await make_evidence_request_async(url, timeout=5)
            if resp and resp.status_code == 200:
                finding.request = req
                finding.response = res
                finding.is_verified = True
                
                # 🚀 REAL DATA PROOF: Download a snippet of the first sensitive file
                if sensitive_files:
                    snippet = await self._get_proof_snippet_async(url, sensitive_files[0])
                    if snippet:
                        finding.description += f"\n\n**REAL DATA PROOF** (from {sensitive_files[0]}):\n```\n{snippet}\n```"
                        finding.evidence["proof_snippet"] = snippet

                # Save asynchronously
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True
        except:
            pass
        return False
