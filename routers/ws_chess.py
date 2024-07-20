from aioredis import Redis
from fastapi.websockets import WebSocket
from starlette.requests import Request

from config import render
from data import models
from resources.ws_exchange import WsManager, Event, online_users, ws_docs
from urls import main_router


@main_router.get('/ws-docs')
async def build_ws_docs(request: Request):
    return render(request, 'ws_docs.html', {'ws_docs': ws_docs})


@main_router.websocket('/chess')
async def chess_platform(websocket: WebSocket):
    wsm = WsManager(websocket)

    @wsm.on_event('message')
    async def message_event(event: Event, text: str):
        await event.forward(text=text)

    @wsm.on_event('view-match')
    async def view_match_event(event: Event, game_id: int):
        match = await models.Match.get_or_none(pk=game_id)
        if match:
            if event.current_user.pk in [match.white_player, match.black_player]:
                return await event.reply_exception('You are now playing this match')
            elif match.pk not in wsm.viewing_matches:
                wsm.viewing_matches.append(match.pk)
                return await event.success()
            return await event.reply_exception('You are viewing this match')
        else:
            await event.reply_exception('Match not found')

    @wsm.on_event('play-offer')
    async def play_offer_event(event: Event):
        if not event.receiver:
            return event.receiver_exc()
        if event.current_user.playing_now:
            return await event.reply_exception('You cannot send offer during playing chess')
        if event.receiver.username not in online_users:
            return await event.reply_exception('You cannot send offer to offline user')
        if event.receiver.playing_now:
            return await event.reply_exception('Offering user playing chess now')
        redis: Redis = websocket.app.redis
        receiver_offers = await event.receiver.get_offers(redis)
        if event.current_user.pk in receiver_offers:
            return await event.reply_exception('You have already sent offer to this user')
        own_offers = await event.current_user.get_offers(redis)
        if event.receiver.pk in own_offers:
            return await event.reply_exception('This user has already sent offer to you')
        if len(receiver_offers) == 5:
            return await event.reply_exception('In this user have already 5 offers')
        await event.receiver.add_offer(event.current_user, redis)
        await event.forward()
        await event.success()

    @wsm.on_event('reject-offer')
    async def reject_offer_event(event: Event):
        if not event.receiver:
            return event.receiver_exc()
        redis: Redis = websocket.app.redis
        offers = await event.current_user.get_offers(redis)
        print(offers)
        if event.receiver.pk in offers:
            await redis.delete(f'offer:{event.receiver.pk}:{event.current_user.pk}')
            await event.forward()
            return await event.success()
        await event.reply_exception('You do not have this offer')

    @wsm.on_event('accept-offer')
    async def accept_offer_event(event: Event):
        redis: Redis = websocket.app.redis
        offers = await event.current_user.get_offers(redis)
        if event.receiver.pk in offers:
            await event.forward()
            return await event.success()

    await wsm.socket_run()
