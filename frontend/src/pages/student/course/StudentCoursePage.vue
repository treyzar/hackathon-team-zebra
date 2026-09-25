<script setup lang="ts">
import CourseWorkspace from "@/modules/student/courses/CourseWorkspace.vue";
defineProps<{ courseId: number }>();
</script>

<template><CourseWorkspace :course-id="courseId" /></template>
