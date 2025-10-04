<template>
  <div v-if="files.length > 0" class="uploaded-files">
    <h2 class="text-xl font-semibold mb-4">Uploaded Files</h2>
    <div class="space-y-3">
      <UploadedFileItem
        v-for="(file, index) in files"
        :key="index"
        :file="file"
        @download="$emit('download', file)"
        @preview="$emit('preview', file)"
        @remove="$emit('remove', index)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UploadedFile } from '~/types/submission'

defineProps<{
  files: UploadedFile[]
}>()

defineEmits<{
  download: [file: UploadedFile]
  preview: [file: UploadedFile]
  remove: [index: number]
}>()
</script>

<style scoped>
.uploaded-files {
  margin-top: 24px;
}
</style>