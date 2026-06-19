import os, django, uuid
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.development'
django.setup()

from scans.models import Scan, ScanTarget
from users.models import User, Workspace
from scans.tasks import run_scan
from scans.services import _dispatch_task

def trigger():
    # 1. Get or create a test user
    user, _ = User.objects.get_or_create(email="admin@test.com", defaults={"full_name": "Test Admin"})
    
    # 2. Get or create a workspace
    workspace, _ = Workspace.objects.get_or_create(
        name="E2E Verification Workspace", 
        owner=user,
        defaults={"slug": f"e2e-verify-{uuid.uuid4().hex[:8]}"}
    )
    
    # 3. Create a target
    target, _ = ScanTarget.objects.get_or_create(
        host="example.com", 
        workspace=workspace,
        defaults={
            "name": "E2E Test Target",
            "target_type": "url",
            "owner": user
        }
    )
    
    # 4. Create a scan
    scan = Scan.objects.create(
        target=target,
        scan_type="quick",
        status="queued",
        triggered_by=user
    )
    
    print(f"Created Scan ID: {scan.id} for {target.host}")
    
    # 5. Dispatch the task synchronously for testing or let Celery handle it
    # Since we want to verify efficiency E2E, we'll run it synchronously here to get immediate feedback
    print("Running scan task synchronously...")
    from django.db import connections
    try:
        # Close all existing connections to ensure we get fresh ones inside the task
        connections.close_all()
        
        run_scan(scan.id)
        
        # Close again after task to avoid stale connections when reading results
        connections.close_all()
        
        scan.refresh_from_db()
        print(f"Scan finished with status: {scan.status}")
        print(f"Findings discovered: {scan.findings.count()}")
        
        for finding in scan.findings.all():
            print(f"- [{finding.severity}] {finding.title}")
            if "**REAL DATA PROOF**" in finding.description:
                print("  [OK] REAL DATA PROOF detected in description")
            else:
                # Some might not have it if they are just info, but we aim for it
                print("  [INFO] Description: " + finding.description[:100] + "...")
                
    except Exception as e:
        import traceback
        print(f"Scan execution failed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    trigger()
