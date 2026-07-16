import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.sessions import create_session, verify_session, destroy_session

def test_session_flow():
    # 1. Create a session
    token = create_session()
    assert token is not None
    assert len(token) > 0
    
    # 2. Verify it is valid
    assert verify_session(token) is True
    
    # 3. Verify an invalid token is False
    assert verify_session("invalid-token") is False
    assert verify_session("") is False
    assert verify_session(None) is False
    
    # 4. Destroy it
    destroy_session(token)
    
    # 5. Verify it is no longer valid
    assert verify_session(token) is False
