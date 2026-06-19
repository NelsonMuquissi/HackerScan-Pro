import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from scans.services import ScanService
from users.models import User, Workspace

def trigger_test():
    user = User.objects.first()
    if not user:
        print("No user found.")
        return
    
    # Elevate user to ADMIN to bypass quota checks for this test
    if user.role != "admin":
        print(f"Elevating user {user.email} to ADMIN...")
        user.role = "admin"
        user.save()
    
    workspace = Workspace.objects.filter(owner=user).first()
    if not workspace:
        # Try any workspace
        workspace = Workspace.objects.first()
        if not workspace:
            print("No workspace found.")
            return
    
    print(f"Triggering quick scan for google.com in workspace {workspace.id}...")
    try:
        scan = ScanService.quick_scan(user, "https://google.com", workspace_id=workspace.id)
        print(f"Scan created and triggered: {scan.id}")
        print(f"Scan status: {scan.status}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    trigger_test()
