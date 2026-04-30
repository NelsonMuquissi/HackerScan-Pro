import logging
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Generator for Technical and Executive PDF reports.
    Uses WeasyPrint to render HTML/CSS.

    WeasyPrint requires native GTK/Pango libraries (libgobject-2.0-0).
    The import is kept lazy (inside methods) so that the rest of the API
    boots normally even when those native libs are absent (e.g. on Windows
    dev machines without GTK installed).
    """

    @staticmethod
    def generate_technical_report(scan_data):
        """
        Generates a technical PDF report with findings, payloads, and remediation details.
        """
        html_content = render_to_string("reports/technical.html", {"scan": scan_data})
        return PDFGenerator._render_pdf(html_content)

    @staticmethod
    def generate_executive_report(scan_data):
        """
        Generates an executive PDF report focused on business risk and high-level summaries.
        """
        html_content = render_to_string("reports/executive.html", {"scan": scan_data})
        return PDFGenerator._render_pdf(html_content)

    @staticmethod
    def _render_pdf(html_content):
        """Internal method to render HTML to PDF bytes."""
        try:
            import os
            from django.conf import settings
            # Lazy import: keeps the API bootable when WeasyPrint's native libs
            # (libgobject-2.0-0 / Pango) are not installed on the host.
            from weasyprint import HTML  # noqa: PLC0415
            
            # Set base_url to the templates/reports directory for assets like logo.png
            template_path = os.path.join(settings.BASE_DIR, "reports", "templates", "reports")
            
            return HTML(string=html_content, base_url=template_path).write_pdf()
        except ImportError as e:

            logger.error(
                "WeasyPrint is not available on this host (missing native GTK/Pango libs). "
                "PDF generation requires a Linux/macOS environment with libgobject-2.0-0. "
                "Error: %s", e,
            )
            raise RuntimeError(
                "PDF generation is unavailable on this host. "
                "Deploy to a Linux environment with GTK/Pango installed."
            ) from e
        except Exception as e:
            logger.error("Error rendering PDF: %s", e)
            raise

