from datetime import datetime

import jwt
from fastapi import WebSocket
from jwt import InvalidTokenError
from starlette.websockets import WebSocketDisconnect

from config import SECRET_KEY, ALGORITHM
from data.models import User, Match

online_users = {}
ws_docs = {}


class Event:
    def __init__(self, event: str, task_id: int, websocket: WebSocket, current_user: User, receiver: User = None):
        self._event = event
        self._task_id = task_id
        self._websocket = websocket
        self.current_user = current_user
        self.receiver = receiver

    async def success(self):
        await self._websocket.send_json(
            {'event': self._event, 'task_id': self._task_id, 'forward_from': 'server', 'error': None, 'success': True})

    async def reply_exception(self, error):
        await self._websocket.send_json(
            {'event': self._event, 'task_id': self._task_id, 'forward_from': 'server', 'error': error})

    async def forward(self, **kwargs):
        receiver_user = self.receiver
        if not self.receiver:
            raise TypeError('Missing argument forward_to')
        if receiver_user.username not in online_users:
            return await self._websocket.send_json(
                {'event': self._event, 'task_id': self._task_id, 'forward_from': 'server',
                 'error': 'User is not online'})
        receiver_web = online_users[receiver_user.username]
        await receiver_web.websocket.send_json(
            {'event': self._event, 'task_id': self._task_id, 'forward_from': self.current_user.username, 'error': None,
             **kwargs}
        )

    async def receiver_exc(self):
        await self.reply_exception('You must give receiver user')


class WsManager:
    websocket: WebSocket
    _current_user: User
    viewing_matches = []
    _ws_routes = {}

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def socket_run(self):
        await self.websocket.accept()
        is_authenticated = await self._check_auth()
        if not is_authenticated:
            return await self.websocket.close(code=1008, reason="Not authenticated")
        await self._current_user.update_status(online=True)
        online_users[self._current_user.username] = self
        try:
            while True:
                data: dict = await self.websocket.receive_json()
                is_authenticated = await self._check_auth()
                if not is_authenticated:
                    return await self._socket_break('Not authenticated')
                if 'event' not in data:
                    return await self._socket_break('Missing field: event')
                if 'task_id' not in data:
                    return await self._socket_break('Missing field: task_id')
                if not isinstance(data['task_id'], int):
                    return await self._socket_break('task_id must be an integer')
                if data['event'] in self._ws_routes:
                    handler = self._ws_routes[data['event']]
                    details = data.copy()
                    details.pop('event')
                    details.pop('forward_to', None)
                    details.pop('task_id')
                    if 'forward_to' in data:
                        if not isinstance(data['forward_to'], str):
                            return await self._socket_break('Receiver username must be str')
                        receiver_user = await User.get_or_none(username=data['forward_to'])
                        if not receiver_user:
                            return await self._socket_break('User not found')
                        await handler(details, data['task_id'], receiver_user)
                    else:
                        await handler(details, data['task_id'])
        except WebSocketDisconnect:
            return await self._socket_break('Socket Disconnect')

    async def _socket_break(self, reason):
        online_users.pop(self._current_user.username)

        if self._current_user.playing_now:
            playing_match = await Match.get_or_none(white_player=self._current_user) or await Match.get_or_none(
                black_player=self._current_user)
            if playing_match.white_player != self._current_user.pk:
                player2: WsManager = online_users[(await playing_match.white_player.get()).username]
                playing_match.winner = 1
            else:
                player2 = online_users[(await playing_match.black_player.get()).username]
                playing_match.winner = 2
            playing_match.finished_at = datetime.now()
            player2._current_user.all_games += 1
            player2._current_user.wins += 1
            self._current_user.all_games += 1
            self._current_user.losses += 1
            await playing_match.save()
            await player2._current_user.save()
            await self._current_user.save()
            await player2.websocket.send_json(
                {'event': 'player-offline', 'task_id': 0, 'forward_from': self._current_user.username, 'error': None}
            )

        await self._current_user.update_status(offline=True)
        try:
            await self.websocket.close(reason=reason)
        except RuntimeError:
            pass

    async def _check_auth(self) -> User:
        headers = self.websocket.headers
        access_token = headers.get('Authorization')
        try:
            payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                return False
        except InvalidTokenError:
            return False
        user = await User.get_or_none(username=username)
        if user is None:
            return False
        self._current_user = user
        return True

    def on_event(self, event: str):
        def wrapper(func):
            if len(online_users) == 0:
                ws_docs[func.__name__] = func.__annotations__
                ws_docs[func.__name__].pop('event')
                ws_docs[func.__name__].update({'event': str, 'task_id': int, 'forward_to': str})

            async def decorated(json_data, task_id: int, receiver: User = None):
                # try:
                await func(event=Event(event, task_id, self.websocket, self._current_user, receiver), **json_data)
                # except TypeError as e:
                #     await self.websocket.send_json(
                #         {'event': event, 'task_id': task_id, 'forward_from': 'server', 'error': str(e)})

            self._ws_routes[event] = decorated
            return decorated

        return wrapper
