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


@shared_task(
    bind=True,
    max_retries=0,
    name="scans.run_scan",
    # Hard limit: 20 min. Soft limit: 18 min (gives strategies time to flush/cleanup).
    # Individual strategies use their own subprocess timeouts (max 10 min for port_scan).
    soft_time_limit=1080,   # 18 minutes
    time_limit=1200,        # 20 minutes
)
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
            ScanType.VULN: ["nuclei_tech", "nuclei_vuln", "sqlmap_scan", "xss_scan", "js_secrets"],
            ScanType.RECON: ["subdomain_recon", "dns_audit", "shodan_recon", "cloud_exposure", "nuclei_tech"],
            ScanType.SSL: ["sslyze_audit"],
            ScanType.FUZZ: ["dir_fuzzing", "api_fuzzer"],
            ScanType.DISCOVERY: ["resource_discovery", "cloud_exposure"],
            ScanType.FULL: [
                "port_scan", "dns_audit", "shodan_recon", "nuclei_tech",
                "headers_check", "nuclei_full", 
                "sslyze_audit", "dir_fuzzing", "resource_discovery",
                "sqlmap_scan", "xss_scan", "js_secrets",
                "cloud_exposure", "api_fuzzer", "container_security"
            ],
            ScanType.AD_AUDIT: ["ad_tactical"],
            ScanType.K8S_SECURITY: ["k8s_hardening", "container_security"],
            ScanType.SAP_AUDIT: ["sap_recon"],
        }

        strategies_to_run = scan.plugin_ids
        if not strategies_to_run:
            strategies_to_run = SCAN_TYPE_MAP.get(scan.scan_type, [])
        
        all_finding_data = []
        errors: list[str] = []

        # 🚀 NEW: Phased Adaptive Scanning Logic
        RECON_STRATEGIES = ["port_scan", "dns_audit", "shodan_recon", "ssl_check", "nuclei_tech"]
        
        # Determine which strategies from the requested list are "Recon" vs "Targeted"
        requested_strategies = scan.plugin_ids
        if not requested_strategies:
            requested_strategies = SCAN_TYPE_MAP.get(scan.scan_type, [])

        recon_to_run = [s for s in requested_strategies if s in RECON_STRATEGIES]
        targeted_to_run = [s for s in requested_strategies if s not in RECON_STRATEGIES]

        all_finding_data = []
        errors: list[str] = []

        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Phase 1: Reconnaissance (Parallel)
        if recon_to_run:
            logger.info("Starting Phase 1 (Recon): %s", recon_to_run)
            with ThreadPoolExecutor(max_workers=min(len(recon_to_run), 4)) as executor:
                future_to_slug = {}
                for slug in recon_to_run:
                    strategy = get_strategy(slug)
                    if strategy:
                        future_to_slug[executor.submit(strategy.run, scan.target, scan)] = slug
                
                for future in as_completed(future_to_slug):
                    slug = future_to_slug[future]
                    try:
                        results = future.result()
                        for fd in results:
                            if not fd.plugin_slug:
                                fd.plugin_slug = slug
                        all_finding_data.extend(results)
                    except Exception as exc:
                        msg = f"Recon Strategy {slug!r} raised: {exc}"
                        logger.exception(msg)
                        errors.append(msg)

        # 🧠 Phase 1.5: Adaptive Intelligence Analysis
        # Check discovered ports/services to refine targeted scan
        open_ports = set()
        discovered_services = set()
        recon_findings_dicts = []
        for fd in all_finding_data:
            # Prepare findings for AI analysis (including evidence for better decision making)
            recon_findings_dicts.append({
                "title": fd.title,
                "description": fd.description,
                "severity": fd.severity,
                "plugin_slug": fd.plugin_slug,
                "evidence": fd.evidence
            })
            
            if fd.plugin_slug == "port_scan" and isinstance(fd.evidence, dict):
                p = fd.evidence.get("port")
                if p:
                    open_ports.add(int(p))
                s = fd.evidence.get("service", "").lower()
                if s:
                    discovered_services.add(s)

        # Adaptive Filtering: Skip web-specific scans if no web ports or web services are open
        WEB_PORTS = {80, 443, 8000, 8080, 8443, 8888, 9000}
        WEB_SERVICES = {"http", "https", "ssl/http", "http-alt", "http-proxy", "http-mgmt"}
        has_web = any(p in WEB_PORTS for p in open_ports) or any(s in WEB_SERVICES for s in discovered_services)
        
        # If port scan was run and found NO web ports, we filter targeted plugins
        if "port_scan" in recon_to_run and not has_web:
            original_targeted = list(targeted_to_run)
            web_plugins = ["nuclei_vuln", "nuclei_full", "dir_fuzzing", "headers_check", "xss_scan", "api_fuzzer"]
            targeted_to_run = [s for s in targeted_to_run if s not in web_plugins]
            if len(original_targeted) != len(targeted_to_run):
                logger.info("Adaptive Logic: No web ports found. Skipping web plugins: %s", 
                            [p for p in original_targeted if p in web_plugins])

        # 🚀 Step 1.75: AI-Powered Optimization (Optional/Adaptive)
        # If the scan is FULL or AI optimization is enabled in config, ask the AI for advice
        if scan.scan_type == ScanType.FULL or scan.config.get("ai_optimize", True):
            try:
                from ai.services import ai_service
                from scans.strategies.base import list_strategies
                
                available_targeted_slugs = [s.slug for s in list_strategies() if s.slug not in RECON_STRATEGIES]
                
                ai_advice = ai_service.suggest_scan_strategy(
                    recon_findings=recon_findings_dicts,
                    available_strategies=available_targeted_slugs
                )
                
                ai_suggested = ai_advice.get("recommended_strategies", [])
                if ai_suggested:
                    # Prioritize AI suggested strategies by moving them to the front or adding missing ones
                    # Only add if they were originally in the targeted_to_run list (respect user selection)
                    final_targeted = [s for s in ai_suggested if s in targeted_to_run]
                    # Add remaining ones that weren't suggested but were requested
                    final_targeted.extend([s for s in targeted_to_run if s not in final_targeted])
                    
                    if targeted_to_run != final_targeted:
                        logger.info("AI Optimization: Reordered targeted strategies based on recon findings. Reasoning: %s", 
                                    ai_advice.get("reasoning", "N/A"))
                        targeted_to_run = final_targeted

                # Pass nuclei tags to the config if suggested
                if ai_advice.get("nuclei_tags"):
                    scan.config["nuclei_tags"] = ai_advice["nuclei_tags"]
                    
            except Exception as e:
                logger.warning("AI Strategy Optimization failed: %s", e)

        # Phase 2: Targeted Analysis (Parallel)
        if targeted_to_run:
            logger.info("Starting Phase 2 (Targeted): %s", targeted_to_run)
            # Limit concurrency for heavier targeted scans to avoid resource exhaustion
            with ThreadPoolExecutor(max_workers=min(len(targeted_to_run), 3)) as executor:
                future_to_slug = {}
                for slug in targeted_to_run:
                    strategy = get_strategy(slug)
                    if strategy:
                        future_to_slug[executor.submit(strategy.run, scan.target, scan)] = slug
                
                for future in as_completed(future_to_slug):
                    slug = future_to_slug[future]
                    try:
                        results = future.result()
                        for fd in results:
                            if not fd.plugin_slug:
                                fd.plugin_slug = slug
                        all_finding_data.extend(results)
                    except Exception as exc:
                        msg = f"Targeted Strategy {slug!r} raised: {exc}"
                        logger.exception(msg)
                        errors.append(msg)

        # 🚀 Step 3.5: Enrich findings with EPSS intelligence
        try:
            epss_service.enrich_findings(all_finding_data)
        except Exception as e:
            logger.error("EPSS enrichment failed: %s", e)

        # 🚀 Phase 3.75: AI False-Positive Reduction
        # Analyze findings to detect and flag false positives using AI
        if scan.config.get("ai_fp_reduction", True):
            try:
                from ai.services import ai_service
                logger.info("Starting Phase 3.75: AI False-Positive Reduction for %d findings", len(all_finding_data))
                
                # We only analyze findings that have evidence and are not informational
                for fd in all_finding_data:
                    # Severity is an enum, so we check value or slug
                    is_info = fd.severity == Severity.INFO
                    if not is_info and fd.evidence:
                        fp_analysis, _ = ai_service.analyze_false_positive(
                            finding_title=fd.title,
                            description=fd.description,
                            evidence=fd.evidence
                        )
                        
                        if fp_analysis.get("is_false_positive") and fp_analysis.get("confidence", 0) > 0.7:
                            logger.info("AI detected False Positive: %s (Confidence: %.2f). Reasoning: %s", 
                                        fd.title, fp_analysis.get("confidence"), fp_analysis.get("reasoning"))
                            fd.is_false_positive = True
                            fd.ai_reasoning = fp_analysis.get("reasoning")
                            # Optionally downgrade severity or mark it
                            
            except Exception as e:
                logger.warning("AI False-Positive Reduction failed: %s", e)

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
                    # Recurring finding: Update to current scan so it shows in reports/counts
                    f = fingerprint_map[fp]
                    f.last_seen_at = timezone.now()
                    f.scan = scan
                    # Update AI insights if they were calculated in this scan
                    f.is_false_positive = fd.is_false_positive
                    f.ai_reasoning = fd.ai_reasoning
                    f.save(update_fields=["last_seen_at", "scan", "is_false_positive", "ai_reasoning"])
                else:
                    # New finding
                    f_new = Finding(
                        scan=scan,
                        plugin_slug=fd.plugin_slug,
                        severity=fd.severity,
                        title=fd.title,
                        description=fd.description,
                        remediation=fd.remediation,
                        # Normalize evidence: JSONField expects dict, but some strategies return strings
                        evidence=fd.evidence if isinstance(fd.evidence, dict) else {"raw": fd.evidence},
                        cvss_score=fd.cvss_score,
                        epss_score=fd.epss_score,
                        is_false_positive=fd.is_false_positive,
                        ai_reasoning=fd.ai_reasoning,
                        first_seen_at=timezone.now(),
                        last_seen_at=timezone.now(),
                        status=FindingStatus.ACTIVE
                    )
                    # Manually trigger fingerprint generation because bulk_create bypasses .save()
                    f_new.fingerprint = fp
                    findings_to_create.append(f_new)
            
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

