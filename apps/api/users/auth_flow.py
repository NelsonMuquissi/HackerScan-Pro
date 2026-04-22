"""
Robust Authentication and Authorization Flow using Pydantic and Passlib.
Designed to be modular and secure, easily integratable into any view logic.
"""
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any
from django.contrib.auth.hashers import make_password, check_password

# ==========================================
# 1. Pydantic Models for Validation
# ==========================================

class UserRegistrationSchema(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    password: str = Field(..., min_length=8, description="Must be at least 8 characters long")

class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponseSchema(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str] = []

# ==========================================
# 2. Secure Password Hashing with Passlib
# ==========================================

# django.contrib.auth.hashers handles multiple algorithms based on PASSWORD_HASHERS setting

class PasswordService:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a plain text password."""
        return make_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against its hashed version."""
        return check_password(plain_password, hashed_password)

# ==========================================
# 3. Authorization and JWT Management
# ==========================================

from django.conf import settings

# In a real environment, load this securely from environment variables (e.g., os.getenv('JWT_SECRET_KEY'))
SECRET_KEY = settings.SECRET_KEY  
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class AuthServiceFlow:
    @staticmethod
    def create_token_pair(data: dict) -> TokenResponseSchema:
        """Create both access and refresh JWT tokens."""
        # Access token
        access_expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_payload = data.copy()
        access_payload.update({"exp": access_expire, "type": "access"})
        access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
        
        # Refresh token (e.g., 7 days)
        refresh_expire = datetime.utcnow() + timedelta(days=7)
        refresh_payload = {"user_id": data.get("user_id"), "exp": refresh_expire, "type": "refresh"}
        refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)

        return TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """Decode and verify the JWT access token. Returns payload or raises ValueError."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type and payload.get("purpose") != token_type:
                # Handle dual semantics: 'type' vs 'purpose'
                if not (token_type == "access" and "purpose" in payload):
                    raise ValueError(f"Invalid token type. Expected {token_type}")
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token")
            
    @staticmethod
    def check_permissions(payload: Dict[str, Any], required_roles: list[str] = None) -> bool:
        """Check if the user defined by the JWT payload has the required roles."""
        if not required_roles:
            return True
            
        user_roles = payload.get("roles", [])
        # Returns True if the user has any of the required roles
        return any(role in user_roles for role in required_roles)
