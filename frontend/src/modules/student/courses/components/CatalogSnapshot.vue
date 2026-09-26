<script setup lang="ts">
import { computed } from "vue";
import type { MyRating } from "../types";
import { ratingGoalText, ratingPlaceText, streakText } from "../presentation";

const props = defineProps<{
  rating: MyRating | null;
}>();

const place = computed(() => (props.rating ? ratingPlaceText(props.rating) : null));
const goal = computed(() => (props.rating ? ratingGoalText(props.rating) : null));
</script>

<template>
  <aside class="student-snapshot" aria-label="Мои баллы">
    <section class="student-points">
      <div class="student-points-heading">
        <strong>Мои баллы</strong>
        <span v-if="place">{{ place }}</span>
      </div>
      <template v-if="rating">
        <div class="student-points-value">{{ rating.total }}</div>
        <ul class="student-points-parts" aria-label="Из чего складываются баллы">
          <li v-for="course in rating.courses" :key="course.course_id">
            <span>{{ course.title }}</span>
            <b>{{ course.points }}</b>
          </li>
          <li class="student-points-streak">
            <span>{{ streakText(rating.streak) }}</span>
            <b>+{{ rating.streak.bonus }}</b>
          </li>
        </ul>
        <p v-if="goal">{{ goal }}</p>
        <p class="student-points-note">
          Серия: +2 балла за каждый день подряд, когда вы отправили решение с баллами или на
          проверку.
        </p>
      </template>
      <p v-else class="student-points-note">Не удалось загрузить рейтинг.</p>
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
.student-points-parts {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  font-size: 14px;
}
.student-points-parts li {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}
.student-points-parts span {
  min-width: 0;
  color: #334155;
  overflow-wrap: anywhere;
}
.student-points-parts b {
  flex: none;
  font-variant-numeric: tabular-nums;
}
.student-points-streak b {
  color: #17915a;
}
.student-points-note {
  color: #68748a !important;
}
.student-points p {
  margin: 0;
  color: #4a546b;
  font-size: 13px;
}
@media (max-width: 1100px) {
  .student-snapshot {
    width: auto;
  }
}
</style>
