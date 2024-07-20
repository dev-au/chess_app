from fastapi import HTTPException
from fastapi.responses import JSONResponse


class APIResponse(JSONResponse):
    def __init__(self, message, status_code=200, **kwargs):
        response = {'detail': {'message': message, 'data': kwargs}}
        super().__init__(response, status_code)


class APIException(HTTPException):
    def __init__(self, status_code: int, message: str):
        super().__init__(status_code, {'message': message, 'data': None})
