from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class SecurityModule(models.Model):
    """
    Defines a specialized security capability that can be purchased.
    Example: Active Directory Tactical Audit, Kubernetes Security Hardening.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, help_text=_("Internal identifier: e.g. ad-audit"))
    description = models.TextField()
    short_description = models.CharField(max_length=255, blank=True)
    
    # Visuals
    icon = models.CharField(max_length=50, default='Shield', help_text=_("Lucide icon identifier"))
    
    # Financials
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')
    stripe_price_id = models.CharField(max_length=255, blank=True, default="")
    
    # Technical Mapping
    # Modules unlock specific strategies in the scan engine
    unlocked_strategies = models.JSONField(default=list, help_text=_("List of scan Strategy internal names unlocked by this module"))
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class WorkspaceModule(models.Model):
    """
    Tracks which modules a specific workspace has purchased/activated.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'users.Workspace', 
        on_delete=models.CASCADE, 
        related_name='purchased_modules'
    )
    module = models.ForeignKey(SecurityModule, on_delete=models.CASCADE)
    
    activated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default="")
    
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('workspace', 'module')

    def __str__(self):
        return f"{self.workspace.name} -> {self.module.name}"
