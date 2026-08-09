from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class MeResponse(BaseModel):
    username: str
    name: str | None = None
    role: str = "platform_admin"
