FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU and requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

ENV PYTHONPATH="/app:$PYTHONPATH"
ENV PYTHONUNBUFFERED=1

COPY . .

RUN chmod +x ./deploy/scripts/entry.sh ./deploy/scripts/entrypoint.sh ./deploy/scripts/healthcheck.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 CMD ./deploy/scripts/healthcheck.sh

ENTRYPOINT ["./deploy/scripts/entry.sh"]
CMD ["api"]
