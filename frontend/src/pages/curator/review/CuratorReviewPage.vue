<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import { reviewApi } from "@/modules/curator/reviews/api";
import ReviewAssessment from "@/modules/curator/reviews/ReviewAssessment.vue";
import ReviewSubmissionContent from "@/modules/curator/reviews/ReviewSubmissionContent.vue";
import {
  nextReviewId,
  reviewTaskTitle,
  selectedReviewId,
  stepNumber,
  studentLabel,
  waitingLabel,
} from "@/modules/curator/reviews/presentation";
import type { ReviewDetail, ReviewListItem } from "@/modules/curator/reviews/types";
import { CURATOR_REVIEW_ROUTE } from "./constants";
import { CURATOR_REVIEWS_ROUTE } from "../reviews/constants";

const route = useRoute();
const router = useRouter();
const courseId = computed(() => Number(route.params.courseId));
const selectedId = computed(() => Number(route.params.submissionId) || null);
const queue = ref<ReviewListItem[]>([]);
const detail = ref<ReviewDetail | null>(null);
const loadedCourseId = ref<number | null>(null);
const loadingQueue = ref(true);
const loadingDetail = ref(false);
const error = ref("");
let queueVersion = 0;
let detailVersion = 0;

const courseTitle = computed(
  () => detail.value?.course_title ?? queue.value[0]?.course_title ?? `Курс #${courseId.value}`,
);

async function loadDetail(id: number): Promise<void> {
  const current = ++detailVersion;
  detail.value = null;
  loadingDetail.value = true;
  error.value = "";
  try {
    const result = await reviewApi.detail(id);
    if (current !== detailVersion || result.course_id !== courseId.value) return;
    detail.value = result;
  } catch (cause) {
    if (current === detailVersion) error.value = getApiErrorMessage(cause);
  } finally {
    if (current === detailVersion) loadingDetail.value = false;
  }
}

async function loadQueue(id: number): Promise<void> {
  const current = ++queueVersion;
  ++detailVersion;
  loadedCourseId.value = null;
  queue.value = [];
  detail.value = null;
  loadingQueue.value = true;
  error.value = "";
  if (!Number.isInteger(id) || id <= 0) {
    error.value = "Курс не найден.";
    loadingQueue.value = false;
    return;
  }
  try {
    const items = await reviewApi.pendingForCourse(id);
    if (current !== queueVersion) return;
    queue.value = items;
    loadedCourseId.value = id;
    if (!items.length) return;
    const selected = selectedReviewId(items, selectedId.value);
    if (selected === null) return;
    if (selected !== selectedId.value) {
      await router.replace({
        name: CURATOR_REVIEW_ROUTE.name,
        params: { courseId: id, submissionId: selected },
      });
    } else {
      await loadDetail(selected);
    }
  } catch (cause) {
    if (current === queueVersion) error.value = getApiErrorMessage(cause);
  } finally {
    if (current === queueVersion) loadingQueue.value = false;
  }
}

watch(courseId, (id) => void loadQueue(id), { immediate: true });
watch(selectedId, (id) => {
  if (id && loadedCourseId.value === courseId.value && queue.value.some((item) => item.id === id)) {
    void loadDetail(id);
  }
});

async function afterSaved(id: number): Promise<void> {
  const next = nextReviewId(queue.value, id);
  queue.value = queue.value.filter((item) => item.id !== id);
  detail.value = null;
  if (next === null) {
    await router.replace({ name: CURATOR_REVIEWS_ROUTE.name });
    return;
  }
  await router.replace({
    name: CURATOR_REVIEW_ROUTE.name,
    params: { courseId: courseId.value, submissionId: next },
  });
}
</script>

