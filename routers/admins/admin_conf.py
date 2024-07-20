from data import schemas, models
from resources import CurrentSuperAdmin, APIResponse, APIException
from urls import admin_router


@admin_router.post("/add-admin")
async def add_new_admin(super_admin: CurrentSuperAdmin, username: str):
    new_admin = await models.User.get_or_none(username=username)
    if new_admin and new_admin != super_admin:
        new_admin.is_admin = True
        await new_admin.save()
        return APIResponse('User promoted to admin successfully')
    raise APIException(404, 'User not found')


@admin_router.delete("/delete-admin")
async def delete_admin(super_admin: CurrentSuperAdmin, username: str):
    admin = await models.User.get_or_none(username=username)
    if admin and admin != super_admin:
        admin.is_admin = False
        await admin.save()
        return APIResponse('Admin deleted successfully')
    raise APIException(404, 'Admin not found')

