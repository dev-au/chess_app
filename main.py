from aioredis import from_url
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from tortoise.contrib.fastapi import register_tortoise
from config import REDIS_URL
from data.models import User
from resources.auth import get_password_hash
from urls import urls
import routers

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

for router in urls:
    app.include_router(router)


@app.on_event("startup")
async def startup():
    redis = await from_url(REDIS_URL)
    app.redis = redis
    register_tortoise(
        app,
        db_url="sqlite://db.sqlite3",
        modules={"models": ["data.models"]},
        generate_schemas=True,
    )


@app.get('/init')
async def init_project():
    check_exists = await User.exists(username="admin")
    if check_exists:
        return {'ok': False}
    # Create Super Admin
    r = await User.create(
        username="admin",
        password=get_password_hash('1234qwer'),
        fullname='Abdulloh Umar',
        age=17,
        country='Uzbekistan',
        is_active=False,
        is_admin=True,
        is_super_admin=True,
    )
    return {'ok': True}
