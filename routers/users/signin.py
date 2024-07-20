from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm

from data import models
from resources import APIException
from resources.auth import verify_password, create_access_token
from urls import user_router


@user_router.post('/signin')
async def signin_user(user: Annotated[OAuth2PasswordRequestForm, Depends()]):
    db_user = await models.User.get_or_none(username=user.username)
    if db_user:
        hashed_password = db_user.password
        if verify_password(user.password, hashed_password):
            return create_access_token(user.username)
    raise APIException(404, 'User not found')
