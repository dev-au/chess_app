from fastapi.templating import Jinja2Templates

render = Jinja2Templates(directory="templates").TemplateResponse

ACCESS_TOKEN_EXPIRE_DAYS = 30
SECRET_KEY = '8479676b92865fcadfe9aad1863ef10be8ec8489057a81ee7146878cdc19dde7'
ALGORITHM = 'HS256'

REDIS_URL = 'redis://localhost:6379/2'
