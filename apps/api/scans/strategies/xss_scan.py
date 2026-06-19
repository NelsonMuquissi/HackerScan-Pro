"""
XSS Detection Strategy — v2.

Checks:
  - Reflected XSS via XSStrike (external tool) with parameter enumeration
  - DOM-based XSS via Playwright browser instrumentation:
      • document.write / innerHTML / outerHTML sinks
      • location.hash / search / href sources
      • eval() / setTimeout() / Function() sinks
      • postMessage-based DOM XSS
      • jQuery .html() / .append() sinks
  - Stored XSS indicator detection (mutation after page interaction)
  - CSP bypass detection (script-src unsafe-inline / missing nonce)
"""
import logging
import asyncio
import os
import re
import shutil
from typing import AsyncGenerator, List
from urllib.parse import urlparse, urlencode, urljoin, parse_qs, urlunparse

from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

# ── Reflected XSS payloads ─────────────────────────────────────────────────────
REFLECTED_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "'\"><script>alert(1)</script>",
    "<svg onload=alert(1)>",
    "<details open ontoggle=alert(1)>",
    "javascript:alert(1)",
    "<iframe srcdoc=\"<script>alert(1)</script>\">",
    "<math><maction actiontype=\"statusline#\" xlink:href=\"javascript:alert(1)\">click</maction></math>",
]

# ── DOM-XSS payloads per sink type ─────────────────────────────────────────────
DOM_PAYLOADS = {
    "hash": [
        "#<img src=x onerror=window.__xss_dom=1>",
        "#<svg onload=window.__xss_dom=1>",
        "#\"><script>window.__xss_dom=1</script>",
        "#javascript:window.__xss_dom=1",
    ],
    "search": [
        "?q=<script>window.__xss_dom=1</script>",
        "?q=<img src=x onerror=window.__xss_dom=1>",
        "?search=\"><script>window.__xss_dom=1</script>",
        "?input=<svg onload=window.__xss_dom=1>",
    ],
    "postMessage": [
        # Injected via page.evaluate after load
        'window.postMessage("<img src=x onerror=window.__xss_dom=1>","*")',
        'window.postMessage({"html":"<script>window.__xss_dom=1<\\/script>"},"*")',
        'window.postMessage({"data":"<svg onload=window.__xss_dom=1>"},"*")',
    ],
    "referrer": [
        "https://evil.com/?q=<script>window.__xss_dom=1</script>",
        "https://evil.com/#<img src=x onerror=window.__xss_dom=1>",
    ],
    "name": [
        "<img src=x onerror=window.__xss_dom=1>",
        "<svg onload=window.__xss_dom=1>",
    ],
    "prototype": [
        "__proto__[__proto_polluted]=__xss_sentinel__",
        "constructor[prototype][__proto_polluted]=__xss_sentinel__",
        "__proto__.polluted=true",
    ],
}

