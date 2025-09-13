# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from datetime import timedelta
from app.core.security import create_access_token
from app.core.users import authenticate_user
from app.core.config import settings

router = APIRouter()

class TokenRequest(BaseModel):
    username: str
    password: str

class TokenResp(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/token", response_model=TokenResp)
async def login_for_access_token(form_data: TokenRequest):
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(subject=form_data.username, expires_delta=access_token_expires)
    return {"access_token": token}
