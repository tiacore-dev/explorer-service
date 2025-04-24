# rabbit.py
import json
import aio_pika


RABBIT_URL = "amqp://guest:guest@localhost/"

QUEUE_NAME = "site_analysis_tasks"


async def get_connection():
    return await aio_pika.connect_robust(RABBIT_URL)


async def publish_task(queue_name: str, data: dict):
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(data).encode()),
            routing_key=queue.name
        )


async def consume_tasks(queue_name: str, callback):
    connection = await get_connection()
    channel = await connection.channel()
    queue = await channel.declare_queue(queue_name, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                data = json.loads(message.body)
                await callback(data)
