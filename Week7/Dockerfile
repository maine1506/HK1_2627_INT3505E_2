FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml ./
COPY src ./src
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir .

FROM python:3.12-slim
WORKDIR /app
RUN groupadd -r app && useradd -r -g app -d /app app && chown app:app /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app wsgi.py gunicorn.conf.py ./
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 FLASK_APP=product_api.factory:create_app
USER app
EXPOSE 5000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "wsgi:app"]
