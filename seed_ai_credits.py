import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from ai.credit_service import CreditService
from users.models import Workspace

def seed_credits():
    workspaces = Workspace.objects.all()
    if not workspaces.exists():
        print("No workspaces found to seed credits.")
        return

    for ws in workspaces:
        print(f"Seeding 10,000 bonus credits to workspace: {ws.name} ({ws.id})")
        try:
            CreditService.credit(
                workspace=ws,
                amount=10000,
                action="admin_manual_seed",
                credit_type="bonus"
            )
            print(f"Successfully seeded credits for {ws.name}")
        except Exception as e:
            print(f"Error seeding credits for {ws.name}: {e}")

if __name__ == "__main__":
    seed_credits()
