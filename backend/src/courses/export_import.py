from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException, status
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from courses import service
from courses.models import Course, Module, Step, StepRevision
from files.models import File, FileStatus
from models import User
from steps import StepPayload


EXPORT_SCHEMA_VERSION = 1

_payload_adapter = TypeAdapter(StepPayload)

def unprocessable(msg = "Unprocessable") -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=msg)

async def export_as_json(db: AsyncSession, course: Course) -> dict[str, Any]:
    modules = await service.live_modules(db, course.id)
    steps = list(
        await db.scalars(
            select(Step)
            .where(
                Step.module_id.in_([m.id for m in modules]),
                Step.deleted_at.is_(None),
            )
            .order_by(Step.position, Step.id)
        )
    )
    revision_ids = [s.current_revision_id for s in steps if s.current_revision_id]
    revisions: dict[int, StepRevision] = {
        r.id: r
        for r in await db.scalars(
            select(StepRevision).where(StepRevision.id.in_(revision_ids))
        )
    }

    by_module: dict[int, list[dict[str, Any]]] = {m.id: [] for m in modules}
    for step in steps:
        rev = revisions.get(step.current_revision_id or -1)
        if rev is None:
            continue
        by_module[step.module_id].append(
            {
                "type": step.type,
                "is_hidden": step.is_hidden,
                "max_score": rev.max_score,
                "content": rev.content,
                "answer_key": rev.answer_key,
                "settings": rev.settings,
            }
        )

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "course": {
            "slug": course.slug,
            "title": course.title,
            "description": course.description,
            "step_access": course.step_access.value,
            "is_published": course.is_published,
            "modules": [
                {"title": m.title, "steps": by_module[m.id]} for m in modules
            ],
        },
    }



#import

def _unique_slug(base: str, taken: set[str]) -> str:
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def _collect_referenced_file_ids(payload: dict[str, Any]) -> set[int]:
    ids: set[int] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in ("file_id", "input_file", "output_file") and isinstance(item, int):
                    ids.add(item)
                elif key == "files" and isinstance(item, list):
                    ids.update(x for x in item if isinstance(x, int))
                else:
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return ids


def _prune_missing_files(payload: dict[str, Any], available: set[int]) -> int:
    dropped = 0

    def prune_test(tests: list[Any]) -> list[Any]:
        nonlocal dropped
        kept: list[Any] = []
        for test in tests:
            if not isinstance(test, dict):
                kept.append(test)
                continue
            broken = any(
                isinstance(test.get(key), int) and test[key] not in available
                for key in ("input_file", "output_file")
            )
            if broken:
                dropped += 1
                continue
            kept.append(test)
        return kept

    def walk(value: Any) -> None:
        nonlocal dropped
        if isinstance(value, dict):
            if isinstance(value.get("tests"), list):
                value["tests"] = prune_test(value["tests"])
            if isinstance(value.get("files"), list) and all(
                isinstance(x, int) or x is None for x in value["files"]
            ):
                kept = [x for x in value["files"] if isinstance(x, int) and x in available]
                dropped += len(value["files"]) - len(kept)
                value["files"] = kept
            for key in ("file_id", "input_file", "output_file"):
                if isinstance(value.get(key), int) and value[key] not in available:
                    value.pop(key)
                    dropped += 1
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return dropped


async def _live_file_ids(db: AsyncSession, ids: set[int]) -> set[int]:
    if not ids:
        return set()
    rows = await db.scalars(
        select(File.id).where(File.id.in_(ids), File.status == FileStatus.READY)
    )
    return set(rows)


