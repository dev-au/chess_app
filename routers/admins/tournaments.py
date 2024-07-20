from data import schemas, models
from resources import CurrentAdmin, APIResponse, APIException
from urls import admin_router


@admin_router.post('/start-tournament')
async def start_tournament(admin: CurrentAdmin, tournament_data: schemas.StartTournamentModel):
    if tournament_data.created_at > tournament_data.finishing_at:
        raise APIException(400, 'Tournament finishing time must after start of tournament')
    tournament_data = tournament_data.model_dump()
    tournament_data['owner'] = admin
    await models.Tournament.create(**tournament_data)
    return APIResponse('Tournament started successfully')
