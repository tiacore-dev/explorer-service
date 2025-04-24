# worker.py
import asyncio
from app.openai_funcs.assistant_runner import run_assistant_step
from app.rabbit import consume_tasks, QUEUE_NAME

if __name__ == "__main__":
    asyncio.run(consume_tasks(QUEUE_NAME, run_assistant_step))
