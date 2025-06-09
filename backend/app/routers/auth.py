"""OAuth 2.1 PKCE authentication endpoints."""

from typing import Annotated
from urllib.parse import urlencode, urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
import structlog

from ..config import settings
from ..models.auth import (
    AuthorizationRequest,
    TokenRequest,
    Token,
    User,
)
from ..services.auth import AuthService
from ..dependencies import get_auth_service

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/authorize")
async def authorize(
    response_type: str = Query(..., pattern="^code$"),
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    scope: str = Query(...),
    state: str = Query(...),
    code_challenge: str = Query(..., min_length=43, max_length=128),
    code_challenge_method: str = Query(default="S256", pattern="^(plain|S256)$"),
    auth_service: AuthService = Depends(get_auth_service)
) -> HTMLResponse:
    """OAuth 2.1 authorization endpoint."""
    # Validate client_id
    if client_id != settings.oauth_client_id:
        raise HTTPException(status_code=400, detail="Invalid client_id")
        
    # Validate redirect_uri
    if redirect_uri not in settings.allowed_redirect_uris:
        raise HTTPException(status_code=400, detail="Invalid redirect_uri")
        
    # In production, would show login form
    # For demo, auto-approve with test user
    login_form = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Authorize Access</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 400px;
                margin: 100px auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h2 {{
                margin-top: 0;
                color: #333;
            }}
            .scope {{
                background: #f0f0f0;
                padding: 10px;
                border-radius: 4px;
                margin: 20px 0;
            }}
            button {{
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
            }}
            .approve {{
                background: #4CAF50;
                color: white;
            }}
            .approve:hover {{
                background: #45a049;
            }}
            .deny {{
                background: #f44336;
                color: white;
            }}
            .deny:hover {{
                background: #da190b;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Authorize Application</h2>
            <p>The application <strong>{client_id}</strong> is requesting access to:</p>
            <div class="scope">
                <strong>Scopes:</strong> {scope}
            </div>
            <form method="post" action="/auth/authorize">
                <input type="hidden" name="response_type" value="{response_type}">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="scope" value="{scope}">
                <input type="hidden" name="state" value="{state}">
                <input type="hidden" name="code_challenge" value="{code_challenge}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
                <button type="submit" name="action" value="approve" class="approve">Approve</button>
                <button type="submit" name="action" value="deny" class="deny">Deny</button>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=login_form)


@router.post("/authorize")
async def authorize_post(
    response_type: str = Form(...),
    client_id: str = Form(...),
    redirect_uri: str = Form(...),
    scope: str = Form(...),
    state: str = Form(...),
    code_challenge: str = Form(...),
    code_challenge_method: str = Form(...),
    action: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service)
) -> RedirectResponse:
    """Handle authorization form submission."""
    if action != "approve":
        # User denied access
        error_params = urlencode({
            "error": "access_denied",
            "state": state
        })
        return RedirectResponse(url=f"{redirect_uri}?{error_params}")
        
    # Create authorization code
    # In production, would use actual authenticated user ID
    user_id = "demo_user_123"
    
    code = await auth_service.create_authorization_code(
        user_id=user_id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method
    )
    
    # Redirect back with code
    success_params = urlencode({
        "code": code,
        "state": state
    })
    
    return RedirectResponse(url=f"{redirect_uri}?{success_params}")


@router.post("/token", response_model=Token)
async def token(
    grant_type: str = Form(..., pattern="^(authorization_code|refresh_token)$"),
    code: str = Form(None),
    redirect_uri: str = Form(None),
    code_verifier: str = Form(None),
    refresh_token: str = Form(None),
    client_id: str = Form(...),
    client_secret: str = Form(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> Token:
    """OAuth 2.1 token endpoint."""
    # Validate client
    if client_id != settings.oauth_client_id:
        raise HTTPException(status_code=400, detail="Invalid client_id")
        
    # Public clients don't use client_secret
    # If provided, validate it
    if client_secret and client_secret != settings.oauth_client_secret:
        raise HTTPException(status_code=400, detail="Invalid client_secret")
        
    if grant_type == "authorization_code":
        if not all([code, redirect_uri, code_verifier]):
            raise HTTPException(
                status_code=400,
                detail="Missing required parameters for authorization_code grant"
            )
            
        # Exchange code for tokens
        token_data = await auth_service.exchange_authorization_code(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid authorization code")
            
        return Token(**token_data)
        
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise HTTPException(
                status_code=400,
                detail="Missing refresh_token"
            )
            
        # Refresh access token
        token_data = await auth_service.refresh_access_token(
            refresh_token=refresh_token,
            client_id=client_id
        )
        
        if not token_data:
            raise HTTPException(status_code=400, detail="Invalid refresh token")
            
        return Token(**token_data)
        
    else:
        raise HTTPException(status_code=400, detail="Unsupported grant_type")


@router.post("/revoke")
async def revoke_token(
    token: str = Form(...),
    token_type_hint: str = Form(None),
    auth_service: AuthService = Depends(get_auth_service)
) -> Response:
    """Revoke a token."""
    # Try to decode as access token
    token_data = await auth_service.verify_token(token)
    if token_data and token_data.jti:
        await auth_service.revoke_token(token_data.jti)
        
    # Always return 200 OK per spec
    return Response(status_code=200)


@router.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """OAuth 2.1 server metadata."""
    base_url = "https://api.example.com"  # In production, get from request
    
    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/auth/authorize",
        "token_endpoint": f"{base_url}/auth/token",
        "token_endpoint_auth_methods_supported": ["none", "client_secret_post"],
        "revocation_endpoint": f"{base_url}/auth/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["read:llm", "read:html", "write:crawl"],
    }