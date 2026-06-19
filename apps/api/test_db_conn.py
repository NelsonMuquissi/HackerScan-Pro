import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
django.setup()
from scans.models import Scan
print("Querying database...")
count = Scan.objects.count()
print(f"Database query successful. Scan count: {count}")
