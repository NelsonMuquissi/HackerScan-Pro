"""
Custom middleware for HackerScan Pro.

PrometheusMiddleware — instruments every HTTP request with:
  - hackerscan_http_requests_total (counter)
  - hackerscan_http_request_duration_seconds (histogram)
  - hackerscan_http_requests_in_progress (gauge)
"""
import time
import structlog

from .metrics import (
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
)

logger = structlog.get_logger("hackerscan.middleware")

# Paths that should NOT be instrumented (avoid metric cardinality explosion)
_SKIP_PATHS = frozenset({"/health/", "/health/ready/", "/metrics/"})


class PrometheusMiddleware:
    """
    Django middleware that records Prometheus metrics for every request.
    Skips health/metrics endpoints to avoid noise.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Skip internal endpoints
        if path in _SKIP_PATHS:
            return self.get_response(request)

        method = request.method

        # Normalize path to first two segments to avoid label explosion
        # e.g. /v1/scans/abc-123/ → /v1/scans/
        endpoint = self._normalize_path(path)

        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).inc()
        start_time = time.perf_counter()

        try:
            response = self.get_response(request)
        except Exception:
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint, status_code="500"
            ).inc()
            HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()
            raise

        duration = time.perf_counter() - start_time
        status_code = str(response.status_code)

        HTTP_REQUESTS_TOTAL.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            method=method, endpoint=endpoint
        ).observe(duration)
        HTTP_REQUESTS_IN_PROGRESS.labels(method=method).dec()

        # Log slow requests (> 2s)
        if duration > 2.0:
            logger.warning(
                "slow_request",
                path=path,
                method=method,
                duration_s=round(duration, 3),
                status=status_code,
            )

        return response

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        Reduce path cardinality by keeping only the first two segments.
        /v1/scans/abc-123/findings/ → /v1/scans/
        /v1/auth/login/ → /v1/auth/
        """
        parts = path.strip("/").split("/")
        if len(parts) >= 2:
            return f"/{parts[0]}/{parts[1]}/"
        return path
