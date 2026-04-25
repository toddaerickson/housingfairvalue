FROM python:3.11-slim

RUN useradd --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
RUN pip install --no-cache-dir .

RUN chown -R app:app /app

USER app
EXPOSE 8000
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
