from fastapi import APIRouter
from app.openai_funcs.assistant_runner import create_thread, load_result
from app.rabbit import publish_task

# Создаем роутеры
explore_router = APIRouter()


@explore_router.post("/analyze_site")
async def analyze_site(site_url: str):
    thread = await create_thread()
    data = {
        "thread_id": thread.id,
        "visited": [],
        "pending": [site_url],
        "depth": 0,
        "max_depth": 3,
        "data": []
    }
    await publish_task("site_analysis_tasks", data)
    return {"status": "started", "thread_id": thread.id}


@explore_router.get("/analyze_site/{thread_id}")
async def get_analysis(thread_id: str):
    result = load_result(thread_id)
    if not result:
        return {"status": "processing", "message": "Анализ ещё не завершён"}

    return {
        "status": "done",
        "thread_id": thread_id,
        "depth": result["depth"],
        "visited": result["visited"],
        "data": result["data"]
    }
