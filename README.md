# Проект № 3 по дисциплине: "Прикладной Python"

[![CI](https://github.com/tolikStalker/HSE-URL-Shortener/actions/workflows/ci.yml/badge.svg)](https://github.com/tolikStalker/HSE-URL-Shortener/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)]()

## Создание веб-сервиса для сокращения ссылок (URL Shortener)

### Описание

REST API веб-сервис для сокращения ссылок. Позволяет пользователям превращать длинные URL-адреса в короткие, собирать статистику переходов и управлять своими ссылками.

**Основные возможности:**

- Генерация коротких ссылок (случайный ID или пользовательский `alias`).
- Редирект с короткой ссылки на оригинальную с подсчетом кликов.
- Указание времени жизни ссылки (после истечения она недоступна).
- Сбор статистики: количество переходов, дата последнего использования.
- Регистрация и авторизация пользователей (JWT токены).
- Фоновая очистка истекших и давно не используемых ссылок.
- Кэширование частых запросов с использованием Redis для быстрого редиректа.

---

### Технологический стек

- **Backend:** FastAPI, Python 3.12, Uvicorn
- **ORM & DB:** SQLAlchemy 2.0+ (Async, Mapped), PostgreSQL 17, Alembic (миграции)
- **Кэширование:** Redis 7
- **Авторизация:** JWT (PyJWT), хеширование паролей bcrypt (pwdlib)
- **Тестирование:** pytest, httpx, pytest-asyncio, pytest-mock, coverage, pytest-xdist
- **Нагрузочное тестирование:** Locust
- **Линтинг:** ruff
- **Инфраструктура:** Docker, Docker Compose, uv (пакетный менеджер)
- **CI/CD:** GitHub Actions

---

### Переменные окружения

Все настройки задаются через файл `.env`. Описание каждой переменной:

| Переменная                    | Описание                                                            | Значение по умолчанию                                                     |
| ----------------------------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `DATABASE_URL`                | URL подключения к PostgreSQL (asyncpg)                              | `postgresql+asyncpg://shortener:shortener_secret@postgres:5432/shortener` |
| `REDIS_URL`                   | URL подключения к Redis                                             | `redis://redis:6379/0`                                                    |
| `SECRET_KEY`                  | Секретный ключ для подписи JWT токенов (минимум 32 символа).        | `your-super-puper-secret-key-that-min-32-chars`                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни JWT токена (в минутах)                                  | `60`                                                                      |
| `CLEANUP_UNUSED_DAYS`         | Через сколько дней неиспользования ссылка автоматически удаляется   | `30`                                                                      |
| `CACHE_TTL`                   | Время жизни кэша Redis (в секундах)                                 | `300`                                                                     |
| `BASE_URL`                    | Базовый URL сервиса (используется для формирования коротких ссылок) | `http://localhost:8000`                                                   |

---

### Инструкция по запуску

#### Запуск через Docker

Убедитесь, что у вас установлен `Docker` и `Docker Compose`.

1. Клонируйте репозиторий и перейдите в папку с проектом:

```bash
git clone https://github.com/tolikStalker/HSE-URL-Shortener.git
cd HSE-URL-Shortener
```

2. Создайте файл `.env` в корне проекта на основе `.env_example`.

```bash
cp .env_example .env
```

3. Запустите сервисы:

```bash
docker compose up --build -d
```

Миграции БД применяются автоматически при старте контейнера.

4. Проверьте, что сервис работает:

```bash
curl http://localhost:8000/health
# Ответ: {"status":"ok"}
```

Сервис будет доступен по адресу: `http://localhost:8000`

Swagger UI (интерактивная документация): **http://localhost:8000/docs**

**Остановка:**

```bash
docker compose down
```

**Остановка с удалением данных (volumes):**

```bash
docker compose down -v
```

---

### Фоновые задачи

Сервис автоматически запускает фоновую задачу очистки ссылок (каждые 10 минут):

- **Истекшие ссылки** — удаляются ссылки, у которых `expires_at` в прошлом.
- **Неиспользуемые ссылки** — удаляются ссылки, по которым не было переходов в течение `CLEANUP_UNUSED_DAYS` дней (по умолчанию 30).

Кэш удалённых ссылок автоматически инвалидируется.

---

### Описание базы данных

Проект использует базу данных **PostgreSQL**.
Структура состоит из двух основных таблиц:

1. **`users` (Пользователи)**
    - `id` (UUID, Primary Key)
    - `username`, `email` (Уникальные строки)
    - `hashed_password` (Строка)
    - `created_at` (Дата и время регистрации)
2. **`links` (Ссылки)**
    - `id` (UUID, Primary Key)
    - `short_code` (Строка, Уникальный индекс) - сама короткая ссылка
    - `original_url` (Текст) - оригинальный длинный URL
    - `owner_id` (UUID, Foreign Key) - связь с таблицей `users` (nullable — для анонимных ссылок)
    - Сбор статистики: `click_count` (int), `last_used_at` (datetime)
    - Жизненный цикл: `created_at`, `expires_at`

#### ER-диаграмма

```mermaid
erDiagram
    users {
        UUID id PK
        VARCHAR(50) username UK
        VARCHAR(255) email UK
        VARCHAR(255) hashed_password
        TIMESTAMP created_at
    }

    links {
        UUID id PK
        VARCHAR(20) short_code UK
        TEXT original_url
        UUID owner_id FK
        INTEGER click_count
        TIMESTAMP created_at
        TIMESTAMP expires_at
        TIMESTAMP last_used_at
    }

    users ||--o{ links : "owner_id"
```

Миграции управляются с использованием **Alembic**.

---

### Тестирование

Тесты организованы в три категории:

```
tests/
├── conftest.py                      # Общие fixture (SQLite in-memory DB, mock Redis)
├── unit/                            # Юнит-тесты (изолированные, без БД)
│   ├── test_app_components.py       # database.get_db, Redis lifecycle, auth dependencies
│   ├── test_cache_service.py        # CacheService (Redis операции)
│   ├── test_cleanup_service.py      # Очистка истёкших/неиспользуемых ссылок
│   ├── test_code_generation.py      # Генератор коротких кодов
│   ├── test_link_service.py         # LinkService (вся бизнес-логика)
│   ├── test_main.py                 # lifespan, periodic_cleanup
│   └── test_user_service.py         # UserService (регистрация, аутентификация)
├── integration/                     # Интеграционные тесты (HTTP через AsyncClient)
│   ├── test_auth_endpoints.py       # /auth/register, /auth/login + валидация входных данных
│   ├── test_error_handling.py       # Обработка ошибок (404, 410, 403, 401)
│   ├── test_links_endpoints.py      # /links/* (CRUD, поиск, статистика)
│   ├── test_redirect_endpoints.py   # Редиректы, клики, expired ссылки
│   └── test_security.py             # SQLi, XSS, path traversal, невалидные URL
└── load/                            # Нагрузочные тесты
    └── locustfile.py
```

#### Запуск тестов

```bash
# Все тесты
uv run pytest tests -v

# Только юнит-тесты
uv run pytest tests/unit -v -m unit

# Только интеграционные тесты
uv run pytest tests/integration -v -m integration

# Только тесты безопасности
uv run pytest tests/integration/test_security.py -v

# С отчётом о покрытии
uv run coverage run -m pytest tests
uv run coverage report -m
uv run coverage html  # HTML-отчёт в папке htmlcov/
```

#### Покрытие

Текущее покрытие кода: **100%**

Визуализированный HTML-отчёт о покрытии доступен в папке `htmlcov/`.

| Модуль          | Покрытие |
| --------------- | -------- |
| `app/api/`      | 100%     |
| `app/services/` | 100%     |
| `app/auth/`     | 100%     |
| `app/models/`   | 100%     |
| `app/redis.py`  | 100%     |
| `app/main.py`   | 100%     |

#### Нагрузочное тестирование (Locust)

Запускается против работающего экземпляра приложения (например, Docker):

```bash
# Запустить приложение в Docker
docker compose up -d

# Запустить Locust (откроет веб-интерфейс на http://localhost:8089)
uv run locust -f tests/load/locustfile.py --host http://localhost:8000
```

Локаст тестирует: регистрацию/логин, создание ссылок, редиректы, поиск, health-check.

Рекомендуемые этапы нагрузочного тестирования:

| Этап        | Пользователи | Spawn rate | Продолжительность |
| ----------- | ------------ | ---------- | ----------------- |
| Smoke Test  | 10           | 1          | 2-5 мин           |
| Load Test   | 50-100       | 5          | 10 мин            |
| Stress Test | 200-500      | 10-20      | до деградации     |

---

### Описание API и примеры запросов

Полная интерактивная документация (Swagger UI) доступна после запуска по адресу:
**http://localhost:8000/docs**

#### 1. Регистрация и Авторизация

_Зарегистрированные пользователи могут изменять и удалять свои ссылки._

##### Регистрация

- `POST /auth/register` — регистрация нового пользователя.

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "mysecretpassword"
  }'
```

Ответ (`201 Created`):

```json
{
	"id": "550e8400-e29b-41d4-a716-446655440000",
	"username": "testuser",
	"email": "test@example.com",
	"created_at": "2026-03-09T12:00:00Z"
}
```

##### Логин

- `POST /auth/login` — получение JWT токена.

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=testuser&password=mysecretpassword'
```

Ответ (`200 OK`):

```json
{
	"access_token": "eyJhbGciOiJIUzI1NiIs...",
	"token_type": "bearer"
}
```

> Сохраните `access_token` — он используется в заголовке `Authorization: Bearer <token>` для защищённых эндпоинтов.

#### 2. Работа со ссылками

Аутентификация для создания не обязательна (создастся анонимная ссылка).

##### Создание короткой ссылки

- `POST /links/shorten` — создать короткую ссылку (аутентификация **необязательна**).

**Простое создание (анонимно):**

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H 'Content-Type: application/json' \
  -d '{"original_url": "https://example.com/very/long/url"}'
```

**Создание с кастомным alias и временем жизни (авторизованный пользователь):**

```bash
curl -X POST http://localhost:8000/links/shorten \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <ваш_токен>' \
  -d '{
    "original_url": "https://google.com/",
    "custom_alias": "my-google-123",
    "expires_at": "2026-12-31T23:59:00Z"
  }'
