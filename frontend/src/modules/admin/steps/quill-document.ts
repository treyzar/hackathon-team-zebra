import type { RichText } from "../shared/types";

export interface QuillOp {
  insert: string | { image: string };
  attributes?: Record<string, unknown>;
}
type Node = Record<string, unknown>;

const IMAGE_TAG = "zebra-file-id=";

export function imageUrl(url: string, id: number): string {
  // Presigned URLs expire; only the stable file ID is written to the course revision.
  return `${url}#${IMAGE_TAG}${id}`;
}

function imageId(url: string): number | null {
  const match = url.match(/#zebra-file-id=(\d+)$/);
  return match ? Number(match[1]) : null;
}

function marks(attributes: Record<string, unknown>): Node[] {
  const result: Node[] = [];
  for (const name of ["bold", "italic", "underline", "strike", "code"]) {
    if (attributes[name]) result.push({ type: name });
  }
  if (typeof attributes.link === "string")
    result.push({
      type: "link",
      attrs: { href: attributes.link, target: "_blank", rel: "noopener noreferrer nofollow" },
    });
  return result;
}

function block(inline: Node[], attributes: Record<string, unknown>): Node {
  const content = inline.length ? { content: inline } : {};
  if (typeof attributes.header === "number")
    return { type: "heading", attrs: { level: attributes.header }, ...content };
  if (attributes.blockquote)
    return { type: "blockquote", content: [{ type: "paragraph", ...content }] };
  if (attributes["code-block"]) return { type: "codeBlock", ...content };
  return { type: "paragraph", ...content };
}

export function quillOpsToDoc(ops: QuillOp[]): RichText {
  const content: Node[] = [];
  let inline: Node[] = [];
  function endLine(attributes: Record<string, unknown>): void {
    const list = attributes.list;
    const codeBlock = attributes["code-block"];

    if (list === "ordered" || list === "bullet") {
      const type = list === "ordered" ? "orderedList" : "bulletList";
      const item = {type: "listItem", content: [block(inline, attributes)]};
      inline = [];
      const previous = content[content.length - 1];
      if (previous?.type === type) (previous.content as Node[]).push(item);
      else content.push({type, content: [item]});
      return;
    }

    if (codeBlock) {
      const text = inline
        .map((node) => (node.type === "text" ? String(node.text ?? "") : ""))
        .join("");
      inline = [];
      const language = codeBlock === true ? "plain" : String(codeBlock);
      const previous = content[content.length - 1];
      if (previous?.type === "codeBlock" &&
        (previous.attrs as Record<string, unknown> | undefined)?.language === language) {
        const prev = previous.content as { type: string; text?: string }[];
        const head = prev[0];
        prev[0] = { type: "text", text: head?.text ? `${head.text}\n${text}` : text };
        return;
      }
      content.push({
        type: "codeBlock",
        attrs: { language },
        content: [{ type: "text", text }],
      });
      return;
    }

  const line = block(inline, attributes);
  inline = [];
  content.push(line);
}
  for (const op of ops) {
    // Quill stores block formatting on newline operations; ProseMirror stores it on the block node.
    if (typeof op.insert === "string") {
      const pieces = op.insert.split("\n");
      pieces.forEach((piece, index) => {
        if (piece)
          inline.push({
            type: "text",
            text: piece,
            ...(marks(op.attributes ?? {}).length ? { marks: marks(op.attributes ?? {}) } : {}),
          });
        if (index < pieces.length - 1) endLine(op.attributes ?? {});
      });
    } else if (typeof op.insert.image === "string") {
      const id = imageId(op.insert.image);
      if (id === null)
        throw new Error("Изображение нужно добавить через кнопку загрузки в редакторе.");
      inline.push({ type: "image", attrs: { file_id: id } });
    }
  }
  if (inline.length) endLine({});
  return { type: "doc", content: content.length ? content : [{ type: "paragraph" }] };
}

function inlineOps(nodes: unknown[], ops: QuillOp[], urls: Map<number, string>): void {
  for (const item of nodes) {
    if (!item || typeof item !== "object") continue;
    const node = item as Node;
    if (node.type === "text") {
      const attributes: Record<string, unknown> = {};
      for (const mark of Array.isArray(node.marks) ? node.marks : []) {
        const item = mark as Node;
        if (item.type === "link") attributes.link = (item.attrs as Node)?.href;
        else if (typeof item.type === "string") attributes[item.type] = true;
      }
      ops.push({
        insert: String(node.text ?? ""),
        ...(Object.keys(attributes).length ? { attributes } : {}),
      });
    }
    if (node.type === "image") {
      const id = Number((node.attrs as Node)?.file_id);
      const url = urls.get(id);
      if (url) ops.push({ insert: { image: imageUrl(url, id) } });
    }
  }
}

export function docImageIds(doc: RichText): number[] {
  const ids: number[] = [];
  function visit(nodes: unknown[]): void {
    for (const item of nodes) {
      if (!item || typeof item !== "object") continue;
      const node = item as Node;
      if (node.type === "image") {
        const id = Number((node.attrs as Node)?.file_id);
        if (Number.isInteger(id) && id > 0) ids.push(id);
      }
      if (Array.isArray(node.content)) visit(node.content);
    }
  }
  visit(doc.content);
  return [...new Set(ids)];
}

export function docToQuillOps(doc: RichText, urls: Map<number, string>): QuillOp[] {
  const ops: QuillOp[] = [];
  function visit(nodes: unknown[], list?: string): void {
    for (const item of nodes) {
      if (!item || typeof item !== "object") continue;
      const node = item as Node;
      if (node.type === "orderedList" || node.type === "bulletList") {
        visit(
          Array.isArray(node.content) ? node.content : [],
          node.type === "orderedList" ? "ordered" : "bullet",
        );
      } else if (node.type === "listItem") {
        visit(Array.isArray(node.content) ? node.content : [], list);
      } else if (node.type === "blockquote") {
        for (const child of Array.isArray(node.content) ? node.content : []) {
          const paragraph = child as Node;
          inlineOps(Array.isArray(paragraph.content) ? paragraph.content : [], ops, urls);
          ops.push({ insert: "\n", attributes: { blockquote: true } });
        }
      } else if (node.type === "codeBlock") {
        const language = (node.attrs as Record<string, unknown> | undefined)?.language;
        const attributes: Record<string, unknown> = {
          "code-block": typeof language === "string" ? language : true,
        };
        const text = (Array.isArray(node.content) ? node.content : [])
          .map((child) => (child as { text?: string }).text ?? "")
          .join("");
        for (const line of text.split("\n")) {
          if (line) ops.push({ insert: line });
          ops.push({ insert: "\n", attributes });
        }
      } else {
        inlineOps(Array.isArray(node.content) ? node.content : [], ops, urls);
        const attributes: Record<string, unknown> = {};
        if (node.type === "heading") attributes.header = Number((node.attrs as Node)?.level ?? 1);
        if (node.type === "blockquote") attributes.blockquote = true;
        if (list) attributes.list = list;
        ops.push({ insert: "\n", ...(Object.keys(attributes).length ? { attributes } : {}) });
      }
    }
  }
  visit(doc.content);
  return ops.length ? ops : [{ insert: "\n" }];
}

export function hasDocContent(doc: RichText): boolean {
  function hasContent(nodes: unknown[]): boolean {
    return nodes.some((part) => {
      const item = part as Node;
      return (
        item?.type === "image" ||
        (item?.type === "text" && Boolean(String(item.text).trim())) ||
        (Array.isArray(item?.content) && hasContent(item.content))
      );
    });
  }
  return hasContent(doc.content);
}