<template>
  <section class="review-workspace" aria-label="Проверка работ по курсу">
    <aside class="review-workspace__queue" aria-label="Работы курса">
      <RouterLink :to="CURATOR_REVIEWS_ROUTE.path" class="review-workspace__back">
        ← Работы по курсам
      </RouterLink>
      <h2>{{ courseTitle }}</h2>
      <p>{{ queue.length }} работ на проверке</p>
      <div v-if="loadingQueue" class="review-workspace__status" role="status">
        Загружаем очередь…
      </div>
      <nav v-else class="review-workspace__items" aria-label="Список работ на проверку">
        <RouterLink
          v-for="item in queue"
          :key="item.id"
          :to="{
            name: CURATOR_REVIEW_ROUTE.name,
            params: { courseId: item.course_id, submissionId: item.id },
          }"
          class="review-workspace__item"
          :class="{ 'review-workspace__item--active': item.id === selectedId }"
          :aria-current="item.id === selectedId ? 'true' : undefined"
        >
          <span class="review-workspace__item-top">
            <b>{{ studentLabel(item) }}</b>
            <span>{{ waitingLabel(item.waiting_seconds) }}</span>
          </span>
          <small>{{ reviewTaskTitle(item) }} · {{ stepNumber(item) }}</small>
          <span v-if="item.is_late" class="review-workspace__badge">После дедлайна</span>
        </RouterLink>
      </nav>
      <span class="review-workspace__hint">После решения откроется следующая работа в списке</span>
    </aside>

    <div v-if="error" class="review-workspace__message" role="alert">
      {{ error }}
      <button type="button" @click="loadQueue(courseId)">Повторить</button>
    </div>
    <div v-else-if="loadingQueue || loadingDetail" class="review-workspace__message" role="status">
      Загружаем работу…
    </div>
    <div v-else-if="!queue.length" class="review-workspace__message">
      В этом курсе больше нет работ на проверку.
      <RouterLink :to="CURATOR_REVIEWS_ROUTE.path">К списку курсов</RouterLink>
    </div>
    <ReviewSubmissionContent v-else-if="detail" :detail="detail" />
    <ReviewAssessment v-if="detail && !loadingDetail" :detail="detail" @saved="afterSaved" />
  </section>
</template>

<style scoped>
.review-workspace {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr) 330px;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--color-bg);
  font-size: 14px;
  line-height: 1.5;
}
.review-workspace__queue {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  min-height: 0;
  padding: 18px 14px;
  border-right: 1px solid var(--color-border);
  background: #fff;
}
.review-workspace__back {
  color: var(--color-primary);
  text-decoration: none;
}
.review-workspace__back:hover {
  text-decoration: underline;
}
.review-workspace__queue h2 {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 700;
}
.review-workspace__queue > p {
  margin: 0 0 6px;
  color: var(--color-muted);
}
.review-workspace__items {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.review-workspace__item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 9px 11px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  background: #fff;
  color: var(--color-text);
  text-decoration: none;
}
.review-workspace__item--active {
  border: 2px solid var(--color-primary);
  background: var(--color-primary-soft);
}
.review-workspace__item-top {
  display: flex;
  justify-content: space-between;
  gap: 6px;
}
.review-workspace__item-top b {
  font-weight: 600;
}
.review-workspace__item-top > span,
.review-workspace__item small,
.review-workspace__hint {
  color: var(--color-muted);
  font-size: 12px;
}
.review-workspace__item small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-workspace__badge {
  align-self: flex-start;
  margin-top: 2px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--color-warning-soft);
  color: var(--color-warning);
  font-size: 12px;
  font-weight: 600;
}
.review-workspace__hint {
  margin-top: auto;
}
.review-workspace__message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 12px;
  padding: 24px;
  color: var(--color-muted);
}
.review-workspace__message button,
.review-workspace__message a {
  border: 0;
  background: transparent;
  color: var(--color-primary);
  font: inherit;
  cursor: pointer;
}
@media (max-width: 1150px) {
  .review-workspace {
    grid-template-columns: 220px minmax(320px, 1fr) 280px;
    overflow-x: auto;
  }
}
@media (max-width: 767px) {
  .review-workspace {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 100%;
    overflow: visible;
  }
  .review-workspace__queue {
    max-height: 260px;
    flex: none;
  }
  .review-workspace__items {
    min-height: 100px;
  }
  .review-workspace__hint {
    display: none;
  }
}
</style>
