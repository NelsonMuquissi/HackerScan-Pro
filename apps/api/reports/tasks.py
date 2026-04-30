import logging
from celery import shared_task
from .models import Report
from .generators.pdf import PDFGenerator
from .generators.json import JSONGenerator
from .generators.csv import CSVGenerator
from .generators.html import HTMLGenerator
from scans.models import Scan
from ai.services import ai_service


logger = logging.getLogger(__name__)

@shared_task(queue="reports")
def generate_scan_report(report_id):
    """
    Async task to generate scan reports in different formats.
    """
    try:
        report = Report.objects.get(id=report_id)
        report.status = Report.Status.PROCESSING
        report.save()

        scan = report.scan
        workspace = scan.target.workspace
        user = scan.triggered_by
        # Prepare findings data
        findings_data = []
        for finding in scan.findings.all():
            ai_explanation = finding.ai_explanation or ""
            ai_remediation = finding.ai_remediation or ""

            # For technical reports, try to enrich with AI if missing
            if report.type == Report.Type.TECHNICAL:
                if not ai_explanation:
                    try:
                        ai_explanation = ai_service.explain_finding(
                            finding.title,
                            finding.description,
                            finding.severity,
                            evidence=finding.evidence,
                            workspace=workspace,
                            user=user
                        )
                        finding.ai_explanation = ai_explanation
                        finding.save(update_fields=['ai_explanation'])
                    except Exception as ai_e:
                        logger.warning("Failed to generate AI explanation for %s: %s", finding.id, ai_e)

                if not ai_remediation:
                    try:
                        ai_remediation = ai_service.generate_remediation_code(
                            finding.title,
                            finding.description,
                            evidence=finding.evidence,
                            workspace=workspace,
                            user=user
                        )
                        finding.ai_remediation = ai_remediation
                        finding.save(update_fields=['ai_remediation'])
                    except Exception as ai_e:
                        logger.warning("Failed to generate AI remediation for %s: %s", finding.id, ai_e)

            # finding.evidence is a JSONField; serialize it for template/export use
            evidence_display = finding.evidence
            if isinstance(evidence_display, (dict, list)):
                import json as _json  # noqa: PLC0415
                evidence_display = _json.dumps(evidence_display, indent=2)

            findings_data.append({
                'title': finding.title,
                'severity': finding.severity,
                'description': finding.description,
                'evidence': evidence_display,
                'payload': evidence_display,  # For template compatibility
                'remediation': finding.remediation,
                'status': 'Resolved' if finding.resolved_at else ('False Positive' if finding.is_false_positive else 'Open'),
                'ai_explanation': ai_explanation or finding.description,
                'ai_remediation': ai_remediation or finding.remediation,
                'business_impact': getattr(finding, 'business_impact', "Possible data exposure or service disruption."),
                'executive_summary': getattr(finding, 'executive_summary', "Immediate mitigation recommended by the technical team."),
            })

        # 4. Generate AI Attack Chain Prediction for Premium Reporting
        ai_prediction = ""
        try:
            # We use findings_data which is already redacted/prepared
            ai_prediction = ai_service.predict_attack_chains(
                findings_data,
                workspace=workspace,
                user=user
            )
        except Exception as ai_e:
            logger.warning("Failed to generate AI attack chain for report %s: %s", report_id, ai_e)

        # Aggregate severity counts from findings
        critical_count = sum(1 for f in findings_data if f['severity'].upper() == 'CRITICAL')
        high_count = sum(1 for f in findings_data if f['severity'].upper() == 'HIGH')
        medium_count = sum(1 for f in findings_data if f['severity'].upper() == 'MEDIUM')
        low_count = sum(1 for f in findings_data if f['severity'].upper() == 'LOW')

        scan_data = {
            'id': str(scan.id),
            'target': scan.target.host,
            'status': scan.status,
            'created_at': scan.created_at.isoformat() if scan.created_at else None,
            'findings': findings_data,
            'critical_count': critical_count,
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'ai_prediction': ai_prediction,
            'workspace': {
                'name': scan.target.workspace.name if hasattr(scan.target, 'workspace') and scan.target.workspace else "Default Workspace"
            }
        }

        content = None
        current_format = report.format
        if report.format == Report.Format.PDF:
            try:
                # Pass the rich scan_data to the generator
                content = PDFGenerator.generate_technical_report(scan_data) if report.type == Report.Type.TECHNICAL else PDFGenerator.generate_executive_report(scan_data)
            except Exception as pdf_e:
                logger.warning("PDF generation failed, falling back to HTML: %s", pdf_e)
                # Failover to HTML if PDF fails (common in local dev without GTK)
                content = HTMLGenerator.generate(scan_data, report_type=report.type)
                current_format = Report.Format.HTML
                report.format = Report.Format.HTML
                report.save(update_fields=['format'])

        elif report.format == Report.Format.JSON:
            content = JSONGenerator.generate(scan_data)
        elif report.format == Report.Format.CSV:
            content = CSVGenerator.generate(findings_data)
        elif report.format == Report.Format.HTML:
            content = HTMLGenerator.generate(scan_data, report_type=report.type)

        if content:
            from core.services.storage import StorageService
            storage_service = StorageService()
            
            # File name construction
            extension = current_format.lower()
            file_name = f"reports/{report.id}.{extension}"
            
            if current_format == Report.Format.PDF:
                content_type = "application/pdf"
            elif current_format == Report.Format.JSON:
                content_type = "application/json"
            elif current_format == Report.Format.CSV:
                content_type = "text/csv"
            else:
                content_type = "text/html"
            
            # Upload to storage
            file_url = storage_service.upload_file(content, file_name, content_type=content_type)
            
            if file_url:
                report.status = Report.Status.COMPLETED
                report.file_url = file_url
                report.save()
                logger.info(f"Report {report_id} generated and uploaded successfully.")
            else:
                raise ValueError("Failed to upload report to storage")
        else:
            raise ValueError(f"No content generated for format {report.format}")

    except Exception as e:
        logger.error(f"Error generating report {report_id}: {str(e)}")
        if 'report' in locals():
            report.status = Report.Status.FAILED
            report.save()
        raise
