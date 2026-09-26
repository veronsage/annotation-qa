# Annotation QA

Сервис для проверки качества разметки. На вход подаются картинки, разметка bounding box от нескольких разметчиков, список разметчиков и (по желанию) правила. На выходе получается очередь объектов, которые стоит проверить руками: там, где разметчики не сошлись по классу, кто-то пропустил объект, рамка вылезает за картинку и т.п.

Проект делается в рамках курса «Разработка безопасного ПО», ВШЭ. Описание проекта в [project.md](project.md).

## Запуск

Нужен Python 3.12. Проще всего:

```
./run.sh
```

Скрипт при первом запуске сам создаст `.venv` и поставит зависимости, потом запустит сервер и откроет Swagger. Порт можно передать аргументом: `./run.sh 8001`.

Вручную то же самое:

```
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs  
Страница с очередью: http://127.0.0.1:8000/

Все запросы к `/projects` требуют заголовок `X-API-Key`. Ключ задаётся переменной `AQA_API_KEY`. Если её нет, сервер сгенерирует ключ и напишет его в консоль. В Swagger ключ вводится через кнопку Authorize.

## Пример

```
export AQA_API_KEY=...   # ключ, с которым запущен сервер
H="X-API-Key: $AQA_API_KEY"
PID=$(curl -s -H "$H" -X POST localhost:8000/projects -H 'Content-Type: application/json' -d '{"name":"demo"}' | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')
curl -H "$H" -X POST localhost:8000/projects/$PID/annotations -F annotations=@samples/dataset.json -F rules=@samples/rules.json
curl -H "$H" -X POST localhost:8000/projects/$PID/annotators -F annotators=@samples/annotators.csv
curl -H "$H" -X POST localhost:8000/projects/$PID/analyze
curl -H "$H" localhost:8000/projects/$PID/review-queue
```

Данные в `samples/` выдуманные.

## Тесты

```
.venv/bin/python -m pytest
```
