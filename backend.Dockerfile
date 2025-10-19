FROM python:3.12-alpine

LABEL version="1.0"
LABEL description="Python 3.14.0a7 Alpine 3.21"

WORKDIR /app

COPY . .

RUN apk update && \
    apk add --no-cache --upgrade bash && \
    apk add --no-cache postgresql-client ffmpeg && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del .build-deps && \
    apk add --no-cache dos2unix && \
    find . -type f -name "*.sh" -exec dos2unix {} \; && \
    find . -type f -name "*.sh" -exec chmod +x {} \; && \
    apk del dos2unix

EXPOSE 8000
