from celery import shared_task
import logging
from .services import PoPVerificationService

logger = logging.getLogger(__name__)

@shared_task(name="bounty.verify_submission")
def verify_bounty_submission_task(submission_id: str):
    """
    Background task to verify Proof-of-Possession for a bounty submission.
    """
    import asyncio
    logger.info(f"Starting PoP verification for submission {submission_id}")
    
    # Since the service is async, we run it in the event loop.
    # Celery workers are usually synchronous, so we use asyncio.run
    try:
        success = asyncio.run(PoPVerificationService.verify_submission(submission_id))
        if success:
            logger.info(f"PoP verification SUCCESS for submission {submission_id}")
        else:
            logger.warning(f"PoP verification FAILED for submission {submission_id}")
        return success
    except Exception as e:
        logger.error(f"Error in PoP verification task: {str(e)}")
        return False
