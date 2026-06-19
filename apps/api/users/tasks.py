import logging
from celery import shared_task
from django.utils import timezone
from .models import AuditLog, User, UserRole
from notifications.models import Notification
from django.core.cache import cache

logger = logging.getLogger(__name__)

@shared_task(name="users.verify_audit_log_integrity")
def verify_audit_log_integrity(force=False):
    """
    Periodic task to verify the cryptographic integrity of all audit logs.
    Uses batch processing for scalability.
    """
    CACHE_KEY = "audit_log_integrity_status"
    
    # Check if we should skip based on cache
    if not force:
        cached_status = cache.get(CACHE_KEY)
        if cached_status and cached_status.get("status") == "SECURE":
            # If it was secure less than 30 mins ago, skip
            last_checked_str = cached_status.get("last_checked")
            if last_checked_str:
                last_checked = timezone.datetime.fromisoformat(last_checked_str)
                if (timezone.now() - last_checked).total_seconds() < 1800:
                    return {"status": "SKIPPED", "message": "Recently verified."}

    # We fetch all logs that have a hash (skip legacy logs) ordered by sequence
    # Use .iterator() to avoid loading everything into memory
    logs = AuditLog.objects.exclude(current_hash__isnull=True).order_by('created_at', 'id').iterator(chunk_size=1000)
    violations = []
    
    expected_previous_hash = "0" * 64
    processed_count = 0
    
    for log in logs:
        # 1. Verify internal hash (fields haven't changed)
        if not log.verify_integrity():
            violations.append({
                "id": str(log.id),
                "error": "Internal hash mismatch (tampered fields)",
                "action": log.action,
                "timestamp": log.created_at.isoformat()
            })
        
        # 2. Verify chain link
        if log.previous_hash != expected_previous_hash:
             # Check if we already added it due to internal mismatch
             if not any(v['id'] == str(log.id) for v in violations):
                violations.append({
                    "id": str(log.id),
                    "error": f"Chain link broken. Expected prev: {expected_previous_hash[:10]}..., Got: {log.previous_hash[:10]}...",
                    "action": log.action,
                    "timestamp": log.created_at.isoformat()
                })
        
        # Update expected_previous_hash for the next iteration
        expected_previous_hash = log.current_hash
        processed_count += 1
        
        # Limit the number of violations reported in a single notification to avoid payload bloat
        if len(violations) > 50:
            break

    status = "SECURE"
    if violations:
        status = "COMPROMISED"
        msg = f"SECURITY ALERT: {len(violations)} audit log integrity violations detected!"
        logger.critical(msg)
            
        # Notify Superadmins
        superadmins = User.objects.filter(role="superadmin")
        
        for admin in superadmins:
            Notification.objects.create(
                user=admin,
                type=Notification.Type.AUDIT_TAMPERING,
                title="CRITICAL: Audit Log Tampering Detected",
                message=f"System integrity check failed for {len(violations)} log entries. The audit trail has been compromised.",
                data={"violations": violations[:10], "total_violations": len(violations)}
            )
            
    # Cache the result for 1 hour
    cache.set(CACHE_KEY, {
        "status": status,
        "last_checked": timezone.now().isoformat(),
        "violation_count": len(violations),
        "logs_processed": processed_count
    }, 3600)
    
    if violations:
        return {
            "status": "VIOLATION_DETECTED",
            "count": len(violations),
            "violations": violations[:10]
        }
    
    logger.info(f"Audit Log Integrity Verification: PASSED. {processed_count} logs verified.")
    return {"status": "OK", "message": f"Successfully verified {processed_count} logs."}


@shared_task(name="users.backfill_audit_logs")
def backfill_audit_logs():
    """
    Background task to backfill hashes for legacy logs and repair broken chains.
    """
    from django.db import transaction
    
    # 1. Identify logs without current_hash
    legacy_logs = AuditLog.objects.filter(current_hash__isnull=True).order_by("created_at", "id")
    total_count = legacy_logs.count()
    
    if total_count == 0:
        return {"status": "OK", "message": "No legacy logs found."}

    logger.info(f"Starting audit log backfill for {total_count} entries...")
    
    processed_count = 0
    current_prev_hash = "0" * 64
    
    # We'll process legacy logs in chunks to avoid massive transactions
    while True:
        batch = list(legacy_logs[processed_count:processed_count + 500])
        if not batch:
            break
            
        with transaction.atomic():
            for log in batch:
                log.previous_hash = current_prev_hash
                log.current_hash = log.calculate_hash()
                log.save(update_fields=["previous_hash", "current_hash"])
                current_prev_hash = log.current_hash
                processed_count += 1
                
    # Now check if we need to link this to the existing chain
    # Find the log that immediately follows the last legacy log (if any)
    last_legacy = AuditLog.objects.filter(current_hash__isnull=False).order_by("created_at", "id")[processed_count - 1]
    following_log = AuditLog.objects.filter(created_at__gte=last_legacy.created_at).exclude(id=last_legacy.id).order_by("created_at", "id").first()
    
    if following_log and following_log.previous_hash != last_legacy.current_hash:
        logger.info(f"Linking legacy chain to existing chain at log {following_log.id}")
        following_log.previous_hash = last_legacy.current_hash
        following_log.save(update_fields=["previous_hash"])
        # Repair the rest of the chain iteratively
        repair_audit_chain(following_log)

    return {"status": "OK", "processed": processed_count}


