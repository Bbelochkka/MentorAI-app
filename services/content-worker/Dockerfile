FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /worker

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY services/content-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN curl -k "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt" -w "\n" >> $(python -m certifi)

COPY services/content-worker/worker.py ./worker.py
COPY services/content-service/app ./app

CMD ["python", "worker.py"]