import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan, ScanStatus

def check_failed_scans():
    print("Checking for failed scans...")
    failed_scans = Scan.objects.filter(status=ScanStatus.FAILED).order_by('-created_at')[:10]
    
    if not failed_scans:
        print("No failed scans found in the last 10 records.")
        return

    print(f"Found {len(failed_scans)} failed scans:")
    for scan in failed_scans:
        print(f"--- Scan ID: {scan.id} ---")
        print(f"Target: {scan.target.host}")
        print(f"Type: {scan.scan_type}")
        print(f"Created: {scan.created_at}")
        print(f"Error: {scan.error_message}")
        print("-" * 40)

if __name__ == "__main__":
    check_failed_scans()
