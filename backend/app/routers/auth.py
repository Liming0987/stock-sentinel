from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest):
    """Register a new user."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login and receive JWT token."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token():
    """Refresh an expired token."""
    # TODO: Implement
    raise HTTPException(status_code=501, detail="Not implemented")
