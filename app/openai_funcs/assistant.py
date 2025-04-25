import asyncio
import json
from openai import AsyncOpenAI
from loguru import logger
from app.config import Settings
from app.handlers.parsers import fetch_url

settings = Settings()

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY
)
assistant_id = settings.ASSISTANT_ID


async def create_thread():
    try:
        thread = await client.beta.threads.create()
        logger.info(f"Создан новый поток: {thread.id}")
        return thread
    except Exception as e:
        logger.error(f"Ошибка при создании потока: {e}")
        return None


async def create_run(user_input, thread_id):
    logger.info(
        f"Запуск нового рана для пользователя  в потоке {thread_id}")
    try:
        await client.beta.threads.messages.create(
            thread_id=thread_id, role="user", content=user_input)

        run = await client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
        )

        while True:
            run_status = await client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run.id)

            if run_status.status == "completed":
                messages = await client.beta.threads.messages.list(thread_id=thread_id)
                response = next(
                    (msg.content[0].text.value for msg in messages.data if msg.role == "assistant"),
                    "Ассистент не вернул ответ."
                )

                break

            elif run_status.status == "requires_action":
                tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
                for tool in tool_calls:
                    if tool.function.name == "fetch_url":
                        args = json.loads(tool.function.arguments)
                        logger.info(
                            f"Ассистент вызвал fetch_url с аргументами: {args}")
                        url = args["url"]
                        result = fetch_url(url)  # ← вызов функции
                        await client.beta.threads.runs.submit_tool_outputs(
                            thread_id=thread_id,
                            run_id=run.id,
                            tool_outputs=[{
                                "tool_call_id": tool.id,
                                "output": json.dumps(result, ensure_ascii=False)
                            }]
                        )
                continue

            elif run_status.status == "in_progress":
                logger.debug("Run in progress...")

            elif run_status.status == "incomplete":
                logger.info("Run is incomplete. Retrying...")

            else:
                logger.warning(f"Неизвестный статус рана: {run_status.status}")

            await asyncio.sleep(1)

        return response

    except Exception as e:
        logger.exception(f"Ошибка в run: {e}")
        return "Произошла ошибка при обработке."
