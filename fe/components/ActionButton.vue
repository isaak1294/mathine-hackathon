<!-- filepath: components/ActionButton.vue -->
<template>
  <button
    @click="$emit('click')"
    :class="buttonClasses"
  >
    {{ text }}
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  text: string
  variant: 'blue' | 'green' | 'red' | 'gray'
}>()

defineEmits<{
  click: []
}>()

const buttonClasses = computed(() => {
  const baseClasses = 'px-3 py-1 text-sm rounded hover:opacity-80 transition-opacity'
  
  const variantClasses = {
    blue: 'bg-blue-100 text-blue-700 hover:bg-blue-200',
    green: 'bg-green-100 text-green-700 hover:bg-green-200',
    red: 'bg-red-100 text-red-700 hover:bg-red-200',
    gray: 'bg-gray-100 text-gray-700 hover:bg-gray-200'
  }
  
  return `${baseClasses} ${variantClasses[props.variant]}`
})
</script>