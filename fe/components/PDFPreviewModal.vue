<template>
  <Modal @close="$emit('close')">
    <div class="pdf-preview">
      <h3 class="text-lg font-semibold mb-4">{{ file.name }}</h3>
      <iframe
        :src="file.url"
        class="w-full h-96 border border-gray-300 rounded"
        frameborder="0"
      ></iframe>
    </div>
  </Modal>
</template>

<script setup lang="ts">
import type { UploadedFile } from '~/types/submission'

defineProps<{
  file: UploadedFile
}>()

defineEmits<{
  close: []
}>()
</script>

<style scoped>
.pdf-preview {
  width: 100%;
  max-width: 800px;
}
</style>