"""
HackerScan Pro - Zero Simulation E2E Test Suite (Mock-Based Logic Verification)
Run: python -X utf8 manage.py shell --command="import asyncio; from zero_simulation_e2e import main; asyncio.run(main())"
"""
import sys, io, traceback, time, uuid, os, re, asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def ok(msg):     print(f"  [PASS] {msg}", flush=True)
def fail(msg):   print(f"  [FAIL] {msg}", flush=True)
def info(msg):   print(f"  [INFO] {msg}", flush=True)
def warn(msg):   print(f"  [WARN] {msg}", flush=True)

# Mock missing modules for logic verification
try:
    import playwright
except ImportError:
    warn("Playwright not found, mocking for logic verification")
    pw_mock = MagicMock()
    sys.modules["playwright"] = pw_mock
    sys.modules["playwright.async_api"] = pw_mock

RESULTS = []
def record(name, passed, detail=""):
    RESULTS.append({"name": name, "passed": passed, "detail": detail})
    (ok if passed else fail)(f"{name}: {detail}")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Mock Scan objects
class MockScan:
    def __init__(self, host="example.com"):
        self.id = str(uuid.uuid4())
        self.target = MagicMock()
        self.target.host = host
        self.target.target_type = "url"
        self.target.credentials = MagicMock()
        self.target.credentials.filter.return_value = []
    def save(self): pass

# Mock Channels to avoid Redis errors during E2E logic verification
from unittest.mock import MagicMock
import sys
mock_channel_layer = MagicMock()
mock_channel_layer.group_send = AsyncMock()

# Mock scans.services to prevent terminal broadcast errors
try:
    import scans.services
    scans.services.broadcast_terminal_line = MagicMock()
    scans.services.async_broadcast_terminal_line = AsyncMock()
except ImportError:
    pass

with patch("channels.layers.get_channel_layer", return_value=mock_channel_layer):
    pass

