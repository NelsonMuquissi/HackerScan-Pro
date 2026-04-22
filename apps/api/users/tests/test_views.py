"""
Integration tests for users/ endpoints.
Uses DRF's APIClient against real views (test DB).
"""
import pytest
from unittest.mock import patch
from django.urls import reverse


class TestRegisterEndpoint:
    @patch("users.services.UserService._send_verification_email")
    def test_register_returns_201(self, _, api_client, db):
        res = api_client.post("/v1/auth/register/", {
            "email": "new@test.com",
            "password": "SecurePass123!",
            "full_name": "New User",
        }, format="json")
        assert res.status_code == 201
        assert "message" in res.json()

    @patch("users.services.UserService._send_verification_email")
    def test_register_duplicate_email_returns_409(self, _, api_client, user, db):
        res = api_client.post("/v1/auth/register/", {
            "email": user.email,
            "password": "SecurePass123!",
            "full_name": "Dup",
        }, format="json")
        assert res.status_code == 409

    def test_register_weak_password_returns_400(self, api_client, db):
        res = api_client.post("/v1/auth/register/", {
            "email": "weak@test.com",
            "password": "12345",
            "full_name": "Weak",
        }, format="json")
        assert res.status_code == 400


class TestLoginEndpoint:
    def test_login_success(self, api_client, user):
        res = api_client.post("/v1/auth/login/", {
            "email": user.email,
            "password": "SecurePass123!",
        }, format="json")
        assert res.status_code == 200
        data = res.json()
        assert "access" in data
        assert "refresh" in data

    def test_login_wrong_password_returns_401(self, api_client, user):
        res = api_client.post("/v1/auth/login/", {
            "email": user.email,
            "password": "wrong",
        }, format="json")
        assert res.status_code == 401

    def test_login_unauthenticated_user_gets_error(self, api_client, unverified_user):
        res = api_client.post("/v1/auth/login/", {
            "email": unverified_user.email,
            "password": "SecurePass123!",
        }, format="json")
        assert res.status_code == 400


class TestMeEndpoint:
    def test_get_me_authenticated(self, auth_client, user):
        res = auth_client.get("/v1/users/me/")
        assert res.status_code == 200
        assert res.json()["email"] == user.email

    def test_get_me_unauthenticated_returns_401(self, api_client):
        res = api_client.get("/v1/users/me/")
        assert res.status_code == 401

    def test_patch_me_updates_name(self, auth_client, user, db):
        res = auth_client.patch("/v1/users/me/", {"full_name": "Updated"}, format="json")
        assert res.status_code == 200
        assert res.json()["full_name"] == "Updated"


class TestAPIKeysEndpoint:
    def test_create_api_key(self, auth_client, user, db):
        res = auth_client.post("/v1/users/me/api-keys/", {
            "name": "My CI Key",
            "scopes": ["scans:read"],
        }, format="json")
        assert res.status_code == 201
        data = res.json()
        assert data["key"].startswith("hs_live_")
        assert "key_prefix" in data

    def test_list_api_keys(self, auth_client, user, db):
        from users.models import APIKey  # noqa: PLC0415
        APIKey.generate(user=user, name="Test", scopes=[])
        res = auth_client.get("/v1/users/me/api-keys/")
        assert res.status_code == 200
        assert len(res.json()) >= 1

    def test_revoke_api_key(self, auth_client, user, db):
        from users.models import APIKey  # noqa: PLC0415
        instance, _ = APIKey.generate(user=user, name="To Revoke", scopes=[])
        res = auth_client.delete(f"/v1/users/me/api-keys/{instance.id}/")
        assert res.status_code == 204
        instance.refresh_from_db()
        assert not instance.is_active


class TestTOTPEndpoints:
    def test_setup_returns_otpauth_url(self, auth_client, user, db):
        res = auth_client.post("/v1/users/me/2fa/setup/")
        assert res.status_code == 200
        assert "otpauth_url" in res.json()
        assert "secret" in res.json()

    def test_verify_wrong_code_returns_error(self, auth_client, user, db):
        auth_client.post("/v1/users/me/2fa/setup/")
        res = auth_client.post("/v1/users/me/2fa/verify/", {"code": "000000"}, format="json")
        assert res.status_code == 400
