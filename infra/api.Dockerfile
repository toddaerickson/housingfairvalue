FROM python:3.11-slim

RUN useradd --create-home --shell /usr/sbin/nologin app
WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend
RUN pip install --no-cache-dir .

RUN chown -R app:app /app

USER app
EXPOSE 8000
# --proxy-headers + --forwarded-allow-ips='*' so the rate limiter keys on the
# real client IP from X-Forwarded-For (set by Fly's edge proxy) rather than
# the proxy's own IP, which would put every request in a single bucket.
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
