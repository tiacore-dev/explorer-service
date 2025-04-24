import time
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from app.utils.driver import create_firefox_driver


def fetch_url(url: str) -> dict:

    driver = create_firefox_driver()

    try:
        driver.get(url)
        time.sleep(2)  # Ждём загрузки

        # Скроллим до конца (ленивая подгрузка)
        scroll_height = driver.execute_script(
            "return document.body.scrollHeight")
        driver.execute_script(f"window.scrollTo(0, {scroll_height});")
        time.sleep(1)

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")

        # Заголовки
        headings = [h.get_text(strip=True)
                    for h in soup.find_all(["h1", "h2", "h3"])]

        # Текст (короткие блоки и параграфы)
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(
            "p") if len(p.get_text(strip=True)) > 50]

        # Цены (по шаблону ₽ / $ / €)
        prices = re.findall(r"[\d\s]+(?:₽|\$|€)", html)

        # Ссылки
        raw_links = [a.get("href") for a in soup.find_all("a", href=True)]
        absolute_links = list(
            {urljoin(url, link) for link in raw_links if link.startswith("/") or url in link})

        return {
            "url": url,
            "headings": headings,
            "text": paragraphs,
            "prices": prices,
            "links": absolute_links,
        }

    finally:
        driver.quit()
