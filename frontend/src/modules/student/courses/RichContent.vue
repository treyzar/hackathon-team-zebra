<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { getContentFileUrl } from "./api";
import { renderRichText, richTextImageIds } from "./rich-text";
import type { RichDocument } from "./types";

const props = defineProps<{ document: RichDocument | null }>();
const imageUrls = ref(new Map<number, string>());
const html = computed(() => renderRichText(props.document, imageUrls.value));
let version = 0;

watch(
  () => props.document,
  async (document) => {
    const current = ++version;
    imageUrls.value = new Map();
    if (!document) return;
    const urls = await Promise.all(
      richTextImageIds(document).map(async (id) => {
        try {
          return [id, await getContentFileUrl(id)] as const;
        } catch {
          return null;
        }
      }),
    );
    if (current === version)
      imageUrls.value = new Map(
        urls.filter((entry): entry is readonly [number, string] => entry !== null),
      );
  },
  { immediate: true },
);
</script>

<template>
  <div class="student-rich-content" v-html="html" />
</template>

<style scoped>
.student-rich-content {
  min-width: 0;
  overflow-wrap: anywhere;
  line-height: 1.7;
  color: #26334c;
}
.student-rich-content :deep(> :first-child) {
  margin-top: 0;
}
.student-rich-content :deep(> :last-child) {
  margin-bottom: 0;
}
.student-rich-content :deep(p) {
  margin: 0 0 13px;
}
.student-rich-content :deep(h2),
.student-rich-content :deep(h3),
.student-rich-content :deep(h4) {
  color: #0f172a;
  margin: 22px 0 10px;
  line-height: 1.25;
}
.student-rich-content :deep(h2) {
  font-size: 23px;
}
.student-rich-content :deep(h3) {
  font-size: 19px;
}
.student-rich-content :deep(h4) {
  font-size: 16px;
}
.student-rich-content :deep(ul),
.student-rich-content :deep(ol) {
  padding-left: 26px;
  margin: 0 0 16px;
}
.student-rich-content :deep(li) {
  margin: 5px 0;
}
.student-rich-content :deep(blockquote) {
  margin: 16px 0;
  border-left: 4px solid #aebeff;
  padding: 8px 18px;
  background: #f5f7ff;
}
.student-rich-content :deep(pre) {
  max-width: 100%;
  overflow: auto;
  padding: 16px;
  border-radius: 12px;
  background: #101a32;
  color: #ecf1ff;
}
.student-rich-content :deep(img) {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 16px auto;
  border-radius: 12px;
}
.student-rich-content :deep(a) {
  color: #3457f0;
  text-decoration: underline;
}
</style>