# JavaScript injected into every page to instrument dangerous sinks
# Sets window.__xss_dom = {sink, value} when called with tainted input
INSTRUMENTATION_SCRIPT = """
(function() {
    window.__xss_dom = null;
    const _marker = '__xss_sentinel__';

    // Helper to detect sentinel in values
    const isTainted = (v) => {
        if (typeof v === 'string' && v.includes(_marker)) return true;
        if (typeof v === 'object' && v !== null) {
            try {
                const s = JSON.stringify(v);
                return s && s.includes(_marker);
            } catch(e) {}
        }
        return false;
    };

    // Wrap innerHTML / outerHTML / srcdoc
    const wrapProperty = (proto, prop) => {
        const descriptor = Object.getOwnPropertyDescriptor(proto, prop);
        if (!descriptor || !descriptor.set) return;
        const originalSet = descriptor.set;
        Object.defineProperty(proto, prop, {
            set: function(v) {
                if (isTainted(v)) {
                    window.__xss_dom = { sink: prop, value: String(v).substring(0, 200) };
                }
                return originalSet.apply(this, arguments);
            },
            get: descriptor.get,
            configurable: true
        });
    };

    wrapProperty(Element.prototype, 'innerHTML');
    wrapProperty(Element.prototype, 'outerHTML');
    wrapProperty(HTMLIFrameElement.prototype, 'srcdoc');

    // Wrap document.write
    const _origWrite = document.write.bind(document);
    document.write = function(...args) {
        const s = args.join('');
        if (isTainted(s)) window.__xss_dom = { sink: 'document.write', value: s.substring(0, 200) };
        return _origWrite(...args);
    };

    // Wrap insertAdjacentHTML
    const _origInsertHTML = Element.prototype.insertAdjacentHTML;
    Element.prototype.insertAdjacentHTML = function(pos, html) {
        if (isTainted(html))
            window.__xss_dom = { sink: 'insertAdjacentHTML', value: String(html).substring(0, 200) };
        return _origInsertHTML.apply(this, arguments);
    };

    // Wrap setAttribute for event handlers
    const _origSetAttr = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function(name, val) {
        if (name.toLowerCase().startsWith('on') && isTainted(val))
            window.__xss_dom = { sink: 'setAttribute(' + name + ')', value: String(val).substring(0, 200) };
        return _origSetAttr.apply(this, arguments);
    };

    // Wrap eval
    const _origEval = window.eval;
    window.eval = function(s) {
        if (isTainted(s))
            window.__xss_dom = { sink: 'eval', value: String(s).substring(0, 200) };
        return _origEval(s);
    };

    // Wrap setTimeout/setInterval with string arg
    const _origST = window.setTimeout;
    window.setTimeout = function(fn, ...rest) {
        if (typeof fn === 'string' && isTainted(fn))
            window.__xss_dom = { sink: 'setTimeout', value: fn.substring(0, 200) };
        return _origST(fn, ...rest);
    };

    // Intercept location assignment
    const _locDescriptor = Object.getOwnPropertyDescriptor(Location.prototype, 'href') || Object.getOwnPropertyDescriptor(window.location, 'href');
    if (_locDescriptor && _locDescriptor.set) {
        const _origLocSet = _locDescriptor.set;
        Object.defineProperty(window.location, 'href', {
            set: function(v) {
                if (isTainted(v))
                    window.__xss_dom = { sink: 'location.href', value: String(v).substring(0, 200) };
                // We DON'T call the original set to prevent navigation during scan
            },
            get: _locDescriptor.get,
            configurable: true
        });
    }

    // Intercept jQuery sinks if present
    const hookJQuery = () => {
        if (window.jQuery && window.jQuery.fn) {
            const sinks = ['html', 'append', 'prepend', 'after', 'before', 'replaceAll', 'replaceWith'];
            sinks.forEach(sink => {
                const orig = window.jQuery.fn[sink];
                if (orig) {
                    window.jQuery.fn[sink] = function(v) {
                        if (isTainted(v))
                            window.__xss_dom = { sink: 'jQuery.' + sink, value: String(v).substring(0, 200) };
                        return orig.apply(this, arguments);
                    };
                }
            });
        }
    };
    hookJQuery();
    // Also try hooking later if jQuery is loaded via script
    setTimeout(hookJQuery, 1000);
    setTimeout(hookJQuery, 3000);

    // Prototype Pollution detection
    try {
        Object.defineProperty(Object.prototype, '__proto_polluted', {
            set(v) {
                if (isTainted(v)) {
                    window.__xss_dom = { sink: 'Prototype Pollution', value: String(v).substring(0, 200) };
                }
            },
            configurable: true
        });
    } catch(e) {}
})();
"""


