"""
Prometheus metrics definitions for HackerScan Pro.

Exposes:
- HTTP request counters and latency histograms
- Business metrics (active scans, AI calls, report generation)
- /metrics/ endpoint for Prometheus scraping
"""
import time
from django.http import HttpResponse
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ── HTTP Metrics ────────────────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "hackerscan_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "hackerscan_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "hackerscan_http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method"],
)

# ── Business Metrics ────────────────────────────────────────────────────
ACTIVE_SCANS_GAUGE = Gauge(
    "hackerscan_active_scans",
    "Number of scans currently in RUNNING state",
)

SCANS_STARTED_TOTAL = Counter(
    "hackerscan_scans_started_total",
    "Total number of scans initiated",
    ["scan_type"],
)

SCANS_COMPLETED_TOTAL = Counter(
    "hackerscan_scans_completed_total",
    "Total number of scans that finished",
    ["status"],  # completed, failed, timed_out
)

AI_CALLS_TOTAL = Counter(
    "hackerscan_ai_calls_total",
    "Total calls to the AI service (Anthropic)",
    ["method", "status"],  # method: explain/remediate/attack_chain, status: success/error/fallback
)

REPORTS_GENERATED_TOTAL = Counter(
    "hackerscan_reports_generated_total",
    "Total reports generated",
    ["format", "type"],  # format: pdf/json/csv, type: technical/executive
)

FINDINGS_DETECTED_TOTAL = Counter(
    "hackerscan_findings_detected_total",
    "Total vulnerability findings detected across all scans",
    ["severity"],  # critical, high, medium, low, info
)


def metrics_view(request):
    """
    Endpoint that returns all Prometheus metrics.
    Should be mounted at /metrics/ and typically not exposed publicly.
    """
    return HttpResponse(
        generate_latest(),
        content_type=CONTENT_TYPE_LATEST,
    )
