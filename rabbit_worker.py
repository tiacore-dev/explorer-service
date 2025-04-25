# worker.py
import asyncio
from loguru import logger
from app.openai_funcs.assistant_runner import run_assistant_step
from app.rabbit import consume_tasks
from app.config import Settings

settings = Settings()

logger.add("worker.log", rotation="1 MB", encoding="utf-8")  # лог в файл


if __name__ == "__main__":
    asyncio.run(consume_tasks(settings.QUEUE_NAME, run_assistant_step))
