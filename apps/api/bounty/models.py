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
    
    # Evidence Vault Fields (Auditability)
    visual_proof_b64 = models.TextField(blank=True, null=True, help_text=_("Screenshot of the vulnerability provided by researcher"))
    technical_details = models.JSONField(default=dict, blank=True, help_text=_("Structured technical artifacts for audit trail"))
    compliance_mapping = models.JSONField(default=dict, blank=True, help_text=_("Mapping to security standards (OWASP, MITRE, etc.)"))
    verification_hash = models.CharField(max_length=64, blank=True, help_text=_("SHA-256 fingerprint for audit integrity"))
    
    # Certificates & Audit Reports
    compliance_certificate = models.FileField(upload_to='certificates/', null=True, blank=True, help_text=_("Generated PDF compliance certificate"))
    
    # Metadata
    internal_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.severity}] {self.title} by {self.researcher.email}"

    def verify_integrity(self):
        """
        Verify that the submission data matches the digital fingerprint.
        Returns True if integrity is preserved.
        """
        import hashlib
        import json
        
        # We must use a deterministic way to serialize JSON fields for hashing
        compliance_str = json.dumps(self.compliance_mapping, sort_keys=True)
        
        raw_data = f"{self.researcher_id}:{self.program_id}:{self.title}:{self.target_domain}:{self.description}:{compliance_str}"
        expected_hash = hashlib.sha256(raw_data.encode()).hexdigest()
        return self.verification_hash == expected_hash

    def save(self, *args, **kwargs):
        if not self.verification_hash:
            import hashlib
            import json
            # Create a unique fingerprint for this submission including all technical data
            compliance_str = json.dumps(self.compliance_mapping, sort_keys=True)
            raw_data = f"{self.researcher_id}:{self.program_id}:{self.title}:{self.target_domain}:{self.description}:{compliance_str}"
            self.verification_hash = hashlib.sha256(raw_data.encode()).hexdigest()
        super().save(*args, **kwargs)

class BountyAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(BountySubmission, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='evidence/')
    filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=100, help_text=_("MIME type or category (PCAP, LOG, BIN)"))
    file_size = models.BigIntegerField()
    
    # Integrity for each attachment
    file_hash = models.CharField(max_length=64, help_text=_("SHA-256 hash of the file content"))
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} for {self.submission.id}"
