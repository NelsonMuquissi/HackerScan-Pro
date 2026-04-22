from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class BountyProgram(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', _('Rascunho')
        ACTIVE = 'ACTIVE', _('Ativo')
        PAUSED = 'PAUSED', _('Pausado')
        CLOSED = 'CLOSED', _('Encerrado')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        'users.Workspace', 
        on_delete=models.CASCADE, 
        related_name='bounty_programs'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(help_text=_("Markdown description of rules and program goals"))
    
    # JSON for flexibility: list of assets/domains
    scope = models.JSONField(default=list, help_text=_("List of assets in scope"))
    
    # JSON for rewards: {"CRITICAL": 5000, "HIGH": 2000, ...}
    rewards = models.JSONField(default=dict, help_text=_("Mapping of severity to reward amount"))
    
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.workspace.name})"

class BountySubmission(models.Model):
    class Severity(models.TextChoices):
        CRITICAL = 'CRITICAL', _('Crítico')
        HIGH = 'HIGH', _('Alto')
        MEDIUM = 'MEDIUM', _('Médio')
        LOW = 'LOW', _('Baixo')
        INFO = 'INFO', _('Informativo')

    class Status(models.TextChoices):
        NEW = 'NEW', _('Novo')
        TRIAGED = 'TRIAGED', _('Triado')
        NEGOTIATING = 'NEGOTIATING', _('Em Negociação')
        RESOLVED = 'RESOLVED', _('Resolvido')
        DUPLICATE = 'DUPLICATE', _('Duplicado')
        OUT_OF_SCOPE = 'OUT_OF_SCOPE', _('Fora de Escopo')
        REJECTED = 'REJECTED', _('Rejeitado')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(BountyProgram, on_delete=models.CASCADE, related_name='submissions')
    researcher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bounty_submissions')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    target_domain = models.CharField(max_length=255, default="", help_text=_("The specific domain/asset being verified for proof of possession"))
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    
    # Financials
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=3, default='USD')

    # Proof of Possession / Verification
    proof_token = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    proof_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    internal_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.title} by {self.researcher.email}"
