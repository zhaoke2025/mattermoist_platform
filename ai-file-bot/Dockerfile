FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install paddlepaddle==3.0.0 \
        -i https://www.paddlepaddle.org.cn/packages/stable/cpu/ \
    && pip install -r requirements.txt

COPY src ./src

CMD ["python", "-m", "src.main"]
