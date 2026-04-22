"""
Celery tasks for the scans app.

run_scan(scan_id)
  1. Marks the scan as RUNNING
  2. Resolves the plugin_ids to strategy instances
  3. Runs each strategy, collecting FindingData results
  4. Persists Finding objects in bulk
  5. Marks scan as COMPLETED (or FAILED on exception)

notify_scan_complete(scan_id)
  Placeholder for webhook/email notification (to be expanded in Step 6).
"""
import logging
from celery import shared_task
from django.db import transaction

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=0, name="scans.run_scan")
def run_scan(self, scan_id: str) -> dict:
    """
    Returns a summary dict for logging/result backend.
    """
    from billing.services import BillingService      # noqa: PLC0415
    from scans.models import Scan, Finding, ScanStatus, ScanType, FindingStatus  # noqa: PLC0415
    from scans.strategies.base import get_strategy      # noqa: PLC0415
    # Import strategies
    import scans.strategies.port_scan    # noqa: F401
    import scans.strategies.ssl_check    # noqa: F401
    import scans.strategies.headers_check  # noqa: F401
    import scans.strategies.nuclei_scan   # noqa: F401
    import scans.strategies.subdomain_recon  # noqa: F401
    import scans.strategies.sslyze_audit  # noqa: F401
    import scans.strategies.dir_fuzzing  # noqa: F401
    import scans.strategies.resource_discovery # noqa: F401
    import scans.strategies.specialized  # noqa: F401
    import scans.strategies.sqlmap_scan  # noqa: F401
    import scans.strategies.xss_scan     # noqa: F401
    import scans.strategies.js_secrets   # noqa: F401
    import scans.strategies.dns_audit    # noqa: F401
    import scans.strategies.cloud_enum   # noqa: F401
    import scans.strategies.container_security # noqa: F401
    import scans.strategies.api_fuzzer   # noqa: F401
    import scans.strategies.shodan_recon # noqa: F401
    from scans.external.epss import epss_service # noqa: PLC0415

    try:
        scan = Scan.objects.select_related("target").get(pk=scan_id)
    except Scan.DoesNotExist:
        logger.error("run_scan: Scan %s not found", scan_id)
        return {"error": "Scan not found"}

    # Guard: only run pending/queued scans
    if scan.status not in (ScanStatus.PENDING, ScanStatus.QUEUED):
        logger.warning("run_scan: Scan %s already in status %s", scan_id, scan.status)
        return {"skipped": True, "status": scan.status}

    # Store Celery task ID for possible cancellation
    scan.celery_task_id = self.request.id or ""
    scan.save(update_fields=["celery_task_id"])

    # Give the frontend a moment to connect its websocket before broadcasting logs
    import time
    time.sleep(1.5)

    scan.mark_running()

    from scans.services import broadcast_scan_update
    broadcast_scan_update(scan)

    try:
        # Define strategy mapping for each ScanType
        SCAN_TYPE_MAP = {
            ScanType.QUICK: ["port_scan", "headers_check"],
            ScanType.VULN: ["nuclei_vuln", "sqlmap_scan", "xss_scan", "js_secrets"],
            ScanType.RECON: ["subdomain_recon", "dns_audit", "shodan_recon", "cloud_exposure"],
            ScanType.SSL: ["sslyze_audit"],
            ScanType.FUZZ: ["dir_fuzzing", "api_fuzzer"],
            ScanType.DISCOVERY: ["resource_discovery", "cloud_exposure"],
            ScanType.FULL: [
                "port_scan", "headers_check", "nuclei_full", 
                "sslyze_audit", "dir_fuzzing", "resource_discovery",
                "sqlmap_scan", "xss_scan", "js_secrets", "dns_audit",
                "shodan_recon", "cloud_exposure", "api_fuzzer", "container_security"
            ],
            ScanType.AD_AUDIT: ["ad_tactical"],
            ScanType.K8S_SECURITY: ["k8s_hardening", "container_security"],
            ScanType.SAP_AUDIT: ["sap_recon"],
        }

        strategies_to_run = SCAN_TYPE_MAP.get(scan.scan_type, [])
        
        all_finding_data = []
        errors: list[str] = []

        for slug in strategies_to_run:
            strategy = get_strategy(slug)
            if strategy is None:
                logger.warning("run_scan: Unknown strategy slug %r — skipping", slug)
                continue
            try:
                results = strategy.run(target=scan.target, scan=scan)
                # Back-fill plugin_slug from strategy if not set
                for fd in results:
                    if not fd.plugin_slug:
                        fd.plugin_slug = strategy.slug
                all_finding_data.extend(results)
            except Exception as exc:
                msg = f"Strategy {slug!r} raised: {exc}"
                logger.exception(msg)
                errors.append(msg)

        # 🚀 Step 3.5: Enrich findings with EPSS intelligence
        try:
            epss_service.enrich_findings(all_finding_data)
        except Exception as e:
            logger.error("EPSS enrichment failed: %s", e)

        # Lifecycle Tracking: Compare with previous findings for this target
        from django.utils import timezone
        existing_findings = Finding.objects.filter(scan__target=scan.target, status=FindingStatus.ACTIVE)
        fingerprint_map = {f.fingerprint: f for f in existing_findings}

        findings_to_create = []
        fingerprints_seen_now = set()

        with transaction.atomic():
            for fd in all_finding_data:
                # Fallback slug if empty
                if not fd.plugin_slug:
                    fd.plugin_slug = "unknown"
                    
                fp = fd.get_fingerprint(scan.target.id) 
                fingerprints_seen_now.add(fp)
                
                if fp in fingerprint_map:
                    # Recurring finding
                    f = fingerprint_map[fp]
                    f.last_seen_at = timezone.now()
                    f.save(update_fields=["last_seen_at"])
                else:
                    # New finding
                    findings_to_create.append(
                        Finding(
                            scan=scan,
                            plugin_slug=fd.plugin_slug,
                            severity=fd.severity,
                            title=fd.title,
                            description=fd.description,
                            remediation=fd.remediation,
                            evidence=fd.evidence,
                            cvss_score=fd.cvss_score,
                            epss_score=fd.epss_score,
                            first_seen_at=timezone.now(),
                            last_seen_at=timezone.now(),
                            status=FindingStatus.ACTIVE
                        )
                    )
            
            if findings_to_create:
                Finding.objects.bulk_create(findings_to_create)
                # Increment usage counter
                BillingService.increment_usage(scan.target.workspace, "findings_count", len(findings_to_create))

            # Mark "Resolved" findings: those that were active but not found in this scan
            resolved_count = existing_findings.exclude(fingerprint__in=fingerprints_seen_now).update(
                status=FindingStatus.RESOLVED,
                resolved_at=timezone.now()
            )
            if resolved_count > 0:
                logger.info("run_scan: Scan %s resolved %d findings", scan_id, resolved_count)

        if errors:
            scan.mark_failed(error="\n".join(errors))
            logger.error("run_scan: Scan %s finished with errors: %s", scan_id, errors)
        else:
            scan.mark_completed()
            logger.info("run_scan: Scan %s completed — %d findings", scan_id, scan.total_findings)

    except Exception as exc:
        msg = f"Unexpected error during scan {scan_id}: {exc}"
        logger.exception(msg)
        scan.mark_failed(error=msg)

    broadcast_scan_update(scan)

    # Trigger notification (non-blocking, ignore failures)
    try:
        notify_scan_complete.delay(str(scan_id))
    except Exception:
        pass

    return {
        "scan_id": str(scan_id),
        "status": scan.status,
        "total_findings": scan.total_findings,
    }


