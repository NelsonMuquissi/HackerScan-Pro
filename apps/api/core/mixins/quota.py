"""
HackScan Pro — Quota Check Mixin.

Drop-in mixin for DRF views that consume workspace quota.
Returns HTTP 402 Payment Required when the limit is exceeded.
"""
from rest_framework import status
from rest_framework.response import Response

from billing.services import BillingService


class QuotaCheckMixin:
    """
    Mixin for DRF CreateModelMixin views that enforce plan limits.

    Usage:
        class ScanCreateView(QuotaCheckMixin, generics.CreateAPIView):
            quota_action = "create_scan"
            ...
    """
    quota_action: str | None = None

    def get_workspace(self):
        """Override in the target view if workspace resolution differs."""
        return self.request.user.owned_workspaces.first()

    def create(self, request, *args, **kwargs):
        if self.quota_action:
            workspace = self.get_workspace()
            
            if workspace is None:
                return Response(
                    {"detail": "Workspace não encontrado."},
                    status=status.HTTP_403_FORBIDDEN,
                )
                
            allowed, reason = BillingService.check_quota(workspace, self.quota_action)

            if not allowed:
                return Response(
                    {"detail": reason, "upgrade_url": "/billing/upgrade/"},
                    status=status.HTTP_402_PAYMENT_REQUIRED,
                )

        return super().create(request, *args, **kwargs)
