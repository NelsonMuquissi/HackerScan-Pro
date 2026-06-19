import logging
import subprocess
import json
import tempfile
import os
import asyncio
from typing import List, AsyncGenerator
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)


@register
class SSLyzeAuditStrategy(BaseScanStrategy):
    """
    SSL/TLS audit engine using sslyze.
    Checks for weak ciphers, expired certs, and poor configurations.
    """
    slug = "sslyze_audit"
    name = "SSL/TLS Audit"

    async def run_async(self, target: "ScanTarget", scan: "Scan" = None) -> AsyncGenerator[FindingData, None]:
        host = target.host

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            output_file = tf.name

        try:
            cmd = [
                "sslyze",
                host,
                "--json_out", output_file,
            ]

            self.log(scan, f"Starting SSL/TLS audit for {host}...")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()

            if process.returncode != 0 and not os.path.exists(output_file):
                yield FindingData(
                    title="SSL/TLS Audit Error",
                    description=f"sslyze could not connect to {host}. It may not support HTTPS.",
                    severity=Severity.INFO,
                    evidence={"error": stderr.decode()[:1000]},
                    remediation="Verify that the target supports HTTPS on port 443.",
                    poc=f"sslyze {host}",
                    plugin_slug=self.slug
                )
                return

            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    try:
                        data = json.loads(f.read())
                    except json.JSONDecodeError:
                        logger.warning("sslyze produced invalid JSON for %s", host)
                        return

                    if not isinstance(data, dict):
                        logger.warning("sslyze produced non-dict JSON for %s", host)
                        return

                    for server_result in data.get("server_scan_results", []):
                        if not server_result:
                            continue
                        scan_res = server_result.get("scan_result", {})
                        common_poc = f"sslyze {host}"

                        # Heartbleed
                        heartbleed = scan_res.get("heartbleed") or {}
                        hb_res = heartbleed.get("result") or {}
                        if hb_res.get("is_vulnerable_to_heartbleed"):
                            yield FindingData(
                                title="Heartbleed Vulnerability",
                                severity=Severity.CRITICAL,
                                description=f"The server at {host} is vulnerable to Heartbleed (CVE-2014-0160).",
                                remediation="Patch OpenSSL to a version >= 1.0.1g and regenerate all keys/certificates.",
                                evidence=hb_res,
                                cvss_score=7.5,
                                poc=common_poc,
                                plugin_slug=self.slug
                            )

                        # OpenSSL CCS injection (CVE-2014-0224)
                        ccs = scan_res.get("openssl_ccs_injection") or {}
                        ccs_res = ccs.get("result") or {}
                        if ccs_res.get("is_vulnerable_to_ccs_injection"):
                            yield FindingData(
                                title="OpenSSL CCS Injection Vulnerability",
                                severity=Severity.HIGH,
                                description=f"Server at {host} is vulnerable to OpenSSL CCS Injection (CVE-2014-0224).",
                                remediation="Update OpenSSL to a patched version.",
                                evidence=ccs_res,
                                cvss_score=6.8,
                                poc=common_poc,
                                plugin_slug=self.slug
                            )

                        # Deprecated TLS protocols
                        deprecated_protos = []
                        for proto_key, proto_name in [
                            ("ssl_2_0_cipher_suites", "SSLv2"),
                            ("ssl_3_0_cipher_suites", "SSLv3"),
                            ("tls_1_0_cipher_suites", "TLS 1.0"),
                            ("tls_1_1_cipher_suites", "TLS 1.1"),
                        ]:
                            proto_result = scan_res.get(proto_key) or {}
                            proto_res = proto_result.get("result") or {}
                            accepted = proto_res.get("accepted_cipher_suites") or []
                            if accepted:
                                deprecated_protos.append(proto_name)

                        if deprecated_protos:
                            yield FindingData(
                                title="Deprecated TLS/SSL Protocols Enabled",
                                severity=Severity.MEDIUM,
                                description=(
                                    f"The server at {host} supports deprecated protocols: "
                                    f"{', '.join(deprecated_protos)}. "
                                    "These protocols are considered insecure and should be disabled."
                                ),
                                remediation=(
                                    "Disable SSLv2, SSLv3, TLS 1.0, and TLS 1.1. "
                                    "Configure the server to support only TLS 1.2 and TLS 1.3."
                                ),
                                evidence={"deprecated_protocols": deprecated_protos},
                                cvss_score=5.3,
                                poc=common_poc,
                                plugin_slug=self.slug
                            )

        except Exception as e:
            logger.error(f"SSLyze error: {e}")
            self.log(scan, f"Engine error: {str(e)}")
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Verify by re-running sslyze for the specific target asynchronously.
        """
        from asgiref.sync import sync_to_async
        scan = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()

        found = False
        async for r in self.run_async(target):
            if r.title == finding.title:
                found = True
                break
        
        if found:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
            
        return False
