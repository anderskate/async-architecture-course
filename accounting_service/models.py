import uuid

import sqlalchemy
from sqlalchemy.orm import relationship, validates
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID


DATABASE_URL = 'postgresql://postgres:postgres@localhost:5434/accounting'


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
    balance = Column(Integer, default=0)
    tasks = relationship('Task')
    transactions = relationship('Transaction')


class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True)
    public_id = Column(UUID(as_uuid=True), default=uuid.uuid4)
    status = Column('status', String(255), server_default='assigned')
    description = Column(String(255))
    jira_id = Column(String(255), unique=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    retention_cost = Column(Integer)
    reward_cost = Column(Integer)

    @validates
    def validate_description(self, key, value):
        assert any(symbol in '[]' for symbol in value)
        return value


class Transaction(Base):
    __tablename__ = "transaction"
    id = Column(Integer, primary_key=True)
    type = Column(String(255))
    user_id = Column(Integer, ForeignKey('user.id'))


engine = sqlalchemy.create_engine(DATABASE_URL)
if not database_exists(engine.url):
    create_database(engine.url)
Base.metadata.create_all(engine)
