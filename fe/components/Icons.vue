<!-- filepath: fe/components/Icons.vue -->
<template>
  <svg
    :width="size"
    :height="size"
    :viewBox="viewBox"
    fill="none"
    stroke="currentColor"
    stroke-width="2"
    stroke-linecap="round"
    stroke-linejoin="round"
    :class="className"
  >
    <template v-if="name === 'FileText'">
      <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
      <path d="M14,2 14,8 20,8"/>
      <path d="M10,9 16,9"/>
      <path d="M10,13 16,13"/>
      <path d="M10,17 12,17"/>
    </template>
    <template v-else-if="name === 'Upload'">
      <path d="m3 16 4 4 4-4"/>
      <path d="M7 20V4"/>
      <path d="m11 4 4 4-4 4"/>
      <path d="M15 8V20"/>
    </template>
    <template v-else-if="name === 'X'">
      <path d="m18 6-12 12"/>
      <path d="M6 6l12 12"/>
    </template>
    <template v-else-if="name === 'CheckCircle2'">
      <circle cx="12" cy="12" r="10"/>
      <path d="m9 12 2 2 4-4"/>
    </template>
    <template v-else-if="name === 'AlertCircle'">
      <circle cx="12" cy="12" r="10"/>
      <path d="m9 9 3 3 3-3"/>
      <path d="M12 17h.01"/>
    </template>
  </svg>
</template>

<script setup lang="ts">
const props = defineProps<{
  name: 'FileText' | 'Upload' | 'X' | 'CheckCircle2' | 'AlertCircle'
  size?: number
  className?: string
}>()

const viewBox = '0 0 24 24'
</script>