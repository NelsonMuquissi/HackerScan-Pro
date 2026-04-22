import csv
import io

class CSVGenerator:
    """
    Export scan findings as tabular CSV.
    """
    @staticmethod
    def generate(findings):
        """
        Expects a list of findings dictionaries.
        """
        output = io.StringIO()
        if not findings:
            return ""

        writer = csv.DictWriter(output, fieldnames=findings[0].keys())
        writer.writeheader()
        writer.writerows(findings)
        
        return output.getvalue()
