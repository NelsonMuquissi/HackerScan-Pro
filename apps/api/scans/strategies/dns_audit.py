"""
DNS Security Audit Strategy — v2.

Checks:
  - DNS Zone Transfer (AXFR) — with reliable detection logic
  - SPF policy weakness (softfail / neutral / missing)
  - DMARC policy check (missing or p=none)
  - DKIM presence check
  - CAA record check (Certificate Authority Authorization)
  - Subdomain Takeover via dangling CNAMEs
  - DNS Verification token leakage (INFO)
"""
import logging
import re
import asyncio
import shutil
from typing import List

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity

logger = logging.getLogger(__name__)

# Services commonly associated with subdomain takeover via dangling CNAMEs
TAKEOVER_SIGNATURES = {
    "github.io":              "GitHub Pages",
    "herokuapp.com":          "Heroku",
    "s3.amazonaws.com":       "AWS S3",
    "storage.googleapis.com": "Google Cloud Storage",
    "azurewebsites.net":      "Azure App Service",
    "cloudfront.net":         "AWS CloudFront",
    "netlify.app":            "Netlify",
    "vercel.app":             "Vercel",
    "surge.sh":               "Surge.sh",
    "bitbucket.io":           "Bitbucket Pages",
    "ghost.io":               "Ghost",
    "helpjuice.com":          "HelpJuice",
    "helpscoutdocs.com":      "HelpScout",
    "uservoice.com":          "UserVoice",
    "zendesk.com":            "Zendesk",
    "readme.io":              "ReadMe",
    "fly.dev":                "Fly.io",
    "pages.dev":              "Cloudflare Pages",
}


