FROM python:3.13.13-slim-bookworm
RUN pip install --no-cache-dir "mlflow==3.18.0" "psycopg[binary]==3.3.8"
RUN useradd --create-home --uid 10001 mlflow && mkdir /mlartifacts && chown mlflow:mlflow /mlartifacts
USER mlflow
EXPOSE 5000
