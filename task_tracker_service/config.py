import asyncio

# env Variable
KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092"
KAFKA_TOPIC = "users-stream"
KAFKA_CONSUMER_GROUP = "group-id"

loop = asyncio.get_event_loop()
