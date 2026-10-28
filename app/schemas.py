import datetime as dt

from pydantic import BaseModel, ConfigDict, Field

from .models import Role, Stage, Status


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    role: Role


class RoleUpdate(BaseModel):
    role: Role


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RequestCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = ""
    kind: str = Field(default="leave", pattern="^(leave|purchase|work-order)$")


class Decision(BaseModel):
    comment: str = ""


class LogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    actor_id: int
    action: str
    comment: str
    created_at: dt.datetime


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    kind: str
    status: Status
    stage: Stage
    requester_id: int
    created_at: dt.datetime
    logs: list[LogOut] = []
