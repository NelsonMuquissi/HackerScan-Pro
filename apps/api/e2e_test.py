from django.contrib.auth import get_user_model
from users.models import Workspace
from scans.models import ScanTarget, Scan, ScanType, TargetType
from scans.tasks import run_scan
from scans.models import Finding

User = get_user_model()

def run_test():
    # 1. Setup user and workspace
    user, _ = User.objects.get_or_create(email="e2e@example.com")
    workspace, _ = Workspace.objects.get_or_create(name="E2E Workspace", owner=user)
    
    # 2. Setup target
    target, _ = ScanTarget.objects.get_or_create(
        workspace=workspace, 
        host="scanme.nmap.org", 
        defaults={"name": "Nmap ScanMe", "owner": user, "target_type": TargetType.DOMAIN}
    )
    
    # 3. Create Scan
    scan = Scan.objects.create(
        target=target,
        triggered_by=user,
        scan_type=ScanType.QUICK,
        plugin_ids=["port_scan", "api_fuzzer"]
    )
    
    print(f"Running scan {scan.id} for target {target.host}...")
    run_scan(str(scan.id))
    
    # 4. Check findings
    scan.refresh_from_db()
    print(f"Scan finished with status: {scan.status}")
    findings = Finding.objects.filter(scan=scan)
    print(f"Total findings: {findings.count()}")
    for f in findings:
        print(f" - [{f.severity}] {f.title}: {f.description[:100]}")

run_test()
