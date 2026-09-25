<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { StepType } from "../shared/types";

const props = defineProps<{ moduleLabel: string }>();
const emit = defineEmits<{ choose: [type: StepType]; cancel: [] }>();
const selected = ref<StepType>("theory");
const cards: {
  label: string;
  description: string;
  grading: string;
  icon: string;
  type: StepType;
}[] = [
  {
    label: "Теория",
    description: "Текст и картинки",
    grading: "ЗАЧЁТ ПРИ ПРОЧТЕНИИ",
    icon: "▤",
    type: "theory",
  },
  {
    label: "Контрольный вопрос",
    description: "Один или несколько вариантов",
    grading: "АВТОПРОВЕРКА",
    icon: "?",
    type: "multiple_choice",
  },
  {
    label: "Задача с тестами",
    description: "Python и проверка по тестам",
    grading: "АВТОПРОВЕРКА",
    icon: "〈〉",
    type: "programming",
  },
  {
    label: "Проект",
    description: "Scratch, Minecraft или другое: ссылка, скриншот или файл",
    grading: "КУРАТОР",
    icon: "⚑",
    type: "free_text",
  },
];

function keydown(event: KeyboardEvent): void {
  if (event.key === "Escape") emit("cancel");
}
onMounted(() => {
  document.addEventListener("keydown", keydown);
  document.body.style.overflow = "hidden";
});
onBeforeUnmount(() => {
  document.removeEventListener("keydown", keydown);
  document.body.style.overflow = "";
});
</script>

<template>
  <div class="step-picker-backdrop" @click.self="emit('cancel')">
    <section class="step-picker" role="dialog" aria-modal="true" aria-label="Добавить шаг">
      <div class="step-picker-head">
        <h2>Добавить шаг{{ props.moduleLabel ? ` в модуль «${props.moduleLabel}»` : "" }}</h2>
        <button
          class="admin-button step-picker-close"
          type="button"
          aria-label="Закрыть"
          @click="emit('cancel')"
        >
          ×
        </button>
      </div>
      <div class="step-picker-grid">
        <button
          v-for="card in cards"
          :key="card.label"
          class="step-picker-card"
          :class="{ 'step-picker-card--selected': card.type === selected }"
          type="button"
          @click="selected = card.type"
        >
          <span class="step-picker-icon" aria-hidden="true">{{ card.icon }}</span>
          <strong>{{ card.label }}</strong>
          <span class="step-picker-description">{{ card.description }}</span>
          <span class="admin-section-label">{{ card.grading }}</span>
        </button>
        <div class="step-picker-help">
          <strong>Нужен другой тип?</strong
          ><span>Тип шага задаёт форму, экран ученика и правило проверки.</span>
        </div>
      </div>
      <div class="step-picker-footer">
        <span
          >Выбрано: <strong>{{ cards.find((card) => card.type === selected)?.label }}</strong></span
        >
        <button class="admin-button" type="button" @click="emit('cancel')">Отмена</button>
        <button
          class="admin-button admin-button--primary"
          type="button"
          @click="emit('choose', selected)"
        >
          Добавить шаг
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.step-picker-backdrop {
  position: fixed;
  z-index: 50;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 20px;
  background: #0b122080;
}
.step-picker {
  display: grid;
  gap: 16px;
  width: min(900px, 100%);
  max-height: min(760px, calc(100dvh - 40px));
  overflow: auto;
  padding: 28px;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 22px 70px #07132c4d;
}
.step-picker-head {
  display: flex;
  align-items: center;
  gap: 20px;
}
.step-picker-head h2 {
  flex: 1;
  margin: 0;
  font-size: 22px;
  line-height: 1.25;
}
.step-picker-close {
  width: 40px;
  padding: 0;
  font-size: 20px;
}
.step-picker-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.step-picker-card {
  display: flex;
  flex-direction: column;
  align-items: start;
  gap: 8px;
  min-height: 175px;
  padding: 16px;
  border: 1px solid #e1e6f0;
  border-radius: 16px;
  background: #fff;
  color: #0f172a;
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.step-picker-card:hover {
  border-color: #c9d5fc;
}
.step-picker-card--selected {
  border: 2px solid #3457f0;
  background: #eaf0fe;
  padding: 15px;
}
.step-picker-card--disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.step-picker-icon {
  display: grid;
  width: 40px;
  height: 40px;
  place-items: center;
  border-radius: 10px;
  background: #3457f0;
  color: #fff;
  font-size: 21px;
  font-weight: 700;
}
.step-picker-card strong {
  font-size: 16px;
  line-height: 1.2;
}
.step-picker-description {
  color: #4a546b;
  font-size: 13px;
}
.step-picker-card .admin-section-label {
  margin-top: auto;
  font-size: 10px;
}
.step-picker-help {
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 16px;
  border: 2px dashed #e1e6f0;
  border-radius: 16px;
  color: #4a546b;
  font-size: 13px;
}
.step-picker-help strong {
  color: #0f172a;
  font-size: 16px;
}
.step-picker-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #e1e6f0;
  font-size: 13px;
}
.step-picker-footer > span {
  flex: 1;
  color: #4a546b;
}
.step-picker-footer strong {
  color: #0f172a;
}
@media (max-width: 750px) {
  .step-picker-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .step-picker {
    padding: 20px;
  }
}
@media (max-width: 450px) {
  .step-picker-grid {
    grid-template-columns: 1fr;
  }
  .step-picker-footer {
    flex-wrap: wrap;
  }
}
</style>
