import pytest
from django.utils import timezone
from users.models import AuditLog, User, UserRole

@pytest.mark.django_db
class TestAuditChain:
    def setup_method(self):
        self.user = User.objects.create_user(
            email="audit_tester@hackerscan.pro",
            password="Password123!",
            full_name="Audit Tester",
            role=UserRole.ADMIN
        )

    def test_hash_chaining(self):
        """Verify that logs are correctly chained via previous_hash."""
        # 1. Create first log (Genesis)
        log1 = AuditLog.log(action="test.action.1", user=self.user)
        assert log1.current_hash is not None
        assert log1.previous_hash == "0" * 64
        
        # 2. Create second log
        log2 = AuditLog.log(action="test.action.2", user=self.user)
        assert log2.previous_hash == log1.current_hash
        assert log2.current_hash != log1.current_hash
        assert log2.verify_integrity() is True

        # 3. Create third log
        log3 = AuditLog.log(action="test.action.3", user=self.user)
        assert log3.previous_hash == log2.current_hash
        assert log3.verify_integrity() is True

    def test_tamper_detection(self):
        """Verify that modifying a field breaks the hash verification."""
        log = AuditLog.log(action="secure.action", user=self.user)
        original_hash = log.current_hash
        
        # Manually tamper with a field (this would be hard in real life due to DB constraints, but let's test the logic)
        log.action = "malicious.action"
        
        # Recalculated hash should not match stored current_hash
        assert log.verify_integrity() is False
        assert log.calculate_hash() != original_hash

    def test_chain_continuity(self):
        """Verify the chain remains consistent across multiple entries."""
        logs = []
        for i in range(5):
            logs.append(AuditLog.log(action=f"step.{i}", user=self.user))
        
        for i in range(1, 5):
            assert logs[i].previous_hash == logs[i-1].current_hash
            assert logs[i].verify_integrity() is True
