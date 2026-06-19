"""
Base strategy interface for HackScan Pro scan plugins.

Every scan plugin must subclass BaseScanStrategy and implement `run()`.
The runner (tasks.py) discovers registered strategies and calls them in order.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncGenerator

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

    Subclasses SHOULD implement:
      - run_async(target, scan) -> AsyncGenerator[FindingData, None]
    
    Subclasses MAY implement:
      - verify_async(finding) -> bool
    """
    name:        str = ""
    slug:        str = ""
    description: str = ""

    async def run_async(self, target: "ScanTarget", scan: "Scan" = None) -> AsyncGenerator[FindingData, None]:
        """
        Execute the scan strategy asynchronously.
        By default, it runs the synchronous run() in a thread.
        Subclasses should override this for native async performance.
        Yields FindingData objects as they are discovered.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        # Fallback: run sync version in a thread
        findings = await loop.run_in_executor(None, self.run, target, scan)
        for f in findings:
            yield f

    def run(self, target: "ScanTarget", scan: "Scan" = None) -> list[FindingData]:
        """
        Execute the scan strategy against the given target (Synchronous).
        By default, it wraps run_async() using nest_asyncio.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
        
        findings = []
        async def _collect():
            async for f in self.run_async(target, scan):
                findings.append(f)
        
        loop.run_until_complete(_collect())
        return findings

    async def verify_async(self, finding: "Finding") -> bool:
        """
        Re-verify a specific finding asynchronously.
        Subclasses should override this for targeted verification.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.verify, finding)

    def verify(self, finding: "Finding") -> bool:
        """
        Re-verify a specific finding synchronously.
        By default, it wraps verify_async() using nest_asyncio.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            
        return loop.run_until_complete(self.verify_async(finding))

    def log(self, scan: "Scan", message: str):
        """Log a message to the scan terminal."""
        if not scan:
            return
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
