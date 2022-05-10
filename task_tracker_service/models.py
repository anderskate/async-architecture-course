import uuid

import sqlalchemy
from sqlalchemy.dialects.postgresql import UUID

DATABASE_URL = 'postgresql://postgres:postgres@localhost:5433/tracker'


metadata = sqlalchemy.MetaData()


User = sqlalchemy.Table(
    "user",
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('public_id', UUID(as_uuid=True), default=uuid.uuid4),
    sqlalchemy.Column('email', sqlalchemy.String(255), unique=True),
    sqlalchemy.Column('password', sqlalchemy.String(255)),
    sqlalchemy.Column('active', sqlalchemy.Boolean()),
    sqlalchemy.Column('confirmed_at', sqlalchemy.DateTime()),
    sqlalchemy.Column('role', sqlalchemy.String(255), default='admin'),
)

Task = sqlalchemy.Table(
    "task",
    metadata,
    sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column('public_id', UUID(as_uuid=True), default=uuid.uuid4),
    sqlalchemy.Column('status', sqlalchemy.String(255)),
    sqlalchemy.Column('description', sqlalchemy.String(255)),
)

sqlalchemy.create_engine(DATABASE_URL)
