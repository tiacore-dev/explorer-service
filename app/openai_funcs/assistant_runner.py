import json
import asyncio
from loguru import logger
from openai import AsyncOpenAI
from app.rabbit import publish_task
from app.openai_funcs.summary import send_final_summary
from app.openai_funcs.save_load import save_result
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


def format_final_output(data: list, visited: list, pending: list, max_depth: int) -> str:
    output = [
        f"🌐 Обход завершён на глубине {max_depth}. Обработано страниц: {len(visited)}"]
    output.append("")

    for page in data:
        url = page.get("url", "")
        headings = page.get("headings", [])
        text = page.get("text", [])
        prices = page.get("prices", [])

        output.append(f"🔹 <{url}>")
        if headings:
            output.append("  ▫️ Заголовки:")
            for h in headings[:3]:
                output.append(f"    - {h}")

        if text:
            output.append("  ▫️ Тексты:")
            for p in text[:2]:
                output.append(
                    f"    - {p[:100]}{'...' if len(p) > 100 else ''}")

        if prices:
            output.append(
                f"  ▫️ Найдено {len(prices)} цен: {', '.join(prices[:3])}...")

        output.append("")  # Пустая строка между страницами

    output.append(
        f"🕸 Всего страниц в очереди на момент остановки: {len(pending)}")
    if pending:
        output.append("  Остались:")
        for p in pending[:5]:
            output.append(f"    - {p}")

    return "\n".join(output)


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
        save_result(
            thread_id,
            data=task_data["data"],
            visited=task_data["visited"],
            pending=task_data["pending"],
            max_depth=task_data["max_depth"]
        )

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
            tool_outputs = []

            for tool in tool_calls:
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

                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": json.dumps(result)
                    })

            # И только потом один вызов
            await client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run.id,
                tool_outputs=tool_outputs
            )

            continue

        await asyncio.sleep(1)

    task_data["depth"] = depth + 1
    task_data["pending"] = pending

    logger.info(
        f"[{thread_id}] Завершение шага. Глубина увеличена до {task_data['depth']}")
    logger.info(f"[{thread_id}] Осталось ссылок в pending: {len(pending)}")

    save_result(
        thread_id,
        data=task_data["data"],
        visited=task_data["visited"],
        pending=task_data["pending"],
        max_depth=task_data["max_depth"]
    )
    logger.info(f"[{thread_id}] Результат сохранён в файл.")

    # 👉 Если pending пустой — завершаем анализ
    if task_data["depth"] >= task_data["max_depth"]:
        await send_final_summary(
            thread_id=thread_id,
            data=task_data["data"],
            visited=task_data["visited"],
            pending=task_data["pending"],
            max_depth=task_data["max_depth"]
        )
        logger.info(
            f"[{thread_id}] Финальный ассистент вызван для подведения итогов.")
    else:
        await publish_task(settings.QUEUE_NAME, task_data)
        logger.info(f"[{thread_id}] Задача повторно отправлена в очередь.")
