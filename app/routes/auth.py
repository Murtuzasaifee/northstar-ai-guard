from fastapi import APIRouter, HTTPException, status

from app.middleware.auth import (
    authenticate_user,
    create_access_token,
    create_user,
)
from pydantic import BaseModel, Field


router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=100)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
def register(req: RegisterRequest):
    try:
        create_user(req.username, req.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    token = create_access_token(req.username)
    return AuthResponse(access_token=token, username=req.username)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token(user["username"])
    return AuthResponse(access_token=token, username=user["username"])
