FROM python:3.12-slim

RUN apt-get update && apt-get install -y     stockfish     gcc     libpq-dev     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m nebula && chown -R nebula:nebula /app
USER nebula

EXPOSE 8000

ENV DATABASE_URL="postgresql+asyncpg://nebula_chess_user:DLLM7pkCPXLfBIk34Lj98dVtYiyJqrAk@dpg-d8u0qs7lk1mc73c6b18g-a.frankfurt-postgres.render.com/nebula_chess"

CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --loop uvloop
