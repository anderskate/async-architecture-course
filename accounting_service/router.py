import json
import random

from fastapi import APIRouter
from aiokafka import AIOKafkaConsumer
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import update
from sqlalchemy.future import select
from loguru import logger

from config import (
    loop, KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP, USER_KAFKA_TOPIC, TASK_KAFKA_TOPIC
)
from constants import UserEvents, TaskEvents
from models import User, Task, Transaction


route = APIRouter()

DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5434/accounting'

engine = create_async_engine(DATABASE_URL)



async def _create_transaction():
    pass

async def _hold_user_money():
    pass


async def _create_new_task(data):
    data.pop('id')

    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    user_query = select(User).where(User.public_id == data.get('user_id'))
    async with async_session() as session:
        result = await session.execute(user_query)
        user = result.scalar()
    if not user:
        return
    new_task = Task(
        public_id=data.get('public_id'),
        status=data.get('status'),
        description=data.get('description'),
        jira_id=data.get('jira_id'),
        user_id=user.id,
        retention_cost=random.randint(-20, -10),
        reward_cost=random.randint(20, 40),
    )

    # Should be in transaction
    async with async_session() as session:
        session.add(new_task)
        # Hold user money
        query = update(User).where(User.id == user.id).values(
            balance=user.balance + new_task.retention_cost)
        await session.execute(query)
        # Create transaction record
        new_transaction_record = Transaction(
            type=f'Hold user money - {new_task.retention_cost}, '
                 f'by task - {new_task.public_id}',
            user_id=user.id
        )
        session.add(new_transaction_record)
        await session.commit()
    logger.info(new_task)


async def _update_user(data: dict):
    data.pop('id')
    user_public_id = data.get('public_id')
    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    query = update(User).where(User.public_id == user_public_id).values(**data)
    async with async_session() as session:
        await session.execute(query)
        await session.commit()
    logger.info(data)


async def _create_new_user(data: dict):
    data.pop('id')

    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    new_user = User(**data)
    async with async_session() as session:
        session.add(new_user)
        await session.commit()
    logger.info(data)


async def _complete_task(data):
    task_public_id = data.get('public_id')

    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        task_query = select(Task).where(Task.public_id == data.get('public_id'))
        result_1 = await session.execute(task_query)
        task = result_1.scalar()

        user_query = select(User).where(
            User.id == task.user_id)
        result_2 = await session.execute(user_query)
        user = result_2.scalar()


        query = update(Task).where(Task.public_id == task_public_id).values(
            status='completed',
        )
        await session.execute(query)

        # Reward cost by user completed task
        query = update(User).where(User.id == user.id).values(
            balance=user.balance + task.reward_cost,
        )
        await session.execute(query)

        # Create transaction record
        new_transaction_record = Transaction(
            type=f'Reward user money - {task.reward_cost}, '
                 f'by task - {task.public_id}',
            user_id=user.id
        )
        session.add(new_transaction_record)

        await session.commit()


async def _assign_task(data: dict):
    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        task_query = select(Task).where(
            Task.public_id == data.get('public_id'))
        result_1 = await session.execute(task_query)
        task = result_1.scalar()

        user_query = select(User).where(
            User.public_id == data.get('user_id'))
        result_2 = await session.execute(user_query)
        user = result_2.scalar()

        if not user or not task:
            return

        # Change assigment
        query = update(Task).where(Task.id == task.id).values(
            user_id=user.id,
        )
        await session.execute(query)

        # Hold user money
        query = update(User).where(User.id == user.id).values(
            balance=user.balance + task.retention_cost,
        )
        await session.execute(query)

        # Create transaction record
        new_transaction_record = Transaction(
            type=f'Hold user money - {task.retention_cost}, '
                 f'by task - {task.public_id}',
            user_id=user.id
        )
        session.add(new_transaction_record)


async def consume_events():
    topics = (USER_KAFKA_TOPIC, TASK_KAFKA_TOPIC)

    streams_consumer = AIOKafkaConsumer(
        *topics, loop=loop,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        # group_id=KAFKA_CONSUMER_GROUP
    )
    await streams_consumer.start()

    events_map = {
        UserEvents.USER_CREATED.value: _create_new_user,
        UserEvents.USER_UPDATED.value: _update_user,
        TaskEvents.TASK_CREATED.value: _create_new_task,
        TaskEvents.TASK_COMPLETED.value: _complete_task,
        TaskEvents.TASK_ASSIGNED.value: _assign_task,
    }

    try:
        async for msg in streams_consumer:
            msg_value = json.loads(msg.value.decode('utf-8'))
            event_name = msg_value.get('event_name')
            event_data = msg_value.get('data')
            event_command = events_map.get(event_name)
            await event_command(event_data)
    finally:
        await streams_consumer.stop()
