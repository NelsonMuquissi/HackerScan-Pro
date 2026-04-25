import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from users.models import User, Workspace
from billing.models import Plan, Subscription, SubscriptionStatus

def setup_god_mode():
    email = 'emelsonmuquissi@gmail.com'
    try:
        user = User.objects.get(email=email)
        workspace = user.owned_workspaces.first()
        
        if not workspace:
            print(f"No workspace found for {email}")
            return

        # Create or update Enterprise Plan
        plan, _ = Plan.objects.get_or_create(
            name='enterprise',
            defaults={
                'display_name': 'Enterprise Plan',
                'limits': {
                    'scans_per_month': -1,
                    'max_targets': -1,
                    'api_access': True,
                    'max_scheduled_scans': -1
                }
            }
        )
        
        # Ensure plan limits are set to unlimited even if it existed
        plan.limits = {
            'scans_per_month': -1,
            'max_targets': -1,
            'api_access': True,
            'max_scheduled_scans': -1
        }
        plan.save()

        # Create or update Subscription
        sub, created = Subscription.objects.get_or_create(
            workspace=workspace,
            defaults={
                'plan': plan,
                'status': SubscriptionStatus.ACTIVE,
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + timedelta(days=3650) # 10 years
            }
        )
        
        if not created:
            sub.plan = plan
            sub.status = SubscriptionStatus.ACTIVE
            sub.current_period_end = timezone.now() + timedelta(days=3650)
            sub.save()
            
        print(f"SUCCESS: Subscription for {workspace.slug} updated to {plan.name}")
        
    except User.DoesNotExist:
        print(f"User {email} not found")

if __name__ == "__main__":
    setup_god_mode()
