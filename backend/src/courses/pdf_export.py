from __future__ import annotations

import asyncio
import base64 as _b64
import html as _html
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from weasyprint import CSS, HTML

from courses import service
from courses.models import Course, Step, StepRevision
from files.models import File, FileStatus

_PDF_CSS = CSS(filename=str(Path(__file__).with_name("pdf_export.css")))

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


def _render_doc(node: Any, images: dict[int, str]) -> str:
    if not isinstance(node, dict) or node.get("type") != "doc":
        return ""
    return _render_node(node, images)


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
    if not ids:
        return {}
    from files import storage

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
    return await asyncio.to_thread(
        lambda: HTML(string=html).write_pdf(stylesheets=[_PDF_CSS])
    )


def _build_pdf_html(
    course: Course, modules, parsed_by_module, images, include_answers: bool
) -> str:
    total_steps = sum(len(v) for v in parsed_by_module.values())
    visibility = "опубликован" if course.is_published else "черновик"
    access = (
        "по очереди" if course.step_access.value == "sequential" else "все шаги сразу"
    )
    description_html = _render_doc(course.description, images)

    parts: list[str] = [
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>",
        f"<title>{_escape(course.title)}</title>",
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

    raw_body = (
        content.get("body") or content.get("question") or content.get("statement")
    )
    title, body = _split_title(raw_body)
    body_html = _render_doc(body, images)

    type_label = _STEP_TYPE_LABELS.get(step.type, step.type)
    score_part = f" · {rev.max_score} б." if rev.max_score else ""
    hidden = " · <span class='hidden-flag'>скрыт</span>" if step.is_hidden else ""

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
            f"<li>{'<span class="correct-mark">✓</span> ' if o.get('id') in correct_set else '<span class="wrong-mark">·</span> '}"
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
            rows.append(
                f"<h4>Шаблон кода</h4><pre><code>{_escape(template)}</code></pre>"
            )
        return f"<div style='margin-top:8pt'>{''.join(rows)}</div>" if rows else ""
    return ""


def _render_answer_key(step_type: str, content: dict, answer_key: dict, images) -> str:
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
                        f"<файл #{test['input_file']}>"
                        if test.get("input_file")
                        else ""
                    )
                    out = test.get("output") or (
                        f"<файл #{test['output_file']}>"
                        if test.get("output_file")
                        else ""
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