def _require_mapping(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise unprocessable(f"{what} должен быть объектом")
    return value


def _require_string(value: Any, what: str, max_len: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise unprocessable(f"{what} должен быть непустой строкой")
    if max_len is not None and len(value) > max_len:
        raise unprocessable(f"{what} длиннее {max_len} символов")
    return value.strip()


async def import_course(
    db: AsyncSession, user: User, raw: bytes
) -> tuple[Course, list[str]]:
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as e:
        raise unprocessable(f"Файл не является JSON: {e}") from e

    document = _require_mapping(document, "файл")
    if document.get("schema_version") != EXPORT_SCHEMA_VERSION:
        raise unprocessable(f"Неизвестная версия схемы: {document.get('schema_version')!r}")
    payload = _require_mapping(document.get("course"), "поле `course`")

    warnings: list[str] = []

    slug_base = _require_string(payload.get("slug"), "slug", max_len=100)
    taken = set(await db.scalars(select(Course.slug)))
    slug = _unique_slug(slug_base, taken)
    if slug != slug_base:
        warnings.append(
            f"Адрес «{slug_base}» занят, импортировано как «{slug}»"
        )

    title = _require_string(payload.get("title"), "title", max_len=200)
    description = payload.get("description")
    if not isinstance(description, dict) or description.get("type") != "doc":
        description = {"type": "doc", "content": []}

    step_access_raw = payload.get("step_access", "all")
    try:
        from courses.models import StepAccess

        step_access = StepAccess(step_access_raw)
    except ValueError as e:
        raise unprocessable(f"Неизвестный step_access: {step_access_raw!r}") from e

    course = Course(
        slug=slug,
        title=title,
        description=description,
        is_published=False,
        step_access=step_access,
    )
    db.add(course)
    await db.flush()

    modules_raw = payload.get("modules")
    if not isinstance(modules_raw, list):
        raise unprocessable("`modules` должен быть списком")

    for module_index, module_raw in enumerate(modules_raw):
        module_raw = _require_mapping(module_raw, f"модуль #{module_index + 1}")
        module_title = _require_string(
            module_raw.get("title"), f"название модуля #{module_index + 1}", max_len=200
        )
        module = Module(
            course_id=course.id, title=module_title, position=module_index
        )
        db.add(module)
        await db.flush()

        steps_raw = module_raw.get("steps") or []
        if not isinstance(steps_raw, list):
            raise unprocessable(f"`steps` модуля #{module_index + 1} должен быть списком")

        for step_index, step_raw in enumerate(steps_raw):
            where = f"шаг {module_index + 1}.{step_index + 1}"
            step_raw = _require_mapping(step_raw, where)

            try:
                parsed = _payload_adapter.validate_python(step_raw)
            except ValidationError as e:
                first = e.errors(include_url=False)[0] if e.errors() else {}
                loc = ".".join(str(x) for x in first.get("loc", ())) or "payload"
                raise unprocessable(f"{where}: {loc}: {first.get('msg', 'некорректный payload')}") from e

            dumped = json.loads(parsed.model_dump_json())
            wanted = _collect_referenced_file_ids(dumped)
            available = await _live_file_ids(db, wanted)
            dropped = _prune_missing_files(dumped, available)
            if dropped:
                warnings.append(
                    f"{where}: {dropped} ссылок на файлы не найдены и отброшены"
                )
            try:
                parsed = _payload_adapter.validate_python(dumped)
            except ValidationError as e:
                first = e.errors(include_url=False)[0] if e.errors() else {}
                raise unprocessable(
                    f"{where}: после очистки файловых ссылок payload некорректен: "
                    f"{first.get('msg', 'ошибка')}",
                ) from e

            step = Step(
                module_id=module.id,
                type=parsed.type,
                position=step_index,
                is_hidden=bool(step_raw.get("is_hidden", False)),
            )
            db.add(step)
            await db.flush()

            await service.add_revision(
                db, step, parsed, user, "Импорт курса", is_breaking=False
            )

    return course, warnings


def _require_string(value: Any, what: str, max_len: int | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise unprocessable(f"{what} должен быть непустой строкой")  # ← f-string
    if max_len is not None and len(value) > max_len:
        raise unprocessable(f"{what} длиннее {max_len} символов")
    return value.strip()


# ============================================================================
# PDF export
# ============================================================================

import base64 as _b64
import html as _html


_PDF_CSS = """
@page { size: A4; margin: 20mm 18mm 22mm 18mm;
        @bottom-right { content: counter(page) " / " counter(pages);
                        font-size: 9pt; color: #7a879c; } }
* { box-sizing: border-box; }
body { font-family: "DejaVu Sans", "PT Sans", "Noto Sans", sans-serif;
       color: #1d2b43; font-size: 11.5pt; line-height: 1.55; margin: 0; }
h1 { font-size: 24pt; margin: 0 0 6pt; color: #0f172a; letter-spacing: -0.02em; }
h2 { font-size: 18pt; margin: 0 0 10pt; color: #0f172a; letter-spacing: -0.02em;
     break-before: page; }
h2.first { break-before: auto; }
h3 { font-size: 14pt; margin: 14pt 0 6pt; color: #0f172a; }
h4 { font-size: 12pt; margin: 12pt 0 4pt; }
p  { margin: 0 0 8pt; }
ul, ol { margin: 0 0 8pt 18pt; padding: 0; }
li { margin: 2pt 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 10pt;
       background: #f1f3f9; padding: 1pt 4pt; border-radius: 3pt; }
pre { font-family: "DejaVu Sans Mono", monospace; font-size: 10pt;
      background: #f6f7fb; border: 1px solid #e1e6f0; border-radius: 6pt;
      padding: 8pt 10pt; white-space: pre-wrap; word-wrap: break-word; }
pre code { background: none; padding: 0; }
blockquote { border-left: 3pt solid #aebeff; background: #f5f7ff;
             padding: 6pt 10pt; margin: 8pt 0; color: #42516b; }
img { max-width: 100%; height: auto; display: block; margin: 10pt auto;
      border-radius: 6pt; }
hr { border: 0; border-top: 1px solid #e1e6f0; margin: 14pt 0; }
.muted { color: #6e7b91; font-size: 10pt; }
.cover { padding-bottom: 8pt; margin-bottom: 20pt;
         border-bottom: 2pt solid #3457f0; }
.kicker { color: #3457f0; font-size: 9.5pt; font-weight: 800;
          letter-spacing: 0.14em; text-transform: uppercase; margin-bottom: 6pt; }
.meta { margin-top: 8pt; color: #4a546b; font-size: 10.5pt; }
.meta span { margin-right: 14pt; }
.step { margin: 0 0 18pt; padding: 12pt 14pt; border: 1px solid #e1e6f0;
        border-radius: 8pt; break-inside: avoid; }
.step-title { font-size: 13pt; margin: 2pt 0 6pt; color: #0f172a; }
.step-meta { color: #6e7b91; font-size: 9.5pt; }
.step-type { display: inline-block; padding: 1pt 6pt; border-radius: 4pt;
             background: #eaf0fe; color: #3457f0; font-size: 9pt;
             font-weight: 700; }
.hidden-flag { color: #b8520f; }
.answer-key { margin-top: 10pt; padding: 8pt 10pt; background: #fff8ec;
              border: 1px dashed #e7c79a; border-radius: 6pt; font-size: 10.5pt;
              break-inside: avoid; }
.answer-key h5 { margin: 0 0 4pt; font-size: 10.5pt; color: #8a5414;
                 text-transform: uppercase; letter-spacing: 0.08em; }
.answer-key ul { margin: 0 0 4pt 16pt; }
.correct-mark { color: #17915a; font-weight: 700; }
.wrong-mark { color: #9aa4b6; }
.test-group { margin-top: 6pt; }
.test-group-name { font-weight: 700; color: #42516b; }
.test-row { margin: 3pt 0 6pt; }
.test-row pre { margin: 2pt 0; font-size: 9.5pt; }
.missing-image { color: #b33a3a; font-size: 10pt; }
"""

_STEP_TYPE_LABELS = {
    "theory": "Теория",
    "single_choice": "Один верный вариант",
    "multiple_choice": "Несколько верных вариантов",
    "free_text": "Свободный ответ",
    "programming": "Программирование",
}


def _escape(value: Any) -> str:
    return _html.escape("" if value is None else str(value), quote=True)


def _safe_href(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if lowered.startswith(("http://", "https://", "mailto:")):
        return _escape(value)
    return None


def _render_text(marks: list | None, text: str) -> str:
    out = _escape(text)
    for mark in marks or []:
        kind = mark.get("type")
        attrs = mark.get("attrs") or {}
        if kind == "bold":
            out = f"<strong>{out}</strong>"
        elif kind == "italic":
            out = f"<em>{out}</em>"
        elif kind == "underline":
            out = f"<u>{out}</u>"
        elif kind == "strike":
            out = f"<s>{out}</s>"
        elif kind == "code":
            out = f"<code>{out}</code>"
        elif kind == "link":
            href = _safe_href(attrs.get("href"))
            if href:
                out = f'<a href="{href}">{out}</a>'
    return out


def _render_image(node: dict, images: dict[int, str]) -> str:
    file_id = (node.get("attrs") or {}).get("file_id")
    if not isinstance(file_id, int):
        return ""
    src = images.get(file_id)
    if not src:
        return f'<p class="missing-image">[изображение недоступно: файл #{file_id}]</p>'
    alt = _escape((node.get("attrs") or {}).get("alt") or "Изображение")
    return f'<img src="{src}" alt="{alt}">'


def _render_block(node_type: str | None, attrs: dict, children: str) -> str:
    if node_type == "doc":
        return children
    if node_type == "paragraph":
        return f"<p>{children or '&nbsp;'}</p>"
    if node_type == "heading":
        level = max(1, min(6, int(attrs.get("level") or 1)))
        return f"<h{level}>{children}</h{level}>"
    if node_type == "bulletList":
        return f"<ul>{children}</ul>"
    if node_type == "orderedList":
        return f"<ol>{children}</ol>"
    if node_type == "listItem":
        return f"<li>{children}</li>"
    if node_type == "blockquote":
        return f"<blockquote>{children}</blockquote>"
    if node_type == "codeBlock":
        return f"<pre><code>{children}</code></pre>"
    if node_type == "horizontalRule":
        return "<hr>"
    return children


def _render_doc(node: Any, images: dict[int, str]) -> str:
    if not isinstance(node, dict) or node.get("type") != "doc":
        return ""
    return _render_node(node, images)


def _render_node(node: dict, images: dict[int, str]) -> str:
    node_type = node.get("type")
    if node_type == "text":
        return _render_text(node.get("marks"), node.get("text") or "")
    if node_type == "hardBreak":
        return "<br>"
    if node_type == "image":
        return _render_image(node, images)
    children = "".join(_render_node(c, images) for c in node.get("content") or [])
    return _render_block(node_type, node.get("attrs") or {}, children)


def _iter_doc_file_ids(node: Any) -> set[int]:
    ids: set[int] = set()
    if isinstance(node, dict):
        if node.get("type") == "image":
            fid = (node.get("attrs") or {}).get("file_id")
            if isinstance(fid, int):
                ids.add(fid)
        for v in node.values():
            ids |= _iter_doc_file_ids(v)
    elif isinstance(node, list):
        for item in node:
            ids |= _iter_doc_file_ids(item)
    return ids


def _split_title(doc: Any) -> tuple[str, dict | None]:
    """Отделить название шага (heading с attrs.zebra_title=true) от тела."""
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        return "", doc
    content = doc.get("content") or []
    if not content:
        return "", doc
    first = content[0]
    attrs = first.get("attrs") or {}
    if first.get("type") == "heading" and attrs.get("zebra_title") is True:
        title = "".join(
            p.get("text") or ""
            for p in (first.get("content") or [])
            if p.get("type") == "text"
        ).strip()
        rest = content[1:] or [{"type": "paragraph"}]
        return title, {"type": "doc", "content": rest}
    return "", doc


async def _load_images(db: AsyncSession, ids: set[int]) -> dict[int, str]:
    """Скачать готовые файлы из S3 и вернуть id → data-URI."""
    if not ids:
        return {}
    from files import storage  # локально, чтобы не тянуть S3 в тестах

    rows = list(
        await db.scalars(
            select(File).where(File.id.in_(ids), File.status == FileStatus.READY)
        )
    )
    result: dict[int, str] = {}
    for f in rows:
        try:
            data = await storage.read_object(f.storage_key)
        except (FileNotFoundError, storage.StorageError):
            continue
        result[f.id] = f"data:{f.mime};base64,{_b64.b64encode(data).decode('ascii')}"
    return result


async def export_as_pdf(
    db: AsyncSession, course: Course, *, include_answers: bool = True
) -> bytes:
    from weasyprint import HTML

    modules = await service.live_modules(db, course.id)
    module_ids = [m.id for m in modules]
    steps: list[Step] = []
    if module_ids:
        steps = list(
            await db.scalars(
                select(Step)
                .where(Step.module_id.in_(module_ids), Step.deleted_at.is_(None))
                .order_by(Step.position, Step.id)
            )
        )
    revision_ids = [s.current_revision_id for s in steps if s.current_revision_id]
    revisions: dict[int, StepRevision] = {}
    if revision_ids:
        revisions = {
            r.id: r
            for r in await db.scalars(
                select(StepRevision).where(StepRevision.id.in_(revision_ids))
            )
        }

    docs_to_scan: list[Any] = [course.description]
    parsed_by_module: dict[int, list] = {m.id: [] for m in modules}
    for step in steps:
        rev = revisions.get(step.current_revision_id or -1)
        if rev is None:
            continue
        parsed = service.parse(step, rev)
        content = parsed.content.model_dump(mode="json")
        answer_key = parsed.answer_key.model_dump(mode="json")
        for key in ("body", "question", "statement"):
            value = content.get(key)
            if isinstance(value, dict) and value.get("type") == "doc":
                docs_to_scan.append(value)
        ref = answer_key.get("reference")
        if isinstance(ref, dict) and ref.get("type") == "doc":
            docs_to_scan.append(ref)
        parsed_by_module[step.module_id].append((step, rev, parsed))

    image_ids: set[int] = set()
    for doc in docs_to_scan:
        image_ids |= _iter_doc_file_ids(doc)
    images = await _load_images(db, image_ids)

    html = _build_pdf_html(course, modules, parsed_by_module, images, include_answers)
    return await asyncio.to_thread(lambda: HTML(string=html).write_pdf())


def _build_pdf_html(
    course: Course, modules, parsed_by_module, images, include_answers: bool
) -> str:
    total_steps = sum(len(v) for v in parsed_by_module.values())
    visibility = "опубликован" if course.is_published else "черновик"
    access = (
        "по очереди"
        if course.step_access.value == "sequential"
        else "все шаги сразу"
    )
    description_html = _render_doc(course.description, images)

    parts: list[str] = [
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>",
        f"<title>{_escape(course.title)}</title>",
        f"<style>{_PDF_CSS}</style>",
        "</head><body>",
        "<section class='cover'>",
        "<div class='kicker'>Курс · Zebra</div>",
        f"<h1>{_escape(course.title)}</h1>",
        "<div class='meta'>",
        f"<span>slug: <code>{_escape(course.slug)}</code></span>",
        f"<span>{visibility}</span>",
        f"<span>доступ: {_escape(access)}</span>",
        f"<span>модулей: {len(modules)}</span>",
        f"<span>шагов: {total_steps}</span>",
        "</div>",
    ]
    if description_html:
        parts.append(f"<div style='margin-top:12pt'>{description_html}</div>")
    parts.append("</section>")

    if not modules:
        parts.append("<p class='muted'>В курсе пока нет модулей.</p>")

    for index, module in enumerate(modules, 1):
        css_class = "first" if index == 1 else ""
        parts.append(
            f"<section><h2 class='{css_class}'>Модуль {index}. {_escape(module.title)}</h2>"
        )
        items = parsed_by_module[module.id]
        if not items:
            parts.append("<p class='muted'>В модуле пока нет шагов.</p>")
        for step_index, (step, rev, parsed) in enumerate(items, 1):
            parts.append(
                _render_step_pdf(
                    step, rev, parsed, f"{index}.{step_index}", images, include_answers
                )
            )
        parts.append("</section>")

    parts.append("</body></html>")
    return "".join(parts)


def _render_step_pdf(
    step: Step, rev: StepRevision, parsed, number: str, images, include_answers: bool
) -> str:
    content = parsed.content.model_dump(mode="json")
    answer_key = parsed.answer_key.model_dump(mode="json")

    raw_body = content.get("body") or content.get("question") or content.get("statement")
    title, body = _split_title(raw_body)
    body_html = _render_doc(body, images)

    type_label = _STEP_TYPE_LABELS.get(step.type, step.type)
    score_part = f" · {rev.max_score} б." if rev.max_score else ""
    hidden = (
        " · <span class='hidden-flag'>скрыт</span>" if step.is_hidden else ""
    )

    parts: list[str] = [
        "<article class='step'>",
        f"<div><span class='step-type'>{_escape(type_label)}</span>"
        f"<span class='step-meta'> · шаг {number}{score_part}{hidden}</span></div>",
    ]
    if title:
        parts.append(f"<h3 class='step-title'>{_escape(title)}</h3>")
    parts.append(body_html)

    extra = _render_step_specific(step.type, content, answer_key)
    if extra:
        parts.append(extra)

    if include_answers:
        key = _render_answer_key(step.type, content, answer_key, images)
        if key:
            parts.append(key)

    parts.append("</article>")
    return "".join(parts)


def _render_step_specific(step_type: str, content: dict, answer_key: dict) -> str:
    if step_type in ("single_choice", "multiple_choice"):
        options = content.get("options") or []
        correct = answer_key.get("correct")
        correct_set = {correct} if isinstance(correct, str) else set(correct or [])
        items = [
            f"<li>{'<span class=\"correct-mark\">✓</span> ' if o.get('id') in correct_set else '<span class=\"wrong-mark\">·</span> '}"
            f"{_escape(o.get('text') or '')}</li>"
            for o in options
        ]
        return f"<div style='margin-top:8pt'><h4>Варианты</h4><ul>{''.join(items)}</ul></div>"

    if step_type == "programming":
        rows: list[str] = []
        samples = content.get("samples") or []
        if samples:
            rows.append("<h4>Примеры</h4>")
            for i, s in enumerate(samples, 1):
                rows.append(
                    f"<div class='test-row'><strong>Пример {i}</strong>"
                    f"<pre>Ввод:\n{_escape(s.get('input') or '')}</pre>"
                    f"<pre>Вывод:\n{_escape(s.get('output') or '')}</pre></div>"
                )
        template = content.get("template")
        if template:
            rows.append(f"<h4>Шаблон кода</h4><pre><code>{_escape(template)}</code></pre>")
        return f"<div style='margin-top:8pt'>{''.join(rows)}</div>" if rows else ""
    return ""


def _render_answer_key(
    step_type: str, content: dict, answer_key: dict, images
) -> str:
    rows: list[str] = []
    if step_type in ("single_choice", "multiple_choice"):
        correct = answer_key.get("correct")
        ids = [correct] if isinstance(correct, str) else list(correct or [])
        options = {o.get("id"): o.get("text") for o in (content.get("options") or [])}
        if ids:
            items = "".join(
                f"<li>{_escape(options.get(oid) or f'<{oid}>')}</li>" for oid in ids
            )
            rows.append(f"<ul>{items}</ul>")

    elif step_type == "free_text":
        ref = _render_doc(answer_key.get("reference"), images)
        if ref:
            rows.append("<div><strong>Эталон:</strong></div>" + ref)
        criteria = answer_key.get("criteria")
        if criteria:
            rows.append(f"<div><strong>Критерии:</strong> {_escape(criteria)}</div>")
        files = answer_key.get("files") or []
        if files:
            rows.append(
                "<div><strong>Файлы эталона:</strong> "
                + ", ".join(f"#{fid}" for fid in files)
                + "</div>"
            )

    elif step_type == "programming":
        ref = answer_key.get("reference_solution")
        if ref:
            rows.append(
                "<div><strong>Эталонное решение:</strong></div>"
                f"<pre><code>{_escape(ref)}</code></pre>"
            )
        groups = answer_key.get("test_groups") or []
        if groups:
            rows.append("<div><strong>Скрытые тесты:</strong></div>")
            for group in groups:
                rows.append(
                    f"<div class='test-group'><span class='test-group-name'>"
                    f"{_escape(group.get('name') or 'группа')}</span> · "
                    f"{group.get('points', 0)} б."
                )
                for i, test in enumerate(group.get("tests") or [], 1):
                    inp = test.get("input") or (
                        f"<файл #{test['input_file']}>" if test.get("input_file") else ""
                    )
                    out = test.get("output") or (
                        f"<файл #{test['output_file']}>" if test.get("output_file") else ""
                    )
                    rows.append(
                        f"<div class='test-row'>Тест {i}"
                        f"<pre>Ввод:\n{_escape(inp)}</pre>"
                        f"<pre>Ожидание:\n{_escape(out)}</pre></div>"
                    )
                rows.append("</div>")

    if not rows:
        return ""
    return (
        "<section class='answer-key'><h5>Ключ ответа · для проверяющих</h5>"
        + "".join(rows)
        + "</section>"
    )