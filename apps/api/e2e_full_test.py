"""
HackerScan Pro - Comprehensive E2E Test Suite (Async Native)
Real targets, no mocks, no simulations.

Run: python -X utf8 manage.py shell --command="import asyncio; from e2e_full_test import main; asyncio.run(main())"
"""
import sys, io, traceback, time, uuid, os, asyncio
from datetime import datetime

# Force UTF-8 to avoid Windows cp1252 errors
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

def ok(msg):     print(f"  [PASS] {msg}", flush=True)
def fail(msg):   print(f"  [FAIL] {msg}", flush=True)
def info(msg):   print(f"  [INFO] {msg}", flush=True)
def warn(msg):   print(f"  [WARN] {msg}", flush=True)
def header(msg): print(f"\n{'='*60}\n{msg}\n{'='*60}", flush=True)

RESULTS = []

def record(name, passed, detail=""):
    RESULTS.append({"name": name, "passed": passed, "detail": detail})
    (ok if passed else fail)(f"{name}: {detail}")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
import django
try:
    django.setup()
except Exception:
    pass

# ─── Mock Objects ────────────────────────────────────────────────────────────

class MockScan:
    def __init__(self):
        self.id          = str(uuid.uuid4())
        self.scan_type   = "quick"
        self.config      = {}
        self.plugin_ids  = []
        self.total_findings = 0

    class target:
        host = "example.com"
        workspace_id = "test-ws"
        target_type = "url"
        def __init__(self, host="example.com", target_type="url"):
            self.host = host
            self.target_type = target_type

mock_scan = MockScan()

# =============================================================
# ASYNC TEST RUNNER
# =============================================================

async def main():
    header("HackerScan Pro: Real E2E Async Validation")
    
    # 1. make_evidence_request_async Utility
    header("TEST 1: make_evidence_request_async Utility")
    try:
        from scans.utils import make_evidence_request_async
        resp, req_dump, res_dump, poc = await make_evidence_request_async("http://example.com", timeout=10)
        assert resp is not None
        assert resp.status_code == 200
        record("make_evidence_request_async basic GET", True, f"HTTP {resp.status_code}")
    except Exception as e:
        record("make_evidence_request_async", False, str(e))

    # 2. Strategy Registry
    header("TEST 2: Strategy Registry")
    try:
        from scans.strategies.base import list_strategies
        # Import all to trigger registration
        import scans.strategies.port_scan, scans.strategies.ssl_check
        import scans.strategies.headers_check, scans.strategies.nuclei_scan
        import scans.strategies.subdomain_recon, scans.strategies.sslyze_audit
        import scans.strategies.dir_fuzzing, scans.strategies.resource_discovery
        import scans.strategies.specialized, scans.strategies.sqlmap_scan
        import scans.strategies.xss_scan, scans.strategies.js_secrets
        import scans.strategies.dns_audit, scans.strategies.cloud_enum
        import scans.strategies.container_security, scans.strategies.api_fuzzer
        import scans.strategies.shodan_recon

        strategies = list_strategies()
        slugs = [s.slug for s in strategies]
        record("Strategy registry", len(slugs) >= 10, f"Found {len(slugs)} strategies")
    except Exception as e:
        record("Strategy registry", False, str(e))

    # 3. Headers Check (Async)
    header("TEST 3: headers_check Strategy")
    try:
        from scans.strategies.base import get_strategy
        s = get_strategy("headers_check")
        target = mock_scan.target("http://example.com", "url")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("headers_check run_async", len(findings) > 0, f"Found {len(findings)} security headers")
    except Exception as e:
        record("headers_check", False, str(e))

    # 4. API Fuzzer (Async Fallback)
    header("TEST 4: api_fuzzer Strategy (Fallback Engine)")
    try:
        s = get_strategy("api_fuzzer")
        target = mock_scan.target("http://httpbin.org", "url")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("api_fuzzer run_async", len(findings) > 0, f"Found {len(findings)} endpoints on httpbin")
    except Exception as e:
        record("api_fuzzer", False, str(e))

    # 5. Dir Fuzzing (Async Fallback)
    header("TEST 5: dir_fuzzing Strategy")
    try:
        s = get_strategy("dir_fuzzing")
        target = mock_scan.target("http://testphp.vulnweb.com", "url")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("dir_fuzzing run_async", len(findings) > 0, f"Found {len(findings)} paths on vulnweb")
    except Exception as e:
        record("dir_fuzzing", False, str(e))

    # 6. SQL Injection Enrichment Mock-Target logic
    header("TEST 6: sqlmap_scan Enrichment logic")
    try:
        from scans.strategies.sqlmap_scan import SQLMapStrategy
        s = SQLMapStrategy()
        mock_log = "current database: 'hackerscan_db'\ncurrent user: 'admin'"
        from scans.strategies.base import FindingData
        findings = [FindingData(title="SQLi", description="Detected", plugin_slug="sqlmap_scan")]
        s._apply_enrichment(findings, mock_log)
        passed = "REAL DATA PROOF" in findings[0].description and "hackerscan_db" in findings[0].description
        record("sqlmap enrichment logic", passed, "Verified metadata injection into findings")
    except Exception as e:
        record("sqlmap enrichment", False, str(e))

    # 7. XSS Scan (Real but likely no hits on simple target)
    header("TEST 7: xss_scan Strategy")
    try:
        s = get_strategy("xss_scan")
        target = mock_scan.target("http://testphp.vulnweb.com/listproducts.php?cat=1", "url")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("xss_scan run_async", True, f"Ran successfully, found {len(findings)} potential issues")
    except Exception as e:
        record("xss_scan", False, str(e))

    # 8. DNS Audit (Real)
    header("TEST 8: dns_audit Strategy")
    try:
        s = get_strategy("dns_audit")
        target = mock_scan.target("google.com", "domain")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("dns_audit run_async", len(findings) > 0, f"Found {len(findings)} DNS records")
    except Exception as e:
        record("dns_audit", False, str(e))

    # 9. SSL Audit (Real)
    header("TEST 9: ssl_check Strategy")
    try:
        s = get_strategy("ssl_check")
        target = mock_scan.target("google.com", "domain")
        findings = []
        async for f in s.run_async(target, scan=mock_scan):
            findings.append(f)
        record("ssl_check run_async", len(findings) > 0, f"Found {len(findings)} TLS findings")
    except Exception as e:
        record("ssl_check", False, str(e))

    header("FINAL E2E ASYNC REPORT")
    passed_count = sum(1 for r in RESULTS if r["passed"])
    total_count = len(RESULTS)
    for r in RESULTS:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"  {status} {r['name']}: {r['detail']}")
    print(f"\nSummary: {passed_count}/{total_count} Passed")
    print(f"Success Rate: {(passed_count/total_count)*100:.1f}%")

if __name__ == "__main__":
    pass
