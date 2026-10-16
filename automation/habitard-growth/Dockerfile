FROM python:3.13-slim
WORKDIR /app
COPY . /app
RUN useradd --uid 10001 --create-home habitard && mkdir -p /data && chown habitard:habitard /data
ENV HOST=0.0.0.0 PORT=8000 DATABASE_PATH=/data/habitard.db PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "container_start.py"]
