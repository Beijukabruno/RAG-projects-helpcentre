FROM python:3.10-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU wheel for sentence-transformers
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Add GEMMA_API_KEY as a build argument and environment variable
ARG GEMMA_API_KEY
ENV GEMMA_API_KEY=$GEMMA_API_KEY

ENV PYTHONPATH="/app:$PYTHONPATH"

# Copy app code
COPY consolidated_chatbot.py ./
COPY guardrail.py ./
COPY . .

# Precompute chunks and vector DB during build
RUN python scripts/chunk_markdown.py && python scripts/embed_and_index.py

COPY entrypoint.sh ./
RUN chmod +x ./entrypoint.sh

EXPOSE 8000

# Add healthcheck script
COPY healthcheck.sh ./
RUN chmod +x ./healthcheck.sh
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 CMD ./healthcheck.sh

ENTRYPOINT ["./entrypoint.sh"]
