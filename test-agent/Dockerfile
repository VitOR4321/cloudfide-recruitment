FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY test-agent ./test-agent
CMD ["python", "-m", "unittest", "discover", "-s", "test-agent/tests", "-v"]
