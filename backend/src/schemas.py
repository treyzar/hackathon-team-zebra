from pydantic import BaseModel, EmailStr, Field, field_validator

from models import Role


class UserAuth(BaseModel):
    username: str
    password: str


class UserSignup(BaseModel):
    email: EmailStr
    username: str = Field(min_length=6, max_length=20, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=64)
    name: str = Field(min_length=1, max_length=60)
    surname: str = Field(min_length=1, max_length=60)
    patronymic: str = Field(max_length=60, default="")

    @field_validator("email")
    @classmethod
    def normalize_email(cls, mail: EmailStr) -> EmailStr:
        return mail.lower()


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: Role
    name: str
    surname: str
    patronymic: str
    model_config = {"from_attributes": True}


class RoleUpdate(BaseModel):
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str
