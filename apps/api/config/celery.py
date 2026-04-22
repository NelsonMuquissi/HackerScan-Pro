"""
Celery application entrypoint for HackScan Pro.

Usage:
    celery -A config.celery worker --queues=urgent,reports,notifications,scheduled,celery
    celery -A config.celery beat --scheduler=django_celery_beat.schedulers:DatabaseScheduler
"""
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("hackscan")

# Pull CELERY_* settings from Django settings
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in every installed app
app.autodiscover_tasks()

# ─── Queue routing ──────────────────────────────────────────────────────────
app.conf.task_routes = {
    # Scans — dedicated scans queue for isolated worker
    "scans.run_scan":                  {"queue": "scans"},
    # Notifications
    "scans.notify_scan_complete":      {"queue": "notifications"},
    # Reports (future)
    "reports.*":                       {"queue": "reports"},
    # Scheduled / periodic tasks
    "scheduled.*":                     {"queue": "scheduled"},
}

# Default queue for anything not matched above
app.conf.task_default_queue = "celery"
