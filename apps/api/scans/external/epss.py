import logging
import httpx
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class EPSSService:
    """
    Service to fetch Exploit Prediction Scoring System (EPSS) data.
    Provides the probability of a CVE being exploited in the next 30 days.
    """
    API_URL = "https://api.first.org/data/v1/epss"

    def __init__(self):
        self._cache: Dict[str, float] = {}

    def get_score(self, cve_id: str) -> Optional[float]:
        """
        Fetch EPSS score for a specific CVE.
        Returns a float between 0 and 1, or None if not found/error.
        """
        if not cve_id or not cve_id.startswith("CVE-"):
            return None

        if cve_id in self._cache:
            return self._cache[cve_id]

        try:
            params = {"cve": cve_id}
            response = httpx.get(self.API_URL, params=params, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("data", [])
                if results:
                    # EPSS score is returned as a string representing a probability (e.g., "0.00123")
                    score_str = results[0].get("epss")
                    if score_str:
                        score = float(score_str)
                        self._cache[cve_id] = score
                        return score
            
            logger.warning(f"EPSS score not found for {cve_id} (Status: {response.status_code})")
        except Exception as e:
            logger.error(f"Error fetching EPSS score for {cve_id}: {e}")
        
        return None

    def enrich_findings(self, findings):
        """
        Helper to enrich a list of FindingData with EPSS scores.
        Attempts to extract CVE IDs from evidence or title.
        """
        import re
        cve_pattern = re.compile(r"CVE-\d{4}-\d{4,7}")

        for finding in findings:
            # Try to find CVE in evidence or title
            text_to_search = f"{finding.title} {finding.evidence}"
            match = cve_pattern.search(text_to_search)
            
            if match:
                cve_id = match.group(0)
                score = self.get_score(cve_id)
                if score is not None:
                    finding.epss_score = score
                    logger.info(f"Enriched {finding.title} with EPSS score: {score}")

epss_service = EPSSService()
