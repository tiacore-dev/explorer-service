from fastapi import APIRouter, Depends, HTTPException
from app.handlers.auth import check_api_key
from app.openai_funcs.assistant_runner import create_thread,  format_final_output, send_final_summary
from app.openai_funcs.save_load import save_result, load_result
from app.rabbit import publish_task
from app.config import Settings

settings = Settings()
# Создаем роутеры
explore_router = APIRouter()


@explore_router.post("/analyze_site")
async def analyze_site(site_url: str, max_depth: int, _=Depends(check_api_key)):
    thread = await create_thread()
    data = {
        "thread_id": thread.id,
        "visited": [],
        "pending": [site_url],
        "depth": 0,
        "max_depth": max_depth,
        "data": []
    }
    await publish_task(settings.QUEUE_NAME, data)
    return {"status": "started", "thread_id": thread.id}


@explore_router.get("/{thread_id}")
async def get_analysis(thread_id: str, _=Depends(check_api_key)):
    result = load_result(thread_id)

    if not result:
        return {"status": "processing", "message": "Анализ ещё не завершён"}

    response = {
        "summary": result.get("summary"),
        "final_message": format_final_output(
            data=result["data"],
            visited=result["visited"],
            pending=result["pending"],
            max_depth=result["max_depth"],
        ),
    }

    return response


@explore_router.get("/generate-summary/{thread_id}")
async def generate_summary(thread_id: str, _=Depends(check_api_key)):
    result = load_result(thread_id)

    if not result:
        raise HTTPException(
            status_code=404, detail="Результаты не найдены. Анализ ещё не завершён.")

    summary = await send_final_summary(
        thread_id=thread_id,
        data=result["data"],
        visited=result["visited"],
        pending=result["pending"],
        max_depth=result["max_depth"]
    )

    result["summary"] = summary
    save_result(
        thread_id,
        data=result["data"],
        visited=result["visited"],
        pending=result["pending"],
        max_depth=result["max_depth"],
        summary=summary
    )

    return {"summary": summary}
