import json
import uuid
from typing import Optional
from http import HTTPStatus

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import create_engine
from sqlalchemy.orm import class_mapper
from sqlalchemy_utils import database_exists, create_database
from flask_security import (
    Security, SQLAlchemyUserDatastore,
    UserMixin, RoleMixin
)
from flask_security.registerable import register_user
from flask_jwt_extended import (
    create_access_token, create_refresh_token, JWTManager
)
from flask_security.utils import verify_password
from flask import abort
from kafka import KafkaProducer
from flask_restful import Resource, Api, reqparse
from loguru import logger

from constants import UserEvents


app = Flask(__name__)
api = Api(app)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
app.config['CSRF_SESSION_KEY'] = 'fwegfrewgweg'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres@localhost:5432/auth'
app.config['SECURITY_PASSWORD_SALT'] = 'fe2rwgergrehe'
app.config['SECURITY_SEND_REGISTER_EMAIL'] = False
app.config['JWT_SECRET_KEY'] = 'erwgerwgrewg'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 1
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 24

jwt = JWTManager(app)


# Create database connection object
db = SQLAlchemy(app)


# Define models
roles_users = db.Table('roles_users',
     db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
     db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(
        UUID(as_uuid=True), default=uuid.uuid4,
    )
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    role = db.Column(db.String(255), default='admin')
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, role_model=None)
security = Security(app, user_datastore)


# Create a db with tables if not exists
@app.before_first_request
def create_user():
    engine = create_engine(
        "postgresql://postgres:postgres@localhost:5432/auth"
    )
    if not database_exists(engine.url):
        create_database(engine.url)
    db.create_all()
    db.session.commit()


def asdict(obj):
    """Convert sqlalchemy model objects to dict."""
    return dict(
        (col.name, getattr(obj, col.name))
        for col in class_mapper(obj.__class__).mapped_table.c
    )


# Set Kafka Producer
producer = KafkaProducer(bootstrap_servers=['localhost:9092'])


# Views
register_post_parser = reqparse.RequestParser()
register_post_parser.add_argument(
    "email", required=True, help="Email cannot be blank!"
)
register_post_parser.add_argument(
    "password", required=True, help="Password cannot be blank!"
)


class Register(Resource):
    """Endpoint to sign up."""

    def post(self):
        """Register a new user."""
        args = register_post_parser.parse_args()
        email = args.get("email")
        password = args.get("password")
        if User.query.filter_by(email=email).first():
            return abort(
                HTTPStatus.BAD_REQUEST, "This email address already exists!"
            )
        user = register_user(email=email, password=password)

        # Send event to Kafka that new user is created
        event = {
            'event_name': UserEvents.USER_CREATED.value, 'data': asdict(user)
        }
        producer.send(
            topic='users-stream',
            value=json.dumps(event, default=str).encode('utf-8')
        )
        logger.info(event)

        return {
            "msg": "Thank you for registering. "
                   "Now you can log in to your account.",
        }


login_post_parser = reqparse.RequestParser()
login_post_parser.add_argument(
    "email", required=True, help="Email cannot be blank!"
)
login_post_parser.add_argument(
    "password", required=True, help="Password cannot be blank!"
)
login_post_parser.add_argument("User-Agent", location="headers")


class Login(Resource):
    """Endpoint to user login."""

    def _authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Check user credentials - login and password.
        If credentials is correct return user object.
        """
        user = user_datastore.get_user(identifier=email)
        if not user:
            return None
        password_is_correct = verify_password(password, user.password)
        if not password_is_correct:
            return None
        return user

    def _get_user_tokens(self, user: User):
        """
        Get user tokens.
        save_refresh - save refresh token in redis
        save_log - save log for user login
        """

        access_token = create_access_token(
            identity=user.id, additional_claims={'permissions': 0}
        )
        refresh_token = create_refresh_token(identity=user.id)
        return {
            "access": access_token,
            "refresh": refresh_token,
        }

    def post(self):
        """Check user credentials and get JWT token for user."""

        args = login_post_parser.parse_args()

        error_message = "Email or password is incorrect"

        email = args.get("email")
        authenticated_user = self._authenticate_user(
            email=email, password=args.get("password")
        )
        if not authenticated_user:
            return abort(HTTPStatus.FORBIDDEN, error_message)

        return self._get_user_tokens(authenticated_user)


parser = reqparse.RequestParser()
parser.add_argument('role')


class ChangeUserRole(Resource):
    """Endpoint to change User role."""

    def patch(self, user_id):
        args = parser.parse_args()
        new_role = args.get('role')
        user = user_datastore.get_user(identifier=int(user_id))
        if not user:
            return {'info': 'User not found', 'status': 'error'}
        user.role = new_role
        db.session.commit()

        # Send event to Kafka that user role changed
        event = {
            'event_name': UserEvents.USER_UPDATED.value, 'data': asdict(user)
        }
        producer.send(
            topic='users-stream',
            value=json.dumps(event, default=str).encode('utf-8')
        )
        logger.info(event)
        return {'info': 'User role changed', 'status': 'ok'}


api.add_resource(Register, '/register')
api.add_resource(Login, '/logn')
api.add_resource(ChangeUserRole, '/users/<user_id>')


if __name__ == '__main__':
    app.run()
