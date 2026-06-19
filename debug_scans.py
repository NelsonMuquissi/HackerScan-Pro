import os
import django
import sys
import logging

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan, ScanStatus
from scans.services import ScanService

def debug_scans():
    print("Checking all scans status...")
    scans = Scan.objects.all().order_by('-created_at')[:20]
    
    if not scans:
        print("No scans found in the database.")
        return

    print(f"{'ID':<38} | {'Target':<20} | {'Status':<10} | {'Type':<10}")
    print("-" * 85)
    for scan in scans:
        print(f"{str(scan.id):<38} | {scan.target.host:<20} | {scan.status:<10} | {scan.scan_type:<10}")

    pending_scans = Scan.objects.filter(status=ScanStatus.PENDING)
    if pending_scans.exists():
        print(f"\nFound {pending_scans.count()} PENDING scans.")
        for scan in pending_scans:
            print(f"Triggering scan {scan.id}...")
            try:
                ScanService.trigger(scan.target.workspace_id, scan.id)
                print(f"Successfully triggered {scan.id}")
            except Exception as e:
                print(f"Failed to trigger {scan.id}: {e}")
    else:
        print("\nNo PENDING scans found.")

if __name__ == "__main__":
    debug_scans()
