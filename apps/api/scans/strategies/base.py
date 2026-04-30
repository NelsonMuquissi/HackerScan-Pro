"""
Base strategy interface for HackScan Pro scan plugins.

Every scan plugin must subclass BaseScanStrategy and implement `run()`.
The runner (tasks.py) discovers registered strategies and calls them in order.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scans.models import Scan, ScanTarget


@dataclass
class FindingData:
    """
    Lightweight DTO returned by strategies.
    Gets persisted into the Finding model by the task runner.
    """
    title: str
    description: str
    severity: str = "info"          # Severity enum value
    plugin_slug: str = ""
    remediation: str = ""
    evidence: dict | str = field(default_factory=dict)   # accepts both str and dict
    cvss_score: float | None = None
    epss_score: float | None = None
    # Optional metadata (not persisted to Finding model, but useful for logging/reporting)
    category: str = ""
    confidence: int = 0
    is_false_positive: bool = False
    ai_reasoning: str = ""
    
    # Proof of Concept / Verification
    request: str = ""
    response: str = ""
    poc: str = ""
    is_verified: bool = False


    def get_fingerprint(self, target_id: str | UUID) -> str:
        """Reproduce the same fingerprint logic as the Finding model."""
        import hashlib
        raw = f"{target_id}:{self.plugin_slug}:{self.title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:64]


class BaseScanStrategy(ABC):
    """
    Abstract base class for all scan strategies.

    Subclasses MUST define:
      - name (str): Human-readable name
      - slug (str): Machine-readable identifier (matches ScanPlugin.slug)
      - description (str): What the plugin checks

    Subclasses MUST implement:
      - run(target, scan) -> list[FindingData]
    """
    name:        str = ""
    slug:        str = ""
    description: str = ""

    @abstractmethod
    def run(self, target: "ScanTarget", scan: "Scan") -> list[FindingData]:
        """
        Execute the scan strategy against the given target.
        Must be safe to call multiple times (idempotent at the finding level).
        Should NOT raise exceptions — catch and return a Finding with severity=critical if needed.
        """
        ...

    def verify(self, finding: "Finding") -> bool:
        """
        Re-verify a specific finding. 
        Returns True if the vulnerability is confirmed to still exist.
        Subclasses should override this for targeted verification.
        """
        return False

    def log(self, scan: "Scan", message: str):
        """Log a message to the scan terminal."""
        from scans.services import broadcast_terminal_line
        broadcast_terminal_line(scan, f"[{self.slug}] {message}\r\n")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} slug={self.slug!r}>"


# ─── Registry ──────────────────────────────────────────────────────────────

_REGISTRY: dict[str, type[BaseScanStrategy]] = {}


def register(cls: type[BaseScanStrategy]) -> type[BaseScanStrategy]:
    """Decorator to register a strategy in the global registry."""
    _REGISTRY[cls.slug] = cls
    return cls


def get_strategy(slug: str) -> BaseScanStrategy | None:
    """Return an instantiated strategy for the given slug, or None."""
    cls = _REGISTRY.get(slug)
    return cls() if cls else None


def list_strategies() -> list[BaseScanStrategy]:
    """Return all registered strategy instances."""
    return [cls() for cls in _REGISTRY.values()]
