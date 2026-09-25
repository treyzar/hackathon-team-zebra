<script setup lang="ts">
import { ref, watch } from "vue";
import { reviewApi } from "./api";
import type { ReviewFile } from "./types";

const props = defineProps<{ ids: number[]; label: string }>();
const files = ref<Record<number, ReviewFile>>({});
let version = 0;

watch(
  () => props.ids,
  async (ids) => {
    const current = ++version;
    files.value = {};
    const resolved = await Promise.all(
      ids.map(async (id) => {
        try {
          const file = await reviewApi.file(id);
          return /^https?:\/\//i.test(file.download_url) ? ([id, file] as const) : null;
        } catch {
          return null;
        }
      }),
    );
    if (current === version) {
      files.value = Object.fromEntries(resolved.filter((item) => item !== null));
    }
  },
  { immediate: true },
);
</script>

<template>
  <div v-if="ids.length" class="review-files">
    <div v-for="(id, index) in ids" :key="id" class="review-files__item">
      <a
        v-if="files[id]?.mime.startsWith('image/')"
        :href="files[id]?.download_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <img :src="files[id]?.download_url" :alt="files[id]?.filename || `${label} ${index + 1}`" />
      </a>
      <a
        :href="files[id]?.download_url || undefined"
        target="_blank"
        rel="noopener noreferrer"
        :aria-disabled="!files[id]"
        @click="!files[id] && $event.preventDefault()"
      >
        📎 {{ files[id]?.filename || `${label} ${index + 1}` }}
      </a>
    </div>
  </div>
</template>

<style scoped>
.review-files {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.review-files__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-width: 0;
}
.review-files img {
  display: block;
  max-width: 100%;
  max-height: 320px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  object-fit: contain;
}
.review-files a {
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
}
.review-files a:hover:not([aria-disabled="true"]) {
  text-decoration: underline;
}
.review-files a[aria-disabled="true"] {
  color: var(--color-muted);
  cursor: default;
}
</style>
