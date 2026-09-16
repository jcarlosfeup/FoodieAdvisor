FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY pyproject.toml README.md ./
COPY api ./api
COPY db ./db
COPY services ./services
COPY scripts ./scripts
COPY config.py main.py storage.py ./
COPY view ./view
COPY migrations ./migrations
COPY world_cities.csv restaurants.csv ./

RUN python -m pip install --upgrade pip \
    && python -m pip install '.[postgres]'

EXPOSE 8501

CMD ["streamlit", "run", "main.py", "--server.address=0.0.0.0", "--server.port=8501"]