<script setup lang="ts">
defineProps<{ courses: number; steps: number; points: number }>();
</script>
<template>
  <section class="student-snapshot" aria-label="Ваш прогресс">
    <h2>Ваш прогресс</h2>
    <div class="student-snapshot-row">
      <span>Курсов</span><strong>{{ courses }}</strong>
    </div>
    <div class="student-snapshot-row">
      <span>Шагов пройдено</span><strong>{{ steps }}</strong>
    </div>
    <div class="student-snapshot-row">
      <span>Баллов набрано</span><strong>{{ points }}</strong>
    </div>
  </section>
</template>
<style scoped>
.student-snapshot {
  display: flex;
  flex-direction: column;
  min-height: 292px;
  padding: 24px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
}
.student-snapshot h2 {
  margin: 0 0 17px;
  font-size: 18px;
}
.student-snapshot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-top: 1px solid #edf0f6;
  color: #65728a;
}
.student-snapshot-row strong {
  color: #0f172a;
  font-size: 22px;
}
</style>
