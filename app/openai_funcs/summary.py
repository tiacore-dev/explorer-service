import json
from app.openai_funcs.save_load import save_result
from app.openai_funcs.assistant import create_run


def build_summary_prompt(data: list, visited: list, _, max_depth: int) -> str:
    prompt = [
        "Проведи анализ сайта на основе полученной информации.",
        f"Обошли {len(visited)} страниц, максимум глубины — {max_depth}.",
        "Вот собранные данные:\n"
    ]

    for page in data[:10]:  # Ограничим до 10 страниц
        prompt.append(f"\n=== Страница: {page['url']} ===")

        if page["headings"]:
            prompt.append(f"\nЗаголовки: {', '.join(page['headings'][:5])}")

        if page["text"]:
            text = ' '.join(page["text"][:3])
            prompt.append(f"\nКлючевой текст: {text[:500]}...")

        if page["prices"]:
            prompt.append(f"\nЦены: {', '.join(page['prices'][:5])}")

        if page["links"]:
            prompt.append(f"\nСсылки: {', '.join(page['links'][:3])}...")

    prompt.append("\nСформируй краткое резюме:")
    prompt.append("1. Что предлагает сайт?")
    prompt.append("2. Какие уникальные особенности/услуги?")
    prompt.append("3. Есть ли цены? Какие?")
    prompt.append("4. Уровень доверия и отзывы?")
    prompt.append("5. Общие плюсы и минусы?")
    prompt.append("6. Что можно улучшить или автоматизировать?")

    return '\n'.join(prompt)


async def send_final_summary(thread_id: str, data, visited, pending, max_depth):
    prompt = f"""Вот собранные данные с сайта. Сформулируй краткий анализ: какие услуги предлагает сайт, на что делает упор, какова структура, что можно сказать о текстах и ценах.

    Данные:
    Visited: {len(visited)} страниц
    Max Depth: {max_depth}
    Контент:
    {json.dumps(data, ensure_ascii=False, indent=2)}
    """
    summary = await create_run(prompt, thread_id)

    save_result(
        thread_id,
        data=data,
        visited=visited,
        pending=pending,
        max_depth=max_depth,
        summary=summary
    )

    return summary
