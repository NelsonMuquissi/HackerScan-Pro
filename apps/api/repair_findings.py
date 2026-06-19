import os
import django
import hashlib

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Finding, FindingStatus

def repair_data():
    findings = Finding.objects.all()
    updated = 0
    for f in findings:
        raw = f"{f.scan.target_id}:{f.plugin_slug}:{f.title}"
        f.fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:64]
        f.status = FindingStatus.ACTIVE
        
        # Also normalize severity to lowercase if it's uppercase
        if f.severity:
            f.severity = f.severity.lower()
            
        f.save()
        updated += 1
    print(f"Successfully repaired {updated} findings.")

if __name__ == "__main__":
    repair_data()
