from data import schemas
from resources import APIException, APIResponse, CurrentUser
from resources.auth import verify_password, get_password_hash
from urls import user_router


@user_router.post('/edit')
async def edit_user(changing_data: schemas.ChangeDataModel, user: CurrentUser):
    now_password = user.password
    if verify_password(changing_data.old_password, now_password):
        changing_data = changing_data.model_dump()
        changing_data.pop('old_password')
        changing_data['password'] = get_password_hash(changing_data['password'])
        try:
            await user.update_from_dict(changing_data)
            await user.save()
            return APIResponse('User changed successfully')
        except Exception as e:
            raise APIException(400, str(e))
    raise APIException(400, 'Incorrect password')
