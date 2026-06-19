import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from users.models import Workspace
from ai.models import AIWallet

def check_admin_test_ws():
    print("Checking Admin Test's Workspace...")
    ws = Workspace.objects.filter(name="Admin Test's Workspace").first()
    if ws:
        print(f"Workspace found: {ws.id}")
        wallet = AIWallet.objects.filter(workspace=ws).first()
        if wallet:
            print(f"Wallet found. Balance: {wallet.balance_total}")
        else:
            print("Wallet NOT found for this workspace.")
    else:
        print("Workspace NOT found.")

if __name__ == "__main__":
    check_admin_test_ws()
