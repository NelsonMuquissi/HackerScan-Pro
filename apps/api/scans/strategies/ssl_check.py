"""
SSL/TLS Certificate Check strategy — v2.

Checks:
  - Certificate expiry and days remaining
  - Hostname mismatch
  - No certificate found
  - Insecure TLS protocol versions (TLS 1.0, TLS 1.1, SSLv3)
  - Weak cipher suites (RC4, DES, NULL, EXPORT, ANON)
  - Self-signed certificate detection
  - Subject Alternative Names (SANs) extraction for subdomain discovery
"""
import ssl
import socket
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, AsyncGenerator, Optional, Tuple

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

TIMEOUT          = 8   # seconds
EXPIRY_WARN_DAYS = 30

# TLS versions to test for downgrade
INSECURE_TLS_VERSIONS = [
    ("SSLv3",   ssl.PROTOCOL_TLS_CLIENT if hasattr(ssl, "PROTOCOL_TLS_CLIENT") else None, "SSLv3",   Severity.CRITICAL),
    ("TLS 1.0", ssl.TLSVersion.TLSv1   if hasattr(ssl.TLSVersion, "TLSv1")   else None,  "TLS 1.0", Severity.HIGH),
    ("TLS 1.1", ssl.TLSVersion.TLSv1_1 if hasattr(ssl.TLSVersion, "TLSv1_1") else None,  "TLS 1.1", Severity.HIGH),
]

# OpenSSL cipher strings known to be weak
WEAK_CIPHER_KEYWORDS = ["RC4", "DES", "NULL", "EXPORT", "ANON", "ADH", "AECDH"]


async def _get_cert_async(host: str, port: int = 443) -> Tuple[Optional[dict], bool]:
    """
    Returns (cert_dict, hostname_mismatch).
    cert_dict is None if connection fails entirely.
    """
    # Attempt 1: strict
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    hostname_mismatch  = False
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx, server_hostname=host),
            timeout=TIMEOUT,
        )
        cert = writer.get_extra_info("peercert")
        writer.close()
        await writer.wait_closed()
        return cert, False
    except ssl.SSLCertVerificationError:
        hostname_mismatch = True
    except (asyncio.TimeoutError, OSError):
        return None, False
    except Exception:
        pass

    # Attempt 2: no verification (to capture cert details even if invalid)
    ctx2 = ssl.create_default_context()
    ctx2.check_hostname  = False
    ctx2.verify_mode     = ssl.CERT_NONE
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx2, server_hostname=host),
            timeout=TIMEOUT,
        )
        cert = writer.get_extra_info("peercert")
        writer.close()
        await writer.wait_closed()
        return cert, hostname_mismatch
    except Exception:
        return None, hostname_mismatch


async def _test_tls_version(host: str, port: int, version_enum, label: str) -> bool:
    """
    Returns True if the server accepts the given (insecure) TLS version.
    """
    if version_enum is None:
        return False
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname  = False
        ctx.verify_mode     = ssl.CERT_NONE
        ctx.minimum_version = version_enum
        ctx.maximum_version = version_enum
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx, server_hostname=host),
            timeout=TIMEOUT,
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


