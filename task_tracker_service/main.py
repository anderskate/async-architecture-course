import asyncio
import databases

from fastapi import FastAPI
import sqlalchemy
from sqlalchemy_utils import database_exists, create_database

import router

DATABASE_URL = 'postgresql://postgres:postgres@localhost:5433/tracker'
database = databases.Database(DATABASE_URL)

metadata = sqlalchemy.MetaData()
engine = sqlalchemy.create_engine(DATABASE_URL)

if not database_exists(engine.url):
    create_database(engine.url)
metadata.create_all(engine)


app = FastAPI()


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get('/')
async def Home():
    return "welcome home"

app.include_router(router.route)
asyncio.create_task(router.consume())


