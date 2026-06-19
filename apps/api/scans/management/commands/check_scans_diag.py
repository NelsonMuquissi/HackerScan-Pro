from django.core.management.base import BaseCommand
from scans.models import Scan, ScanStatus

class Command(BaseCommand):
    help = 'Check failed scans and their error messages'

    def handle(self, *args, **options):
        self.stdout.write("Checking for failed scans...")
        failed_scans = Scan.objects.filter(status=ScanStatus.FAILED).order_by('-created_at')[:20]
        
        if not failed_scans:
            self.stdout.write(self.style.SUCCESS("No failed scans found."))
            return

        self.stdout.write(f"Found {len(failed_scans)} failed scans:")
        for scan in failed_scans:
            self.stdout.write(f"\n--- Scan ID: {scan.id} ---")
            self.stdout.write(f"Target: {scan.target.host}")
            self.stdout.write(f"Type: {scan.scan_type}")
            self.stdout.write(f"Created: {scan.created_at}")
            self.stdout.write(self.style.ERROR(f"Error: {scan.error_message}"))
            self.stdout.write("-" * 40)
