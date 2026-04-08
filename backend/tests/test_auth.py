"""
Auth test suite for Phase 5 — Plan 01.

Tests cover:
  - Password hashing (argon2 round-trip)
  - JWT encode/decode
  - Auth routes: login, logout, /auth/me
  - Protected endpoint enforcement
  - Rate limiting (429 after 5/min)
  - CORS headers
  - Security headers
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Unit tests — security.py (no HTTP needed)
# ---------------------------------------------------------------------------

def test_password_hash():
    from app.core.security import hash_password, verify_password
    hashed = hash_password("secret")
    assert hashed.startswith("$argon2")
    assert verify_password("secret", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_roundtrip():
    # _set_env autouse fixture has already patched jwt_secret on settings
    from app.core.security import create_access_token, decode_access_token
    token = create_access_token({"sub": "admin"})
    assert isinstance(token, str)
    assert token.count(".") == 2  # header.payload.signature

    payload = decode_access_token(token)
    assert payload["sub"] == "admin"
    assert "exp" in payload


def test_jwt_invalid():
    # _set_env autouse fixture has already patched jwt_secret on settings
    import jwt
    from app.core.security import decode_access_token
    with pytest.raises(jwt.PyJWTError):
        decode_access_token("garbage.not.valid")


# ---------------------------------------------------------------------------
# HTTP integration tests — use fresh app with test env vars
# ---------------------------------------------------------------------------

_pwd_ctx = CryptContext(schemes=["argon2"], deprecated="auto")
_TEST_PASS = "testpass"
_TEST_HASH = _pwd_ctx.hash(_TEST_PASS)


@pytest.fixture(autouse=True)
def _set_env(monkeypatch):
    """
    Inject auth env vars before each test by directly patching the settings object.

    Avoids importlib.reload which causes @limiter.limit to be applied multiple
    times, multiplying rate-limit counts per request.
    """
    from app.core import config as cfg_mod
    from app.core import security as sec_mod
    from app.core.rate_limit import limiter

    # Patch the live settings object directly
    monkeypatch.setattr(cfg_mod.settings, "jwt_secret", "testsecret-integration")
    monkeypatch.setattr(cfg_mod.settings, "admin_username", "admin")
    monkeypatch.setattr(cfg_mod.settings, "admin_password_hash", _TEST_HASH)
    monkeypatch.setattr(cfg_mod.settings, "frontend_url", "http://localhost:5173")

    # Also patch security module's pwd_ctx if it cached the secret
    # (jwt_secret is used at call time in create/decode_access_token — no cache issue)

    # Reset rate limiter so each test starts with a clean bucket
    limiter._storage.reset()


def _get_app():
    """Import app fresh (after env reload) each time."""
    import importlib
    import app.main as main_mod
    importlib.reload(main_mod)
    return main_mod.app


@pytest_asyncio.fixture
async def client():
    import app.main as main_mod
    transport = ASGITransport(app=main_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client():
    """Client with valid auth cookie already set."""
    import app.main as main_mod
    transport = ASGITransport(app=main_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/auth/login",
            data={"username": "admin", "password": _TEST_PASS},
        )
        assert resp.status_code == 200, f"auth_client login failed: {resp.text}"
        yield c


# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client):
    resp = await client.post(
        "/auth/login",
        data={"username": "admin", "password": _TEST_PASS},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrongpass"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_logout(auth_client):
    resp = await auth_client.post("/auth/logout")
    assert resp.status_code == 200
    # Cookie should be cleared (max-age=0 or deleted)
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_me_authenticated(auth_client):
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_me_unauthenticated(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_blocked(client):
    resp = await client.get("/api/signals")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_rate_limit(client):
    """6th login attempt within 1 minute should return 429."""
    for i in range(5):
        await client.post(
            "/auth/login",
            data={"username": "admin", "password": "wrongpass"},
        )
    resp = await client.post(
        "/auth/login",
        data={"username": "admin", "password": "wrongpass"},
    )
    assert resp.status_code == 429


@pytest.mark.asyncio
async def test_cors_header(client):
    resp = await client.options(
        "/api/signals",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Either 200 preflight or 401 — the CORS header must be present
    assert "access-control-allow-origin" in resp.headers
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


@pytest.mark.asyncio
async def test_security_headers(auth_client):
    """Security headers are present on authenticated responses."""
    resp = await auth_client.get("/auth/me")
    assert resp.status_code == 200
    headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    assert "x-frame-options" in headers_lower
    assert "x-content-type-options" in headers_lower
