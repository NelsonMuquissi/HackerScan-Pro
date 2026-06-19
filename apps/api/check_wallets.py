import os
import django
import sys

# Set up Django environment
# sys.path.append(os.path.join(os.getcwd(), 'apps', 'api')) # Already in /app
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
        print(f"--- Workspace: {wallet.workspace.name} ({wallet.workspace.id}) ---")
        print(f"Subscription: {wallet.balance_subscription}")
        print(f"Purchased: {wallet.balance_purchased}")
        print(f"Bonus: {wallet.balance_bonus}")
        print(f"Total: {wallet.balance_total}")
        print("-" * 20)

if __name__ == "__main__":
    check_wallets()
