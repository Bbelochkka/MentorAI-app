# MentorAI — infrastructure bootstrap for the content module

Это подготовленный инфраструктурный каркас под модуль генерации курсов и тестов.

Что уже сделано:

- очищен starter-проект: удалены `backend/venv` и `frontend/node_modules`;
- backend вынесен в `services/content-service`;
- создан `services/content-worker` как скелет фонового обработчика;
- добавлен `docker-compose.yml`;
- добавлены сервисы `postgres`, `redis`, `minio`, `content-service`, `content-worker`;
- настроен health endpoint: `GET /health` и `GET /api/health`.

## Структура

```text
mentorai_microservices_bootstrap/
  frontend/
  services/
    content-service/
    content-worker/
  infrastructure/
    postgres/init/01_content_module.sql
  shared/contracts/
  docker-compose.yml
  .env.example
```

## Быстрый старт

1. Открой проект в VS Code.
2. Убедись, что Docker Desktop запущен.
3. В корне проекта при необходимости отредактируй `.env`.
4. Выполни:

```bash
docker compose up --build
```

После запуска будут доступны:

- Content service: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`
- Postgres: `localhost:5432`
- Redis: `localhost:6379`

## Проверка

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:

```json
{
  "status": "ok",
  "service": "content-service",
  "checks": {
    "postgres": "ok",
    "redis": "ok",
    "minio": "ok"
  }
}
```

## Тестовый вход для стартовых экранов

- e-mail: `aoanuchina@hse.edu.ru`
- пароль: `password123`

Эти значения заданы через `.env` и используются только как временный bootstrap.

## Что делать дальше

Следующий шаг — реализовать вертикальный срез модуля:

1. загрузка документа;
2. обработка документа и chunking;
3. генерация черновика курса;
4. публикация курса;
5. генерация и публикация теста;
6. прохождение теста.
