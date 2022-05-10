import json

from fastapi import APIRouter
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import create_async_engine
from loguru import logger

from config import (
    loop, KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP, USER_KAFKA_TOPIC,
)
from constants import UserEvents
from models import User


route = APIRouter()

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5433/tracker'

engine = create_async_engine(DATABASE_URL)


async def _update_user(data: dict):
    data.pop('id')
    user_public_id = data.get('public_id')
    async with engine.begin() as connection:
        query = User.update().where(
            User.c.public_id == user_public_id
        ).values(**data)
        await connection.execute(query)
        logger.info(data)


async def _create_new_user(data: dict):
    data.pop('id')
    async with engine.begin() as connection:
        query = User.insert().values(**data)
        await connection.execute(query)
        logger.info(data)


async def consume():
    user_streams_consumer = AIOKafkaConsumer(
        USER_KAFKA_TOPIC, loop=loop,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP
    )
    await user_streams_consumer.start()

    user_events_map = {
        UserEvents.USER_CREATED.value: _create_new_user,
        UserEvents.USER_UPDATED.value: _update_user,
    }

    try:
        async for msg in user_streams_consumer:
            msg_value = json.loads(msg.value.decode('utf-8'))
            event_name = msg_value.get('event_name')
            event_data = msg_value.get('data')
            event_command = user_events_map.get(event_name)
            await event_command(event_data)
    finally:
        await user_streams_consumer.stop()
