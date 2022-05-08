import json


from fastapi import APIRouter

from config import loop, KAFKA_BOOTSTRAP_SERVERS, KAFKA_CONSUMER_GROUP, KAFKA_TOPIC
from aiokafka import AIOKafkaConsumer

route = APIRouter()


async def consume():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC, loop=loop,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_CONSUMER_GROUP
    )
    await consumer.start()

    events_map = {
        'user_created': 'Create a new user',
        'user_role_updated': 'Update user role'
    }

    try:
        async for msg in consumer:
            msg_value = json.loads(msg.value.decode('utf-8'))
            event_name = msg_value.get('event_name')
            print(events_map.get(event_name))
    finally:
        await consumer.stop()
