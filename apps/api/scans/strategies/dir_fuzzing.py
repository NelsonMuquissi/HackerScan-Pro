import logging
import subprocess
import os
from pathlib import Path
from typing import List
from .base import BaseScanStrategy, register, FindingData
from scans.models import Severity

logger = logging.getLogger(__name__)

# Resolve the wordlist path relative to this file so it works regardless of
# the current working directory.  The wordlist lives at:
#   <repo-root>/apps/api/scans/wordlists/common.txt
_STRATEGY_DIR = Path(__file__).resolve().parent
_DEFAULT_WORDLIST = _STRATEGY_DIR / "wordlists" / "common.txt"


@register
class DirFuzzingStrategy(BaseScanStrategy):
    """
    Directory fuzzing engine using gobuster.
    Checks for sensitive directories and files.
    """
    slug = "dir_fuzzing"
    name = "Directory Fuzzing"

    def run(self, target, scan=None) -> List[FindingData]:
        findings = []
        # target.host is the correct field on ScanTarget (target.address does not exist)
        host = target.host
        url = host if host.startswith("http") else f"http://{host}"

        wordlist = str(_DEFAULT_WORDLIST)
        if not os.path.exists(wordlist):
            logger.warning(
                "DirFuzzingStrategy: wordlist not found at %s — skipping fuzz scan. "
                "Create apps/api/scans/wordlists/common.txt to enable this scanner.",
                wordlist,
            )
            findings.append(FindingData(
                title="Directory Fuzzing Skipped",
                description=(
                    f"The wordlist required for directory fuzzing was not found at {wordlist}. "
                    "Create the wordlist file to enable this scanner."
                ),
                severity=Severity.INFO,
                remediation="Add a wordlist at apps/api/scans/wordlists/common.txt.",
            ))
            return findings

        try:
            cmd = [
                "gobuster",
                "dir",
                "-u", url,
                "-w", wordlist,
                "-z",  # No progress bar
                "-q",  # Quiet
            ]

            logger.info("Running gobuster: %s", " ".join(cmd))
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(timeout=120)

            discovered = []
            for line in stdout.splitlines():
                if "(Status: 200)" in line or "(Status: 301)" in line or "(Status: 302)" in line:
                    discovered.append(line.strip())

            if discovered:
                findings.append(FindingData(
                    title=f"Discovered {len(discovered)} Accessible Paths",
                    description=(
                        f"Automated directory fuzzing identified {len(discovered)} accessible "
                        f"paths on {host}."
                    ),
                    severity=Severity.MEDIUM,
                    evidence="\n".join(discovered),
                    remediation=(
                        "Review the discovered paths for any accidental exposures, "
                        "directory listings, or misconfigured permissions."
                    ),
                ))
            else:
                findings.append(FindingData(
                    title="No Sensitive Paths Discovered",
                    description=f"Directory fuzzing found no accessible paths on {host}.",
                    severity=Severity.INFO,
                    evidence=f"Gobuster scan completed for {url}.",
                    remediation="No action required.",
                ))
        except FileNotFoundError:
            logger.warning("gobuster not found in PATH — skipping dir fuzzing scan.")
            findings.append(FindingData(
                title="Directory Fuzzing Unavailable",
                description="gobuster is not installed or not in PATH on this server.",
                severity=Severity.INFO,
                remediation="Install gobuster to enable directory fuzzing.",
            ))
        except subprocess.TimeoutExpired:
            logger.warning("gobuster timed out for %s", host)
        except Exception as e:
            logger.error("DirFuzzingStrategy error: %s", e)

        return findings
