<script setup lang="ts">
import { computed } from "vue";
import type { CourseListItem, StudentNotification } from "../types";
import { notificationPresentation } from "../presentation";

const props = defineProps<{
  courses: CourseListItem[];
  notifications: StudentNotification[];
}>();

const points = computed(() =>
  props.courses.reduce((sum, course) => sum + course.progress.points_earned, 0),
);
const pointsMax = computed(() =>
  props.courses.reduce((sum, course) => sum + course.progress.points_max, 0),
);
const pointsPercent = computed(() =>
  pointsMax.value ? Math.min(100, Math.round((points.value / pointsMax.value) * 100)) : 0,
);
const recent = computed(() => props.notifications.slice(0, 2));
</script>

<template>
  <aside class="student-snapshot" aria-label="Баллы и последние события">
    <section class="student-points">
      <div class="student-points-heading">
        <strong>Мои баллы</strong>
        <span>{{ pointsMax ? `из ${pointsMax}` : "" }}</span>
      </div>
      <div class="student-points-value">{{ points }}</div>
      <div class="student-points-track" aria-hidden="true">
        <span :style="{ width: `${pointsPercent}%` }" />
      </div>
      <p>{{ pointsPercent }}% от доступных сейчас баллов</p>
    </section>

    <section class="student-news">
      <strong class="student-news-title">Что нового</strong>
      <div v-if="!recent.length" class="student-news-empty">Новых событий пока нет.</div>
      <article
        v-for="notification in recent"
        :key="notification.id"
        class="student-news-card"
        :class="`student-news-card--${notificationPresentation(notification).tone}`"
      >
        <b>{{ notificationPresentation(notification).title }}</b>
        <span>{{ notificationPresentation(notification).description }}</span>
      </article>
    </section>
  </aside>
</template>

<style scoped>
.student-snapshot {
  width: 340px;
  min-width: 0;
  padding: 20px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.student-points {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 14px;
  border-bottom: 1px solid #e1e6f0;
}
.student-points-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}
.student-points-heading strong {
  font-size: 15px;
}
.student-points-heading span {
  color: #68748a;
  font-size: 13px;
}
.student-points-value {
  font-size: 36px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
}
.student-points-track {
  height: 8px;
  overflow: hidden;
  border-radius: 999px;
  background: #e1e6f0;
}
.student-points-track span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #3457f0;
}
.student-points p {
  margin: 0;
  color: #4a546b;
  font-size: 13px;
}
.student-news {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
}
.student-news-title {
  font-size: 15px;
}
.student-news-empty {
  padding: 12px 0;
  color: #68748a;
  font-size: 14px;
}
.student-news-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 11px 13px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.4;
}
.student-news-card b {
  font-size: 13px;
}
.student-news-card span {
  color: #334155;
}
.student-news-card--success {
  background: #e4f5ec;
}
.student-news-card--success b {
  color: #17915a;
}
.student-news-card--warning {
  background: #fff1e6;
}
.student-news-card--warning b {
  color: #b8520f;
}
.student-news-card--info {
  background: #eaf0fe;
}
.student-news-card--info b {
  color: #3457f0;
}
.student-news-card--neutral {
  background: #f0f2f6;
}
.student-news-card--neutral b {
  color: #4a546b;
}
@media (max-width: 1100px) {
  .student-snapshot {
    width: auto;
  }
}
</style>
