from fastapi import APIRouter
from fastapi.security import OAuth2PasswordBearer

user_router = APIRouter(prefix="/user", tags=["user"])
admin_router = APIRouter(prefix='/admin', tags=["admin"])
main_router = APIRouter(prefix='', tags=["main"])

urls = (main_router, user_router, admin_router, )
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="user/signin")