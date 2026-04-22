from django.db import models
import uuid
from django.utils.translation import gettext_lazy as _

class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendente')
        PROCESSING = 'PROCESSING', _('Processando')
        COMPLETED = 'COMPLETED', _('Concluído')
        FAILED = 'FAILED', _('Falhou')

    class Type(models.TextChoices):
        TECHNICAL = 'TECHNICAL', _('Técnico')
        EXECUTIVE = 'EXECUTIVE', _('Executivo')

    class Format(models.TextChoices):
        PDF = 'PDF', _('PDF')
        JSON = 'JSON', _('JSON')
        CSV = 'CSV', _('CSV')
        HTML = 'HTML', _('HTML')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scan = models.ForeignKey('scans.Scan', on_delete=models.CASCADE, related_name='reports')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    type = models.CharField(max_length=20, choices=Type.choices)
    format = models.CharField(max_length=10, choices=Format.choices)
    file_url = models.URLField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report {self.type} ({self.format}) - {self.scan_id}"
