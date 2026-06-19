import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.join(os.getcwd(), 'apps', 'api'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from ai.models import AIWallet
from users.models import Workspace

def check_wallets():
    print("Checking AI Wallets...")
    wallets = AIWallet.objects.all()
    if not wallets:
        print("No AI Wallets found.")
        return

    for wallet in wallets:
        print(f"--- Workspace: {wallet.workspace.name} ---")
        print(f"Subscription: {wallet.subscription_balance}")
        print(f"Purchased: {wallet.purchased_balance}")
        print(f"Bonus: {wallet.bonus_balance}")
        print(f"Total: {wallet.total_balance}")
        print("-" * 20)

if __name__ == "__main__":
    check_wallets()
