## Сервис SmartCollect

REST‑API для управления заявками на выплату: Django REST Framework обрабатывает HTTP‑слой, Celery + Redis имитируют асинхронное исполнение заявок, данные хранятся в PostgreSQL (в тестах и по умолчанию используется SQLite).

### Стек

- Python 3.10+, Django 4.2, DRF, drf-spectacular (OpenAPI/Swagger)
- Celery 5 + Redis в роли брокера и хранилища результатов
- PostgreSQL (основная БД в docker-compose и проде; если переменные `DB_*` не заданы, Django использует SQLite исключительно для локального тестирования)

### Быстрый старт (без Docker)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # установка зависимостей
cp .env.example .env                     # при необходимости переопределить переменные
python manage.py migrate                 # запуск миграций
python manage.py runserver 0.0.0.0:8000  # запуск приложения
celery -A config worker -l info          # запуск Celery worker'а во втором терминале
```

### Makefile

- `make install` — установить зависимости.
- `make migrate` — применить миграции.
- `make runserver` — стартовать Django‑сервер разработки.
- `make worker` — запустить Celery worker.
- `make test` — прогнать тесты.
- Дополнительно: `make beat`, `make shell`, `make createsuperuser`.

> Если `make` недоступен (например, в PowerShell без GNU Make), используйте аналогичные команды напрямую:  
> `python manage.py migrate`, `python manage.py test`, `python manage.py runserver`, `celery -A config worker -l info`, или установите GNU Make (`choco install make`).

### Docker / docker-compose

```
docker compose up --build web worker
```

В комплект входит `db` (Postgres 15), `redis`, `web` (Django) и `worker` (Celery). Секреты/настройки можно переопределить через `.env` или переменные среды Docker Compose.

### API

- `POST /api/payouts/` — создать заявку (валидация + постановка задачи в Celery).
- `GET /api/payouts/` — список с поиском и сортировкой.
- `GET /api/payouts/{id}/` — детали заявки.
- `PATCH /api/payouts/{id}/` — частичное обновление (статус/описание).
- `DELETE /api/payouts/{id}/` — удаление.

Запросы требуют аутентификации (Basic/Session). Документация: `/api/docs/` (Swagger UI) и `/api/schema/` (OpenAPI JSON).

### Тесты

```
make test
```

Тесты проверяют успешное создание заявки и факт постановки Celery‑таски (через mock). БД — временный SQLite, миграции накатываются автоматически.

### Краткое описание деплоя

1. **Сервисы.** Нужны PostgreSQL (боевой), Redis или RabbitMQ, приложение Django (gunicorn) и отдельные Celery worker'ы/beat.  
2. **Подготовка окружения.** Создать `.env`/секреты с `DJANGO_SECRET_KEY`, реквизитами БД, `CELERY_BROKER_URL`, `DJANGO_ALLOWED_HOSTS`, `TIME_ZONE` и т.д.; открыть сетевой доступ приложения к БД/брокеру; подготовить тома/бэкапы БД.
3. **Сборка и поставка.** Собрать контейнер (`docker build -t smartcollect .`) или собрать пакет в CI, прогнать тесты, запушить в реестр.
4. **Миграции.** Перед выкатыванием выполнить `python manage.py migrate` (через job/команду в пайплайне).
5. **Запуск сервисов.**  
   - Django: `gunicorn config.wsgi:application --bind 0.0.0.0:8000` за reverse‑proxy (nginx/Traefik) с TLS, health‑check'ами и логированием.  
   - Celery: `celery -A config worker -l info` (несколько экземпляров при необходимости) и, опционально, `celery -A config beat -l info` для расписаний.  
6. **Наблюдаемость и отказоустойчивость.** Настроить мониторинг (логирование уже структурировано), перезапуски через orchestrator (systemd, Supervisor, Kubernetes Deployments), алерты на неудачные таски.

Такой процесс обеспечивает воспроизводимость окружения, отделяет веб‑трафик от фоновых задач и даёт минимальный набор шагов для вывода сервиса в прод.
