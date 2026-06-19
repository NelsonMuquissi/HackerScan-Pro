from django.utils.decorators import method_decorator
from rest_framework import viewsets
from .models import SecurityModule
from .serializers import SecurityModuleSerializer
from users.decorators import superadmin_required

@method_decorator(superadmin_required, name='dispatch')
class GlobalAdminMarketplaceViewSet(viewsets.ModelViewSet):
    """
    SuperAdmin CRUD for Security Modules.
    """
    queryset = SecurityModule.objects.all().order_by("-created_at")
    serializer_class = SecurityModuleSerializer
    # BaseView or standard ModelViewSet? 
    # Let's stick to standard DRF for CRUD but use the decorator.
