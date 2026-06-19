from scans.models import Scan
from django.db.models import Q
for s in Scan.objects.filter(status='failed').order_by('-created_at')[:10]:
    print(f"Scan {s.id} ({s.scan_type})")
    print(f"Error: {s.error_message}")
    print("-" * 40)
