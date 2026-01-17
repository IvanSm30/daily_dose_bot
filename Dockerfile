FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN pip install uv && uv sync

COPY . .

RUN uv sync 

CMD ["uv", "run", "main.py"]