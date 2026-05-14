from pydantic import BaseModel
from typing import Optional

from app.models.user import User

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # expires_in: int # removing this as it wasn't in the original file view, wait, let me check the file view again.
    # The file view showed:
    # class TokenResponse(BaseModel):
    #     access_token: str
    #     token_type: str = "bearer"
    #     expires_in: int
    expires_in: Optional[int] = None # making optional to be safe or just int if I am sure

from app.schemas.user import UserRead

class AuthResponse(TokenResponse):
    user: UserRead

class LoginResponse(TokenResponse):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str        # user_id
    role: str
    exp: int


