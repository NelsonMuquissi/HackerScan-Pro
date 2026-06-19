import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
django.setup()

from scans.models import Scan
from scans.services import _dispatch_task
from scans.tasks import run_scan

# The stagnant scan ID from diagnostics
stagnant_id = "d8d8fa88-f0c4-448b-91fc-7a2336b65057"

try:
    scan = Scan.objects.get(id=stagnant_id)
    print(f"Attempting to re-trigger stagnant scan: {scan.id} (Status: {scan.status})")
    
    # Reset status to QUEUED just in case
    scan.status = 'queued'
    scan.save()
    
    print("Dispatching task via _dispatch_task...")
    _dispatch_task(run_scan, scan.id)
    
    print("Successfully re-dispatched scan.")
except Scan.DoesNotExist:
    print(f"Scan {stagnant_id} not found.")
except Exception as e:
    print(f"Error: {e}")