@shared_task(name="scans.notify_scan_complete")
def notify_scan_complete(scan_id: str) -> None:
    """
    Send notifications when a scan finishes.
    Delegates to NotificationService which handles email, webhook and in-app channels
    according to the workspace's notification preferences.
    """
    from scans.models import Scan  # noqa: PLC0415
    try:
        scan = Scan.objects.select_related("target__workspace", "triggered_by").get(pk=scan_id)
    except Scan.DoesNotExist:
        logger.warning("notify_scan_complete: Scan %s not found", scan_id)
        return

    try:
        from notifications.services import NotificationService  # noqa: PLC0415
        NotificationService.notify_scan_completed(scan)
        logger.info("notify_scan_complete: notifications sent for scan %s", scan_id)
    except Exception:
        # Notification failure must never propagate — the scan already succeeded.
        logger.exception("notify_scan_complete: failed to send notifications for scan %s", scan_id)


@shared_task(name="scans.run_scheduled_scan")
def run_scheduled_scan(scheduled_scan_id: str) -> dict:
    """
    Triggers a scan based on a ScheduledScan configuration.
    Called by Celery Beat.
    """
    from scans.models import ScheduledScan, ScanStatus  # noqa: PLC0415
    from scans.services import ScanService             # noqa: PLC0415
    from billing.services import BillingService         # noqa: PLC0415

    try:
        ss = ScheduledScan.objects.select_related("target", "triggered_by").get(pk=scheduled_scan_id)
    except ScheduledScan.DoesNotExist:
        logger.error("run_scheduled_scan: ScheduledScan %s not found", scheduled_scan_id)
        return {"error": "ScheduledScan not found"}

    if not ss.is_active:
        return {"error": "ScheduledScan is inactive"}

    # Use a dummy request or mock user for quota check
    # In a real scenario, we'd check if the workspace has enough quota for this auto-trigger
    # For now, we allow it if the subscription is active.

    try:
        scan = ScanService.create(
            user=ss.triggered_by,
            workspace_id=ss.target.workspace_id,
            target_id=ss.target.id,
            scan_type=ss.scan_type,
            config={}
        )
        ScanService.trigger(ss.target.workspace_id, scan.id)
        logger.info("run_scheduled_scan: triggered scan %s for schedule %s", scan.id, ss.id)
        return {"scan_id": str(scan.id)}
    except Exception as exc:
        logger.exception("run_scheduled_scan: failed to trigger scan for schedule %s", ss.id)
        return {"error": str(exc)}

