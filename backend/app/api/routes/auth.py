"""
Auth routes: login, logout, /auth/me.

POST /auth/login  — validates credentials, sets httpOnly JWT cookie
POST /auth/logout — clears the JWT cookie
GET  /auth/me     — returns current user from cookie
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import create_access_token, verify_password

__all__ = ["router"]

router = APIRouter(tags=["auth"])


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """Validate credentials and set httpOnly JWT cookie."""
    username_ok = form_data.username == settings.admin_username
    password_ok = (
        bool(settings.admin_password_hash)
        and verify_password(form_data.password, settings.admin_password_hash)
    )
    if not (username_ok and password_ok):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": form_data.username})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=False,  # False for HTTP dev; True in prod behind HTTPS
        samesite=settings.cookie_samesite,
        max_age=1800,
    )
    return {"status": "ok"}


@router.post("/logout")
async def logout(response: Response):
    """Clear the JWT cookie."""
    response.delete_cookie("access_token")
    return {"status": "ok"}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    """Return current authenticated user info."""
    return {"username": current_user["sub"]}
