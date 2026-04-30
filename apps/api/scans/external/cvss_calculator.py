import math

class CVSS31Calculator:
    """
    CVSS v3.1 Base Score Calculator.
    Implementation of the official FIRST.org CVSS v3.1 equations.
    """
    
    # Weights for CVSS v3.1
    AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
    AC = {"L": 0.77, "H": 0.44}
    PR = {
        "U": {"N": 0.85, "L": 0.62, "H": 0.27}, # Scope Unchanged
        "C": {"N": 0.85, "L": 0.68, "H": 0.50}  # Scope Changed
    }
    UI = {"N": 0.85, "R": 0.62}
    CIA = {"H": 0.56, "L": 0.22, "N": 0}
    
    @classmethod
    def calculate(cls, vector: str) -> float:
        """
        Calculates the Base Score for a given CVSS v3.1 vector string.
        Example: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
        """
        try:
            params = cls._parse_vector(vector)
            
            # Extract values
            av = cls.AV[params["AV"]]
            ac = cls.AC[params["AC"]]
            scope = params["S"]
            pr = cls.PR[scope][params["PR"]]
            ui = cls.UI[params["UI"]]
            conf = cls.CIA[params["C"]]
            integ = cls.CIA[params["I"]]
            avail = cls.CIA[params["A"]]
            
            # Impact Sub Score (ISS)
            iss = 1 - ((1 - conf) * (1 - integ) * (1 - avail))
            
            # Impact
            if scope == "U":
                impact = 6.42 * iss
            else:
                impact = 7.52 * (iss - 0.029) - 3.25 * ((iss - 0.02) ** 15)
            
            # Exploitability
            exploitability = 8.22 * av * ac * pr * ui
            
            # Base Score
            if impact <= 0:
                base_score = 0
            else:
                if scope == "U":
                    base_score = cls._roundup(min(impact + exploitability, 10))
                else:
                    base_score = cls._roundup(min(1.08 * (impact + exploitability), 10))
            
            return base_score
            
        except (KeyError, ValueError, ZeroDivisionError) as e:
            # Return 0.0 or raise? For security tools, usually better to return 0 and log
            return 0.0

    @staticmethod
    def _parse_vector(vector: str) -> dict:
        """Parses CVSS vector string into a dictionary."""
        # Strip prefix if present
        if vector.startswith("CVSS:3.1/"):
            vector = vector[9:]
        elif vector.startswith("CVSS:3.0/"):
            vector = vector[9:]
            
        parts = vector.split("/")
        params = {}
        for part in parts:
            if ":" in part:
                key, val = part.split(":")
                params[key] = val
        
        # Validate required fields
        required = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
        for r in required:
            if r not in params:
                raise ValueError(f"Missing required CVSS parameter: {r}")
                
        return params

    @staticmethod
    def _roundup(input_val: float) -> float:
        """Official CVSS Roundup function: rounds up to one decimal place."""
        int_input = int(input_val * 100000)
        if (int_input % 10000) == 0:
            return int_input / 100000.0
        else:
            return (math.floor(int_input / 10000.0) + 1) / 10.0

    @classmethod
    def get_severity(cls, score: float) -> str:
        """Returns the severity label for a given CVSS score."""
        if score == 0: return "info"
        if 0.1 <= score <= 3.9: return "low"
        if 4.0 <= score <= 6.9: return "medium"
        if 7.0 <= score <= 8.9: return "high"
        if 9.0 <= score <= 10.0: return "critical"
        return "info"
