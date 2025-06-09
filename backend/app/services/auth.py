"""Authentication service with OAuth 2.1 PKCE support."""

import hashlib
import secrets
import base64
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import redis.asyncio as redis
from jose import JWTError, jwt
from passlib.context import CryptContext
import structlog

from ..config import settings
from ..models.auth import User, UserInDB, TokenData

logger = structlog.get_logger()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Handles authentication and authorization."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.secret_key = settings.secret_key
        self.algorithm = settings.algorithm
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
        
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
        
    async def create_access_token(
        self,
        subject: str,
        scopes: List[str] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token."""
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=settings.access_token_expire_minutes
            )
            
        # Generate unique JWT ID
        jti = secrets.token_urlsafe(32)
        
        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "jti": jti,
            "scopes": scopes or []
        }
        
        # Store JTI in Redis for revocation
        await self.redis.setex(
            f"jwt:{jti}",
            int(expires_delta.total_seconds() if expires_delta else settings.access_token_expire_minutes * 60),
            "valid"
        )
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
        
    async def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Check if token is revoked
            jti = payload.get("jti")
            if jti:
                is_valid = await self.redis.get(f"jwt:{jti}")
                if not is_valid:
                    return None
                    
            token_data = TokenData(
                sub=payload.get("sub"),
                scopes=payload.get("scopes", []),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
                jti=jti
            )
            return token_data
            
        except JWTError:
            return None
            
    async def revoke_token(self, jti: str):
        """Revoke a token by its JTI."""
        await self.redis.delete(f"jwt:{jti}")
        
    # OAuth 2.1 PKCE methods
    
    def generate_code_verifier(self) -> str:
        """Generate a code verifier for PKCE."""
        verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8')
        return verifier.rstrip('=')
        
    def generate_code_challenge(self, verifier: str) -> str:
        """Generate code challenge from verifier."""
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
        return challenge.rstrip('=')
        
    def verify_code_challenge(self, verifier: str, challenge: str) -> bool:
        """Verify PKCE code challenge."""
        expected_challenge = self.generate_code_challenge(verifier)
        return secrets.compare_digest(expected_challenge, challenge)
        
    async def create_authorization_code(
        self,
        user_id: str,
        client_id: str,
        redirect_uri: str,
        scope: str,
        code_challenge: str,
        code_challenge_method: str = "S256"
    ) -> str:
        """Create an authorization code."""
        code = secrets.token_urlsafe(32)
        
        # Store code details in Redis (expires in 10 minutes)
        code_data = {
            "user_id": user_id,
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.redis.setex(
            f"auth_code:{code}",
            600,  # 10 minutes
            str(code_data)
        )
        
        return code
        
    async def exchange_authorization_code(
        self,
        code: str,
        client_id: str,
        redirect_uri: str,
        code_verifier: str
    ) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for tokens."""
        # Get code data from Redis
        code_data_str = await self.redis.get(f"auth_code:{code}")
        if not code_data_str:
            return None
            
        # Parse code data
        import ast
        code_data = ast.literal_eval(code_data_str)
        
        # Verify client and redirect URI
        if (code_data["client_id"] != client_id or 
            code_data["redirect_uri"] != redirect_uri):
            return None
            
        # Verify PKCE
        if code_data["code_challenge_method"] == "S256":
            if not self.verify_code_challenge(code_verifier, code_data["code_challenge"]):
                return None
        else:
            # Plain method
            if code_verifier != code_data["code_challenge"]:
                return None
                
        # Delete used code
        await self.redis.delete(f"auth_code:{code}")
        
        # Create tokens
        access_token = await self.create_access_token(
            subject=code_data["user_id"],
            scopes=code_data["scope"].split()
        )
        
        refresh_token = secrets.token_urlsafe(32)
        
        # Store refresh token
        await self.redis.setex(
            f"refresh_token:{refresh_token}",
            settings.refresh_token_expire_days * 24 * 3600,
            code_data["user_id"]
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "refresh_token": refresh_token,
            "scope": code_data["scope"]
        }
        
    async def refresh_access_token(
        self,
        refresh_token: str,
        client_id: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh an access token."""
        # Get user ID from refresh token
        user_id = await self.redis.get(f"refresh_token:{refresh_token}")
        if not user_id:
            return None
            
        # Create new access token
        access_token = await self.create_access_token(
            subject=user_id,
            scopes=["read:llm", "read:html"]  # Default scopes
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_expire_minutes * 60,
            "scope": "read:llm read:html"
        }