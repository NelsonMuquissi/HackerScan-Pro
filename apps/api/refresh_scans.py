import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan

def refresh_scans():
    scans = Scan.objects.all()
    updated = 0
    for s in scans:
        s._refresh_finding_counts()
        s.save()
        updated += 1
    print(f"Successfully refreshed {updated} scans.")

if __name__ == "__main__":
    refresh_scans()