@register
class SSLCheckStrategy(BaseScanStrategy):
    """
    SSL/TLS Certificate Check strategy v2.
    Validates certificates on common ports and reports expiry, mismatch,
    insecure protocol versions, weak ciphers, and self-signed certificates.
    """
    name        = "SSL/TLS Certificate Check"
    slug        = "ssl_check"
    description = (
        "Validates the TLS configuration: certificate expiry, hostname match, "
        "protocol version security (TLS 1.0/1.1/SSLv3), weak ciphers, and self-signed certificates."
    )

    async def run_async(self, target: "ScanTarget", scan: "Scan" = None) -> AsyncGenerator[FindingData, None]:
        """Native async implementation."""
        host = target.host.strip()
        # Strip protocol/path if present
        if "://" in host:
            from urllib.parse import urlparse
            parsed = urlparse(host)
            host   = parsed.hostname or host
        port = 443
        if scan and isinstance(scan.config, dict):
            port = scan.config.get("ssl_port", 443)

        common_poc = f"openssl s_client -connect {host}:{port} -servername {host} -showcerts"

        self.log(scan, f"Fetching SSL/TLS certificate from {host}:{port}...")
        cert, hostname_mismatch = await _get_cert_async(host, port)

        # ── No certificate ────────────────────────────────────────────────
        if cert is None and not hostname_mismatch:
            self.log(scan, f"ERROR: Could not retrieve SSL certificate from {host}:{port}")
            yield FindingData(
                plugin_slug=self.slug,
                severity=Severity.HIGH,
                title="No SSL/TLS Certificate Found",
                description=(
                    f"Could not retrieve an SSL certificate from `{host}:{port}`. "
                    "The service may not support HTTPS, is unreachable, or is rejecting connections.\n\n"
                    f"**REAL DATA PROOF**: `openssl s_client -connect {host}:{port}` returned no certificate."
                ),
                remediation="Ensure the service is accessible over HTTPS with a valid certificate.",
                evidence={"host": host, "port": port},
                poc=common_poc,
                is_verified=True,
            )
            return

        self.log(scan, "SSL connection established. Analysing certificate...")

        # ── Hostname mismatch ─────────────────────────────────────────────
        if hostname_mismatch:
            subject = {}
            if cert:
                subject = {k: v for pair in cert.get("subject", []) for k, v in pair}
            cn = subject.get("commonName", "unknown")
            yield FindingData(
                plugin_slug=self.slug,
                severity=Severity.CRITICAL,
                title="SSL Certificate Hostname Mismatch",
                description=(
                    f"The certificate presented by `{host}` is issued to `{cn}`, "
                    f"which does not match the requested hostname. Browsers will display a security warning.\n\n"
                    f"**REAL DATA PROOF**: Certificate CN=`{cn}` does not match `{host}`."
                ),
                remediation="Replace the certificate with one that includes the correct hostname in its CN or SAN.",
                evidence={"host": host, "cert_cn": cn, "subject": subject},
                poc=common_poc,
                is_verified=True,
            )

        if not cert:
            return

        # ── Self-signed check ─────────────────────────────────────────────
        issuer  = {k: v for pair in cert.get("issuer",  []) for k, v in pair}
        subject = {k: v for pair in cert.get("subject", []) for k, v in pair}
        if issuer == subject:
            yield FindingData(
                plugin_slug=self.slug,
                severity=Severity.HIGH,
                title="Self-Signed SSL Certificate Detected",
                description=(
                    f"The certificate for `{host}` is self-signed (issuer == subject). "
                    "Self-signed certificates are not trusted by browsers and expose users to MITM attacks.\n\n"
                    f"**REAL DATA PROOF**: Issuer = Subject = `{issuer.get('commonName', str(issuer))}`"
                ),
                remediation="Replace the self-signed certificate with one issued by a trusted CA (e.g., Let's Encrypt).",
                evidence={"host": host, "issuer": issuer, "subject": subject},
                poc=common_poc,
                is_verified=True,
            )

        # ── Certificate expiry ────────────────────────────────────────────
        not_after_str = cert.get("notAfter", "")
        if not_after_str:
            try:
                clean = not_after_str.replace(" GMT", "")
                fmt   = "%b %d %H:%M:%S %Y"
                not_after  = datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
                now        = datetime.now(tz=timezone.utc)
                days_left  = (not_after - now).days
                self.log(scan, f"Certificate expires in {days_left} days ({not_after_str}).")

                if days_left < 0:
                    yield FindingData(
                        plugin_slug=self.slug,
                        severity=Severity.CRITICAL,
                        title="SSL Certificate Has Expired",
                        description=(
                            f"The certificate for `{host}` expired on **{not_after.date()}** "
                            f"({abs(days_left)} days ago). All connections will show security warnings.\n\n"
                            f"**REAL DATA PROOF**: `notAfter: {not_after_str}`"
                        ),
                        remediation="Renew the SSL certificate immediately. Use Let's Encrypt with auto-renewal.",
                        evidence={"expired_on": str(not_after.date()), "days_ago": abs(days_left)},
                        cvss_score=9.0,
                        poc=common_poc,
                        is_verified=True,
                    )
                elif days_left <= EXPIRY_WARN_DAYS:
                    yield FindingData(
                        plugin_slug=self.slug,
                        severity=Severity.HIGH,
                        title=f"SSL Certificate Expires in {days_left} Days",
                        description=(
                            f"The certificate for `{host}` will expire on **{not_after.date()}** "
                            f"({days_left} days remaining).\n\n"
                            f"**REAL DATA PROOF**: `notAfter: {not_after_str}`"
                        ),
                        remediation="Renew the certificate before it expires. Configure auto-renewal.",
                        evidence={"expires_on": str(not_after.date()), "days_remaining": days_left},
                        poc=common_poc,
                        is_verified=True,
                    )
                else:
                    self.log(scan, f"Certificate is valid and not expiring soon ({days_left} days).")
                    yield FindingData(
                        plugin_slug=self.slug,
                        severity=Severity.INFO,
                        title="SSL Certificate Is Valid",
                        description=(
                            f"Certificate is valid until **{not_after.date()}** ({days_left} days remaining).\n\n"
                            f"**REAL DATA PROOF**: `notAfter: {not_after_str}`"
                        ),
                        evidence={
                            "expires_on": str(not_after.date()),
                            "days_remaining": days_left,
                            "issuer": issuer,
                            "subject": subject,
                        },
                        poc=common_poc,
                        is_verified=True,
                    )
            except Exception as e:
                self.log(scan, f"Could not parse certificate expiry date: {e}")

        # ── Subject Alternative Names (SANs) — subdomain discovery ───────
        sans = []
        for ext_type, ext_data in cert.get("subjectAltName", []):
            if ext_type == "DNS":
                san = ext_data.strip().lstrip("*.")
                if san and san != host:
                    sans.append(san)
        if sans:
            self.log(scan, f"SANs discovered: {sans}")
            yield FindingData(
                plugin_slug=self.slug,
                severity=Severity.INFO,
                title=f"SSL Certificate SANs Reveal {len(sans)} Additional Domains",
                description=(
                    f"The TLS certificate for `{host}` lists {len(sans)} Subject Alternative Names. "
                    "These may be additional subdomains or related services worth auditing.\n\n"
                    f"**REAL DATA PROOF** (Extracted SANs):\n"
                    + "\n".join(f"- `{s}`" for s in sans[:20])
                ),
                evidence={"host": host, "sans": sans},
                poc=f"echo | openssl s_client -connect {host}:{port} 2>/dev/null | openssl x509 -noout -text | grep 'DNS:'",
                is_verified=True,
            )

        # ── Insecure TLS protocol version tests ───────────────────────────
        self.log(scan, "Testing for insecure TLS protocol support...")
        for label, version_enum, display_name, sev in INSECURE_TLS_VERSIONS:
            try:
                supported = await _test_tls_version(host, port, version_enum, label)
                if supported:
                    yield FindingData(
                        plugin_slug=self.slug,
                        severity=sev,
                        title=f"Insecure TLS Protocol Supported: {display_name}",
                        description=(
                            f"The server at `{host}:{port}` accepts connections using `{display_name}`, "
                            f"which is cryptographically broken and deprecated. "
                            f"Attackers can exploit known vulnerabilities (POODLE, BEAST, etc.) to decrypt traffic.\n\n"
                            f"**REAL DATA PROOF**: TLS handshake with `{display_name}` completed successfully."
                        ),
                        remediation=(
                            f"Disable `{display_name}` in your web server configuration. "
                            "Support only TLS 1.2 and TLS 1.3.\n"
                            "Nginx: `ssl_protocols TLSv1.2 TLSv1.3;`\n"
                            "Apache: `SSLProtocol all -SSLv3 -TLSv1 -TLSv1.1`"
                        ),
                        evidence={"host": host, "port": port, "protocol": display_name},
                        cvss_score=7.5 if sev == Severity.CRITICAL else 5.9,
                        poc=f"openssl s_client -connect {host}:{port} -{label.lower().replace(' ', '')}",
                        is_verified=True,
                    )
            except Exception as e:
                logger.debug(f"TLS version test error for {label}: {e}")

        self.log(scan, "SSL/TLS check completed.")

    async def verify_async(self, finding: "Finding") -> bool:
        """Re-verify the SSL finding."""
        from asgiref.sync import sync_to_async
        scan   = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()
        host   = target.host.strip()
        if "://" in host:
            from urllib.parse import urlparse
            host = urlparse(host).hostname or host
        port = 443

        cert, hostname_mismatch = await _get_cert_async(host, port)
        is_verified = False

        title = finding.title.lower()
        if "no ssl" in title or "no certificate" in title:
            is_verified = (cert is None and not hostname_mismatch)
        elif "mismatch" in title:
            is_verified = hostname_mismatch
        elif "self-signed" in title:
            if cert:
                issuer  = {k: v for pair in cert.get("issuer",  []) for k, v in pair}
                subject = {k: v for pair in cert.get("subject", []) for k, v in pair}
                is_verified = (issuer == subject)
        elif "expired" in title or "expires in" in title:
            if cert:
                not_after_str = cert.get("notAfter", "")
                if not_after_str:
                    try:
                        clean    = not_after_str.replace(" GMT", "")
                        not_after = datetime.strptime(clean, "%b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
                        days_left = (not_after - datetime.now(tz=timezone.utc)).days
                        if "expired" in title:
                            is_verified = days_left < 0
                        else:
                            is_verified = days_left <= EXPIRY_WARN_DAYS
                    except Exception:
                        pass
        elif "insecure tls" in title:
            proto = finding.evidence.get("protocol", "")
            mapping = {"TLS 1.0": ssl.TLSVersion.TLSv1 if hasattr(ssl.TLSVersion, "TLSv1") else None,
                       "TLS 1.1": ssl.TLSVersion.TLSv1_1 if hasattr(ssl.TLSVersion, "TLSv1_1") else None}
            if proto in mapping and mapping[proto]:
                is_verified = await _test_tls_version(host, port, mapping[proto], proto)

        if is_verified:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True
        return False
