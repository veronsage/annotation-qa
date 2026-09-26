#!/usr/bin/env bash
# Запуск сервиса одной командой: ./run.sh [порт]
set -e
cd "$(dirname "$0")"

PORT="${1:-8000}"
# ключ API: берём из окружения или генерируем на этот запуск
export AQA_API_KEY="${AQA_API_KEY:-$(python3 -c 'import secrets;print(secrets.token_urlsafe(12))')}"

if [ ! -x .venv/bin/uvicorn ]; then
  echo "Создаю окружение и ставлю зависимости..."
  python3.12 -m venv .venv
  .venv/bin/pip install -q -r requirements-dev.txt
fi

# открыть Swagger, когда сервер поднимется
(
  for _ in $(seq 1 30); do
    if curl -s "http://127.0.0.1:$PORT/openapi.json" >/dev/null; then
      open "http://127.0.0.1:$PORT/docs"
      break
    fi
    sleep 0.5
  done
) &

echo "Swagger: http://127.0.0.1:$PORT/docs  (остановить: Ctrl+C)"
echo "API key: $AQA_API_KEY  (в Swagger кнопка Authorize)"
exec .venv/bin/uvicorn app.main:app --reload --port "$PORT"
