<template>
  <div class="file-item">
    <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
      <div class="flex items-center space-x-3">
        <!-- File Icon -->
        <FileIcon :type="file.type" />
        
        <!-- File Info -->
        <FileInfo :file="file" />
      </div>
      
      <!-- File Actions -->
      <FileActions 
        :file="file"
        @download="$emit('download', file)"
        @preview="$emit('preview', file)"
        @remove="$emit('remove')"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { UploadedFile } from '~/types/submission'

defineProps<{
  file: UploadedFile
}>()

defineEmits<{
  download: [file: UploadedFile]
  preview: [file: UploadedFile]
  remove: []
}>()
</script>

<style scoped>
.file-item {
  transition: all 0.2s ease;
}

.file-item:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
</style>