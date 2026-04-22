
import os
import django
import sys

# Setup Django
sys.path.append(os.path.join(os.getcwd(), 'apps/api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from billing.models import Plan, UsageRecord
from users.models import Workspace

def fix_quotas():
    # 1. Increase FREE plan limits
    free_plan = Plan.objects.filter(name="free").first()
    if free_plan:
        print(f"Updating limits for {free_plan.name}...")
        free_plan.limits['scans_per_month'] = 1000
        free_plan.limits['targets'] = 100
        free_plan.save()
        print("Limits updated to 1000 scans/month.")
    else:
        # Create it if it doesn't exist
        Plan.objects.create(
            name="free",
            display_name="Free Tier",
            limits={"scans_per_month": 1000, "targets": 100, "api_calls_per_month": 10000}
        )
        print("Created Free plan with 1000 scans limit.")

    # 2. Reset usage for all workspaces
    count = UsageRecord.objects.all().update(scans_count=0)
    print(f"Reset usage for {count} records.")

if __name__ == "__main__":
    fix_quotas()
