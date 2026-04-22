import logging
from uuid import UUID
from .models import Webhook

logger = logging.getLogger(__name__)

class WebhookDispatcherService:
    @staticmethod
    def dispatch(workspace_id: UUID, event_type: str, payload: dict):
        """
        Broadcasts an event to all matching webhooks in a workspace.
        """
        webhooks = Webhook.objects.filter(
            workspace_id=workspace_id,
            is_active=True,
            events__contains=[event_type]
        )
        
        if not webhooks.exists():
            return

        from .tasks import send_webhook_task  # noqa: PLC0415
        
        for webhook in webhooks:
            send_webhook_task.delay(str(webhook.id), event_type, payload)
            
        logger.info(
            "WebhookDispatcher: Dispatched event %s to %d webhooks in workspace %s", 
            event_type, webhooks.count(), workspace_id
        )
