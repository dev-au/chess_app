from datetime import datetime

from pydantic import BaseModel


class TokenModel(BaseModel):
    access_token: str
    token_type: str


class SignUpModel(BaseModel):
    username: str
    password: str
    fullname: str
    age: int
    country: str


class SignInModel(BaseModel):
    username: str
    password: str


class ChangeDataModel(BaseModel):
    password: str | None
    fullname: str | None
    age: int | None
    country: str | None
    old_password: str


class StartTournamentModel(BaseModel):
    name: str
    created_at: datetime
    finishing_at: datetime
