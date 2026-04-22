import logging
from django.template.loader import render_to_string
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class HTMLGenerator:
    """
    Generator for Technical and Executive HTML reports.
    Inlines CSS for standalone portability.
    """

    @staticmethod
    def generate(scan_data, report_type="TECHNICAL"):
        """
        Generates an HTML report with inlined CSS.
        """
        template = "reports/technical.html" if report_type == "TECHNICAL" else "reports/executive.html"
        
        # Load CSS content to inline it
        css_path = os.path.join(settings.BASE_DIR, "reports", "templates", "reports", "report.css")
        css_content = ""
        try:
            with open(css_path, "r", encoding="utf-8") as f:
                css_content = f.read()
        except Exception as e:
            logger.warning("Could not read report.css for inlining: %s", e)

        html_content = render_to_string(template, {
            "scan": scan_data,
            "inline_css": css_content
        })
        
        return html_content.encode("utf-8")
