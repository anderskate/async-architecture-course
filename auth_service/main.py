import json
import pickle
from typing import Optional

from http import HTTPStatus

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_security import Security, SQLAlchemyUserDatastore, \
    UserMixin, RoleMixin, login_required
from flask_security.registerable import register_user
from flask_jwt_extended import create_access_token, create_refresh_token, decode_token, JWTManager
from flask_security.utils import hash_password, verify_password
from flask import abort
from kafka import KafkaProducer

from flask_restful import Resource, Api, reqparse


# Create task_tracker_service
app = Flask(__name__)
api = Api(app)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'super-secret'
app.config['CSRF_SESSION_KEY'] = 'fwegfrewgweg'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
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
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))


# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)


# Create a user to test with
@app.before_first_request
def create_user():
    db.create_all()
    user_datastore.create_user(email='andrey@mail.ru', password='password')
    db.session.commit()

# Views


register_post_parser = reqparse.RequestParser()
register_post_parser.add_argument("email", required=True, help="Email cannot be blank!")
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
            return abort(HTTPStatus.BAD_REQUEST, "This email address already exists!")
        register_user(email=email, password=password)

        event = {
            'event_name': 'user_created',
            'data': {
                'public_id': '43432',
                'email': 'and3re@mail.ru',
                'full_name': 'Andre3y Star',
                'role': 'admin13'
            }
        }
        producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
        producer.send(
            topic='users-stream', value=json.dumps(event).encode('utf-8')
        )
        # TODO Send event to Kafka that new user is created

        return {
            "msg": "Thank you for registering. Now you can log in to your account.",
        }

login_post_parser = reqparse.RequestParser()
login_post_parser.add_argument("email", required=True, help="Email cannot be blank!")
login_post_parser.add_argument(
    "password", required=True, help="Password cannot be blank!"
)
login_post_parser.add_argument("User-Agent", location="headers")


class Login(Resource):
    """Endpoint to user login."""

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
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

    def get_user_tokens(
            self, user: User,
            user_agent: Optional[str] = None,
            save_refresh: bool = True,
            save_log: bool = True
    ):
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
        authenticated_user = self.authenticate_user(
            email=email, password=args.get("password")
        )
        if not authenticated_user:
            return abort(HTTPStatus.FORBIDDEN, error_message)

        return self.get_user_tokens(
            authenticated_user, args.get("User-Agent")
        )


api.add_resource(Register, '/register')
api.add_resource(Login, '/logn')


if __name__ == '__main__':
    app.run()
