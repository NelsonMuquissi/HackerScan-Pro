"""
Unit tests for users/models.py
"""
import pytest
from django.contrib.auth import get_user_model
from users.models import APIKey, AuditLog, UserProfile

User = get_user_model()


class TestUser:
    def test_create_user_hashes_password(self, db):
        user = User.objects.create_user(
            email="bob@test.com", password="SecurePass123!", full_name="Bob"
        )
        assert user.pk is not None
        assert user.check_password("SecurePass123!")
        assert not user.check_password("wrong")

    def test_email_is_normalised(self, db):
        user = User.objects.create_user(
            email="BOB@TEST.COM", password="SecurePass123!", full_name="Bob"
        )
        assert user.email == "bob@test.com"

    def test_soft_delete(self, user, db):
        user_id = user.id
        user.delete()
        assert User.objects.filter(pk=user_id).count() == 0
        assert User.all_objects.filter(pk=user_id).count() == 1

    def test_profile_auto_created_by_signal(self, db):
        user = User.objects.create_user(
            email="signal@test.com", password="SecurePass123!", full_name="Signal"
        )
        assert UserProfile.objects.filter(user=user).exists()


class TestAPIKey:
    def test_generate_returns_raw_key(self, user, db):
        instance, raw_key = APIKey.generate(user=user, name="CI", scopes=["scans:read"])
        assert raw_key.startswith("hs_live_")
        assert instance.key_prefix == raw_key[:8]

    def test_authenticate_valid_key(self, user, db):
        _, raw_key = APIKey.generate(user=user, name="CI", scopes=[])
        found = APIKey.authenticate(raw_key)
        assert found is not None
        assert found.user_id == user.id

    def test_authenticate_invalid_key_returns_none(self, db):
        assert APIKey.authenticate("hs_live_totally_fake") is None


class TestAuditLog:
    def test_log_creates_record(self, user, db):
        AuditLog.log(action="test.action", user=user, metadata={"key": "value"})
        log = AuditLog.objects.get(action="test.action")
        assert log.user == user
        assert log.metadata["key"] == "value"
