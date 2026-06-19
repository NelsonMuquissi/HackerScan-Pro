import time
import logging
import threading
from typing import Set

from django.core.management.base import BaseCommand
from django.db import transaction

from scans.models import ScanTarget, ScanType
from scans.services import ScanService

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Continuously monitors Certificate Transparency (CT) logs for new subdomains of our targets."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tracked_domains: Set[str] = set()
        self.last_sync: float = 0
        self.sync_interval: int = 60  # Refresh target list every 60 seconds
        self._lock = threading.Lock()

    def sync_tracked_domains(self):
        """Loads domains from the database to memory for fast checking."""
        now = time.time()
        if now - self.last_sync < self.sync_interval:
            return

        with self._lock:
            # We only track domain-type targets that are verified (or you could track all)
            targets = ScanTarget.objects.filter(target_type="domain").values_list("host", flat=True)
            self.tracked_domains = {t.lower() for t in targets}
            self.last_sync = now
            logger.info(f"[CT Monitor] Synced {len(self.tracked_domains)} domains to track.")

    def handle_certstream_event(self, message, context):
        """Callback for CertStream events."""
        if message.get('message_type') == "heartbeat":
            return

        if message.get('message_type') == "certificate_update":
            all_domains = message['data']['leaf_cert']['all_domains']
            
            # Periodically sync our tracked domains
            self.sync_tracked_domains()
            
            with self._lock:
                tracked = self.tracked_domains.copy()
            
            if not tracked:
                return

            for domain in all_domains:
                domain = domain.lower()
                # e.g., if domain is "api.staging.example.com", and we track "example.com"
                for tracked_domain in tracked:
                    if domain == tracked_domain or domain.endswith(f".{tracked_domain}"):
                        if "*." in domain:
                            continue  # Ignore wildcards for now
                        
                        logger.warning(f"🚨 [CT Monitor] Match found: {domain} belongs to {tracked_domain}!")
                        self.trigger_scan(tracked_domain, domain)

    def trigger_scan(self, parent_domain: str, new_subdomain: str):
        """
        Triggers a Discovery/Recon scan for the new subdomain to detect Shadow IT.
        """
        try:
            # Find the parent target
            parent_target = ScanTarget.objects.filter(host__iexact=parent_domain).first()
            if not parent_target:
                return
            
            # First, add the new subdomain as a target in the same workspace
            with transaction.atomic():
                new_target, created = ScanTarget.objects.get_or_create(
                    workspace=parent_target.workspace,
                    host=new_subdomain,
                    defaults={
                        "owner": parent_target.owner,
                        "name": f"Auto-discovered CT: {new_subdomain}",
                        "target_type": "domain",
                        "description": "Auto-discovered via CT Logs Event Monitor",
                        "tags": ["ct-log", "shadow-it", "auto-discovery"]
                    }
                )

            # Trigger a fast RECON scan to see what it is
            if created:
                logger.info(f"🛡️ [CT Monitor] Triggering RECON scan for {new_subdomain}")
                scan = ScanService.create(
                    user=parent_target.owner,
                    workspace_id=parent_target.workspace_id,
                    target_id=new_target.id,
                    scan_type=ScanType.RECON,
                    config={"source": "ct_event_monitor"}
                )
                from scans.tasks import run_scan
                run_scan.delay(scan.id)
                
        except Exception as e:
            logger.error(f"[CT Monitor] Failed to trigger scan for {new_subdomain}: {e}")

    def handle(self, *args, **options):
        try:
            import certstream
        except ImportError:
            self.stdout.write(self.style.ERROR("certstream library not installed. Run 'pip install certstream'"))
            return

        self.stdout.write(self.style.SUCCESS("🚀 Starting Continuous CT Log Monitor..."))
        self.sync_tracked_domains()

        # certstream.listen_for_events blocks forever
        certstream.listen_for_events(self.handle_certstream_event, url='wss://certstream.calidog.io/')

