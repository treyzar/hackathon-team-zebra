# Импорт курса: формат JSON

Инструкция для людей и ИИ-агентов, которые готовят файл для
`POST /api/admin/courses/import`.

Формат совпадает с тем, что отдаёт `GET /api/admin/courses/{id}/export`:
дамп с одного инстанса можно без правок залить на другой (но см. раздел
«Про ID» — файловые ссылки переносятся не всегда).

## Куда и что отдавать

- Эндпоинт: `POST /api/admin/courses/import` (multipart/form-data).
- Поле: `file` — файл `.json` с документом ниже.
- Доступ: только администратор.
- Ответ: `{"course_id": int, "slug": str, "title": str, "warnings": [str]}`.
- Курс **всегда создаётся черновиком** (`is_published=false`), поля
  `is_published` в документе нет. Публикация — отдельным
  `PATCH /api/admin/courses/{id} {"is_published": true}`.

Структура документа описана формально в `import-schema.json`, рабочий
образец — в `import-example.json`.

## Верхний уровень

```json
{
  "schema_version": 2,
  "course": { "slug": "...", "title": "...", "modules": [ ... ] }
}