@shared_task(name="users.repair_audit_chain_task")
def repair_audit_chain_task(start_log_id=None):
    """
    Task to iteratively repair the cryptographic chain.
    If start_log_id is None, it starts from the first log.
    """
    from .models import AuditLog
    if start_log_id:
        start_log = AuditLog.objects.filter(id=start_log_id).first()
    else:
        # Start from the beginning of time
        start_log = AuditLog.objects.order_by("created_at", "id").first()
        
    if not start_log:
        return {"status": "SKIPPED", "message": "No logs to repair."}

    return repair_audit_chain(start_log)


def repair_audit_chain(start_log):
    """Iteratively repairs the cryptographic chain from a specific point with progress tracking."""
    from django.db.models import Q
    from django.core.cache import cache
    from .models import AuditLog
    
    # Estimate total work
    total_logs = AuditLog.objects.filter(
        Q(created_at__gt=start_log.created_at) | 
        Q(created_at=start_log.created_at, id__gt=start_log.id)
    ).count() + 1
    
    current_log = start_log
    repaired_count = 0
    processed_count = 0
    
    # Initialize cache status
    cache.set("audit_repair_progress", {
        "status": "RUNNING",
        "processed": 0,
        "total": total_logs,
        "percent": 0,
        "repaired": 0,
        "started_at": timezone.now().isoformat()
    }, timeout=3600)
    
    # If starting from the very first log, previous_hash should be genesis
    if not AuditLog.objects.filter(Q(created_at__lt=start_log.created_at) | Q(created_at=start_log.created_at, id__lt=start_log.id)).exists():
        if start_log.previous_hash != "0" * 64:
            start_log.previous_hash = "0" * 64
            start_log.save(update_fields=["previous_hash"])
    
    while current_log:
        try:
            new_hash = current_log.calculate_hash()
            
            # Update current hash
            if current_log.current_hash != new_hash:
                current_log.current_hash = new_hash
                current_log.save(update_fields=["current_hash"])
                repaired_count += 1
            
            processed_count += 1
            
            # Update progress in cache every 50 logs to avoid cache churn
            if processed_count % 50 == 0 or processed_count == total_logs:
                percent = int((processed_count / total_logs) * 100)
                cache.set("audit_repair_progress", {
                    "status": "RUNNING",
                    "processed": processed_count,
                    "total": total_logs,
                    "percent": percent,
                    "repaired": repaired_count,
                    "last_update": timezone.now().isoformat()
                }, timeout=3600)

            # Find next log (deterministic sequence)
            next_log = AuditLog.objects.filter(
                Q(created_at__gt=current_log.created_at) | 
                Q(created_at=current_log.created_at, id__gt=current_log.id)
            ).order_by("created_at", "id").first()
            
            if next_log:
                if next_log.previous_hash != current_log.current_hash:
                    next_log.previous_hash = current_log.current_hash
                    next_log.save(update_fields=["previous_hash"])
                current_log = next_log
            else:
                current_log = None
        except Exception as e:
            logger.error(f"Critical failure during audit repair at log {current_log.id}: {str(e)}")
            cache.set("audit_repair_progress", {
                "status": "FAILED",
                "error": str(e),
                "processed": processed_count,
                "repaired": repaired_count,
                "failed_at": timezone.now().isoformat()
            }, timeout=3600)
            return {"status": "FAILED", "error": str(e), "log_id": current_log.id}
            
    # Final success status
    cache.set("audit_repair_progress", {
        "status": "COMPLETED",
        "processed": processed_count,
        "total": total_logs,
        "percent": 100,
        "repaired": repaired_count,
        "finished_at": timezone.now().isoformat()
    }, timeout=600) # Keep completed status for 10 mins

    logger.info(f"Chain repair completed. {repaired_count} logs updated out of {processed_count} processed.")
    return {"status": "OK", "repaired": repaired_count, "processed": processed_count}
