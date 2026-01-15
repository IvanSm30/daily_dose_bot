Поднятие бд:
docker run -d \
 --name daily-dose-bot-db \
 -e POSTGRES_USER=botuser \
 -e POSTGRES_PASSWORD=securepassword \
 -e POSTGRES_DB=daily_dose_bot \
 -p 5434:5432 \
 postgres:16

Заход в контейнер бд:
docker exec -it daily-dose-bot-db psql -U botuser -d daily_dose_bot

Просмотр списка таблиц:
\dt

Просмотр данных (пример):
SELECT \* FROM users;

Выход из просмотра данных:
\q

Просмотр колонок (пример):
\d+ users

Удаление всех таблиц:
DROP SCHEMA public CASCADE;

Поднятие бота:
uv sync
source .venv/bin/activate
uv run main.py
