import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.main import app

client = TestClient(app)

def test_unauthenticated_redirect():
    # Accessing dashboard without cookie should redirect to login page
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"

def test_login_page_serves():
    # Login page should serve 200 OK. It's a React SPA shell now (auth is
    # decided client-side, not server-rendered) — /login and / serve
    # byte-identical HTML, so this only checks the shell renders, not
    # page-specific text (a prior hidden-div hack for that was removed).
    response = client.get("/login")
    assert response.status_code == 200
    assert '<div id="root">' in response.text

def test_api_login_incorrect():
    # Incorrect credentials should return 401
    response = client.post("/api/login", json={"email": "wrong@email.com", "password": "wrongpassword"})
    assert response.status_code == 401
    assert "E-mel atau kata laluan salah" in response.json()["detail"]

def test_api_login_correct_and_session_access():
    # Correct credentials should set cookie and allow dashboard access
    login_response = client.post("/api/login", json={"email": "bos@infinityai.com", "password": "password123"})
    assert login_response.status_code == 200
    assert login_response.json()["status"] == "success"
    
    # Extract session token from cookie
    session_cookie = login_response.cookies.get("session_token")
    assert session_cookie is not None
    
    # Access dashboard with cookie should succeed (React SPA shell — see
    # test_login_page_serves for why this doesn't check page-specific text)
    dashboard_response = client.get("/", cookies={"session_token": session_cookie})
    assert dashboard_response.status_code == 200
    assert '<div id="root">' in dashboard_response.text

def test_api_logout():
    # Log in first
    login_response = client.post("/api/login", json={"email": "bos@infinityai.com", "password": "password123"})
    session_cookie = login_response.cookies.get("session_token")
    
    # Log out
    logout_response = client.post("/api/logout", cookies={"session_token": session_cookie})
    assert logout_response.status_code == 200
    
    # Accessing dashboard again should fail/redirect
    dashboard_response = client.get("/", cookies={"session_token": session_cookie}, follow_redirects=False)
    assert dashboard_response.status_code == 303

def test_api_me_route():
    # 1. Access without token should return 401
    response = client.get("/api/me")
    assert response.status_code == 401
    
    # 2. Access with valid token should return user profile
    login_response = client.post("/api/login", json={"email": "bos@infinityai.com", "password": "password123"})
    session_cookie = login_response.cookies.get("session_token")
    
    me_response = client.get("/api/me", cookies={"session_token": session_cookie})
    assert me_response.status_code == 200
    data = me_response.json()
    assert data["status"] == "success"
    assert data["user"]["email"] == "bos@infinityai.com"
    assert data["user"]["name"] == "Bos"

def test_pwa_manifest():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["short_name"] == "InfinityAI"

def test_pwa_sw():
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/javascript"
    assert response.headers["service-worker-allowed"] == "/"
    assert "CACHE_NAME" in response.text

def test_secure_cookie_in_production(monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config, "ENVIRONMENT", "production")
    
    # Reset attempts count before test
    import src.api.routes
    src.api.routes.login_attempts = {}
    
    response = client.post("/api/login", json={"email": "bos@infinityai.com", "password": "password123"})
    assert response.status_code == 200
    
    set_cookie = response.headers.get("set-cookie")
    assert "secure" in set_cookie.lower()

def test_login_rate_limiting():
    import src.api.routes
    src.api.routes.login_attempts = {}
    
    # Make 5 failed attempts
    for _ in range(5):
        response = client.post("/api/login", json={"email": "wrong@email.com", "password": "wrongpassword"})
        assert response.status_code == 401
        
    # The 6th attempt should return 429
    response = client.post("/api/login", json={"email": "wrong@email.com", "password": "wrongpassword"})
    assert response.status_code == 429
    assert "Terlalu banyak" in response.json()["detail"]
    
    # Reset for other tests
    src.api.routes.login_attempts = {}

def test_login_fails_without_env_credentials(monkeypatch):
    import src.core.config
    monkeypatch.setattr(src.core.config, "ENVIRONMENT", "production")
    monkeypatch.setattr(src.core.config, "ADMIN_EMAIL", None)
    monkeypatch.setattr(src.core.config, "ADMIN_PASSWORD", None)
    
    with pytest.raises(RuntimeError) as excinfo:
        src.core.config.verify_environment()
    assert "ADMIN_EMAIL dan ADMIN_PASSWORD wajib diset" in str(excinfo.value)



