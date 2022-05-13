import uuid

import sqlalchemy
from sqlalchemy.orm import relationship
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID


DATABASE_URL = 'postgresql://postgres:postgres@localhost:5433/tracker'


Base = declarative_base()


class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True)
    public_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    email = Column(String(255), unique=True)
    password = Column(String(255))
    active = Column(Boolean())
    confirmed_at = Column(DateTime())
    role = Column(String(255), default='admin')
    tasks = relationship('Task')


class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True)
    public_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    status = Column('status', String(255), server_default='assigned')
    description = Column(String(255))
    user_id = Column(Integer, ForeignKey('user.id'))


engine = sqlalchemy.create_engine(DATABASE_URL)
if not database_exists(engine.url):
    create_database(engine.url)
Base.metadata.create_all(engine)
