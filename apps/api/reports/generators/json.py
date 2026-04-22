import json
from rest_framework.utils.encoders import JSONEncoder

class JSONGenerator:
    """
    Export scan findings as structured JSON.
    """
    @staticmethod
    def generate(scan_data):
        return json.dumps(scan_data, cls=JSONEncoder, indent=2)
