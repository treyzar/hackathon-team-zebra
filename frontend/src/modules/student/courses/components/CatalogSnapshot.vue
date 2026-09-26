<script setup lang="ts">
import { computed } from "vue";
import type { MyRating } from "../types";
import { daysText, ratingGoal, ratingPlaceText, streakHint, streakWeek } from "../presentation";

const props = defineProps<{
  rating: MyRating | null;
}>();

const place = computed(() => (props.rating ? ratingPlaceText(props.rating) : null));
const goal = computed(() => (props.rating ? ratingGoal(props.rating) : null));
const week = computed(() => (props.rating ? streakWeek(props.rating.streak) : []));

// Course colours for the bar, in turn; the streak is always orange.
const COURSE_COLORS = ["#3457f0", "#8a9cf7", "#1f9d8b", "#7c4dcc", "#c2467a"];

// What the total is made of, in the order of the bar: courses, then streak.
const parts = computed(() => {
  const rating = props.rating;
  if (!rating) return [];
  return [
    ...rating.courses.map((course, index) => ({
      key: `course-${course.course_id}`,
      label: course.title,
      points: course.points,
      color: COURSE_COLORS[index % COURSE_COLORS.length]!,
    })),
    {
      key: "streak",
      label: rating.streak.days
        ? `Серия: ${daysText(rating.streak.days)} без пропусков`
        : "Серия: пока нет",
      points: rating.streak.bonus,
      color: "#f08a2c",
    },
  ];
});
const barTotal = computed(() => parts.value.reduce((sum, part) => sum + part.points, 0));
</script>

<template>
  <aside class="rating-widget" aria-label="Мой рейтинг">
    <template v-if="rating">
      <h2 class="rating-title">Мой рейтинг</h2>
      <div class="rating-total">
        <strong>{{ rating.total }}</strong>
        <span v-if="place">{{ place }}</span>
      </div>

      <div class="rating-bar" aria-hidden="true">
        <span
          v-for="part in parts.filter((item) => item.points > 0)"
          :key="part.key"
          :style="{ flexGrow: part.points / (barTotal || 1), background: part.color }"
        />
      </div>
      <ul class="rating-parts" aria-label="Из чего складывается рейтинг">
        <li v-for="part in parts" :key="part.key">
          <i class="rating-dot" :style="{ background: part.color }" aria-hidden="true" />
          <span>{{ part.label }}</span>
          <b>{{ part.points }}</b>
        </li>
      </ul>

      <p v-if="goal" class="rating-goal">
        {{ goal.before }}<b v-if="goal.points"> {{ goal.points }}</b
        >{{ goal.after }}
      </p>

      <section class="rating-streak" aria-label="Серия недели">
        <div class="rating-streak-head">
          <h3>Серия недели</h3>
          <span>+2 за день</span>
        </div>
        <ol class="rating-week">
          <li v-for="day in week" :key="day.label" :class="`rating-day--${day.state}`">
            <span class="rating-day-mark">{{
              day.state === "done" ? "+2" : day.state === "today" ? "?" : ""
            }}</span>
            <small>{{ day.label }}</small>
          </li>
        </ol>
        <p>{{ streakHint(rating.streak) }}</p>
      </section>
    </template>
    <p v-else class="rating-empty">Не удалось загрузить рейтинг.</p>
  </aside>
</template>

<style scoped>
.rating-widget {
  display: flex;
  flex-direction: column;
  gap: 14px;
  width: 340px;
  min-width: 0;
  box-sizing: border-box;
  padding: 22px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
}
.rating-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
.rating-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 4px 12px;
}
.rating-total strong {
  font-size: 44px;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}
.rating-total span {
  color: #4a546b;
  font-size: 14px;
}
.rating-bar {
  display: flex;
  gap: 3px;
  height: 10px;
  overflow: hidden;
  border-radius: 999px;
  background: #e1e6f0;
}
.rating-bar span {
  flex-basis: 0;
  min-width: 6px;
  border-radius: 999px;
}
.rating-parts {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
  padding: 0 0 14px;
  border-bottom: 1px solid #e1e6f0;
  list-style: none;
  font-size: 14px;
}
.rating-parts li {
  display: grid;
  grid-template-columns: 12px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
}
.rating-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}
.rating-parts b {
  font-variant-numeric: tabular-nums;
}
.rating-goal {
  margin: 0;
  padding-bottom: 14px;
  border-bottom: 1px solid #e1e6f0;
  color: #4a546b;
  font-size: 14px;
  line-height: 1.5;
}
.rating-goal b {
  color: #3457f0;
}
.rating-streak {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rating-streak-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.rating-streak-head h3 {
  margin: 0;
  font-size: 16px;
}
.rating-streak-head span {
  color: #b8520f;
  font-size: 13px;
  font-weight: 700;
}
.rating-week {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.rating-week li {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.rating-day-mark {
  display: grid;
  width: 100%;
  max-width: 40px;
  aspect-ratio: 1;
  box-sizing: border-box;
  place-items: center;
  border-radius: 10px;
  background: #f0f2f6;
  font-size: 12px;
  font-weight: 700;
}
.rating-day--done .rating-day-mark {
  background: #f08a2c;
  color: #fff;
}
.rating-day--today .rating-day-mark {
  border: 2px dashed #f08a2c;
  background: #fff;
  color: #b8520f;
}
.rating-week small {
  color: #68748a;
  font-size: 12px;
}
.rating-streak p,
.rating-empty {
  margin: 0;
  color: #4a546b;
  font-size: 13px;
}
@media (max-width: 1100px) {
  .rating-widget {
    width: auto;
  }
}
</style>