```

Ответ (`201 Created`):

```json
{
	"id": "...",
	"short_code": "my-google-123",
	"short_url": "http://localhost:8000/my-google-123",
	"original_url": "https://google.com/",
	"created_at": "2026-03-09T12:00:00Z",
	"expires_at": "2026-12-31T23:59:00Z"
}
```

Параметры `custom_alias` и `expires_at` **опциональны**. Alias должен содержать только `a-z`, `A-Z`, `0-9`, `_`, `-` (от 3 до 20 символов).

---

##### Редирект по короткой ссылке

- `GET /{short_code}` — перенаправляет на оригинальный URL (HTTP 302).

```bash
curl -L http://localhost:8000/my-google-123
# перенаправит на https://google.com/
```

При каждом переходе увеличивается счётчик кликов и обновляется дата последнего использования.

---

##### Статистика по ссылке

- `GET /links/{short_code}/stats` — получить статистику (кэшируется в Redis).

```bash
curl http://localhost:8000/links/my-google-123/stats
```

Ответ (`200 OK`):

```json
{
	"short_code": "my-google-123",
	"original_url": "https://google.com/",
	"created_at": "2026-03-09T12:00:00",
	"last_used_at": "2026-03-09T14:30:00",
	"click_count": 42,
	"expires_at": "2026-12-31T23:59:00",
	"owner_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

##### Обновление ссылки

- `PUT /links/{short_code}` — изменить оригинальный URL (**доступно только автору ссылки**).

```bash
curl -X PUT http://localhost:8000/links/my-google-123 \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <ваш_токен>' \
  -d '{"original_url": "https://yandex.ru/"}'
```

Ответ (`200 OK`): обновлённый объект ссылки.

---

##### Удаление ссылки

- `DELETE /links/{short_code}` — удалить ссылку (**доступно только автору ссылки**).

```bash
curl -X DELETE http://localhost:8000/links/my-google-123 \
  -H 'Authorization: Bearer <ваш_токен>'
```

Ответ: `204 No Content`.

> **!!!** Анонимно созданные ссылки нельзя изменить или удалить — они удаляются автоматически при истечении `expires_at` или после `CLEANUP_UNUSED_DAYS` дней неиспользования.

---

##### Поиск ссылки по оригинальному URL

- `GET /links/search?original_url={url}` — найти все короткие ссылки для данного URL.

```bash
curl 'http://localhost:8000/links/search?original_url=https://google.com/'
```

Ответ (`200 OK`): массив объектов `LinkResponse`.

---

#### 3. Health Check

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

### Кэширование (Redis)

Для ускорения работы сервиса используется **Redis**:

| Что кэшируется                 | Ключ Redis           | TTL              | Инвалидация                       |
| ------------------------------ | -------------------- | ---------------- | --------------------------------- |
| Оригинальный URL для редиректа | `link:{short_code}`  | `CACHE_TTL` сек. | При обновлении / удалении ссылки  |
| Статистика по ссылке           | `stats:{short_code}` | `CACHE_TTL` сек. | При клике / обновлении / удалении |

При обновлении (`PUT`) или удалении (`DELETE`) ссылки кэш автоматически очищается.

---

### Структура проекта

```
.
├── app/
│   ├── api/             # Роутеры FastAPI
│   │   ├── auth.py      # Регистрация и логин
│   │   ├── links.py     # CRUD ссылок + поиск
│   │   ├── redirect.py  # GET /{short_code} -> редирект
│   │   └── router.py    # Объединение всех роутеров
│   ├── auth/            # Авторизация
│   │   ├── dependencies.py  # get_current_user, get_optional_user
│   │   └── security.py      # JWT, хеширование паролей
│   ├── models/          # SQLAlchemy модели
│   │   ├── base.py
│   │   ├── user.py
│   │   └── link.py
│   ├── schemas/         # Pydantic схемы
│   │   ├── user.py
│   │   └── link.py
│   ├── services/        # Бизнес-логика
│   │   ├── link_service.py     # Основной сервис ссылок
│   │   ├── cache_service.py    # Работа с Redis кэшем
│   │   └── cleanup_service.py  # Фоновая очистка ссылок
│   ├── utils/
│   │   └── short_code.py  # Генерация коротких кодов
│   ├── main.py          # Точка входа FastAPI
│   ├── config.py        # Настройки (pydantic-settings)
│   ├── database.py      # Подключение к PostgreSQL
│   ├── redis.py         # Подключение к Redis
│   └── dependencies.py  # Зависимости
├── alembic/             # Миграции БД
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── uv.lock
├── .env_example
└── README.md
```

---

### CI/CD

Проект использует **GitHub Actions** для автоматизации проверок и деплоя.

#### Файлы workflow

```
.github/workflows/
├── ci.yml   # Запускается при каждом push и Pull Request
└── cd.yml   # Запускается при push в main/master → деплой на Render
```

#### CI Pipeline (`.github/workflows/ci.yml`)

При каждом **push** в `main`, `master`, `dev` и при открытии **Pull Request**:

1. **Lint** — ruff проверяет весь Python-код
2. **Unit Tests** — `pytest tests/unit`
3. **Integration Tests** — `pytest tests/integration` (с mock Redis через GitHub Services)
4. **Coverage** — генерируется отчёт; pipeline **падает** если покрытие < 90%
5. `coverage.xml` сохраняется как артефакт

Переменные окружения в CI:

- `DATABASE_URL` — SQLite in-memory (тесты не требуют PostgreSQL)
- `REDIS_URL` — Redis запускается как Docker-сервис в GitHub Actions

#### CD Pipeline (`.github/workflows/cd.yml`)

При **merge в `main`/`master`** — автоматически триггерит деплой на **Render.com**.

**Настройка:**

1. Render → сервис → **Settings → Deploy Hooks** → скопировать URL
2. GitHub → репозиторий → **Settings → Secrets → Actions**
3. Создать секрет: `RENDER_DEPLOY_HOOK_URL` = _URL с Render_

> **Рекомендация:** Включите **Branch Protection Rules** для `main` с обязательными статус-проверками `lint` и `test`, чтобы нельзя было смержить PR с упавшими тестами.
