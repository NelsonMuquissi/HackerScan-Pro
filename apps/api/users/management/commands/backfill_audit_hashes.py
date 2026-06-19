from django.core.management.base import BaseCommand
from apps.api.users.tasks import backfill_audit_logs

class Command(BaseCommand):
    help = "Triggers a background task to backfill cryptographic hashes for legacy audit logs."

    def handle(self, *args, **options):
        self.stdout.write("Queueing backfill task...")
        task = backfill_audit_logs.delay()
        self.stdout.write(self.style.SUCCESS(f"Task queued. ID: {task.id}"))
        self.stdout.write("Monitor logs or the Admin Dashboard for progress.")
