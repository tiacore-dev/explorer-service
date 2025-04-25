import json
import aio_pika
from loguru import logger
from app.config import Settings


settings = Settings()

RABBIT_URL = f"amqp://{settings.RABBIT_USER}:{settings.RABBIT_PASS}@{settings.RABBIT_HOST}/"

logger.add("rabbit.log", rotation="1 MB", encoding="utf-8")  # лог в файл


async def get_connection():
    logger.info(f"🔌 Подключение к RabbitMQ по адресу: {RABBIT_URL}")
    connection = await aio_pika.connect_robust(RABBIT_URL)
    logger.success("✅ Успешно подключено к RabbitMQ")
    return connection


async def publish_task(queue_name: str, data: dict):
    logger.info(f"📤 Публикация задачи в очередь: {queue_name}")
    connection = await get_connection()
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(queue_name, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps(data).encode()),
            routing_key=queue.name
        )
    logger.success("✅ Задача опубликована")


async def consume_tasks(queue_name: str, callback):
    logger.info(f"📥 Запуск консюмера для очереди: {queue_name}")
    connection = await get_connection()
    channel = await connection.channel()
    queue = await channel.declare_queue(queue_name, durable=True)

    async with queue.iterator() as queue_iter:
        logger.info("🚀 Готов к приёму задач...")
        async for message in queue_iter:
            async with message.process():
                try:
                    data = json.loads(message.body)
                    logger.info(
                        f"📦 Получена задача: {data.get('thread_id', 'без ID')}")
                    await callback(data)
                    logger.success("✅ Задача обработана")
                except Exception as e:
                    logger.exception(f"❌ Ошибка обработки задачи: {e}")
