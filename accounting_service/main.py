import asyncio
import random
import json

from fastapi import FastAPI, HTTPException, Depends
from kafka import KafkaProducer
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import class_mapper
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from auth_jwt_lib.main import check_token
from loguru import logger
from schema_registry_lib.schema_registry import SchemaRegistry


import router
from models import Task, User
from constants import TaskEvents

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5434/accounting'
engine = create_async_engine(DATABASE_URL)


# Set Kafka Producer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'])


def asdict(obj):
    """Convert sqlalchemy model objects to dict."""
    return dict(
        (col.name, getattr(obj, col.name))
        for col in class_mapper(obj.__class__).mapped_table.c
    )


app = FastAPI()


async def verify_token(
        jwt_token: str = Depends(oauth2_scheme),
):
    """Verify token with extended custom module - auth_jwt_lib."""
    try:
        check_token(jwt_token)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))

schema = SchemaRegistry()


@app.get('/main', dependencies=[Depends(verify_token)])
async def create_new_task():
    return 'ok'


app.include_router(router.route)

asyncio.create_task(router.consume_events())