@register
class DNSAuditStrategy(BaseScanStrategy):
    """
    DNS Security Audit Strategy v2.
    Checks for zone transfer leaks, email spoofing vectors, missing DMARC/DKIM,
    subdomain takeover via dangling CNAMEs, and CAA record gaps.
    """
    slug = "dns_audit"
    name = "DNS Security Audit"
    description = (
        "Analyzes DNS records for zone transfer vulnerabilities, email spoofing (SPF/DMARC/DKIM), "
        "subdomain takeover exposure, and Certificate Authority Authorization gaps."
    )

    async def run_async(self, target, scan=None):
        """Native async implementation — yields FindingData as identified."""
        if target.target_type != "domain":
            self.log(scan, "Target is not a domain — skipping DNS audit.")
            return

        domain = target.host.strip().lower()
        # Strip protocol if present
        if "://" in domain:
            from urllib.parse import urlparse
            domain = urlparse(domain).hostname or domain

        self.log(scan, f"Starting DNS audit for {domain}...")

        # Get name servers first (needed for AXFR)
        ns_servers = await self._get_name_servers_async(domain, scan)

        tasks = []

        # AXFR attempts on each NS
        if ns_servers:
            tasks += [self._attempt_axfr_async(domain, ns, scan) for ns in ns_servers]
        else:
            self.log(scan, "No name servers found — skipping AXFR attempts.")

        # Email / verification record checks
        tasks += [
            self._analyze_txt_records_async(domain, scan),
            self._check_dmarc_async(domain, scan),
            self._check_dkim_async(domain, scan),
            self._check_caa_async(domain, scan),
            self._check_cname_takeover_async(domain, scan),
        ]

        for future in asyncio.as_completed(tasks):
            findings = await future
            for f in findings:
                yield f

    # ─────────────────────────── helpers ──────────────────────────────────

    async def _run_dig(self, *args, timeout: int = 15) -> str:
        """Run dig and return stdout string. Returns '' on error."""
        dig_path = shutil.which("dig")
        if not dig_path:
            return ""
        try:
            proc = await asyncio.create_subprocess_exec(
                dig_path, *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return stdout.decode(errors="ignore")
        except Exception as e:
            logger.debug(f"dig {args} error: {e}")
            return ""

    async def _dns_resolve(self, domain: str, record_type: str) -> List[str]:
        """Resolve DNS record using dnspython (fallback when dig unavailable)."""
        try:
            import dns.resolver
            from asgiref.sync import sync_to_async

            def _resolve():
                try:
                    answers = dns.resolver.resolve(domain, record_type)
                    return [str(r).strip('"').rstrip('.') for r in answers]
                except Exception:
                    return []

            return await sync_to_async(_resolve)()
        except ImportError:
            return []

    # ─────────────────────────── NS lookup ────────────────────────────────

    async def _get_name_servers_async(self, domain: str, scan) -> List[str]:
        output = await self._run_dig("+short", "NS", domain)
        if output.strip():
            servers = [s.strip().rstrip('.') for s in output.splitlines() if s.strip()]
            return servers

        self.log(scan, "dig unavailable — using dnspython for NS lookup.")
        return await self._dns_resolve(domain, "NS")

    # ─────────────────────────── AXFR ─────────────────────────────────────

    async def _attempt_axfr_async(self, domain: str, ns: str, scan) -> List[FindingData]:
        findings = []
        self.log(scan, f"Attempting AXFR zone transfer from {ns}...")
        output = await self._run_dig(f"@{ns}", "AXFR", domain, timeout=20)

        if not output:
            return []

        lines = [l for l in output.splitlines() if l.strip()]

        # Reliable AXFR success indicators:
        # 1. Explicit "Transfer completed" message from dig
        # 2. SOA record appears twice (start + end of transfer)
        # 3. More than 15 non-comment DNS record lines
        soa_count    = sum(1 for l in lines if " SOA " in l)
        record_lines = [l for l in lines if not l.startswith(";") and len(l.split()) >= 4]
        xfr_success  = (
            "Transfer completed" in output
            or soa_count >= 2
            or len(record_lines) > 15
        )
        xfr_failed = "Transfer failed" in output or "connection refused" in output.lower()

        if xfr_success and not xfr_failed:
            # Extract sample records for proof
            sample = []
            for line in record_lines:
                if domain in line and len(sample) < 12:
                    sample.append(line.strip())

            proof_list = "\n".join(f"  {r}" for r in list(dict.fromkeys(sample))[:10])
            findings.append(FindingData(
                title="DNS Zone Transfer (AXFR) Allowed",
                description=(
                    f"The name server `{ns}` accepted a full zone transfer request for `{domain}`. "
                    "This exposes ALL DNS records including internal hostnames and IP addresses to any attacker.\n\n"
                    f"**REAL DATA PROOF** — Sample leaked records ({len(record_lines)} total):\n"
                    f"```\n{proof_list}\n```"
                ),
                severity=Severity.HIGH,
                evidence={
                    "ns": ns,
                    "output_preview": output[:3000],
                    "total_records": len(record_lines),
                    "sample_records": sample,
                },
                plugin_slug=self.slug,
                remediation=(
                    "Configure the authoritative DNS server to allow AXFR only from trusted secondary "
                    "name servers via ACL (e.g., `allow-transfer { trusted_slave_ip; };` in BIND9)."
                ),
                poc=f"dig AXFR @{ns} {domain}",
                is_verified=True,
            ))
        return findings

    # ─────────────────────────── TXT / SPF ────────────────────────────────

    async def _analyze_txt_records_async(self, domain: str, scan) -> List[FindingData]:
        findings = []
        output = await self._run_dig("+short", "TXT", domain)
        records = [l.strip().strip('"') for l in output.splitlines() if l.strip()]

        if not records:
            records = await self._dns_resolve(domain, "TXT")

        spf_found = False
        for record in records:
            # SPF analysis
            if record.startswith("v=spf1"):
                spf_found = True
                if "-all" not in record:
                    sev = Severity.MEDIUM if "~all" in record else Severity.HIGH
                    policy = "softfail (~all)" if "~all" in record else ("neutral (?all)" if "?all" in record else "no -all directive")
                    findings.append(FindingData(
                        title=f"Weak SPF Policy: {policy}",
                        description=(
                            f"The SPF record for `{domain}` uses a {policy}, which does not prevent email spoofing. "
                            f"Attackers can send emails impersonating `{domain}` and they will not be hard-rejected.\n\n"
                            f"**REAL DATA PROOF** (Extracted SPF record):\n`{record}`"
                        ),
                        severity=sev,
                        evidence={"record": record, "domain": domain, "policy": policy},
                        plugin_slug=self.slug,
                        remediation=(
                            f"Change the SPF ending from `{policy}` to `-all` (hardfail). "
                            "Example: `v=spf1 include:_spf.google.com -all`"
                        ),
                        poc=f"dig +short TXT {domain}",
                    ))
                else:
                    self.log(scan, f"SPF policy is correctly set to hardfail for {domain}.")

            # Verification token disclosure (INFO)
            if any(x in record for x in ["google-site-verification", "msVerify", "facebook-domain-verification"]):
                findings.append(FindingData(
                    title="Third-party Verification Token in DNS",
                    description=(
                        f"A third-party service verification token was found in the DNS TXT records for `{domain}`. "
                        f"This reveals which external services are used by the organisation.\n\n"
                        f"**REAL DATA PROOF**: `{record}`"
                    ),
                    severity=Severity.INFO,
                    evidence={"record": record, "domain": domain},
                    plugin_slug=self.slug,
                ))

        if not spf_found:
            findings.append(FindingData(
                title="Missing SPF Record",
                description=(
                    f"No SPF record was found for `{domain}`. Without SPF, anyone can send email "
                    f"claiming to be from `@{domain}` and it will not be rejected by most mail servers.\n\n"
                    f"**REAL DATA PROOF**: `dig +short TXT {domain}` returned no SPF record."
                ),
                severity=Severity.HIGH,
                evidence={"domain": domain},
                plugin_slug=self.slug,
                remediation=(
                    f"Add a TXT record: `v=spf1 include:YOUR_MAIL_PROVIDER -all`\n"
                    f"Example for Google Workspace: `v=spf1 include:_spf.google.com -all`"
                ),
                poc=f"dig +short TXT {domain}",
            ))

        return findings

    # ─────────────────────────── DMARC ────────────────────────────────────

    async def _check_dmarc_async(self, domain: str, scan) -> List[FindingData]:
        findings  = []
        dmarc_fqdn = f"_dmarc.{domain}"

        output = await self._run_dig("+short", "TXT", dmarc_fqdn)
        records = [l.strip().strip('"') for l in output.splitlines() if l.strip() and "v=DMARC1" in l]

        if not records:
            records = [r for r in await self._dns_resolve(dmarc_fqdn, "TXT") if "v=DMARC1" in r]

        if not records:
            findings.append(FindingData(
                title="Missing DMARC Record",
                description=(
                    f"No DMARC record was found at `_dmarc.{domain}`. Without DMARC, email spoofing attacks "
                    f"using the `{domain}` domain cannot be reported or blocked, even if SPF/DKIM are configured.\n\n"
                    f"**REAL DATA PROOF**: `dig +short TXT _dmarc.{domain}` returned no DMARC record."
                ),
                severity=Severity.HIGH,
                evidence={"domain": domain, "dmarc_fqdn": dmarc_fqdn},
                plugin_slug=self.slug,
                remediation=(
                    f"Add a TXT record at `_dmarc.{domain}`:\n"
                    "`v=DMARC1; p=reject; rua=mailto:dmarc-reports@yourdomain.com; adkim=s; aspf=s`\n"
                    "Start with `p=none` to collect reports, then move to `p=quarantine` → `p=reject`."
                ),
                poc=f"dig +short TXT _dmarc.{domain}",
            ))
        else:
            dmarc_record = records[0]
            policy_match = re.search(r"\bp=(\w+)\b", dmarc_record)
            policy = policy_match.group(1).lower() if policy_match else "none"

            if policy == "none":
                findings.append(FindingData(
                    title="DMARC Policy Set to p=none (No Enforcement)",
                    description=(
                        f"DMARC is configured for `{domain}` but with `p=none`, which only requests reports "
                        f"without blocking any spoofed emails. Attackers can still impersonate `{domain}` successfully.\n\n"
                        f"**REAL DATA PROOF** (Extracted DMARC record):\n`{dmarc_record}`"
                    ),
                    severity=Severity.MEDIUM,
                    evidence={"record": dmarc_record, "policy": policy, "domain": domain},
                    plugin_slug=self.slug,
                    remediation=(
                        "Gradually move DMARC policy from `p=none` → `p=quarantine` → `p=reject` "
                        "after analysing DMARC reports to avoid legitimate mail disruption."
                    ),
                    poc=f"dig +short TXT _dmarc.{domain}",
                ))
            else:
                self.log(scan, f"DMARC is correctly enforcing p={policy} for {domain}.")

        return findings

    # ─────────────────────────── DKIM ─────────────────────────────────────

    async def _check_dkim_async(self, domain: str, scan) -> List[FindingData]:
        """Check common DKIM selector names. If none found, report as INFO."""
        findings = []
        common_selectors = [
            "default", "google", "k1", "k2", "mail", "dkim", "s1", "s2",
            "selector1", "selector2", "smtp", "key1", "key2",
        ]

        found = False
        for selector in common_selectors:
            fqdn   = f"{selector}._domainkey.{domain}"
            output = await self._run_dig("+short", "TXT", fqdn)
            if "v=DKIM1" in output or "p=" in output:
                found = True
                self.log(scan, f"DKIM record found at {fqdn}.")
                break
            # Also try dnspython
            if not found:
                recs = await self._dns_resolve(fqdn, "TXT")
                if any("v=DKIM1" in r or "p=" in r for r in recs):
                    found = True
                    break

        if not found:
            findings.append(FindingData(
                title="No DKIM Record Detected (Common Selectors)",
                description=(
                    f"No DKIM record was found for `{domain}` under common selectors "
                    f"({', '.join(common_selectors[:6])}, ...).\n"
                    f"Without DKIM, email receivers cannot verify that emails from `{domain}` were not tampered with in transit.\n\n"
                    f"**REAL DATA PROOF**: Checked {len(common_selectors)} DKIM selectors — none returned a valid DKIM record."
                ),
                severity=Severity.MEDIUM,
                evidence={"domain": domain, "selectors_checked": common_selectors},
                plugin_slug=self.slug,
                remediation=(
                    "Configure DKIM signing on your mail server and publish the public key as a TXT record. "
                    "For Google Workspace, go to Admin Console → Apps → Gmail → Authenticate email."
                ),
                poc=f"dig +short TXT default._domainkey.{domain}",
            ))
        return findings

    # ─────────────────────────── CAA ──────────────────────────────────────

    async def _check_caa_async(self, domain: str, scan) -> List[FindingData]:
        findings = []
        output   = await self._run_dig("+short", "CAA", domain)
        records  = [l.strip() for l in output.splitlines() if l.strip()]

        if not records:
            records = await self._dns_resolve(domain, "CAA")

        if not records:
            findings.append(FindingData(
                title="Missing CAA (Certificate Authority Authorization) Record",
                description=(
                    f"No CAA record was found for `{domain}`. Without CAA records, any Certificate Authority "
                    f"is allowed to issue SSL certificates for this domain. This increases the risk of mis-issuance.\n\n"
                    f"**REAL DATA PROOF**: `dig +short CAA {domain}` returned no records."
                ),
                severity=Severity.INFO,
                evidence={"domain": domain},
                plugin_slug=self.slug,
                remediation=(
                    f"Add a CAA record restricting certificate issuance to your CA(s):\n"
                    f"`{domain}. 300 IN CAA 0 issue \"letsencrypt.org\"`\n"
                    f"`{domain}. 300 IN CAA 0 iodef \"mailto:security@{domain}\"`"
                ),
                poc=f"dig +short CAA {domain}",
            ))
        else:
            self.log(scan, f"CAA record found for {domain}: {records}")

        return findings

    # ─────────────────────────── Subdomain Takeover ───────────────────────

    async def _check_cname_takeover_async(self, domain: str, scan) -> List[FindingData]:
        """
        Checks the apex domain and common subdomains for CNAME records pointing
        to services that might be unclaimed (subdomain takeover).
        """
        findings = []
        candidates = [
            domain,
            f"www.{domain}", f"blog.{domain}", f"dev.{domain}", f"staging.{domain}",
            f"app.{domain}", f"api.{domain}", f"mail.{domain}", f"status.{domain}",
            f"docs.{domain}", f"help.{domain}", f"shop.{domain}",
        ]

        async def _check_one(sub: str) -> List[FindingData]:
            output  = await self._run_dig("+short", "CNAME", sub)
            cname   = output.strip().rstrip('.').lower()
            if not cname:
                return []

            for service_fqdn, service_name in TAKEOVER_SIGNATURES.items():
                if service_fqdn in cname:
                    # Try to resolve the CNAME — if NXDOMAIN, it's dangling
                    resolve_out = await self._run_dig("+short", "A", cname)
                    if not resolve_out.strip():
                        return [FindingData(
                            title=f"Potential Subdomain Takeover: {sub}",
                            description=(
                                f"`{sub}` has a CNAME pointing to `{cname}` ({service_name}), "
                                f"but that target does not resolve. If the service is unclaimed, "
                                f"an attacker can register it and serve content under `{sub}`.\n\n"
                                f"**REAL DATA PROOF**:\n"
                                f"- CNAME: `{sub}` → `{cname}`\n"
                                f"- A record for `{cname}`: (none — NXDOMAIN)"
                            ),
                            severity=Severity.HIGH,
                            evidence={
                                "subdomain": sub,
                                "cname_target": cname,
                                "service": service_name,
                                "resolves": False,
                            },
                            plugin_slug=self.slug,
                            remediation=(
                                f"Either remove the CNAME record for `{sub}` or re-claim the "
                                f"{service_name} resource it points to."
                            ),
                            poc=f"dig CNAME {sub} && dig A {cname}",
                        )]
            return []

        subtasks = [_check_one(sub) for sub in candidates]
        results  = await asyncio.gather(*subtasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                findings.extend(r)

        return findings

    # ─────────────────────────── verify ───────────────────────────────────

    async def verify_async(self, finding: "Finding") -> bool:
        """Re-run the relevant DNS check to confirm the finding still exists."""
        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False

        from asgiref.sync import sync_to_async
        scan   = await sync_to_async(lambda: finding.scan)()
        target = await sync_to_async(lambda: scan.target)()
        domain = target.host.strip().lower()
        if "://" in domain:
            from urllib.parse import urlparse
            domain = urlparse(domain).hostname or domain

        verified = False

        if "AXFR" in finding.title:
            ns      = evidence.get("ns")
            if ns:
                results  = await self._attempt_axfr_async(domain, ns, None)
                verified = len(results) > 0

        elif "SPF" in finding.title or "DMARC" in finding.title:
            if "DMARC" in finding.title:
                results  = await self._check_dmarc_async(domain, None)
            else:
                results  = await self._analyze_txt_records_async(domain, None)
            verified = any(r.title == finding.title for r in results)

        elif "Takeover" in finding.title:
            results  = await self._check_cname_takeover_async(domain, None)
            verified = any(r.evidence.get("subdomain") == evidence.get("subdomain") for r in results)

        if verified:
            finding.is_verified = True
            from asgiref.sync import sync_to_async
            await sync_to_async(finding.save)()
            return True

        return False
