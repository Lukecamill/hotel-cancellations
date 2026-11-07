FROM python:3.13.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src \
    SERVING_BUNDLE=/models SERVICE_HOST=0.0.0.0 SERVICE_PORT=8080 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-serving.txt ./
RUN pip install --no-cache-dir -r requirements-serving.txt \
    && useradd --create-home --uid 10001 hotel
COPY --chown=hotel:hotel src/ ./src/
USER hotel
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
CMD ["python", "-m", "hotel_cancel.service"]
