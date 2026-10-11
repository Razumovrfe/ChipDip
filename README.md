# ChipDip Telegram Bot

Telegram-бот для поиска, просмотра и мониторинга цен на [chipdip.by](https://www.chipdip.by).

## Возможности

- `/search <запрос>` — поиск товаров (до 10 на страницу, до 5 страниц, inline-пагинация)
- `/info <url>` — карточка товара: артикул, цена, наличие, описание, характеристики
- `/track <url> <порог>` — мониторинг цены; уведомление, когда цена опускается ниже порога
- `/mytracks` — список отслеживаемых товаров с кнопкой удаления
- `/categories` — дерево каталога с навигацией и списком товаров
- `/start`, `/help` — справка

После `/start` доступно меню: **Поиск**, **Категории**, **Мои треки**, **Помощь**. Поиск можно начать и текстом запроса, без команды.

Мониторинг запускается по расписанию (по умолчанию каждые 30 минут), проверяет активные треки и пишет историю цен. Уведомление приходит один раз за снижение ниже порога и сбрасывается, когда цена снова поднимается. После 5 ошибок подряд или если товар снят с сайта трек деактивируется, пользователь получает сообщение.

## Стек

- Python 3.10+, aiogram 3.x
- Парсер: httpx + BeautifulSoup4, fallback — undetected-chromedriver
- БД: SQLite + aiosqlite
- Планировщик: APScheduler (`AsyncIOScheduler`)
- Логи: loguru
- Конфиг: pydantic-settings + `.env`
- Контейнеризация: Docker + docker-compose

## Архитектура парсера

Карточки товаров, результаты поиска и каталог chipdip.by отдаются статическим HTML, поэтому основной путь — `httpx` + BeautifulSoup. Selenium (undetected-chromedriver) включается только если httpx заблокирован: HTTP 403/429/503 или пустой ответ. Поисковый параметр — `searchtext`. Скачанный HTML кешируется в SQLite на 1 час.

## Структура проекта

```
bot/
├─ __main__.py          # polling и планировщик
├─ bot.py               # Bot, Dispatcher, обработчик ошибок
├─ config.py            # Settings (pydantic-settings)
├─ logging_config.py    # sinks loguru
├─ fsm.py               # состояния FSM
├─ keyboards.py         # reply-меню и inline-клавиатуры
├─ formatters.py        # HTML-рендер карточек и списков
├─ monitoring.py        # проверка треков
├─ db/                  # schema.sql, connection.py, repo.py
├─ parser/              # service, http_client, selenium_worker, cache, pages/
└─ routers/             # start, search, info, track, mytracks, categories
tests/                  # HTML-фикстуры и unit-тесты
Dockerfile
docker-compose.yml
requirements.txt
```

## Запуск локально

```bash
python -m venv .venv
```

Windows (PowerShell):

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m bot
```

Linux / macOS:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m bot
```

В `.env` нужен `TELEGRAM_BOT_TOKEN`.

## Запуск через Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f
```

Образ ставит Chromium для Selenium-fallback. База и логи лежат в volume `./data`.

## Конфигурация

| Переменная | По умолчанию | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | токен бота |
| `CHIPDIP_URL` | `https://www.chipdip.by` | базовый URL |
| `CHECK_INTERVAL_MINUTES` | `30` | интервал мониторинга |
| `MAX_SEARCH_PAGES` | `5` | максимум страниц поиска |
| `REQUEST_DELAY_SECONDS` | `3` | пауза между запросами к сайту |
| `PARSER_TIMEOUT_SECONDS` | `15` | таймаут запроса |
| `PARSER_MAX_RETRIES` | `3` | число повторов |
| `USE_SELENIUM_FALLBACK` | `true` | Selenium, если httpx заблокирован |
| `MAX_TRACKS_PER_USER` | `50` | лимит треков на пользователя |
| `CACHE_TTL_SECONDS` | `3600` | TTL кеша HTML |
| `DATABASE_PATH` | `./data/bot.db` | путь к БД |
| `LOG_LEVEL` | `INFO` | уровень логов |
| `LOG_DIR` | `./data/logs` | каталог логов |

Шаблон — `.env.example`. Файл `.env` в репозиторий не попадает.

## Тесты

```bash
pip install -r requirements-dev.txt
pytest -q
```

Парсеры проверяются на HTML-фикстурах из `tests/fixtures/`, репозиторий — на in-memory SQLite.

## Логи

- DEBUG пишется в `data/logs/bot.log` (ротация 5 МБ, 10 файлов)
- INFO выводится в консоль
