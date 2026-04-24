"""
HackScan Pro — @ai_action decorator.

Manages the full lifecycle of an AI-backed method call:
  1. Cache check → return cached result (debit as cached)
  2. First-use check → free pass for new workspaces
  3. Balance verification → raise InsufficientCreditsError if short
  4. Execute the wrapped function
  5. Debit actual token usage
  6. Store result in cache
"""
import functools
import hashlib
import logging

from django.core.cache import cache

from .credit_service import CreditService, InsufficientCreditsError  # noqa: F401

logger = logging.getLogger(__name__)


def ai_action(action: str, cache_ttl: int = 3600, allow_express: bool = True):
    """
    Decorator for AI service methods that consume credits.

    The wrapped function MUST return a tuple:
        (result: str, usage: object)
    where ``usage`` has .input_tokens and .output_tokens attributes.

    If no usage info is available, return a SimpleNamespace with zeros.

    Keyword arguments injected by the caller:
        workspace, user, express (optional)
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(
            *args,
            workspace=None,
            user=None,
            express: bool = False,
            **kwargs,
        ):
            # ── 1. Build deterministic cache key ──
            key_data = f"{action}:{repr(args[1:])}:{repr(sorted(kwargs.items()))}"
            cache_key = f"ai:{hashlib.md5(key_data.encode()).hexdigest()}"

            # ── 2. Check cache ──
            cached = cache.get(cache_key)
            if cached is not None:
                CreditService.debit(
                    workspace=workspace,
                    user=user,
                    action=action,
                    was_cached=True,
                    cache_key=cache_key,
                )
                logger.info(
                    "ai.action.cache_hit",
                    extra={"action": action, "cache_key": cache_key},
                )
                return cached

            # ── 3. First-use bonus ──
            is_first = CreditService.is_first_use(workspace, action)
            effective_action = f"{action}_first_use" if is_first else action

            # ── 4. Check balance ──
            effective_express = express and allow_express
            has_balance, cost, balance = CreditService.check_balance(
                workspace, effective_action, effective_express,
            )
            if not has_balance:
                raise InsufficientCreditsError(cost, balance, effective_action)

            # ── 5. Execute the AI function ──
            result, usage = func(*args, **kwargs)

            # ── 6. Debit with real token usage ──
            input_tokens = getattr(usage, "input_tokens", 0) or 0
            output_tokens = getattr(usage, "output_tokens", 0) or 0

            CreditService.debit(
                workspace=workspace,
                user=user,
                action=effective_action,
                tokens_input=input_tokens,
                tokens_output=output_tokens,
                express=effective_express,
            )

            # ── 7. Store in cache ──
            if cache_ttl > 0:
                cache.set(cache_key, result, cache_ttl)

            logger.info(
                "ai.action.executed",
                extra={
                    "action": effective_action,
                    "tokens_in": input_tokens,
                    "tokens_out": output_tokens,
                    "was_first_use": is_first,
                },
            )

            return result

        return wrapper

    return decorator
