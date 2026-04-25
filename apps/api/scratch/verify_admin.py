import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from users.models import User, UserRole
from billing.models import Subscription

email = "emelsonmuquissi@gmail.com"
try:
    user = User.objects.get(email=email)
    print(f"User: {user.email}")
    print(f"Role: {user.role} (SuperAdmin: {user.role == UserRole.SUPERADMIN})")
    
    workspace = user.owned_workspaces.first()
    if workspace:
        print(f"Workspace: {workspace.name}")
        sub = getattr(workspace, 'subscription', None)
        if sub:
            print(f"Subscription: {sub.plan.name}")
            print(f"Status: {sub.status}")
            print(f"Ends at: {sub.current_period_end}")
        else:
            print("Subscription: NONE")
    else:
        print("Workspace: NONE")
except Exception as e:
    print(f"Error: {e}")
