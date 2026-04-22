import uuid
import secrets
from django.db import models
from core.models import TimestampedModel

class Webhook(TimestampedModel):
    """
    Outbound webhook configuration for a workspace.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'users.Workspace', 
        on_delete=models.CASCADE, 
        related_name='webhooks'
    )
    name = models.CharField(max_length=100)
    url = models.URLField(max_length=500)
    secret_token = models.CharField(
        max_length=128, 
        default=lambda: f"whsec_{secrets.token_hex(20)}"
    )
    
    # List of events this webhook is subscribed to (e.g., ["scan.completed", "finding.new"])
    events = models.JSONField(default=list)
    
    is_active = models.BooleanField(default=True)
    
    # Metadata for the last delivery attempt
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.IntegerField(null=True, blank=True)
    failure_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'integrations_webhooks'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.url})"

    def reset_secret(self):
        self.secret_token = f"whsec_{secrets.token_hex(20)}"
        self.save()