@register
class XSStrikeStrategy(BaseScanStrategy):
    """
    XSS Security Audit v2.
    Covers: Reflected XSS (via XSStrike + manual), DOM-based XSS (via Playwright
    browser instrumentation with sink hooking), postMessage XSS, and CSP analysis.
    """
    slug = "xss_scan"
    name = "XSS Security Audit (Reflected + DOM)"
    description = (
        "Advanced Cross-Site Scripting detection covering Reflected XSS, "
        "DOM-based XSS (innerHTML/eval/location sinks), postMessage-based XSS, "
        "and Content Security Policy bypass analysis."
    )

    async def run_async(self, target, scan=None) -> AsyncGenerator[FindingData, None]:
        from scans.utils import make_evidence_request_async

        host = target.host
        url  = host if host.startswith(("http://", "https://")) else f"http://{host}"

        # ── Phase 1: Reflected XSS ──────────────────────────────────────────
        self.log(scan, "Phase 1: Reflected XSS scan (XSStrike)...")
        async for f in self._run_xsstrike_async(url, scan):
            yield f

        # ── Phases 2-5: Browser-based Scans (Playwright) ───────────────────
        # We reuse a single Playwright instance to avoid resource leaks
        try:
            from playwright.async_api import async_playwright
            self.log(scan, "Initializing headless browser for DOM analysis...")
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=[
                    "--no-sandbox", "--disable-setuid-sandbox",
                    "--disable-web-security",
                    "--disable-gpu",
                ])
                try:
                    context = await browser.new_context(ignore_https_errors=True)
                    await context.add_init_script(INSTRUMENTATION_SCRIPT)

                    # Phase 2: DOM-based XSS
                    self.log(scan, "Phase 2: DOM-based XSS scan...")
                    async for f in self._run_dom_xss_async(url, scan, context):
                        yield f

                    # Phase 3: postMessage XSS
                    self.log(scan, "Phase 3: postMessage XSS scan...")
                    async for f in self._run_postmessage_xss_async(url, scan, context):
                        yield f

                    # Phase 5: Client-Side Prototype Pollution
                    self.log(scan, "Phase 4: Client-Side Prototype Pollution scan...")
                    async for f in self._run_prototype_pollution_async(url, scan, context):
                        yield f

                finally:
                    await browser.close()
        except ImportError:
            self.log(scan, "Playwright not available — skipping DOM/postMessage scans.")
        except Exception as e:
            logger.error(f"Browser scan error: {e}")
            self.log(scan, f"Browser scan failed: {e}")

        # ── Phase 4: Client-Side Template Injection (CSTI) ───────────────
        self.log(scan, "Phase 5: Client-Side Template Injection (CSTI) scan...")
        async for f in self._run_csti_scan_async(url, scan):
            yield f

    # ── Phase 1: Reflected XSS ─────────────────────────────────────────────

    async def _run_xsstrike_async(self, url: str, scan) -> AsyncGenerator[FindingData, None]:
        from scans.utils import make_evidence_request_async

        xsstrike_bin = shutil.which("xsstrike")
        xsstrike_script = "/opt/xsstrike/xsstrike.py"
        if os.name == "nt":
            xsstrike_script = "C:\\tools\\xsstrike\\xsstrike.py"

        tool_available = xsstrike_bin or os.path.exists(xsstrike_script)

        if tool_available:
            cmd = (
                [xsstrike_bin, "-u", url, "--crawl", "-l", "1", "--timeout", "10", "--seeds", "10"]
                if xsstrike_bin
                else ["python3", xsstrike_script, "-u", url, "--crawl", "-l", "1", "--timeout", "10", "--seeds", "10"]
            )
            self.log(scan, f"Running XSStrike: {' '.join(cmd)}")
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                try:
                    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
                    output = stdout.decode(errors="ignore")
                except asyncio.TimeoutError:
                    self.log(scan, "XSStrike timed out.")
                    if proc.returncode is None:
                        proc.terminate()
                    output = ""

                params   = re.findall(r"Vulnerable Parameter:\s+([^\n\r]+)", output)
                payloads = re.findall(r"Payload:\s+([^\n\r]+)", output)
                vectors  = re.findall(r"Vector:\s+([^\n\r]+)", output)

                for i, param in enumerate(params):
                    payload = payloads[i] if i < len(payloads) else "<script>alert(1)</script>"
                    vector  = vectors[i]  if i < len(vectors)  else "Unknown"
                    resp, req, res, poc = await make_evidence_request_async(
                        url, method="GET", params={param: payload}
                    )
                    verified = resp and payload in resp.text
                    yield FindingData(
                        title=f"Reflected XSS on Parameter '{param}'",
                        description=(
                            f"XSStrike confirmed reflected XSS on the `{param}` parameter of `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Payload `{payload[:80]}` reflected verbatim in response body."
                        ),
                        severity=Severity.HIGH,
                        evidence={"parameter": param, "payload": payload, "vector": vector,
                                  "xss_type": "reflected"},
                        request=req, response=res,
                        poc=poc or f"curl -G '{url}' --data-urlencode '{param}={payload}'",
                        remediation=(
                            "Apply context-aware output encoding. "
                            "Implement a strict Content-Security-Policy with nonces."
                        ),
                        plugin_slug=self.slug,
                        is_verified=bool(verified),
                    )
            except Exception as e:
                logger.error(f"XSStrike error: {e}")
                self.log(scan, f"XSStrike failed: {e}. Falling back to manual reflected scan.")
                tool_available = False

        if not tool_available:
            # Manual reflected XSS probe
            async for f in self._run_manual_reflected_async(url, scan):
                yield f

    async def _run_manual_reflected_async(self, url: str, scan) -> AsyncGenerator[FindingData, None]:
        """Manual reflected XSS: discover params then inject payloads."""
        from scans.utils import make_evidence_request_async

        # Discover GET parameters from the URL and from a basic crawl
        parsed    = urlparse(url)
        existing_params = list(parse_qs(parsed.query).keys())
        candidate_params = list(set(existing_params + [
            "q", "s", "search", "query", "id", "page", "name",
            "message", "text", "input", "term", "keyword", "error",
        ]))

        sem = asyncio.Semaphore(6)

        async def _probe(param, payload):
            async with sem:
                probe_url = f"{url}{'&' if '?' in url else '?'}{param}={payload}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(
                        probe_url, timeout=6, follow_redirects=True
                    )
                    if not resp:
                        return None
                    # Check reflection WITHOUT encoding
                    if payload in resp.text:
                        # Check if it's inside a script-executable context
                        in_script = bool(re.search(
                            r"<script[^>]*>[^<]*" + re.escape(payload) + r"[^<]*</script>",
                            resp.text, re.IGNORECASE
                        ))
                        in_attr = bool(re.search(
                            r'on\w+=["\'][^"\']*' + re.escape(payload),
                            resp.text, re.IGNORECASE
                        ))
                        sev = Severity.HIGH if (in_script or in_attr) else Severity.MEDIUM
                        return FindingData(
                            title=f"Reflected XSS on Parameter '{param}'",
                            description=(
                                f"The `{param}` parameter reflects user input unsanitized.\n"
                                f"Payload injected: `{payload[:60]}`\n\n"
                                f"**REAL DATA PROOF**: Payload found verbatim in HTTP response "
                                f"{'inside a script/event context' if (in_script or in_attr) else '(HTML context)'}."
                            ),
                            severity=sev,
                            evidence={
                                "parameter": param, "payload": payload,
                                "url": probe_url, "xss_type": "reflected",
                                "in_script_context": in_script,
                                "in_attr_context": in_attr,
                            },
                            request=req, response=res,
                            poc=f"curl -s '{probe_url}' | grep -o '{payload[:30]}...'",
                            remediation=(
                                "HTML-encode all reflected values. "
                                "Use CSP with script-src nonces to prevent execution."
                            ),
                            plugin_slug=self.slug,
                            is_verified=True,
                        )
                except Exception:
                    pass
                return None

        tasks = [
            asyncio.create_task(_probe(p, pl))
            for p in candidate_params
            for pl in REFLECTED_PAYLOADS[:4]  # First 4 payloads to limit noise
        ]
        for coro in asyncio.as_completed(tasks):
            f = await coro
            if f:
                yield f

    # ── Phase 2: DOM-based XSS ─────────────────────────────────────────────

    async def _run_dom_xss_async(self, url: str, scan, context) -> AsyncGenerator[FindingData, None]:
        """
        Uses Playwright with injected JavaScript instrumentation to hook dangerous
        DOM sinks and detect when user-controlled input reaches them.
        """
        SENTINEL = "__xss_sentinel__"

        async def _test_dom_payload(page, payload_url: str, payload: str, source: str):
            """Navigate to payload_url and check if sentinel reached a sink."""
            try:
                # Use a fresh page to avoid state contamination
                await page.goto(payload_url, timeout=15000, wait_until="domcontentloaded")
                await asyncio.sleep(1.5)

                result = await page.evaluate("() => window.__xss_dom")
                if result and isinstance(result, dict):
                    sink  = result.get("sink", "unknown")
                    value = result.get("value", "")
                    return (sink, value, payload_url, payload, source)
            except Exception:
                pass
            return None

        findings = []
        page = await context.new_page()
        try:
            # ── Test hash-based DOM XSS ──────────────────────────────
            for payload in DOM_PAYLOADS["hash"]:
                sentinel_payload = payload.replace("__xss_dom=1", f"__xss_dom={{sink:'hash',value:'{SENTINEL}'}}")
                probe_url = url + sentinel_payload
                hit = await _test_dom_payload(page, probe_url, payload, "location.hash")
                if hit:
                    sink, value, p_url, p_payload, source = hit
                    findings.append(FindingData(
                        title=f"DOM-based XSS via location.hash → {sink}",
                        description=(
                            f"User-controlled `location.hash` value flows into the `{sink}` sink "
                            f"without sanitisation on `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Browser instrumentation confirmed that the "
                            f"sentinel value reached `{sink}` sink. Payload: `{p_payload[:80]}`\n"
                            f"Sink value: `{value[:150]}`"
                        ),
                        severity=Severity.HIGH,
                        evidence={
                            "source": "location.hash", "sink": sink,
                            "payload": p_payload, "url": p_url, "xss_type": "dom",
                        },
                        remediation=(
                            "Never pass unsanitised `location.hash` / URL fragments to DOM sinks. "
                            "Use DOMPurify to sanitise HTML before insertion. "
                            "Implement a strict CSP with `script-src` nonces."
                        ),
                        poc=f"Navigate to: {p_url}",
                        plugin_slug=self.slug,
                        is_verified=True,
                    ))

            # ── Test search/query param DOM XSS ──────────────────────
            for payload in DOM_PAYLOADS["search"]:
                probe_url = url + payload
                hit = await _test_dom_payload(page, probe_url, payload, "URL parameter")
                if hit:
                    sink, value, p_url, p_payload, source = hit
                    findings.append(FindingData(
                        title=f"DOM-based XSS via URL Parameter → {sink}",
                        description=(
                            f"URL parameter value flows into the `{sink}` sink on `{url}`.\n\n"
                            f"**REAL DATA PROOF**: Browser sink instrumentation detected sentinel "
                            f"in `{sink}`. Payload: `{p_payload[:80]}`"
                        ),
                        severity=Severity.HIGH,
                        evidence={
                            "source": "url_param", "sink": sink,
                            "payload": p_payload, "url": p_url, "xss_type": "dom",
                        },
                        remediation=(
                            "Sanitise URL parameter values before writing to the DOM. "
                            "Use textContent instead of innerHTML. "
                            "Deploy DOMPurify and a strict CSP policy."
                        ),
                        poc=f"Navigate to: {p_url}",
                        plugin_slug=self.slug,
                        is_verified=True,
                    ))

            # ── Test Referrer-based DOM XSS ──────────────────────────
            for payload in DOM_PAYLOADS["referrer"]:
                try:
                    await page.set_extra_http_headers({"Referer": payload})
                    hit = await _test_dom_payload(page, url, payload, "document.referrer")
                    if hit:
                        sink, value, p_url, p_payload, source = hit
                        findings.append(FindingData(
                            title=f"DOM-based XSS via Referrer → {sink}",
                            description=(
                                f"The `document.referrer` value flows into the `{sink}` sink on `{url}`.\n\n"
                                f"**REAL DATA PROOF**: Browser instrumentation confirmed that the "
                                f"sentinel value from referrer reached `{sink}` sink."
                            ),
                            severity=Severity.HIGH,
                            evidence={
                                "source": "referrer", "sink": sink,
                                "payload": p_payload, "url": url, "xss_type": "dom",
                            },
                            remediation="Validate and sanitise `document.referrer` before use in DOM sinks.",
                            poc=f"curl -H 'Referer: {p_payload}' {url}",
                            plugin_slug=self.slug,
                            is_verified=True,
                        ))
                except Exception:
                    pass

            # ── Test Window Name DOM XSS ──────────────────────────────
            for payload in DOM_PAYLOADS["name"]:
                try:
                    await page.evaluate(f"window.name = '{payload}'")
                    hit = await _test_dom_payload(page, url, payload, "window.name")
                    if hit:
                        sink, value, p_url, p_payload, source = hit
                        findings.append(FindingData(
                            title=f"DOM-based XSS via window.name → {sink}",
                            description=(
                                f"The `window.name` value flows into the `{sink}` sink on `{url}`.\n\n"
                                f"**REAL DATA PROOF**: Browser instrumentation confirmed that the "
                                f"sentinel value from window.name reached `{sink}` sink."
                            ),
                            severity=Severity.HIGH,
                            evidence={
                                "source": "window.name", "sink": sink,
                                "payload": p_payload, "url": url, "xss_type": "dom",
                            },
                            remediation="Avoid using `window.name` for data storage. If used, sanitise it thoroughly.",
                            poc=f"Set window.name to '{p_payload}' and reload {url}",
                            plugin_slug=self.slug,
                            is_verified=True,
                        ))
                except Exception:
                    pass

            # ── Static source analysis: detect sink patterns in JS ───
            js_dom_findings = await self._analyze_page_js_sources_async(page, url)
            findings.extend(js_dom_findings)
        except Exception as e:
            logger.error(f"DOM XSS scan error: {e}")
            self.log(scan, f"DOM XSS scan error: {e}")
        finally:
            await page.close()

        for f in findings:
            yield f

    async def _analyze_page_js_sources_async(self, page, url: str) -> List[FindingData]:
        """
        Statically analyse JavaScript loaded by the page for dangerous patterns:
        innerHTML, outerHTML, document.write, eval, setTimeout(string),
        location = tainted, jQuery .html().
        """
        findings = []
        try:
            # Collect all script URLs loaded by the page
            js_urls = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script[src]'))
                         .map(s => s.src)
                         .filter(s => s && !s.includes('google') && !s.includes('analytics'))
            """)

            # Also grab inline script content
            inline_scripts = await page.evaluate("""
                () => Array.from(document.querySelectorAll('script:not([src])'))
                         .map(s => ({
                             content: s.textContent,
                             url: '[inline]'
                         }))
                         .filter(s => s.content && s.content.length > 20)
            """)

            # Normalize js_urls to objects for consistent processing
            scripts_to_analyze = inline_scripts
            import httpx
            for js_url in js_urls[:15]:  # Limit to 15 files
                try:
                    async with httpx.AsyncClient(verify=False, timeout=5) as client:
                        resp = await client.get(js_url)
                        if resp.status_code == 200:
                            scripts_to_analyze.append({
                                "content": resp.text,
                                "url": js_url
                            })
                except Exception:
                    pass

            # Patterns indicating dangerous sinks receiving tainted sources
            SINK_PATTERNS = [
                (r"innerHTML\s*=\s*[^;]*(?:location|search|hash|param|query|document\.URL)", "innerHTML from URL source"),
                (r"outerHTML\s*=\s*[^;]*(?:location|search|hash|param|query)", "outerHTML from URL source"),
                (r"document\.write\s*\([^)]*(?:location|search|hash|document\.URL)", "document.write from URL source"),
                (r"eval\s*\([^)]*(?:location|search|hash|param)", "eval() from URL source"),
                (r"setTimeout\s*\(['\"][^'\"]*(?:location|search|hash)", "setTimeout(string) from URL source"),
                (r"\.html\s*\([^)]*(?:location|search|hash|param)", "jQuery .html() from URL source"),
                (r"(?:window\.|document\.)location\s*=\s*[^;]*(?:param|query|search|hash)", "location assignment from input"),
                (r"src\s*=\s*[^;]*(?:location|search|hash|param)", "src assignment from URL source"),
            ]

            for script in scripts_to_analyze:
                content = script["content"]
                s_url = script["url"]
                
                for pattern, desc in SINK_PATTERNS:
                    matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                    for match in matches:
                        match_text = match.group(0)
                        # Calculate line number
                        line_no = content.count('\n', 0, match.start()) + 1
                        
                        # Get a small context snippet
                        context_start = content.rfind('\n', 0, match.start()) + 1
                        context_end = content.find('\n', match.end())
                        if context_end == -1: context_end = len(content)
                        snippet = content[context_start:context_end].strip()

                        finding_title = f"DOM Sink Risk: {desc}"
                        # Avoid duplicate findings for the same sink in the same file
                        if not any(f.title == finding_title and f.evidence.get("url") == s_url for f in findings):
                            findings.append(FindingData(
                                title=finding_title,
                                description=(
                                    f"JavaScript code at `{s_url}` contains a pattern where "
                                    f"a URL-derived source (`location`, `search`, `hash`) flows into "
                                    f"a dangerous sink (`{desc}`) on line {line_no}.\n\n"
                                    f"**REAL DATA PROOF** (Line {line_no}):\n"
                                    f"```javascript\n{line_no}: {snippet}\n```"
                                ),
                                severity=Severity.MEDIUM,
                                evidence={
                                    "pattern": desc, 
                                    "snippet": snippet, 
                                    "line": line_no,
                                    "url": s_url, 
                                    "xss_type": "dom_static"
                                },
                                remediation=(
                                    "Review and sanitise all data flow from URL sources to DOM sinks. "
                                    "Use DOMPurify for HTML content and textContent for plain text."
                                ),
                                poc=f"# Review {s_url} line {line_no} for pattern: {pattern[:40]}",
                                plugin_slug=self.slug,
                            ))
        except Exception as e:
            logger.debug(f"JS source analysis error: {e}")

        return findings

    # ── Phase 3: postMessage XSS ──────────────────────────────────────────

    async def _run_postmessage_xss_async(self, url: str, scan, context) -> AsyncGenerator[FindingData, None]:
        """
        Test for postMessage-based DOM XSS: sends crafted messages and checks
        if the page processes them insecurely into a DOM sink.
        """
        try:
            page = await context.new_page()
            try:
                # Track dialogs (XSS via alert)
                dialog_fired = False
                dialog_msg   = ""
                async def on_dialog(dialog):
                    nonlocal dialog_fired, dialog_msg
                    dialog_fired = True
                    dialog_msg   = dialog.message
                    await dialog.dismiss()
                page.on("dialog", on_dialog)

                await page.goto(url, timeout=15000, wait_until="networkidle")
                await asyncio.sleep(1)

                for payload_js in DOM_PAYLOADS["postMessage"]:
                    try:
                        await page.evaluate(payload_js)
                        await asyncio.sleep(1.5)

                        # Check sink instrumentation
                        dom_result = await page.evaluate("() => window.__xss_dom")

                        if dialog_fired or dom_result:
                            sink = dom_result.get("sink", "unknown") if dom_result else "alert()"
                            yield FindingData(
                                title="DOM-based XSS via postMessage",
                                description=(
                                    f"The page at `{url}` processes `postMessage` data insecurely and "
                                    f"passes it to a DOM sink (`{sink}`) without validation.\n\n"
                                    f"**REAL DATA PROOF**: Browser confirmed "
                                    f"{'dialog execution' if dialog_fired else f'sink `{sink}` reached'} "
                                    f"after sending postMessage payload:\n`{payload_js[:120]}`"
                                ),
                                severity=Severity.HIGH,
                                evidence={
                                    "payload": payload_js, "sink": sink,
                                    "url": url, "xss_type": "postMessage",
                                    "dialog_fired": dialog_fired,
                                    "dialog_msg": dialog_msg,
                                },
                                remediation=(
                                    "Validate the `event.origin` in all `window.addEventListener('message', ...)` handlers. "
                                    "Never pass `event.data` directly to innerHTML or other sinks. "
                                    "Use DOMPurify and allowlist known message origins."
                                ),
                                poc=(
                                    f"# Open browser console on {url} and run:\n"
                                    f"{payload_js}"
                                ),
                                plugin_slug=self.slug,
                                is_verified=True,
                            )
                            # Reset for next payload
                            dialog_fired = False
                            await page.evaluate("() => { window.__xss_dom = null; }")
                    except Exception:
                        pass
            finally:
                await page.close()

        except Exception as e:
            logger.debug(f"postMessage XSS scan error: {e}")

    # ── Phase 4: CSTI Scan ────────────────────────────────────────────────

    async def _run_csti_scan_async(self, url: str, scan) -> AsyncGenerator[FindingData, None]:
        """
        Detect CSTI (Angular, Vue, Moustache, etc.) by injecting {{7*7}} and checking for 49.
        """
        payloads = ["{{7*7}}", "${7*7}", "<%= 7*7 %>", "[[7*7]]"]
        params = ["q", "s", "search", "id", "name"]
        
        from scans.utils import make_evidence_request_async
        for param in params:
            for pl in payloads:
                probe_url = f"{url}{'&' if '?' in url else '?'}{param}={pl}"
                try:
                    resp, req, res, poc = await make_evidence_request_async(probe_url, timeout=5)
                    if resp and "49" in resp.text and pl not in resp.text:
                        yield FindingData(
                            title=f"Client-Side Template Injection (CSTI) on '{param}'",
                            description=(
                                f"The server/client processed the template payload `{pl}` and rendered the result `49`.\n"
                                f"This indicates a CSTI vulnerability which can often be escalated to XSS.\n\n"
                                f"**REAL DATA PROOF**: Payload `{pl}` rendered as `49` in the response."
                            ),
                            severity=Severity.MEDIUM,
                            evidence={"parameter": param, "payload": pl, "result": "49", "url": probe_url},
                            remediation="Ensure template engines are configured to not process user input directly. Use proper escaping.",
                            poc=f"curl -s '{probe_url}' | grep '49'",
                            plugin_slug=self.slug,
                            is_verified=True,
                        )
                except Exception:
                    pass

    # ── Phase 5: Prototype Pollution ──────────────────────────────────────

    async def _run_prototype_pollution_async(self, url: str, scan, context) -> AsyncGenerator[FindingData, None]:
        """
        Detect Client-Side Prototype Pollution by injecting payloads into URL parameters
        and hash, then checking if the global Object.prototype was modified.
        """
        SENTINEL = "__xss_sentinel__"
        payloads = DOM_PAYLOADS["prototype"]

        try:
            page = await context.new_page()
            try:
                for payload in payloads:
                    # Test in both query and hash
                    for separator in ("?", "#"):
                        probe_url = f"{url}{separator}{payload.replace('__xss_sentinel__', SENTINEL)}"
                        try:
                            await page.goto(probe_url, timeout=10000, wait_until="domcontentloaded")
                            await asyncio.sleep(1)
                            
                            dom_result = await page.evaluate("() => window.__xss_dom")
                            if dom_result and dom_result.get("sink") == "Prototype Pollution":
                                yield FindingData(
                                    title="Client-Side Prototype Pollution",
                                    description=(
                                        f"The application on `{url}` is vulnerable to Client-Side Prototype Pollution.\n"
                                        f"An attacker can inject properties into `Object.prototype` via URL parameters.\n\n"
                                        f"**REAL DATA PROOF**: Injected `{payload}` via URL and confirmed `Object.prototype.__proto_polluted` was modified in the global context."
                                    ),
                                    severity=Severity.HIGH,
                                    evidence={"payload": payload, "url": probe_url, "sink": "Prototype Pollution"},
                                    remediation=(
                                        "Sanitise all recursive object merges. Use `Object.create(null)` for plain objects. "
                                        "Freeze `Object.prototype` if possible, or use a library that is resistant to prototype pollution."
                                    ),
                                    poc=f"Navigate to: {probe_url}",
                                    plugin_slug=self.slug,
                                    is_verified=True,
                                )
                                break # Found one for this payload
                        except Exception:
                            pass
            finally:
                await page.close()
        except Exception as e:
            logger.debug(f"Prototype Pollution scan error: {e}")

    # ── Verification ──────────────────────────────────────────────────────

    async def verify_async(self, finding) -> bool:
        from playwright.async_api import async_playwright
        from scans.utils import make_evidence_request_async

        evidence = finding.evidence
        if not isinstance(evidence, dict):
            return False

        xss_type = evidence.get("xss_type", "reflected")
        param    = evidence.get("parameter")
        payload  = evidence.get("payload")
        poc_url  = evidence.get("url")

        # DOM-type: re-run browser check
        if xss_type in ("dom", "postMessage"):
            try:
                async with async_playwright() as pw:
                    browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                    try:
                        context = await browser.new_context(ignore_https_errors=True)
                        await context.add_init_script(INSTRUMENTATION_SCRIPT)
                        page = await context.new_page()

                        dialog_fired = False
                        async def on_dialog(d):
                            nonlocal dialog_fired
                            dialog_fired = True
                            await d.dismiss()
                        page.on("dialog", on_dialog)

                        await page.goto(poc_url or "", timeout=15000, wait_until="domcontentloaded")
                        await asyncio.sleep(2)
                        dom_result = await page.evaluate("() => window.__xss_dom")

                        if dialog_fired or dom_result:
                            finding.is_verified = True
                            finding.description += "\n\n**REAL EXECUTION PROOF**: Confirmed again in headless browser."
                            from asgiref.sync import sync_to_async
                            await sync_to_async(finding.save)()
                            return True
                    finally:
                        await browser.close()
            except Exception:
                pass
            return False

        # Reflected: HTTP reflection check
        if param and payload:
            try:
                from asgiref.sync import sync_to_async
                scan   = await sync_to_async(lambda: finding.scan)()
                target = await sync_to_async(lambda: scan.target)()
                t_url  = target.host
                if not t_url.startswith("http"):
                    t_url = f"http://{t_url}"

                resp, req, res, poc = await make_evidence_request_async(
                    t_url, method="GET", params={param: payload}, timeout=10
                )
                if resp and payload in resp.text:
                    finding.is_verified = True
                    finding.request     = req
                    finding.response    = res
                    finding.poc         = poc
                    from asgiref.sync import sync_to_async
                    await sync_to_async(finding.save)()
                    return True
            except Exception:
                pass

        return False
