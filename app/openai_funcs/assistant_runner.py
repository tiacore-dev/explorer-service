from pathlib import Path
import json
import asyncio
from loguru import logger
from openai import AsyncOpenAI
from app.rabbit import publish_task
from app.config import Settings
from app.handlers.parsers import fetch_url

settings = Settings()

QUEUE_NAME = "site_analysis_tasks"

client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY
)
assistant_id = settings.ASSISTANT_ID


STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


def save_result(thread_id: str, data: dict):
    with open(STORAGE_DIR / f"{thread_id}.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_result(thread_id: str) -> dict:
    path = STORAGE_DIR / f"{thread_id}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


async def create_thread():
    try:
        thread = await client.beta.threads.create()
        logger.info(f"Создан новый поток: {thread.id}")
        return thread
    except Exception as e:
        logger.error(f"Ошибка при создании потока: {e}")
        return None


async def run_assistant_step(task_data: dict):
    thread_id = task_data["thread_id"]
    visited = set(task_data.get("visited", []))
    pending = task_data.get("pending", [])
    depth = task_data.get("depth", 0)
    max_depth = task_data.get("max_depth", 3)

    logger.info(
        f"[{thread_id}] Запуск шага. Depth={depth}, Visited={len(visited)}, Pending={len(pending)}")

    if not pending or depth >= max_depth:
        logger.info(
            f"[{thread_id}] Завершено. Достигнута глубина или закончились ссылки.")
        save_result(thread_id, task_data)
        return

    url = pending.pop(0)
    if url in visited:
        logger.warning(f"[{thread_id}] URL уже посещён: {url}")
        return

    logger.info(f"[{thread_id}] Анализируем страницу: {url}")

    await client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=f"Анализируй страницу: {url}")

    run = await client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    while True:
        run_status = await client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        logger.debug(f"[{thread_id}] Статус раннера: {run_status.status}")

        if run_status.status == "completed":
            logger.info(f"[{thread_id}] Ассистент завершил run")
            break

        elif run_status.status == "requires_action":
            logger.info(
                f"[{thread_id}] Run требует действия. Обрабатываем tool_call")

            tool_calls = run_status.required_action.submit_tool_outputs.tool_calls
            for tool in tool_calls:
                logger.debug(f"[{thread_id}] Tool call: {tool.function.name}")
                if tool.function.name == "fetch_url":
                    args = json.loads(tool.function.arguments)
                    target_url = args["url"]
                    logger.info(
                        f"[{thread_id}] Вызван fetch_url для: {target_url}")

                    result = fetch_url(target_url)
                    task_data["visited"].append(target_url)
                    task_data["data"].append(result)

                    new_links = [
                        l for l in result["links"]
                        if l not in task_data["visited"] and l not in pending
                    ]
                    if new_links:
                        logger.info(
                            f"[{thread_id}] Добавлены новые ссылки: {len(new_links)}")
                    else:
                        logger.info(f"[{thread_id}] Новые ссылки не найдены")

                    pending.extend(new_links)

                    await client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=[{
                            "tool_call_id": tool.id,
                            "output": json.dumps(result)
                        }]
                    )
            continue

        await asyncio.sleep(1)

    task_data["depth"] = depth + 1
    task_data["pending"] = pending
    logger.info(
        f"[{thread_id}] Завершение шага. Глубина увеличена до {task_data['depth']}")
    logger.info(f"[{thread_id}] Осталось ссылок в pending: {len(pending)}")

    save_result(thread_id, task_data)
    logger.info(f"[{thread_id}] Результат сохранён в файл.")

    await publish_task(QUEUE_NAME, task_data)
    logger.info(f"[{thread_id}] Задача повторно отправлена в очередь.")
