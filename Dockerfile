# FROM python:3.9-slim
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1
# ENV PORT=8000
# WORKDIR /app
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . /app/
# EXPOSE ${PORT}
# CMD ["sh", "-c", "gunicorn --workers 3 --log-level debug --bind 0.0.0.0:${PORT} budidayaplus.wsgi:application"]

# builder
FROM python:3.9-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# runtime
FROM python:3.9-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=8000
WORKDIR /app

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY . /app/

EXPOSE ${PORT}
CMD ["sh", "-c", "gunicorn --workers 3 --log-level debug --bind 0.0.0.0:${PORT} budidayaplus.wsgi:application"]
