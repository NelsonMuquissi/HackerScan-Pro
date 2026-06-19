import pytest
from unittest.mock import patch, MagicMock
from reports.models import Report
from reports.tasks import generate_scan_report
from scans.models import Scan, ScanTarget, Finding, ScanStatus, Severity
from users.models import Workspace, User
from django.contrib.auth import get_user_model

@pytest.fixture
def target(db, workspace, user):
    return ScanTarget.objects.create(
        workspace=workspace, 
        owner=user, 
        host="example.com", 
        name="Example"
    )

@pytest.fixture
def scan(db, target, user):
    return Scan.objects.create(target=target, triggered_by=user, status=ScanStatus.COMPLETED)

@pytest.fixture
def report(db, scan):
    return Report.objects.create(scan=scan, type=Report.Type.TECHNICAL, format=Report.Format.JSON)


@pytest.mark.django_db
class TestReportTasks:
    
    @patch("reports.tasks.ai_service")
    @patch("core.services.storage.StorageService.upload_file")
    def test_generate_scan_report_json_success(self, mock_upload, mock_ai, report):
        mock_upload.return_value = "https://storage.example.com/reports/test.json"
        mock_ai.explain_finding.return_value = "AI Explanation"
        mock_ai.generate_remediation_code.return_value = "AI Remediation"
        mock_ai.predict_attack_chains.return_value = "AI Prediction"
        
        # Add a finding to the scan
        Finding.objects.create(
            scan=report.scan,
            title="Test Finding",
            severity=Severity.HIGH,
            description="Test Description",
            evidence={"data": "test"}
        )
        
        generate_scan_report(report.id)
        
        report.refresh_from_db()
        assert report.status == Report.Status.COMPLETED
        assert report.file_url == mock_upload.return_value
        mock_upload.assert_called_once()

    @patch("reports.tasks.PDFGenerator.generate_technical_report")
    @patch("core.services.storage.StorageService.upload_file")
    def test_generate_scan_report_pdf_success(self, mock_upload, mock_pdf, report):
        report.format = Report.Format.PDF
        report.save()
        
        mock_upload.return_value = "https://storage.example.com/reports/test.pdf"
        mock_pdf.return_value = b"%PDF-1.4 test content"
        
        generate_scan_report(report.id)
        
        report.refresh_from_db()
        assert report.status == Report.Status.COMPLETED
        assert report.file_url == mock_upload.return_value
        mock_pdf.assert_called_once()

    @patch("reports.tasks.PDFGenerator.generate_technical_report")
    @patch("reports.tasks.HTMLGenerator.generate")
    @patch("core.services.storage.StorageService.upload_file")
    def test_generate_scan_report_pdf_failover_to_html(self, mock_upload, mock_html, mock_pdf, report):
        report.format = Report.Format.PDF
        report.save()
        
        mock_upload.return_value = "https://storage.example.com/reports/test.html"
        mock_pdf.side_effect = RuntimeError("PDF generation unavailable")
        mock_html.return_value = "<html>Failover</html>"
        
        generate_scan_report(report.id)
        
        report.refresh_from_db()
        assert report.status == Report.Status.COMPLETED
        assert report.format == Report.Format.HTML
        assert report.file_url == mock_upload.return_value
        mock_pdf.assert_called_once()
        mock_html.assert_called_once()
