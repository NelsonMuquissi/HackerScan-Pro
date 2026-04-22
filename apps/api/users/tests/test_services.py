"""
Unit tests for users/services.py
Email sending is mocked to avoid SMTP calls.
"""
import pytest
from unittest.mock import patch

from users.services import AuthService, TwoFactorService, UserService
from core.exceptions import AuthenticationError, ConflictError, ServiceError


class TestUserService:
    @patch("users.services.UserService._send_verification_email")
    def test_register_creates_user_and_profile(self, mock_email, db):
        user = UserService.register("alice@test.com", "SecurePass123!", "Alice")
        assert user.pk is not None
        assert user.email == "alice@test.com"
        assert not user.email_verified
        mock_email.assert_called_once_with(user)

    @patch("users.services.UserService._send_verification_email")
    def test_register_duplicate_email_raises(self, _, db):
        UserService.register("bob@test.com", "SecurePass123!", "Bob")
        with pytest.raises(ConflictError):
            UserService.register("bob@test.com", "SecurePass123!", "Bob2")


class TestAuthService:
    def test_login_success(self, user):
        tokens = AuthService.login(email=user.email, password="SecurePass123!")
        assert "access" in tokens
        assert "refresh" in tokens

    def test_login_wrong_password(self, user):
        with pytest.raises(AuthenticationError):
            AuthService.login(email=user.email, password="wrongpassword")

    def test_login_unverified_email_raises(self, unverified_user):
        from core.exceptions import ServiceError  # noqa: PLC0415
        with pytest.raises(ServiceError):
            AuthService.login(email=unverified_user.email, password="SecurePass123!")

    def test_change_password_success(self, user, db):
        AuthService.change_password(user, "SecurePass123!", "NewPass456@")
        assert user.check_password("NewPass456@")

    def test_change_password_wrong_old(self, user, db):
        with pytest.raises(AuthenticationError):
            AuthService.change_password(user, "wrong", "NewPass456@")


class TestTwoFactorService:
    def test_generate_setup_stores_secret(self, user, db):
        result = TwoFactorService.generate_setup(user)
        user.refresh_from_db()
        assert user.totp_secret is not None
        assert "otpauth_url" in result

    def test_verify_code_correct(self, user, db):
        import pyotp  # noqa: PLC0415
        TwoFactorService.generate_setup(user)
        user.refresh_from_db()
        code = pyotp.TOTP(user.totp_secret).now()
        assert TwoFactorService.verify_code(user, code) is True

    def test_verify_code_wrong(self, user, db):
        TwoFactorService.generate_setup(user)
        assert TwoFactorService.verify_code(user, "000000") is False

    def test_enable_2fa(self, user, db):
        import pyotp  # noqa: PLC0415
        TwoFactorService.generate_setup(user)
        user.refresh_from_db()
        code = pyotp.TOTP(user.totp_secret).now()
        backup_codes = TwoFactorService.verify_and_enable(user, code)
        user.refresh_from_db()
        assert user.totp_enabled is True
        assert len(backup_codes) == 8

    def test_enable_2fa_wrong_code(self, user, db):
        TwoFactorService.generate_setup(user)
        with pytest.raises(ServiceError):
            TwoFactorService.verify_and_enable(user, "999999")
