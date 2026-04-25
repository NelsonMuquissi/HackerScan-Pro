import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.models import Scan, Finding

scan_id = "26039808-a638-4f2c-aa38-1cd557b21aef"
try:
    scan = Scan.objects.get(pk=scan_id)
    findings = Finding.objects.filter(scan=scan)
    print(f"Scan: {scan.id} - Total Findings: {findings.count()}")
    for f in findings:
        print(f"Finding: {f.title}")
        print(f"  AI Explanation: {f.ai_explanation[:100] if f.ai_explanation else 'EMPTY'}")
        print(f"  AI Remediation: {f.ai_remediation[:100] if f.ai_remediation else 'EMPTY'}")
        print("-" * 20)
except Exception as e:
    print(f"Error: {e}")
