<template>
  <div class="file-icon">
    {{ getFileIcon(type) }}
  </div>
</template>

<script setup lang="ts">
defineProps<{
  type: string
}>()

const getFileIcon = (type: string): string => {
  if (type === 'application/pdf') return '📄'
  if (type.includes('word')) return '📝'
  if (type === 'text/plain') return '📃'
  if (type.includes('image')) return '🖼️'
  return '📁'
}
</script>

<style scoped>
.file-icon {
  font-size: 24px;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  border-radius: 8px;
}
</style>