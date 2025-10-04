<template>
  <div class="flex items-center space-x-2">
    <ActionButton
      @click="$emit('download')"
      variant="blue"
      text="Download"
    />
    <ActionButton
      v-if="canPreview"
      @click="$emit('preview')"
      variant="green"
      text="Preview"
    />
    <ActionButton
      @click="$emit('remove')"
      variant="red"
      text="Remove"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { UploadedFile } from '~/types/submission'

const props = defineProps<{
  file: UploadedFile
}>()

defineEmits<{
  download: []
  preview: []
  remove: []
}>()

const canPreview = computed(() => props.file.type === 'application/pdf')
</script>