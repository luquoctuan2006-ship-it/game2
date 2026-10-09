FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir pygbag pygame-ce
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# build client WebAssembly -> game/build/web (FastAPI phuc vu cung origin voi API)
RUN python -m pygbag --build game
ENV WEB_DIR=/app/game/build/web
CMD ["sh","-c","uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
