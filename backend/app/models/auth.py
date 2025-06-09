"""Authentication models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class TokenScope(BaseModel):
    """OAuth2 scope definition."""
    
    name: str
    description: str


class Token(BaseModel):
    """OAuth2 token response."""
    
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: str


class TokenData(BaseModel):
    """Decoded token data."""
    
    sub: str  # Subject (user ID)
    scopes: List[str] = []
    exp: datetime
    iat: datetime
    jti: str  # JWT ID for revocation


class User(BaseModel):
    """User model."""
    
    id: str
    email: EmailStr
    is_active: bool = True
    is_verified: bool = False
    created_at: datetime
    updated_at: datetime


class UserInDB(User):
    """User in database with hashed password."""
    
    hashed_password: str


class PKCEChallenge(BaseModel):
    """PKCE challenge for OAuth2.1."""
    
    code_challenge: str = Field(..., min_length=43, max_length=128)
    code_challenge_method: str = Field(default="S256", pattern="^(plain|S256)$")


class AuthorizationRequest(BaseModel):
    """OAuth2.1 authorization request."""
    
    response_type: str = Field(default="code", pattern="^code$")
    client_id: str
    redirect_uri: str
    scope: str = "read:llm"
    state: str
    code_challenge: str = Field(..., min_length=43, max_length=128)
    code_challenge_method: str = Field(default="S256", pattern="^(plain|S256)$")


class TokenRequest(BaseModel):
    """OAuth2.1 token request."""
    
    grant_type: str = Field(..., pattern="^(authorization_code|refresh_token)$")
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    code_verifier: Optional[str] = Field(None, min_length=43, max_length=128)
    refresh_token: Optional[str] = None
    client_id: str
    
    
class RateLimitInfo(BaseModel):
    """Rate limit information."""
    
    limit: int
    remaining: int
    reset: datetime
    retry_after: Optional[int] = None