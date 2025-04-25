from pathlib import Path
import json

STORAGE_DIR = Path("storage")
STORAGE_DIR.mkdir(exist_ok=True)


def save_result(thread_id: str, data, visited, pending, max_depth, summary: str = None):
    result = {
        "data": data,
        "visited": visited,
        "pending": pending,
        "max_depth": max_depth,
    }
    if summary:
        result["summary"] = summary

    with open(f"storage/{thread_id}.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def load_result(thread_id: str) -> dict:
    path = STORAGE_DIR / f"{thread_id}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
