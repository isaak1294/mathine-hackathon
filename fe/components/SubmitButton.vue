<template>
  <div v-if="fileCount > 0" class="submit-section">
    <button
      @click="$emit('submit')"
      :disabled="isSubmitting"
      class="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
    >
      {{ buttonText }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  fileCount: number
  isSubmitting: boolean
}>()

defineEmits<{
  submit: []
}>()

const buttonText = computed(() => 
  props.isSubmitting 
    ? 'Submitting...' 
    : `Submit ${props.fileCount} File(s)`
)
</script>

<style scoped>
.submit-section {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}
</style>