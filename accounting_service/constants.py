from enum import Enum


class UserEvents(Enum):
    USER_CREATED = 'user_created'
    USER_UPDATED = 'user_updated'


class TaskEvents(Enum):
    TASK_CREATED = 'task_created'
    TASK_ASSIGNED = 'task_assigned'
    TASK_COMPLETED = 'task_completed'
