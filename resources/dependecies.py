from typing import Annotated

import jwt
from fastapi import Depends
from jwt import InvalidTokenError

from data.models import User
from resources import APIException
from resources.auth import SECRET_KEY, ALGORITHM
from urls import oauth2_scheme


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = APIException(
        status_code=401,
        message='Invalid credentials',
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await User.get_or_none(username=username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = APIException(
        status_code=401,
        message='Invalid credentials',
    )
    access_denied_exception = APIException(
        status_code=403,
        message='You do not have admin status',
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await User.get_or_none(username=username)
    if user is None:
        raise credentials_exception
    if not user.is_admin:
        raise access_denied_exception
    return user


async def get_current_super_admin(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = APIException(
        status_code=401,
        message='Invalid credentials',
    )
    access_denied_exception = APIException(
        status_code=403,
        message='You do not have super admin status',
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except InvalidTokenError:
        raise credentials_exception
    user = await User.get_or_none(username=username)
    if user is None:
        raise credentials_exception
    if not user.is_super_admin:
        raise access_denied_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
CurrentSuperAdmin = Annotated[User, Depends(get_current_super_admin)]
