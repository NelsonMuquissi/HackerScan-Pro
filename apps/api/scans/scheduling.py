from django_celery_beat.models import PeriodicTask, CrontabSchedule
import json
from .models import ScheduledScan, Frequency

class ScanScheduler:
    """
    Syncs ScheduledScan records with django-celery-beat PeriodicTask.
    """

    @staticmethod
    def get_or_create_crontab(frequency: str) -> CrontabSchedule:
        if frequency == Frequency.DAILY:
            # 00:00 every day
            cron, _ = CrontabSchedule.objects.get_or_create(hour=0, minute=0)
        elif frequency == Frequency.WEEKLY:
            # 00:00 every Monday
            cron, _ = CrontabSchedule.objects.get_or_create(hour=0, minute=0, day_of_week=1)
        elif frequency == Frequency.MONTHLY:
            # 00:00 on the 1st of every month
            cron, _ = CrontabSchedule.objects.get_or_create(hour=0, minute=0, day_of_month=1)
        else:
            # Default to weekly if unknown
            cron, _ = CrontabSchedule.objects.get_or_create(hour=0, minute=0, day_of_week=1)
        return cron

    @classmethod
    def sync(cls, scheduled_scan: ScheduledScan):
        """Creates or updates the associated PeriodicTask."""
        if not scheduled_scan.is_active:
            if scheduled_scan.periodic_task:
                scheduled_scan.periodic_task.enabled = False
                scheduled_scan.periodic_task.save()
            return

        cron = cls.get_or_create_crontab(scheduled_scan.frequency)
        
        task_name = f"Scan: {scheduled_scan.target.host} ({scheduled_scan.id})"
        task_path = "scans.tasks.run_scheduled_scan"
        task_args = json.dumps([str(scheduled_scan.id)])

        if scheduled_scan.periodic_task:
            pt = scheduled_scan.periodic_task
            pt.name = task_name
            pt.crontab = cron
            pt.task = task_path
            pt.args = task_args
            pt.enabled = True
            pt.save()
        else:
            pt = PeriodicTask.objects.create(
                name=task_name,
                task=task_path,
                crontab=cron,
                args=task_args,
                enabled=True,
                queue="scheduled"
            )
            scheduled_scan.periodic_task = pt
            scheduled_scan.save(update_fields=["periodic_task"])

    @staticmethod
    def delete(scheduled_scan: ScheduledScan):
        """Cleanup associated periodic task."""
        if scheduled_scan.periodic_task:
            scheduled_scan.periodic_task.delete()
