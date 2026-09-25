<script setup lang="ts">
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { getApiErrorMessage } from "@/api/errors";
import { reviewApi } from "@/modules/curator/reviews/api";
import {
  attemptNumber,
  reviewTaskTitle,
  stepNumber,
  studentInitials,
  studentLabel,
  waitingLabel,
} from "@/modules/curator/reviews/presentation";
import type { CourseQueue, ReviewListItem } from "@/modules/curator/reviews/types";
import { CURATOR_REVIEW_ROUTE } from "../review/constants";

const courses = ref<CourseQueue[]>([]);
const expanded = ref(new Set<number>());
const rows = ref<Record<number, ReviewListItem[]>>({});
const loadingRows = ref(new Set<number>());
const loading = ref(true);
const error = ref("");

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    courses.value = await reviewApi.courses();
    expanded.value = new Set();
    rows.value = {};
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    loading.value = false;
  }
}

async function toggle(course: CourseQueue): Promise<void> {
  const next = new Set(expanded.value);
  if (next.has(course.course_id)) {
    next.delete(course.course_id);
    expanded.value = next;
    return;
  }
  next.add(course.course_id);
  expanded.value = next;
  if (rows.value[course.course_id]) return;

  loadingRows.value = new Set([...loadingRows.value, course.course_id]);
  try {
    const items =
      course.total <= course.submissions.length
        ? course.submissions
        : await reviewApi.pendingForCourse(course.course_id);
    rows.value = { ...rows.value, [course.course_id]: items };
  } catch (cause) {
    error.value = getApiErrorMessage(cause);
  } finally {
    const remaining = new Set(loadingRows.value);
    remaining.delete(course.course_id);
    loadingRows.value = remaining;
  }
}

onMounted(load);
</script>

<template>
  <section class="review-courses">
    <h2>Работы по курсам</h2>
    <div v-if="loading" class="review-courses__state" role="status">Загружаем работы…</div>
    <div v-else-if="error && !courses.length" class="review-courses__state" role="alert">
      {{ error }} <button type="button" @click="load">Повторить</button>
    </div>
    <div v-else-if="!courses.length" class="review-courses__state">Работ на проверку пока нет.</div>
    <template v-else>
      <p v-if="error" class="review-courses__error" role="alert">{{ error }}</p>
      <div class="review-courses__columns" aria-hidden="true">
        <span></span>
        <span>УЧЕНИК</span>
        <span>ЗАДАНИЕ</span>
        <span>ПОПЫТКА</span>
        <span>ЖДЁТ</span>
        <span></span>
      </div>
      <article v-for="course in courses" :key="course.course_id" class="review-course">
        <div class="review-course__heading" @click="toggle(course)">
          <button
            type="button"
            class="review-course__toggle"
            :aria-expanded="expanded.has(course.course_id)"
            :aria-controls="`review-course-${course.course_id}`"
          >
            <svg class="review-course__chevron" viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="m5 7.5 5 5 5-5"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            <strong>{{ course.course_title }}</strong>
          </button>
          <span class="review-course__count">
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.6" />
              <path
                d="M10 6v4l2.7 1.6"
                stroke="currentColor"
                stroke-width="1.6"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
            {{ course.total }} на проверке
          </span>
          <RouterLink
            :to="{ name: CURATOR_REVIEW_ROUTE.name, params: { courseId: course.course_id } }"
            class="review-course__all"
            @click.stop
          >
            Проверить все
            <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
              <path
                d="M4 10h11m-4-4 4 4-4 4"
                stroke="currentColor"
                stroke-width="1.8"
                stroke-linecap="round"
                stroke-linejoin="round"
              />
            </svg>
          </RouterLink>
        </div>
        <div v-if="expanded.has(course.course_id)" :id="`review-course-${course.course_id}`">
          <div
            v-if="loadingRows.has(course.course_id)"
            class="review-course__loading"
            role="status"
          >
            Загружаем работы…
          </div>
          <div v-else-if="!rows[course.course_id]?.length" class="review-course__loading">
            Работ на проверку больше нет.
          </div>
          <div v-for="item in rows[course.course_id] ?? []" :key="item.id" class="review-work-row">
            <span class="review-work-row__avatar" aria-hidden="true">{{
              studentInitials(item)
            }}</span>
            <strong class="review-work-row__student">{{ studentLabel(item) }}</strong>
            <span class="review-work-row__task">
              <b>{{ reviewTaskTitle(item) }}</b>
              <span>· {{ item.module_title }} · {{ stepNumber(item) }}</span>
            </span>
            <span class="review-work-row__attempt">{{ attemptNumber(item) }}-я</span>
            <span
              class="review-work-row__wait"
              :class="{ 'review-work-row__wait--late': item.is_late }"
            >
              {{ waitingLabel(item.waiting_seconds) }}
            </span>
            <RouterLink
              :to="{
                name: CURATOR_REVIEW_ROUTE.name,
                params: { courseId: course.course_id, submissionId: item.id },
              }"
              class="review-work-row__action"
            >
              Проверить
            </RouterLink>
          </div>
        </div>
      </article>
    </template>
  </section>
