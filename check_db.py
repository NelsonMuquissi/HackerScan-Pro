import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("Database connection successful!")
except Exception as e:
    print(f"Database connection failed: {e}")
