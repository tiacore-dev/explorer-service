import re
from loguru import logger
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


def clean_html(html):
    """
    Удаляет лишние </div> внутри <td>, учитывая пробельные символы и переносы строк.
    """
    cleaned_html = re.sub(r'</div>\s*</td>', '</td>',
                          html, flags=re.IGNORECASE)
    return cleaned_html


def create_firefox_driver(headless: bool = True) -> webdriver.Firefox:
    try:
        options = Options()
        if headless:
            options.add_argument("--headless")

        # Установка стратегии загрузки страницы
        options.set_capability("pageLoadStrategy", "eager")

        # Отключаем уведомления
        options.set_preference("dom.webnotifications.enabled", False)

        driver = webdriver.Firefox(options=options)
        driver.set_page_load_timeout(15)

        logger.info("Драйвер Firefox успешно создан")
        return driver

    except Exception as e:
        logger.exception(f"Ошибка при создании драйвера Firefox^ {e}")
        raise