</template>

<style scoped>
.review-courses {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-width: 1440px;
  margin: 0 auto;
  font-size: 14px;
  line-height: 1.5;
}
.review-courses h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
}
.review-courses__columns,
.review-work-row {
  display: grid;
  grid-template-columns: 32px 110px minmax(0, 1fr) 100px 88px 110px;
  align-items: center;
  gap: 12px;
}
.review-courses__columns {
  padding: 10px 16px;
  color: var(--color-muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.08em;
}
.review-course {
  overflow: hidden;
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.review-course__heading {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 12px 14px;
  cursor: pointer;
}
.review-course__toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-text);
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.review-course__toggle strong {
  font-size: 16px;
  font-weight: 700;
}
.review-course__chevron {
  width: 20px;
  height: 20px;
  flex: none;
  color: var(--color-muted);
  transition: transform 0.15s;
}
.review-course__toggle[aria-expanded="true"] .review-course__chevron {
  transform: rotate(180deg);
}
.review-course__count {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: none;
  padding: 2px 9px;
  border-radius: 999px;
  background: #efebfe;
  color: #6e4fe8;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}
.review-course__count svg,
.review-course__all svg {
  width: 16px;
  height: 16px;
  flex: none;
}
.review-course__all {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex: none;
  margin-left: 8px;
  color: var(--color-primary);
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.review-course__all:hover {
  text-decoration: underline;
}
.review-work-row {
  padding: 10px 14px;
  border-top: 1px solid var(--color-border);
  min-height: 54px;
}
.review-work-row__avatar {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border-radius: 50%;
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-size: 12px;
  font-weight: 700;
}
.review-work-row__student,
.review-work-row__task,
.review-work-row__attempt,
.review-work-row__wait {
  min-width: 0;
}
.review-work-row__task {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.review-work-row__task b {
  font-weight: 600;
}
.review-work-row__task span,
.review-work-row__attempt,
.review-work-row__wait {
  color: var(--color-muted);
}
.review-work-row__wait--late {
  color: var(--color-warning);
  font-weight: 700;
}
.review-work-row__action {
  display: grid;
  min-height: 32px;
  place-items: center;
  padding: 0 12px;
  border: 1px solid var(--color-border);
  border-radius: 10px;
  color: var(--color-text);
  font-weight: 600;
  text-decoration: none;
}
.review-work-row__action:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.review-course__loading,
.review-courses__state {
  padding: 18px;
  color: var(--color-muted);
}
.review-courses__state {
  border: 1px solid var(--color-border);
  border-radius: 16px;
  background: #fff;
}
.review-courses__error {
  color: var(--color-danger);
}
@media (max-width: 1000px) {
  .review-courses__columns {
    display: none;
  }
  .review-work-row {
    grid-template-columns: 32px minmax(0, 1fr) auto;
    grid-template-areas:
      "avatar student action"
      ". task task"
      ". attempt wait";
  }
  .review-work-row__avatar {
    grid-area: avatar;
  }
  .review-work-row__student {
    grid-area: student;
  }
  .review-work-row__task {
    grid-area: task;
  }
  .review-work-row__attempt {
    grid-area: attempt;
  }
  .review-work-row__wait {
    grid-area: wait;
  }
  .review-work-row__action {
    grid-area: action;
  }
}
@media (max-width: 650px) {
  .review-course__heading {
    flex-wrap: wrap;
  }
  .review-course__toggle {
    flex-basis: 100%;
  }
  .review-course__all {
    margin-left: auto;
  }
}
</style>
