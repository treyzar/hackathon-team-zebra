import type { RichDocument, RichNode } from "./types";

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };
    return entities[character] ?? character;
  });
}

function safeHref(value: unknown): string | null {
  if (typeof value !== "string") return null;
  try {
    const url = new URL(value, "https://example.invalid");
    return ["https:", "http:", "mailto:"].includes(url.protocol) ? escapeHtml(value) : null;
  } catch {
    return null;
  }
}

function renderNodes(nodes: RichNode[] | undefined, imageUrls: Map<number, string>): string {
  return (nodes ?? []).map((node) => renderNode(node, imageUrls)).join("");
}

function renderNode(node: RichNode, imageUrls: Map<number, string>): string {
  if (node.type === "text") {
    let html = escapeHtml(node.text ?? "");
    for (const mark of node.marks ?? []) {
      const tag = {
        bold: "strong",
        italic: "em",
        underline: "u",
        strike: "s",
        code: "code",
      }[mark.type ?? ""];
      if (tag) html = `<${tag}>${html}</${tag}>`;
      if (mark.type === "link") {
        const href = safeHref(mark.attrs?.href);
        if (href)
          html = `<a href="${href}" target="_blank" rel="noopener noreferrer nofollow">${html}</a>`;
      }
    }
    return html;
  }
  if (node.type === "image") {
    const id = Number(node.attrs?.file_id);
    const url = imageUrls.get(id);
    return url && /^https?:\/\//i.test(url)
      ? `<img src="${escapeHtml(url)}" alt="Иллюстрация к заданию" loading="lazy">`
      : "";
  }
  if (node.type === "hardBreak") return "<br>";
  const children = renderNodes(node.content, imageUrls);
  switch (node.type) {
    case "doc":
      return children;
    case "paragraph":
      return `<p>${children || "<br>"}</p>`;
    case "heading": {
      const level = Math.max(2, Math.min(4, Number(node.attrs?.level) || 2));
      return `<h${level}>${children}</h${level}>`;
    }
    case "bulletList":
      return `<ul>${children}</ul>`;
    case "orderedList":
      return `<ol>${children}</ol>`;
    case "listItem":
      return `<li>${children}</li>`;
    case "blockquote":
      return `<blockquote>${children}</blockquote>`;
    case "codeBlock":
      return `<pre><code>${children}</code></pre>`;
    case "horizontalRule":
      return "<hr>";
    default:
      return children;
  }
}

export function richTextImageIds(doc: RichDocument): number[] {
  const ids = new Set<number>();
  function visit(nodes: RichNode[] | undefined): void {
    for (const node of nodes ?? []) {
      if (node.type === "image") {
        const id = Number(node.attrs?.file_id);
        if (Number.isInteger(id) && id > 0) ids.add(id);
      }
      visit(node.content);
    }
  }
  visit(doc.content);
  return [...ids];
}

export function renderRichText(
  doc: RichDocument | null,
  imageUrls = new Map<number, string>(),
): string {
  return doc ? renderNodes(doc.content, imageUrls) : "";
}
