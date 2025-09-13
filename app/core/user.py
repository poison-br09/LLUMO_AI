# app/core/users.py
from app.core.security import get_password_hash, verify_password

TEST_USER = {
    "username": "admin",
    "password_hash": get_password_hash("strongpassword123")
}

def authenticate_user(username: str, password: str) -> bool:
    if username != TEST_USER["username"]:
        return False
    return verify_password(password, TEST_USER["password_hash"])
