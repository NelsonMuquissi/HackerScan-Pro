from django.utils import timezone
from marketplace.models import SecurityModule, WorkspaceModule
from scans.models import ScanType

# Mapping of ScanType to required module slugs
STRATEGY_MODULE_REQUIREMENTS = {
    ScanType.AD_AUDIT: 'ad-audit',
    ScanType.K8S_SECURITY: 'k8s-security',
    ScanType.SAP_AUDIT: 'sap-audit',
}

def check_module_access(workspace, scan_type) -> bool:
    """
    Returns True if the workspace has access to the requested scan_type.
    Standard scan types are always accessible.
    Specialized scan types require an active MarketplaceModule.
    """
    required_slug = STRATEGY_MODULE_REQUIREMENTS.get(scan_type)
    if not required_slug:
        return True  # Standard module
    
    # Check if workspace has an active purchase for this module
    return has_module_access(workspace, required_slug)

def has_module_access(workspace, module_slug: str) -> bool:
    """
    Returns True if the workspace has an active purchase/subscription for the specific module.
    """
    from django.db.models import Q
    return WorkspaceModule.objects.filter(
        workspace=workspace,
        module__slug=module_slug,
        is_active=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).exists()

def get_unlocked_scan_types(workspace) -> list[str]:
    """
    Returns a list of all scan types accessible to this workspace.
    """
    # Base scan types
    unlocked = [
        ScanType.QUICK, ScanType.FULL, ScanType.VULN, 
        ScanType.RECON, ScanType.SSL, ScanType.FUZZ, ScanType.DISCOVERY
    ]
    
    # Add marketplace unlocked types
    active_modules = WorkspaceModule.objects.filter(
        workspace=workspace,
        is_active=True
    ).select_related('module')
    
    for wm in active_modules:
        # If expires_at is set, check it
        if wm.expires_at and wm.expires_at < timezone.now():
            continue
        unlocked.extend(wm.module.unlocked_strategies)
    
    return list(set(unlocked))
