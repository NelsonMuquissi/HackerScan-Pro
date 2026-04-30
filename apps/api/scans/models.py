"""
HackScan Pro — Scans models.

ScanTarget  → a host/IP/URL to be scanned (belongs to a Workspace)
Scan        → one execution run against a target
Finding     → a single security observation produced by a scan
ScanPlugin  → registry of available scan capabilities
"""
import uuid

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel, UUIDModel

User = get_user_model()


# ─── Enums ─────────────────────────────────────────────────────────────────

class TargetType(models.TextChoices):
    DOMAIN = "domain", "Domain"
    IP     = "ip",     "IP Address"
    URL    = "url",    "URL"
    CIDR   = "cidr",   "CIDR Range"


class CredentialType(models.TextChoices):
    BASIC_AUTH = "basic_auth", "Basic Authentication"
    HEADER     = "header",     "HTTP Header"
    COOKIE     = "cookie",     "Cookie"
    OAUTH2     = "oauth2",     "OAuth2 / Bearer Token"


class ScanStatus(models.TextChoices):
    PENDING   = "pending",   "Pending"
    QUEUED    = "queued",    "Queued"
    RUNNING   = "running",   "Running"
    COMPLETED = "completed", "Completed"
    FAILED    = "failed",    "Failed"
    CANCELLED = "cancelled", "Cancelled"


class ScanType(models.TextChoices):
    QUICK       = "quick",       "Quick Scan (Nmap + Headers)"
    FULL        = "full",        "Full Security Scan (Nuclei + All Plugins)"
    VULN        = "vuln",        "Vulnerability Research (Nuclei)"
    RECON       = "recon",       "Recon & Subdomains (Subfinder)"
    SSL         = "ssl",         "SSL/TLS Audit (SSLyze)"
    FUZZ        = "fuzz",        "Directory Fuzzing (Gobuster)"
    DISCOVERY   = "discovery",   "Resource Discovery (BS4 + Custom)"
    AD_AUDIT    = "ad_audit",    "Active Directory Tactical Audit"
    K8S_SECURITY = "k8s_security", "Kubernetes Hardening & Security"
    SAP_AUDIT   = "sap_audit",   "SAP Ecosystem Recon"


class Frequency(models.TextChoices):
    DAILY   = "daily",   "Daily"
    WEEKLY  = "weekly",  "Weekly"
    MONTHLY = "monthly", "Monthly"


class Severity(models.TextChoices):
    INFO     = "info",     "Info"
    LOW      = "low",      "Low"
    MEDIUM   = "medium",   "Medium"
    HIGH     = "high",     "High"
    CRITICAL = "critical", "Critical"


class FindingStatus(models.TextChoices):
    ACTIVE      = "active",      "Active"
    RESOLVED    = "resolved",    "Resolved"
    FIXED       = "fixed",       "Fixed"
    SUPPRESSED  = "suppressed",  "Suppressed"


# ─── ScanTarget ────────────────────────────────────────────────────────────

class ScanTarget(UUIDModel, TimestampedModel):
    """A host/IP/URL registered by the user for scanning."""
    workspace = models.ForeignKey(
        "users.Workspace", on_delete=models.CASCADE, related_name="scan_targets"
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="scan_targets"
    )
    name         = models.CharField(max_length=255)
    host         = models.CharField(max_length=512, help_text="e.g. example.com, 192.168.1.1")
    target_type  = models.CharField(max_length=20, choices=TargetType.choices, default=TargetType.DOMAIN)
    description  = models.TextField(blank=True)
    is_verified  = models.BooleanField(default=False)
    tags         = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("workspace", "host")]

    def __str__(self):
        return f"{self.name} ({self.host})"


class TargetCredential(UUIDModel, TimestampedModel):
    """Credentials associated with a ScanTarget for authenticated scans."""
    target = models.ForeignKey(
        ScanTarget, on_delete=models.CASCADE, related_name="credentials"
    )
    name = models.CharField(max_length=255, help_text="e.g. 'Admin Login', 'API Token'")
    cred_type = models.CharField(max_length=20, choices=CredentialType.choices)
    
    # Encrypted fields would be better in production, using JSON for now
    # Format: {"username": "...", "password": "..."} or {"key": "Authorization", "value": "Bearer ..."}
    value = models.JSONField(help_text="Credential data (keys vary by type)")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.cred_type}) for {self.target.host}"


# ─── ScanPlugin ────────────────────────────────────────────────────────────

class ScanPlugin(UUIDModel, TimestampedModel):
    """Registry of available scanning capabilities."""
    slug        = models.SlugField(max_length=100, unique=True)
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    config_schema = models.JSONField(default=dict, blank=True, help_text="JSON Schema for plugin config")

    class Meta:
        ordering = ["slug"]

    def __str__(self):
        return self.slug


# ─── Scan ──────────────────────────────────────────────────────────────────

