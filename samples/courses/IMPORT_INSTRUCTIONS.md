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
```

## Модуль

```json
{ "title": "Циклы", "skills": ["Циклы for", "Условия"], "steps": [ ... ] }
```

`skills` — навыки модуля для карты навыков учеников (до 12, до 60 символов,
можно не указывать). Навык зачитывается ученику, когда он выполнит все шаги
модуля.

## Чек-лист ручной проверки

В `settings` шага, который проверяет куратор (`free_text`, `short_text` с
`"grading": "manual"`, `programming` с `tests_and_review` или `manual`),
можно задать пункты, которые куратор отмечает при проверке:

```json
"checklist": [
  { "id": "plan", "text": "Есть план решения", "points": 2, "hint": "Хотя бы 3 шага" },
  { "id": "works", "text": "Программа работает", "points": 3 }
]
```

Сумма `points` должна равняться `max_score` шага; `id` — уникальны в шаге.
