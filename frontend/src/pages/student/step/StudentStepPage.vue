<script setup lang="ts">
import CourseWorkspace from "@/modules/student/courses/CourseWorkspace.vue";
defineProps<{ courseId: number; stepId: number }>();
</script>

<template><CourseWorkspace :course-id="courseId" :step-id="stepId" /></template>
