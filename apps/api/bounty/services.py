import httpx
import logging
import subprocess
import re
from django.utils import timezone
from .models import BountySubmission

logger = logging.getLogger(__name__)

class PoPVerificationService:
    """
    Proof-of-Possession (PoP) Verification Service.
    Verifies that a researcher has legitimate control or access to the reported asset.
    """

    @staticmethod
    async def verify_submission(submission_id: str) -> bool:
        """
        Attempts to verify the proof token by:
        1. Fetching a well-known URL on the target asset (HTTP/HTTPS).
        2. Checking DNS TXT records for the target domain.
        """
        try:
            submission = BountySubmission.objects.select_related('program').get(id=submission_id)
            token = str(submission.proof_token)
            target_host = submission.target_domain
            
            if not target_host:
                logger.error(f"PoP: No target domain for submission {submission_id}")
                return False

            # 1. HTTP/HTTPS Verification
            protocols = ["https://", "http://"]
            verification_paths = [
                f"/.well-known/hackerscan-proof.txt",
                f"/hackerscan-{token[:8]}.txt"
            ]
            
            async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
                for proto in protocols:
                    for path in verification_paths:
                        url = f"{proto}{target_host}{path}"
                        try:
                            logger.info(f"PoP: Checking HTTP {url}")
                            response = await client.get(url)
                            if response.status_code == 200 and token in response.text:
                                logger.info(f"PoP: SUCCESS (HTTP) for {submission_id}")
                                return PoPVerificationService._mark_verified(submission)
                        except httpx.RequestError:
                            continue

            # 2. DNS TXT Record Verification (Fallback)
            logger.info(f"PoP: Checking DNS TXT for {target_host}")
            try:
                # Using nslookup for portability on Windows/Linux environments
                # We look for a TXT record that exactly matches the token or contains it
                cmd = ["nslookup", "-type=txt", target_host]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if token in result.stdout:
                    logger.info(f"PoP: SUCCESS (DNS) for {submission_id}")
                    return PoPVerificationService._mark_verified(submission)
            except Exception as e:
                logger.debug(f"PoP: DNS Check failed for {target_host}: {str(e)}")

            logger.warning(f"PoP: All verification attempts failed for {submission_id}")
            return False

        except BountySubmission.DoesNotExist:
            logger.error(f"PoP: Submission {submission_id} not found")
            return False
        except Exception as e:
            logger.exception(f"PoP: Unexpected error for {submission_id}")
            return False

    @staticmethod
    def _mark_verified(submission: BountySubmission) -> bool:
        """Atomic update of verification status."""
        submission.proof_verified = True
        submission.verified_at = timezone.now()
        # Only move to TRIAGED if it's currently NEW
        if submission.status == BountySubmission.Status.NEW:
            submission.status = BountySubmission.Status.TRIAGED
        submission.save(update_fields=['proof_verified', 'verified_at', 'status'])
        return True
