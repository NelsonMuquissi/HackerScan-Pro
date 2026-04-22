"""
Shared pytest fixtures for HackScan Pro API.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture
def api_client():
    """Unauthenticated DRF test client."""
    return APIClient()


@pytest.fixture
def user(db):
    """A verified, active standard user."""
    return User.objects.create_user(
        email="user@hackscan.test",
        password="SecurePass123!",
        full_name="Test User",
        email_verified=True,
        is_active=True,
    )


@pytest.fixture
def unverified_user(db):
    """A registered but unverified user."""
    return User.objects.create_user(
        email="unverified@hackscan.test",
        password="SecurePass123!",
        full_name="Unverified User",
        email_verified=False,
    )


@pytest.fixture
def admin_user(db):
    """A platform admin user."""
    return User.objects.create_user(
        email="admin@hackscan.test",
        password="AdminPass123!",
        full_name="Admin User",
        email_verified=True,
        role="admin",
    )


@pytest.fixture
def auth_client(api_client, user):
    """DRF test client authenticated as 'user'."""
    from users.auth_flow import AuthServiceFlow  # noqa: PLC0415

    token_response = AuthServiceFlow.create_token_pair({"user_id": str(user.id)})
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token_response.access_token}")
    return api_client


# ─── Billing Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def workspace(db, user):
    """A workspace owned by the standard user."""
    from users.models import Workspace  # noqa: PLC0415

    return Workspace.objects.create(
        owner=user,
        name="Test Workspace",
        slug="test-workspace",
        plan="free",
    )


@pytest.fixture
def free_plan(db):
    """The Free plan with basic limits."""
    from billing.models import Plan  # noqa: PLC0415

    return Plan.objects.create(
        name="free",
        display_name="Free",
        price_monthly=0,
        price_yearly=0,
        currency="USD",
        features={"basic_scanning": True},
        limits={
            "scans_per_month": 5,
            "targets": 1,
            "users": 1,
            "api_access": False,
        },
        is_active=True,
    )


@pytest.fixture
def pro_plan(db):
    """The Pro plan with higher limits."""
    from billing.models import Plan  # noqa: PLC0415

    return Plan.objects.create(
        name="pro",
        display_name="Pro",
        price_monthly=29,
        price_yearly=290,
        currency="USD",
        features={"basic_scanning": True, "advanced_scanning": True, "api_access": True},
        limits={
            "scans_per_month": -1,
            "targets": 10,
            "users": 5,
            "api_access": True,
        },
        stripe_price_monthly_id="price_monthly_pro_test",
        stripe_price_yearly_id="price_yearly_pro_test",
        is_active=True,
    )


@pytest.fixture
def subscription(db, workspace, free_plan):
    """An active subscription tying the workspace to the free plan."""
    from django.utils import timezone  # noqa: PLC0415
    from billing.models import Subscription  # noqa: PLC0415

    now = timezone.now()
    return Subscription.objects.create(
        workspace=workspace,
        plan=free_plan,
        status="active",
        billing_cycle="monthly",
        current_period_start=now,
        current_period_end=now + timezone.timedelta(days=30),
    )

