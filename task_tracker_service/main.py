import asyncio
import random

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from fastapi.security import OAuth2PasswordBearer
from auth_jwt_lib.main import check_token


import router
from models import Task, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


DATABASE_URL = 'postgresql+asyncpg://postgres:postgres@localhost:5433/tracker'
engine = create_async_engine(DATABASE_URL)


app = FastAPI()


async def verify_token(
        jwt_token: str = Depends(oauth2_scheme),
):
    """Verify token with extended custom module - auth_jwt_lib."""
    try:
        check_token(jwt_token)
    except Exception as error:
        raise HTTPException(status_code=400, detail=str(error))


class TaskIn(BaseModel):
    description: str
    user_id: str


@app.post('/tasks', dependencies=[Depends(verify_token)])
async def create_new_task(task: TaskIn):
    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )

    query = select(User).where(User.public_id == task.user_id)
    async with async_session() as session:
        result = await session.execute(query)
        user = result.scalar()
        if not user:
            raise HTTPException(status_code=400, detail="User not found")

        new_task = Task(description=task.description, user_id=user.id)
        session.add(new_task)
        await session.commit()

    return {**task.dict()}


@app.patch('/tasks/{task_id}/complete', dependencies=[Depends(verify_token)])
async def complete_task(task_id: int):
    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    async with async_session() as session:
        task_query = select(Task).where(Task.id == task_id)
        result = await session.execute(task_query)
        task = result.scalar()
        if not task:
            raise HTTPException(status_code=400, detail="Task not found")

        query = update(Task).where(Task.id == task_id).values(
            status='completed')
        await session.execute(query)
        await session.commit()
    return {'info': 'task status updated', 'status': 'ok'}


@app.patch('/tasks/shuffle', dependencies=[Depends(verify_token)])
async def shuffle_all_tasks():
    async_session = sessionmaker(
        engine, expire_on_commit=False,
        class_=AsyncSession,
    )
    tasks_query = select(Task).where(Task.status == 'assigned')
    users_query = select(User)
    async with async_session() as session:
        tasks_result = await session.execute(tasks_query)
        tasks = tasks_result.all()
        users_result = await session.execute(users_query)
        users = users_result.all()

        for task in tasks:
            random_user = random.choice(users)[0]
            query = update(Task).where(
                Task.id == task[0].id
            ).values(user_id=random_user.id)
            await session.execute(query)
        await session.commit()

        return {'info': 'All tasks shuffled', 'status': 'ok'}


app.include_router(router.route)
asyncio.create_task(router.consume())
