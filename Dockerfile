FROM docker.m.daocloud.io/library/node:20-slim AS frontend
WORKDIR /workspace

COPY frontend-enterprise/package.json frontend-enterprise/package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci

COPY frontend-enterprise/ ./
RUN npm run build

FROM docker.m.daocloud.io/library/python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_DEFAULT_TIMEOUT=60 \
    DATABASE_URL=sqlite:////app/data/staffdeck.db

WORKDIR /app/backend

COPY backend/pyproject.toml backend/README.md ./
COPY backend/app ./app
COPY backend/mock_servers ./mock_servers
COPY backend/desktop_launcher.py backend/feishu_connector_worker.py ./
COPY backend/single_port_app.py ./single_port_app.py

RUN pip install --no-cache-dir . && \
    mkdir -p /app/data

COPY --from=frontend /workspace/dist /app/frontend-enterprise/dist

VOLUME ["/app/data"]
EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5173/api/health', timeout=3)" || exit 1

CMD ["uvicorn", "single_port_app:app", "--host", "0.0.0.0", "--port", "5173"]
