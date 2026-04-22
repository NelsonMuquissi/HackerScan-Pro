"""
Health check endpoints for HackerScan Pro.

/health/       → Liveness probe  (is the process alive?)
/health/ready/ → Readiness probe (are dependencies reachable?)
"""
import time
import structlog
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache

logger = structlog.get_logger("hackerscan.health")


def health_liveness(request):
    """
    Liveness probe — always returns 200 if the Django process is running.
    Used by orchestrators (K8s, ECS, etc.) to know when to restart.
    Intentionally lightweight: no external calls.
    """
    return JsonResponse({
        "status": "alive",
        "service": "hackerscan-api",
    }, status=200)


def health_readiness(request):
    """
    Readiness probe — verifies all critical dependencies:
      • PostgreSQL (primary database)
      • Redis (cache + Celery broker)
      • Celery (at least one worker responding)

    Returns 200 if ALL services are healthy, 503 otherwise.
    """
    checks = {}
    overall_healthy = True

    # ── 1. Database ─────────────────────────────────────────────────
    db_start = time.perf_counter()
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {
            "status": "up",
            "latency_ms": round((time.perf_counter() - db_start) * 1000, 1),
        }
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)}
        overall_healthy = False
        logger.error("readiness_check_failed", component="database", error=str(e))

    # ── 2. Redis / Cache ────────────────────────────────────────────
    redis_start = time.perf_counter()
    try:
        cache.set("_readiness_probe", "ok", timeout=5)
        value = cache.get("_readiness_probe")
        if value != "ok":
            raise ConnectionError("Cache set/get mismatch")
        cache.delete("_readiness_probe")
        checks["redis"] = {
            "status": "up",
            "latency_ms": round((time.perf_counter() - redis_start) * 1000, 1),
        }
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}
        overall_healthy = False
        logger.error("readiness_check_failed", component="redis", error=str(e))

    # ── 3. Celery Worker ────────────────────────────────────────────
    celery_start = time.perf_counter()
    try:
        from config.celery import app as celery_app

        # Ping the Celery workers with a short timeout
        inspector = celery_app.control.inspect(timeout=2.0)
        ping_response = inspector.ping()

        if ping_response:
            worker_count = len(ping_response)
            checks["celery"] = {
                "status": "up",
                "workers": worker_count,
                "latency_ms": round((time.perf_counter() - celery_start) * 1000, 1),
            }
        else:
            checks["celery"] = {"status": "down", "error": "No workers responded to ping"}
            overall_healthy = False
            logger.warning("readiness_check_failed", component="celery", error="no_workers")
    except Exception as e:
        checks["celery"] = {"status": "down", "error": str(e)}
        overall_healthy = False
        logger.error("readiness_check_failed", component="celery", error=str(e))

    # ── Response ────────────────────────────────────────────────────
    status_code = 200 if overall_healthy else 503
    return JsonResponse({
        "status": "ready" if overall_healthy else "not_ready",
        "checks": checks,
    }, status=status_code)
