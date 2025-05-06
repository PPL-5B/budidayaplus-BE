FROM python:3.9-slim
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=8000
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
EXPOSE ${PORT}
CMD ["sh", "-c", "gunicorn --workers 3 --log-level debug --bind 0.0.0.0:${PORT} budidayaplus.wsgi:application"]