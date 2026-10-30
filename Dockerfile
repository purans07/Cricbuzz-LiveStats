FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements-lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements-lock.txt \
    && useradd --create-home --uid 10001 appuser
COPY --chown=10001:10001 main.py cloud_app.py config.py ./
COPY --chown=10001:10001 api/ ./api/
COPY --chown=10001:10001 database/ ./database/
COPY --chown=10001:10001 models/ ./models/
COPY --chown=10001:10001 services/ ./services/
COPY --chown=10001:10001 utils/ ./utils/
COPY --chown=10001:10001 ui/ ./ui/
COPY --chown=10001:10001 pages/ ./pages/
COPY --chown=10001:10001 deployment/ ./deployment/
COPY --chown=10001:10001 sql/ ./sql/
COPY --chown=10001:10001 data/sample/ ./data/sample/
COPY --chown=10001:10001 documentation/ ./documentation/
COPY --chown=10001:10001 README.md ./
COPY --chown=10001:10001 .streamlit/config.toml ./.streamlit/config.toml
RUN mkdir -p /app/data/runtime && chown 10001:10001 /app/data/runtime
USER appuser
ENV PUBLIC_DATA_MODE=sample DATA_MODE=sample APP_ACCESS_MODE=public_readonly \
    DATABASE_URL=sqlite:////app/data/runtime/public-demo.db
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "streamlit", "run", "cloud_app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
