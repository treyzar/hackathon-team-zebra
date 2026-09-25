<script setup lang="ts">
import type { Group } from "../../shared/types";

defineProps<{
  groups: Group[];
  selectedId: number | null;
  curatorName: (id: number | null) => string;
}>();

const emit = defineEmits<{
  select: [id: number];
}>();
</script>

<template>
  <aside class="groups-sidebar">
    <div v-if="!groups.length" class="groups-sidebar__empty">Групп пока нет</div>
    <div v-else class="groups-sidebar__list">
      <button
        v-for="group in groups"
        :key="group.id"
        class="group-item"
        :class="{
          'group-item--active': selectedId === group.id,
          'group-item--warning': group.curator_id === null,
        }"
        type="button"
        @click="emit('select', group.id)"
      >
        <strong>{{ group.name }}</strong>
        <span :class="{ 'group-item__meta--warning': group.curator_id === null }">
          {{ curatorName(group.curator_id) }} · {{ group.students_count }} учеников
        </span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.groups-sidebar {
  width: 300px;
  min-width: 300px;
  min-height: 0;
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
  scrollbar-gutter: stable;
}
.groups-sidebar__list {
  display: grid;
  gap: 8px;
}
.group-item {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 3px;
  padding: 12px 14px;
  border: 1px solid #e1e6f0;
  border-radius: 12px;
  background: #fff;
  color: #1d2b43;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.group-item:hover {
  border-color: #bfc9dc;
}
.group-item--active {
  border: 2px solid #3457f0;
  padding: 11px 13px;
  background: #eaf0fe;
}
.group-item--warning:not(.group-item--active) {
  border-color: #f8d3b8;
  background: #fff1e6;
}
.group-item strong {
  font-size: 14px;
  font-weight: 700;
}
.group-item span {
  color: #4a546b;
  font-size: 13px;
}
.group-item .group-item__meta--warning {
  color: #b8520f;
}
.groups-sidebar__empty {
  padding: 18px 14px;
  border: 1px dashed #c9d1df;
  border-radius: 12px;
  color: #6e788d;
  text-align: center;
}
@media (max-width: 900px) {
  .groups-sidebar {
    width: 100%;
    min-width: 0;
    height: auto;
    overflow: visible;
    padding-right: 0;
  }
  .groups-sidebar__list {
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }
}
</style>
