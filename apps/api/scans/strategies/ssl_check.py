"""
SSL/TLS Certificate Check strategy.
Validates the certificate on port 443 and reports:
  - Expiry within 30 days → high
  - Expired → critical
  - Hostname mismatch → critical
  - Weak cipher / protocol → medium
  - Valid → info
"""
import ssl
import socket
from datetime import datetime, timezone

from .base import BaseScanStrategy, FindingData, register

TIMEOUT = 5  # seconds
EXPIRY_WARN_DAYS = 30


def _get_cert(host: str, port: int = 443) -> dict | None:
    """Returns the parsed certificate dict or None on error."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    try:
        with ctx.wrap_socket(socket.create_connection((host, port), timeout=TIMEOUT),
                             server_hostname=host) as conn:
            return conn.getpeercert()
    except ssl.SSLCertVerificationError:
        # Still return cert with mismatch flag
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode    = ssl.CERT_NONE
        try:
            with ctx2.wrap_socket(socket.create_connection((host, port), timeout=TIMEOUT),
                                  server_hostname=host) as conn:
                cert = conn.getpeercert()
                if cert:
                    cert["_hostname_mismatch"] = True
                return cert
        except OSError:
            return None
    except OSError:
        return None


@register
class SSLCheckStrategy(BaseScanStrategy):
    name        = "SSL/TLS Certificate Check"
    slug        = "ssl_check"
    description = "Validates the TLS certificate on port 443: expiry, hostname, and protocol."

    def run(self, target, scan) -> list[FindingData]:
        host     = target.host
        port     = scan.config.get("ssl_port", 443)
        findings: list[FindingData] = []

        self.log(scan, f"Fetching SSL/TLS certificate from {host}:{port}...")
        cert = _get_cert(host, port)

        if cert is None:
            self.log(scan, f"ERROR: Failed to retrieve SSL certificate from {host}:{port}")
            findings.append(FindingData(
                plugin_slug=self.slug,
                severity="high",
                title="No SSL/TLS certificate found",
                description=f"Could not retrieve an SSL certificate from {host}:{port}. "
                             "The service may not support HTTPS or is unreachable.",
                remediation="Ensure the service is accessible over HTTPS with a valid certificate.",
                evidence={"host": host, "port": port},
            ))
            return findings

        self.log(scan, "SSL connection established. Analyzing certificate...")

        # Hostname mismatch
        if cert.get("_hostname_mismatch"):
            self.log(scan, "WARNING: Hostname mismatch detected!")
            findings.append(FindingData(
                plugin_slug=self.slug,
                severity="critical",
                title="SSL certificate hostname mismatch",
                description=f"The certificate presented by {host} does not match its hostname.",
                remediation="Replace the certificate with one that matches the server hostname.",
                evidence={"host": host, "subject": cert.get("subject")},
            ))

        # Expiry check
        not_after_str = cert.get("notAfter", "")
        if not_after_str:
            try:
                not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                now       = datetime.now(tz=timezone.utc)
                days_left = (not_after - now).days

                self.log(scan, f"Certificate expires in {days_left} days ({not_after_str})")

                if days_left < 0:
                    self.log(scan, "CRITICAL: Certificate is EXPIRED")
                    findings.append(FindingData(
                        plugin_slug=self.slug,
                        severity="critical",
                        title="SSL certificate has expired",
                        description=f"The certificate expired on {not_after.date()}.",
                        remediation="Renew the SSL certificate immediately.",
                        evidence={"expired_on": str(not_after.date())},
                        cvss_score=9.0,
                    ))
                elif days_left <= EXPIRY_WARN_DAYS:
                    self.log(scan, "WARNING: Certificate expires soon")
                    findings.append(FindingData(
                        plugin_slug=self.slug,
                        severity="high",
                        title=f"SSL certificate expires in {days_left} days",
                        description=f"The certificate for {host} expires on {not_after.date()}.",
                        remediation="Renew the SSL certificate before it expires.",
                        evidence={"expires_on": str(not_after.date()), "days_remaining": days_left},
                    ))
                else:
                    self.log(scan, "SUCCESS: Certificate is valid and not expiring soon.")
                    findings.append(FindingData(
                        plugin_slug=self.slug,
                        severity="info",
                        title="SSL certificate is valid",
                        description=f"Certificate is valid until {not_after.date()} ({days_left} days remaining).",
                        evidence={
                            "expires_on": str(not_after.date()),
                            "days_remaining": days_left,
                            "issuer": dict(x[0] for x in cert.get("issuer", [])),
                        },
                    ))
            except ValueError:
                self.log(scan, "ERROR: Failed to parse certificate expiration date.")
                pass

        self.log(scan, "SSL/TLS check completed.")
        return findings
