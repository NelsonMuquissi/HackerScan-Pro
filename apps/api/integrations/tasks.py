import hmac
import hashlib
import json
import logging
import requests
from celery import shared_task
from django.utils import timezone
from .models import Webhook

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5)
def send_webhook_task(self, webhook_id, event_type, payload):
    """
    Sends a webhook payload with an HMAC-SHA256 signature.
    """
    try:
        webhook = Webhook.objects.get(id=webhook_id)
    except Webhook.DoesNotExist:
        return

    # Prepare signature
    payload_str = json.dumps(payload)
    timestamp = str(int(timezone.now().timestamp()))
    signed_payload = f"{timestamp}.{payload_str}"
    
    signature = hmac.new(
        webhook.secret_token.encode(),
        signed_payload.encode(),
        hashlib.sha256
    ).hexdigest()

    headers = {
        'Content-Type': 'application/json',
        'X-HackerScan-Event': event_type,
        'X-HackerScan-Timestamp': timestamp,
        'X-HackerScan-Signature': signature,
        'User-Agent': 'HackerScan-Webhook-Dispatcher/1.0'
    }

    try:
        response = requests.post(
            webhook.url, 
            data=payload_str, 
            headers=headers, 
            timeout=10
        )
        
        # Update success metrics
        webhook.last_triggered_at = timezone.now()
        webhook.last_status_code = response.status_code
        
        if 200 <= response.status_code < 300:
            webhook.failure_count = 0
        else:
            webhook.failure_count += 1
            logger.warning("Webhook %s failed with status %d", webhook_id, response.status_code)
            
        webhook.save(update_fields=['last_triggered_at', 'last_status_code', 'failure_count'])

    except requests.RequestException as e:
        # Update metrics for failure
        webhook.last_triggered_at = timezone.now()
        webhook.failure_count += 1
        webhook.save(update_fields=['last_triggered_at', 'failure_count'])
        
        logger.error("Webhook %s transmission error: %s", webhook_id, str(e))
        
        # Exponential backoff retry
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
