from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from ai.models import AIWallet, AITransaction, Achievement, CreditPackage
from ai.credit_service import CreditService, InsufficientCreditsError
from users.models import Workspace, User

class TestCreditSystem(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(email="test@example.com", password="password")
        self.workspace = Workspace.objects.create(name="Test Workspace", slug="test-ws", owner=self.user)
        self.wallet = AIWallet.objects.create(
            workspace=self.workspace,
            balance_subscription=100,
            balance_purchased=100,
            balance_bonus=100
        )

    def test_consumption_order(self):
        """
        Tests consumption order: subscription -> purchased -> bonus.
        """
        # 1. Consume 50 (should take from subscription)
        # Assuming explain_finding costs 10 (as defined in credit_service.py)
        CreditService.debit(self.workspace, self.user, action="explain_finding")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_subscription, 90)
        self.assertEqual(self.wallet.balance_purchased, 100)
        self.assertEqual(self.wallet.balance_bonus, 100)

        # 2. Consume 100 (should take 90 from sub, 10 from purchased)
        from ai.credit_service import AI_ACTION_COSTS
        AI_ACTION_COSTS["test_big_action"] = 100
        
        CreditService.debit(self.workspace, self.user, action="test_big_action")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_subscription, 0)
        self.assertEqual(self.wallet.balance_purchased, 90)
        self.assertEqual(self.wallet.balance_bonus, 100)

        # 3. Consume 100 (should take 90 from purchased, 10 from bonus)
        CreditService.debit(self.workspace, self.user, action="test_big_action")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_subscription, 0)
        self.assertEqual(self.wallet.balance_purchased, 0)
        self.assertEqual(self.wallet.balance_bonus, 90)

    def test_insufficient_credits(self):
        """Tests that InsufficientCreditsError is raised when balances are low."""
        self.wallet.balance_subscription = 0
        self.wallet.balance_purchased = 5
        self.wallet.balance_bonus = 0
        self.wallet.save()

        with self.assertRaises(InsufficientCreditsError) as cm:
            CreditService.debit(self.workspace, self.user, action="explain_finding") # Costs 10
        
        self.assertEqual(cm.exception.needed, 10)
        self.assertEqual(cm.exception.available, 5)
        self.assertEqual(cm.exception.shortfall, 5)

    def test_first_use_free(self):
        """Tests that the first use of an action is free."""
        self.assertTrue(CreditService.is_first_use(self.workspace, "new_action"))
        
        # Debit once
        CreditService.debit(self.workspace, self.user, action="new_action")
        
        self.assertFalse(CreditService.is_first_use(self.workspace, "new_action"))

    def test_achievement_grant(self):
        """Tests that achievements award credits only once."""
        Achievement.objects.create(
            slug="test_achieve", 
            name="Test", 
            credits=50, 
            is_active=True
        )
        
        # Grant first time
        unlocked = CreditService.grant_achievement(self.workspace, "test_achieve")
        self.assertTrue(unlocked)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_bonus, 150) # 100 starting + 50
        
        # Grant second time (idempotency)
        unlocked = CreditService.grant_achievement(self.workspace, "test_achieve")
        self.assertFalse(unlocked)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_bonus, 150) # No extra credits

    def test_monthly_grant_idempotency(self):
        """Tests that monthly grants are idempotent and handle rollover."""
        from billing.models import Subscription, Plan
        plan = Plan.objects.create(name="pro", display_name="Pro", features={"ai_credits_monthly": 1000})
        sub = Subscription.objects.create(
            workspace=self.workspace, 
            plan=plan,
            current_period_start=timezone.now(),
            current_period_end=timezone.now() + timezone.timedelta(days=30)
        )
        
        # Grant credits
        CreditService.grant_monthly_credits(self.workspace, sub)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_subscription, 1000)
        
        # Grant again (same period) - should be ignored
        CreditService.grant_monthly_credits(self.workspace, sub)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance_subscription, 1000)
