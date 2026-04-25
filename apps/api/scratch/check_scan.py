import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan, Finding

def check_scan_details():
    scan_id = '26039808-a638-4f2c-aa38-1cd557b21aef'
    scan = Scan.objects.filter(id=scan_id).first()
    
    if not scan:
        print(f"Scan {scan_id} not found")
        return

    print(f"Scan ID: {scan.id}")
    print(f"Target: {scan.target.host}")
    print(f"Status: {scan.status}")
    print(f"Type: {scan.scan_type}")
    print(f"Error Message: {scan.error_message}")
    print(f"Started: {scan.started_at}")
    print(f"Finished: {scan.finished_at}")
    print("-" * 30)
    
    findings = Finding.objects.filter(scan=scan)
    print(f"Findings Count: {findings.count()}")
    for f in findings:
        print(f"[{f.severity.upper()}] {f.title}")
        print(f"  Plugin: {f.plugin_slug}")
        # print(f"  Description: {f.description[:100]}...")
        print("-" * 10)

if __name__ == "__main__":
    check_scan_details()
