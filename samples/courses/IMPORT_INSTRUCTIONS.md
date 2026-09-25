# Импорт курса: формат JSON

Инструкция для людей и ИИ-агентов, которые готовят файл для
`POST /api/admin/courses/import`.

## Куда и что отдавать

- Эндпоинт: `POST /api/admin/courses/import` (multipart/form-data).
- Поле: `file` — файл `.json` с документом ниже.
- Доступ: только администратор.
- Ответ: `{"course_id": int, "slug": str, "title": str, "warnings": [str]}`.
- Курс **всегда создаётся черновиком** (`is_published=false`), даже если в
  JSON стоит `true`. Публикация — отдельным `PATCH /api/admin/courses/{id}`.

Структура документа описана формально в `import-schema.json`, рабочий образец —
в `import-example.json`. Перед отправкой имеет смысл прогнать файл через
`jsonschema` (см. пример в конце README репозитория).

## Верхний уровень

```json
{
  "schema_version": 1,
  "course": { "slug": "...", "title": "...", "modules": [ ... ] }
}
```

- `schema_version` — ровно `1`.
- `course.slug` — `^[a-z0-9]+(-[a-z0-9]+)*$`, до 100 символов. Если занят,
  импорт молча добавит суффикс (`-2`, `-3`, …) и напишет об этом в `warnings`.
- `course.title` — до 200 символов.
- `course.description` — TipTap/ProseMirror документ
  (`{"type": "doc", "content": [...]}`).
- `course.step_access` — `"all"` (по умолчанию) или `"sequential"`.
- `course.modules` — массив модулей, порядок сохраняется.

## Модуль

```json
{ "title": "Циклы", "steps": [ ... ] }
```

Поля кроме `title` и `steps` запрещены.

## Шаг: общие правила

- `type` — один из **зарегистрированных** типов: `theory`, `single_choice`,
  `multiple_choice`, `free_text`, `programming`. Никаких `short_answer`,
  `matching`, `scratch` — их в API нет.
- `max_score` — целое 0..1000. У `theory` всегда `0` (импорт сам это
  поправит).
- `content`, `answer_key`, `settings` — объекты, схему см. ниже.
- Поля вне схемы запрещены (`extra="forbid"`). **Не кладите `is_hidden` в
  шаг** — прячьте шаг отдельным `PATCH /api/admin/steps/{id}` после импорта.
- `settings.max_attempts` — целое ≥ 1 или `null` (без ограничения).
- `settings.show_answer` — `never` | `after_wrong` |
  `after_attempts_exhausted` | `after_solved`.

## RichText

Везде, где ожидается текст (`body`, `question`, `statement`, `reference`),
используется один и тот же TipTap-документ. Минимум:

```json
{ "type": "doc", "content": [
  { "type": "paragraph", "content": [ { "type": "text", "text": "…" } ] }
] }
```

Поддерживаются `paragraph`, `heading` (`attrs.level` 1–6), `bulletList`,
`orderedList`, `listItem`, `blockquote`, `codeBlock`, `horizontalRule`,
`hardBreak`, `image` (только по `file_id` загруженного файла — не по
внешней ссылке), `text` с `marks`: `bold`, `italic`, `underline`, `strike`,
`code`, `link` (`attrs.href` только `http(s):`/`mailto:`).

## Типы шагов

### `theory`

```json
{
  "type": "theory",
  "max_score": 0,
  "content": { "body": { "type": "doc", "content": [ ... ] } },
  "answer_key": {},
  "settings": { "grading": "none" }
}
```

### `single_choice`

```json
{
  "type": "single_choice",
  "max_score": 2,
  "content": {
    "question": { "type": "doc", "content": [ ... ] },
    "options": [
      { "id": "<uuid4>", "text": "вариант" },
      { "id": "<uuid4>", "text": "вариант" }
    ]
  },
  "answer_key": { "correct": "<uuid4 одного из options>" },
  "settings": { "grading": "auto", "show_answer": "after_wrong" }
}
```

`options` — 2..50, `id` уникальны, `correct` обязан совпадать с одним из них.

### `multiple_choice`

То же, но `answer_key.correct` — массив UUID без дублей и хотя бы один
элемент. В `settings` добавляется `scoring`: `all_or_nothing` (по
умолчанию) или `partial`. При `partial` балл считается как
`(верно выбранные − ошибочно выбранные) / всего верных × max_score`,
не меньше 0.

### `free_text`

```json
{
  "type": "free_text",
  "max_score": 5,
  "content": {
    "question": { "type": "doc", "content": [ ... ] },
    "require_text": false,
    "min_files": 0,
    "max_files": 0,
    "allowed_mime": []
  },
  "answer_key": {
    "reference": null,
    "criteria": "что проверить куратору",
    "files": []
  },
  "settings": { "grading": "manual" }
}
```

- `min_files ≤ max_files ≤ 10`; `min_files > 0` требует загрузки файлов.
- `allowed_mime` — пусто = любые.
- `files` — id файлов, загруженных с `purpose=answer_key` (ссылки на
  эталонные решения для куратора). Файлов, загруженных в импортируемом
  JSON нет, поэтому либо оставьте `files: []`, либо удалите ссылки и
  загрузите файлы после импорта через `POST /api/files`.
- `grading` строго `manual`.

### `programming`

```json
{
  "type": "programming",
  "max_score": 10,
  "content": {
    "statement": { "type": "doc", "content": [ ... ] },
    "languages": ["python3"],
    "time_limit_ms": 1000,
    "memory_limit_mb": 256,
    "template": "",
    "samples": [ { "input": "2 3\n", "output": "5" } ]
  },
  "answer_key": {
    "test_groups": [
      { "name": "скрытые", "points": 10,
        "tests": [ { "input": "0 0\n", "output": "0" } ] }
    ],
    "reference_solution": "a, b = map(int, input().split())\nprint(a + b)\n"
  },
  "settings": { "grading": "tests", "scoring": "all_or_nothing" }
}
```

- `languages` — один или несколько ключей из
  `python3|javascript|cpp|csharp|go|pascal`; первый — по умолчанию.
- `template` и `reference_solution` — одни на все языки.
- `grading`: `tests` | `tests_and_review` | `manual`. При `manual`
  `test_groups` может быть пустым; иначе — нужна хотя бы одна группа с
  хотя бы одним тестом.
- `scoring`: `all_or_nothing` (по умолчанию) — полный балл только если
  прошли все группы; `per_group` — сумма баллов полностью пройденных
  групп, при этом **сумма `points` всех групп должна равняться
  `max_score`**, иначе `validate` отклонит шаг.
- Тест задаётся либо текстом (`input` + `output`), либо файлами
  (`input_file` / `output_file`, id файлов с `purpose=answer_key`),
  но не тем и другим одновременно. Файлы в импортируемом JSON
  ссылаются на уже загруженные в S3 объекты — если их нет, ссылка
  отбрасывается с `warnings` (см. `_prune_missing_files`).

## Чего делать нельзя

- Использовать незарегистрированные `type` — импорт упадёт с 422.
- Класть в шаг поля вне схемы (`parts`, `placeholder`, `checker`,
  `is_hidden`, …) — `extra="forbid"`.
- Указывать `language` (единственное число) — только `languages` (список).
- Ссылаться на внешние картинки (`https://example.com/...`) — только
  `file_id` уже загруженного файла.
- Зависеть от `is_published: true` — курс будет черновиком.
- Полагаться на `schema_version` больше 1 — импорт понимает только `1`.

Валидируйте перед отправкой.