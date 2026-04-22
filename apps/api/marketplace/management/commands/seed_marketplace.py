from django.core.management.base import BaseCommand
from marketplace.models import SecurityModule
from scans.models import ScanType

class Command(BaseCommand):
    help = "Seeds the security module marketplace with initial premium capabilities."

    def handle(self, *args, **options):
        modules = [
            {
                "name": "Active Directory Tactical Audit",
                "slug": "ad_audit",
                "description": "Deep analysis of AD misconfigurations, GPO vulnerabilities, and lateral movement paths.",
                "price": 299.00,
                "is_active": True,
                "unlocked_strategies": [ScanType.AD_AUDIT],
                "config_schema": {
                    "domain_controller": {"type": "string", "required": True},
                    "ldap_port": {"type": "integer", "default": 389}
                }
            },
            {
                "name": "K8s Hardening & Security",
                "slug": "k8s_security",
                "description": "Comprehensive Kubernetes cluster audit, checking for over-privileged pods, RBAC issues, and image vulnerabilities.",
                "price": 199.00,
                "is_active": True,
                "unlocked_strategies": [ScanType.K8S_SECURITY],
                "config_schema": {
                    "kubeconfig_path": {"type": "string", "required": False},
                    "namespace_scope": {"type": "string", "default": "all"}
                }
            },
            {
                "name": "SAP Ecosystem Governance",
                "slug": "sap_audit",
                "description": "Specialized audit for SAP landscapes, focusing on NetWeaver security, default credentials, and gateway exposure.",
                "price": 499.00,
                "is_active": True,
                "unlocked_strategies": [ScanType.SAP_AUDIT],
                "config_schema": {
                    "instance_number": {"type": "string", "default": "00"},
                    "client": {"type": "string", "default": "000"}
                }
            }
        ]

        for m_data in modules:
            module, created = SecurityModule.objects.update_or_create(
                slug=m_data["slug"],
                defaults=m_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created module: {module.name}"))
            else:
                self.stdout.write(self.style.INFO(f"Updated module: {module.name}"))

        self.stdout.write(self.style.SUCCESS("Marketplace seeding complete."))
