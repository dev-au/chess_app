from data import models
from resources import CurrentAdmin, APIResponse, APIException
from urls import admin_router


@admin_router.get('/user-info')
async def get_user_info(admin: CurrentAdmin, username: str):
    search_user = await models.User.get_or_none(username=username)
    if search_user:
        return APIResponse('User found', search_user)
    else:
        raise APIException(404, 'User not found')


@admin_router.get('/user-games')
async def get_user_games(admin: CurrentAdmin, username: str):
    search_user = await models.User.get_or_none(username=username)
    if search_user:
        games_white = await models.Game.filter(white_player=search_user)
        games_black = await models.Game.filter(black_player=search_user)
        return APIResponse('User Found', games_white=games_white, games_black=games_black)


