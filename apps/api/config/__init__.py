"""
Config package for HackScan Pro.
Exports the Celery app so that `celery -A config.celery` works
and Django loads the Celery app on startup.
"""
from .celery import app as celery_app

__all__ = ["celery_app"]
