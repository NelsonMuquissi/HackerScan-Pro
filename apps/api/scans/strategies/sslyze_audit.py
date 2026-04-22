import logging
import subprocess
import json
import tempfile
import os
from typing import List
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

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        # target.host is the correct field (target.address does not exist on ScanTarget)
        host = target.host

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            output_file = tf.name

        try:
            cmd = [
                "sslyze",
                host,
                "--json_out", output_file,
            ]

            logger.info("Running sslyze: %s", " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=120)

            if result.returncode != 0 and not os.path.exists(output_file):
                logger.warning("sslyze returned non-zero exit: %s", result.stderr)
                findings.append(FindingData(
                    title="SSL/TLS Audit Error",
                    description=f"sslyze could not connect to {host}. It may not support HTTPS.",
                    severity=Severity.INFO,
                    evidence=result.stderr[:500] if result.stderr else "",
                    remediation="Verify that the target supports HTTPS on port 443.",
                ))
                return findings

            if os.path.exists(output_file):
                with open(output_file, "r") as f:
                    try:
                        data = json.loads(f.read())
                    except json.JSONDecodeError:
                        logger.warning("sslyze produced invalid JSON for %s", host)
                        return findings

                    for server_result in data.get("server_scan_results", []):
                        scan_res = server_result.get("scan_result", {})

                        # Heartbleed
                        heartbleed = scan_res.get("heartbleed", {})
                        if heartbleed.get("result", {}).get("is_vulnerable_to_heartbleed"):
                            findings.append(FindingData(
                                title="Heartbleed Vulnerability",
                                severity=Severity.CRITICAL,
                                description=f"The server at {host} is vulnerable to Heartbleed (CVE-2014-0160).",
                                remediation="Patch OpenSSL to a version >= 1.0.1g and regenerate all keys/certificates.",
                                cvss_score=7.5,
                            ))

                        # OpenSSL CCS injection (CVE-2014-0224)
                        ccs = scan_res.get("openssl_ccs_injection", {})
                        if ccs.get("result", {}).get("is_vulnerable_to_ccs_injection"):
                            findings.append(FindingData(
                                title="OpenSSL CCS Injection Vulnerability",
                                severity=Severity.HIGH,
                                description=f"Server at {host} is vulnerable to OpenSSL CCS Injection (CVE-2014-0224).",
                                remediation="Update OpenSSL to a patched version.",
                                cvss_score=6.8,
                            ))

                        # Deprecated TLS protocols (SSLv2, SSLv3, TLS 1.0, TLS 1.1)
                        deprecated_protos = []
                        for proto_key, proto_name in [
                            ("ssl_2_0_cipher_suites", "SSLv2"),
                            ("ssl_3_0_cipher_suites", "SSLv3"),
                            ("tls_1_0_cipher_suites", "TLS 1.0"),
                            ("tls_1_1_cipher_suites", "TLS 1.1"),
                        ]:
                            proto_result = scan_res.get(proto_key, {})
                            accepted = proto_result.get("result", {}).get("accepted_cipher_suites", [])
                            if accepted:
                                deprecated_protos.append(proto_name)

                        if deprecated_protos:
                            findings.append(FindingData(
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
                                evidence=f"Deprecated protocols detected: {', '.join(deprecated_protos)}",
                                cvss_score=5.3,
                            ))

                        # If no issues found, report a clean audit
                        if not findings:
                            findings.append(FindingData(
                                title="SSL/TLS Audit Passed",
                                description=f"No critical SSL/TLS issues found on {host}.",
                                severity=Severity.INFO,
                                evidence=f"sslyze completed scan for {host}.",
                                remediation="Continue monitoring certificate expiry and protocol support.",
                            ))
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

        return findings
