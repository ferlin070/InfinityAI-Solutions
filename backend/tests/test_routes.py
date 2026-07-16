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
    # Login page should serve 200 OK
    response = client.get("/login")
    assert response.status_code == 200
    assert "Borang Daftar Masuk" in response.text

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
    
    # Access dashboard with cookie should succeed
    dashboard_response = client.get("/", cookies={"session_token": session_cookie})
    assert dashboard_response.status_code == 200
    assert "Pejabat Operasi Harian" in dashboard_response.text

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

