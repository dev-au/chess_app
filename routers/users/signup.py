from data import schemas, models
from resources.auth import get_password_hash
from urls import user_router
from resources import APIResponse, APIException


@user_router.post('/signup')
async def signup_user(user: schemas.SignUpModel):
    try:
        user_dict = user.model_dump()
        user_dict['password'] = get_password_hash(user_dict['password'])
        await models.User.create(**user_dict)
        return APIResponse('User created successfully')
    except Exception as e:
        raise APIException(400, str(e))