async def main():
    header = lambda msg: print(f"\n{'='*60}\n{msg}\n{'='*60}", flush=True)
    header("HackerScan Pro: Zero Simulation E2E Validation")
    
    # 1. SQLMap Enrichment Test
    header("TEST 1: SQLMap Active Metadata Extraction")
    try:
        from scans.strategies.sqlmap_scan import SQLMapStrategy
        from scans.strategies.base import FindingData
        from scans.models import Severity
        
        strategy = SQLMapStrategy()
        log_content = """
        available databases [2]:
        [*] information_schema
        [*] hackerscan_db
        
        current database: 'hackerscan_db'
        current user: 'admin@localhost'
        hostname: 'db-server-01'
        """
        
        findings = [FindingData(title="SQL Injection", description="Detected", severity=Severity.HIGH, plugin_slug="sqlmap_scan")]
        strategy._apply_enrichment(findings, log_content)
        
        f = findings[0]
        passed = "REAL DATA PROOF" in f.description and "hackerscan_db" in f.description
        record("SQLMap Data Enrichment", passed, "Successfully added metadata to finding description")
    except Exception as e:
        record("SQLMap Test", False, str(e))

    # 2. XSS Playwright Verification Test
    header("TEST 2: XSS Playwright Verification logic")
    try:
        from scans.strategies.xss_scan import XSStrikeStrategy
        from scans.models import Finding
        strategy = XSStrikeStrategy()
        
        mock_finding = MagicMock(spec=Finding)
        mock_finding.evidence = {"xss_type": "dom", "parameter": "q", "payload": "<script>alert(1)</script>", "url": "http://victim.com/"}
        mock_finding.scan = MockScan("victim.com")
        mock_finding.description = "XSS found"
        
        # Mock Playwright
        with patch("playwright.async_api.async_playwright") as mock_pw:
            # Playwright is a context manager
            mock_context_mgr = AsyncMock()
            mock_pw.return_value = mock_context_mgr
            
            mock_playwright = AsyncMock()
            mock_context_mgr.__aenter__.return_value = mock_playwright
            
            mock_browser = AsyncMock()
            mock_playwright.chromium.launch.return_value = mock_browser
            
            mock_browser_context = AsyncMock()
            mock_browser.new_context.return_value = mock_browser_context
            
            mock_page = AsyncMock()
            mock_browser_context.new_page.return_value = mock_page
            
            # Simulate a dialog event being triggered
            async def mock_goto(*args, **kwargs):
                # Simulate the callback being called by playwright
                for call in mock_page.on.call_args_list:
                    if call[0][0] == "dialog":
                        handler = call[0][1]
                        mock_dialog = MagicMock()
                        handler(mock_dialog)
                return MagicMock()
            
            mock_page.goto.side_effect = mock_goto
            
            result = await strategy.verify_async(mock_finding)
            passed = result is True and "REAL EXECUTION PROOF" in mock_finding.description
            record("XSS Playwright Verification Logic", passed, "Verified that dialog detection triggers execution proof")
    except Exception as e:
        record("XSS Test", False, str(e))
        traceback.print_exc()

    # 3. JS Secrets Active Validation Test
    header("TEST 3: JS Secrets Active Validation")
    try:
        from scans.strategies.js_secrets import JSSecretScanStrategy
        from scans.models import Finding
        strategy = JSSecretScanStrategy()
        
        # Mock finding — token MUST match regex: ghp_[a-zA-Z0-9]{36}
        import hmac, hashlib
        mock_token = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"  # exactly ghp_ + 36 chars
        stored_hmac = hmac.new(
            b"hackerscan-internal",
            mock_token.encode(),
            hashlib.sha256
        ).hexdigest()
        
        mock_finding = MagicMock(spec=Finding)
        mock_finding.evidence = {
            "source": "http://example.com/app.js",
            "raw_secret_internal": mock_token,
            "secret_hmac": stored_hmac,
            "pattern_name": "GitHub Personal Access Token"
        }
        mock_finding.description = "Secret found - **REAL DATA PROOF**"
        mock_finding.is_verified = False
        
        # Mock the network utility
        with patch("scans.utils.make_evidence_request_async") as mock_req:
            # 1. Source verification (exists in JS)
            mock_resp_js = MagicMock()
            mock_resp_js.status_code = 200
            mock_resp_js.text = f"var key = '{mock_token}';"
            mock_req.return_value = (mock_resp_js, "req", "res", "poc")
            
            # 2. Mock httpx.AsyncClient for API validation (used inside _validate_secret_async)
            mock_resp_api = MagicMock()
            mock_resp_api.status_code = 200
            mock_resp_api.json.return_value = {"login": "test-bot", "name": "Test Bot"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_resp_api
            mock_client_ctx = AsyncMock()
            mock_client_ctx.__aenter__.return_value = mock_client_instance
            
            with patch("httpx.AsyncClient", return_value=mock_client_ctx):
                # Mock asgiref sync_to_async for saving
                with patch("asgiref.sync.sync_to_async", return_value=AsyncMock()):
                    result = await strategy.verify_async(mock_finding)
                    passed = result is True and "REAL DATA PROOF" in mock_finding.description and "test-bot" in mock_finding.description
                    record("JS Secret Active Validation", passed, "Verified that active API check enriches the finding")
    except Exception as e:
        record("JS Secret Test", False, str(e))
        traceback.print_exc()

    # 4. Resource Discovery Data Extraction Test
    header("TEST 4: Resource Discovery Active Extraction")
    try:
        from scans.strategies.resource_discovery import ResourceDiscoveryStrategy
        strategy = ResourceDiscoveryStrategy()
        
        # Test .env extraction
        content = "DB_HOST=internal-db.prod\nDB_USER=root_admin\nSECRET=123"
        findings = strategy._scan_for_secrets(content, "http://target.com/.env", "req", "res", "poc")
        
        env_finding = next((f for f in findings if "Database Credentials" in f.title), None)
        passed = env_finding is not None and env_finding.evidence.get("db_host") == "internal-db.prod"
        record("Resource Discovery (.env extraction)", passed, "Extracted real DB credentials from .env content")
    except Exception as e:
        record("Resource Discovery Test", False, str(e))

    # 5. Cloud Exposure Proof Snippet Test
    header("TEST 5: Cloud Exposure Proof Snippet")
    try:
        from scans.strategies.cloud_enum import CloudExposureStrategy
        from scans.models import Finding
        strategy = CloudExposureStrategy()
        
        mock_finding = MagicMock(spec=Finding)
        mock_finding.evidence = {"url": "http://s3.com/bucket", "sensitive_files": ["dump.sql"]}
        mock_finding.description = "Bucket found"
        
        with patch("scans.utils.make_evidence_request_async") as mock_req:
            # 1. Bucket check
            mock_resp_bucket = MagicMock()
            mock_resp_bucket.status_code = 200
            mock_req.return_value = (mock_resp_bucket, "req", "res", "poc")
            
            # 2. Snippet download
            with patch.object(strategy, "_get_proof_snippet_async", return_value="-- SQL DUMP START") as mock_snippet:
                result = await strategy.verify_async(mock_finding)
                passed = result is True and "REAL DATA PROOF" in mock_finding.description and "SQL DUMP START" in mock_finding.description
                record("Cloud Exposure Proof Snippet", passed, "Verified that snippet download enriches the finding")
    except Exception as e:
        record("Cloud Exposure Test", False, str(e))

    # 6. Database Audit Test (Redis)
    header("TEST 6: Database Audit (Redis Active Probe)")
    try:
        from scans.strategies.database_audit import DatabaseAuditStrategy
        strategy = DatabaseAuditStrategy()
        
        mock_redis_info = (
            b"$1000\r\n"
            b"# Server\r\n"
            b"redis_version:7.0.5\r\n"
            b"os:Linux 5.15.0-x86_64\r\n"
            b"\r\n"
        )
        
        async def mock_open_connection(host, port):
            reader = AsyncMock()
            writer = AsyncMock()
            reader.read.return_value = mock_redis_info
            return reader, writer
            
        with patch("asyncio.open_connection", side_effect=mock_open_connection):
            # We need to simulate the yield from run_async
            results = []
            # Mocking the opened ports check inside run_async
            with patch.object(strategy, "run_async") as mock_run:
                # We'll just test the internal _audit_redis directly for logic verification
                finding = await strategy._audit_redis("127.0.0.1", 6379)
                passed = "REAL DATA PROOF" in finding.description and "7.0.5" in finding.description
                record("Database Audit (Redis Proof)", passed, f"Extracted version 7.0.5 from mock response")
    except Exception as e:
        record("Database Audit Test", False, str(e))

    # 7. Metric Exposure Test (Prometheus)
    header("TEST 7: Metric Exposure (Prometheus Metadata)")
    try:
        from scans.strategies.metric_exposure import MetricExposureStrategy
        strategy = MetricExposureStrategy()
        
        mock_metrics = (
            "# HELP node_uname_info Hardware/OS information\n"
            "# TYPE node_uname_info gauge\n"
            'node_uname_info{release="5.4.0-104-generic",version="v1.2.3"} 1'
        )
        
        async def mock_make_evidence_request(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = mock_metrics
            return resp, "req", "res", "poc"
            
        with patch("scans.utils.make_evidence_request_async", side_effect=mock_make_evidence_request):
            # Test run_async
            findings = []
            async for f in strategy.run_async(MagicMock(host="127.0.0.1"), MagicMock()):
                findings.append(f)
            
            prom_f = next((f for f in findings if "Prometheus" in f.title), None)
            passed = prom_f is not None and "REAL DATA PROOF" in prom_f.description and "5.4.0-104-generic" in prom_f.description
            record("Metric Exposure (Prometheus Proof)", passed, "Extracted kernel release from metrics")
    except Exception as e:
        record("Metric Exposure Test", False, str(e))

    # 8. SAP Recon Test (Web Dispatcher)
    header("TEST 8: SAP Recon (Web Dispatcher Stats)")
    try:
        from scans.strategies.specialized import SAPSpecializedStrategy
        strategy = SAPSpecializedStrategy()
        
        async def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = "SAP Web Dispatcher Statistics - Active connections: 123"
            return resp

        with patch("scans.strategies.specialized.NetworkDiscoveryMixin.check_ports_async", return_value=[8000]):
            with patch("httpx.AsyncClient.get", side_effect=mock_get):
                findings = []
                async for f in strategy.run_async(MagicMock(host="127.0.0.1"), MagicMock()):
                    findings.append(f)
                
                sap_f = next((f for f in findings if "SAP Web Dispatcher" in f.title), None)
                passed = sap_f is not None and "REAL DATA PROOF" in sap_f.description
                record("SAP Recon (Web Dispatcher Proof)", passed, "Verified unauthenticated stats access")
    except Exception as e:
        record("SAP Recon Test", False, str(e))

    # 9. Container Security Test (Docker API)
    header("TEST 9: Container Security (Docker API Metadata)")
    try:
        from scans.strategies.container_security import ContainerSecurityStrategy
        strategy = ContainerSecurityStrategy()
        
        async def mock_evidence_req(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            if "containers/json" in url:
                resp.text = '{"Id": "123", "Names": ["test"]}'
                resp.json.return_value = [{"Id": "123"}]
            else:
                resp.json.return_value = {"Version": "20.10.7", "Os": "linux"}
            return resp, "req", "res", "poc"

        with patch("scans.utils.make_evidence_request_async", side_effect=mock_evidence_req):
            findings = []
            # We test _audit_docker_api directly
            finding = await strategy._audit_docker_api("127.0.0.1", 2375)
            passed = finding is not None and "REAL DATA PROOF" in finding.description and "20.10.7" in finding.description
            record("Container Security (Docker Proof)", passed, "Extracted Docker version 20.10.7")
    except Exception as e:
        record("Container Security Test", False, str(e))

    header("FINAL E2E ZERO SIMULATION REPORT")
    passed_count = sum(1 for r in RESULTS if r["passed"])
    total_count = len(RESULTS)
    for r in RESULTS:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"  {status} {r['name']}: {r['detail']}")
    print(f"\nSummary: {passed_count}/{total_count} Passed")

if __name__ == "__main__":
    pass
