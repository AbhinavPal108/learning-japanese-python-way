# REST API reference — Learning Japanese the Python Way

Base URL for a local lab run: `http://127.0.0.1:8080/api/v1`

Interactive OpenAPI documentation: `http://127.0.0.1:8080/docs`

All request and response bodies use JSON. API version: `v1`.

## Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/numbers` | Return Japanese numbers 1–100 |
| GET | `/numbers/{number}` | Return kanji, hiragana and Romaji for one number |
| POST | `/learning-events` | Save a lesson/audio/application event |
| POST | `/practice/attempts` | Save and score a practice answer |
| POST | `/quizzes/start` | Create and persist a quiz session |
| POST | `/quizzes/{quiz_id}/submit` | Score and save every quiz answer |
| GET | `/quizzes/results/{learner_id}` | Return recent saved results |
| GET | `/quizzes/result/{quiz_id}` | Return a specific quiz record |
| GET | `/progress/{learner_id}` | Return statistics, quiz history, practice attempts and event history |
| GET | `/partner/export/{learner_id}` | Partner endpoint: export learner progress and activity |
| POST | `/partner/events` | Partner endpoint: receive an event from a companion project |

Partner endpoints accept `X-Partner-API-Key` when `PARTNER_API_KEY` is configured. Set the same secret in both projects; do not hard-code it in source code or commit `.env`.

## Example: get a number

```bash
curl http://127.0.0.1:8080/api/v1/numbers/42
```

Expected fields include `number`, `kanji`, `hiragana`, and `romaji`.

## Example: save a practice attempt

```bash
curl -X POST http://127.0.0.1:8080/api/v1/practice/attempts \
  -H 'Content-Type: application/json' \
  -d '{"learner_id":"demo-user","question_number":42,"selected_number":42,"source_project":"partner-project"}'
```

## Example: partner project sends an event

```bash
curl -X POST http://127.0.0.1:8080/api/v1/partner/events \
  -H 'Content-Type: application/json' \
  -H 'X-Partner-API-Key: YOUR_SHARED_SECRET' \
  -d '{"learner_id":"demo-user","event_type":"module_completed","source_project":"partner-project","payload":{"module":"flashcards","completed":true}}'
```

## Example: partner project reads the learner's progress

```bash
curl http://127.0.0.1:8080/api/v1/partner/export/demo-user \
  -H 'X-Partner-API-Key: YOUR_SHARED_SECRET'
```

When no key is configured, partner endpoints are open for local testing. For shared lab or deployed use, configure `PARTNER_API_KEY` before starting the service.

## Quiz workflow

1. `POST /quizzes/start` with `learner_id` and `num_questions`.
2. The API returns `quiz_id` and questions containing Japanese display text and multiple-choice options. The target answer is not returned as a separate field.
3. `POST /quizzes/{quiz_id}/submit` with `{"answers":[{"position":1,"selected_number":42}, ...]}`. Use `null` for unanswered questions.
4. The backend checks answers against stored targets, calculates score/percentage/grade, and saves the quiz and each answer.
5. `GET /progress/{learner_id}` returns the updated aggregate statistics.

## Important integration note

The partner project should call these endpoints over HTTP and exchange JSON. It should **not open or write to this project's SQLite file directly**. This maintains a clear ownership boundary between the two projects. In a browser-to-API call across different hosts, set `CORS_ORIGINS` to the exact browser origin; server-to-server API calls do not rely on CORS, but should use the API key and HTTPS when deployed.