class Scan(UUIDModel, TimestampedModel):
    """One security scan execution against a ScanTarget."""
    target      = models.ForeignKey(ScanTarget, on_delete=models.CASCADE, related_name="scans")
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="triggered_scans")
    status      = models.CharField(max_length=20, choices=ScanStatus.choices, default=ScanStatus.PENDING, db_index=True)
    scan_type   = models.CharField(max_length=20, choices=ScanType.choices, default=ScanType.QUICK, db_index=True)
    plugin_ids  = models.JSONField(default=list, help_text='e.g. ["port_scan", "ssl_check"]')
    config      = models.JSONField(default=dict, blank=True, help_text="Per-scan override config")

    # Timing
    started_at  = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Result summary
    total_findings   = models.IntegerField(default=0)
    critical_count   = models.IntegerField(default=0)
    high_count       = models.IntegerField(default=0)
    medium_count     = models.IntegerField(default=0)
    low_count        = models.IntegerField(default=0)
    info_count       = models.IntegerField(default=0)

    # Error info (if failed)
    error_message = models.TextField(blank=True)

    # Celery task ID for cancellation
    celery_task_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Scan {self.id} [{self.status}] → {self.target.host}"

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def mark_running(self):
        self.status = ScanStatus.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self):
        self.status = ScanStatus.COMPLETED
        self.finished_at = timezone.now()
        self._refresh_finding_counts()
        self.save(update_fields=["status", "finished_at", "total_findings",
                                  "critical_count", "high_count", "medium_count",
                                  "low_count", "info_count"])

    def mark_failed(self, error: str = ""):
        self.status = ScanStatus.FAILED
        self.finished_at = timezone.now()
        self.error_message = error
        self.save(update_fields=["status", "finished_at", "error_message"])

    def _refresh_finding_counts(self):
        from django.db.models import Count # noqa: PLC0415
        qs = self.findings.values("severity").annotate(count=Count("id"))
        
        # Initialize counts
        self.critical_count = 0
        self.high_count     = 0
        self.medium_count   = 0
        self.low_count      = 0
        self.info_count     = 0
        self.total_findings = 0

        for row in qs:
            sev = row["severity"].lower() if row["severity"] else ""
            cnt = row["count"]
            if sev == "critical": self.critical_count += cnt
            elif sev == "high":   self.high_count += cnt
            elif sev == "medium": self.medium_count += cnt
            elif sev == "low":    self.low_count += cnt
            elif sev == "info":   self.info_count += cnt
            self.total_findings += cnt


# ─── ScheduledScan ───────────────────────────────────────────────────────────

class ScheduledScan(UUIDModel, TimestampedModel):
    """Configuration for recurring scans."""
    target      = models.ForeignKey(ScanTarget, on_delete=models.CASCADE, related_name="schedules")
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scheduled_scans")
    scan_type   = models.CharField(max_length=20, choices=ScanType.choices, default=ScanType.QUICK)
    frequency   = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY)
    is_active   = models.BooleanField(default=True)
    
    # Connection to django-celery-beat
    periodic_task = models.OneToOneField(
        "django_celery_beat.PeriodicTask",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_scan"
    )

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("target", "scan_type")]

    def __str__(self):
        return f"{self.frequency.capitalize()} {self.scan_type} on {self.target.host}"


# ─── Finding ───────────────────────────────────────────────────────────────

class Finding(UUIDModel, TimestampedModel):
    """A single security observation produced by a scan plugin."""
    scan        = models.ForeignKey(Scan, on_delete=models.CASCADE, related_name="findings")
    plugin_slug = models.CharField(max_length=100, db_index=True)
    severity    = models.CharField(max_length=20, choices=Severity.choices, default=Severity.INFO, db_index=True)
    status      = models.CharField(max_length=20, choices=FindingStatus.choices, default=FindingStatus.ACTIVE, db_index=True)
    
    title       = models.CharField(max_length=512)
    description = models.TextField()
    remediation = models.TextField(blank=True)
    ai_explanation = models.TextField(blank=True, null=True)
    ai_remediation = models.TextField(blank=True, null=True)

    # Structured evidence
    evidence    = models.JSONField(default=dict, blank=True)
    cvss_score  = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    epss_score  = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    # Lifecycle Tracking
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at  = models.DateTimeField(default=timezone.now)
    
    # Deduplication / tracking
    fingerprint = models.CharField(max_length=64, blank=True, db_index=True,
                                   help_text="SHA-256 of (scan.target_id, plugin_slug, title)")
    is_false_positive = models.BooleanField(default=False)
    ai_reasoning = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-severity", "-created_at"]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.fingerprint:
            import hashlib  # noqa: PLC0415
            raw = f"{self.scan.target_id}:{self.plugin_slug}:{self.title}"
            self.fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:64]
        super().save(*args, **kwargs)
