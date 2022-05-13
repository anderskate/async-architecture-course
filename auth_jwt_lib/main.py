import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidSignatureError


def check_token(token, valid_perms=('admin', 'manager')) -> dict:
    """Simple checking jwt token."""
    if not token:
        raise Exception('No token')
    try:
        token_info = jwt.decode(
            token, key='erwgerwgrewg', algorithms=['HS256']
        )
    except InvalidSignatureError:
        raise Exception('Incorrect Token')
    except ExpiredSignatureError:
        raise Exception('Token expired')
    permission = token_info.get('role')
    if permission not in valid_perms:
        raise Exception('Forbidden')
    return token_info


if __name__ == '__main__':
    token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY1MjI1MzkxMiwianRpIjoiOTk1OTYxODMtYzAyOS00MjViLTkxM2EtZTM3NjU4ZWY3YTY5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6MzAsIm5iZiI6MTY1MjI1MzkxMiwiZXhwIjoxNjUyMjU0MjEyLCJyb2xlIjoiYWRtaW4ifQ.5uTq9oJrNHdwKfIfoX4QQfS3rlvWn0t0dhUre5TvEE8'
    perms = ['admin', 'manager']
    print(check_token(token, perms))
