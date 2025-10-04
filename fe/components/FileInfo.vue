<template>
  <div>
    <p class="font-medium text-gray-900">{{ file.name }}</p>
    <p class="text-sm text-gray-500">
      {{ formatFileSize(file.size) }} • {{ getFileType(file.type) }}
    </p>
    <p class="text-xs text-gray-400">
      Uploaded {{ formatDate(file.uploadedAt) }}
    </p>
  </div>
</template>

<script setup lang="ts">
import type { UploadedFile } from '~/types/submission'

defineProps<{
  file: UploadedFile
}>()

const getFileType = (type: string): string => {
  if (type === 'application/pdf') return 'PDF'
  if (type === 'application/msword') return 'Word Document'
  if (type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') return 'Word Document'
  if (type === 'text/plain') return 'Text File'
  return 'Unknown'
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date: Date): string => {
  return date.toLocaleString()
}
</script>