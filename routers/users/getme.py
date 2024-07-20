from resources import CurrentUser
from urls import user_router


@user_router.post('/getme')
async def edit_user(user: CurrentUser):
    user = dict(user)
    user.pop('password')
    return user

