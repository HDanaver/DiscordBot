FROM mwader/static-ffmpeg:9.0.2-1 AS ffmpeg

FROM python:3.15-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apk add --no-cache \
    ca-certificates \
    libstdc++ \
    libgcc \
    libffi

COPY --from=ffmpeg /ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /ffprobe /usr/local/bin/ffprobe

WORKDIR /app

COPY requirements.txt .

RUN apk add --no-cache --virtual .build-deps \
    build-base \
    cargo \
    rust \
    pkgconf \
    && pip install -r requirements.txt \
    && apk del .build-deps

COPY main.py .
COPY cogs/ ./cogs/

CMD ["python", "main.py"]