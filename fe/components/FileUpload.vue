<template>
  <div class="file-upload">
    <div
      @drop.prevent="handleDrop"
      @dragover.prevent
      @dragenter.prevent
      class="upload-area"
      :class="{ 'drag-over': isDragOver }"
    >
      <input
        ref="fileInput"
        type="file"
        multiple
        @change="handleFileSelect"
        class="hidden"
      />
      
      <div class="text-center">
        <div class="text-4xl mb-4">📁</div>
        <p class="text-gray-600 mb-2">
          Drag and drop files here, or 
          <button @click="$refs.fileInput.click()" class="text-blue-600 hover:text-blue-800">
            browse
          </button>
        </p>
        <p class="text-sm text-gray-500">Support: PDF, DOC, DOCX, TXT (Max 10MB)</p>
      </div>
    </div>
    
    <div v-if="selectedFiles.length" class="mt-4">
      <h4 class="font-medium mb-2">Selected Files:</h4>
      <div class="space-y-2">
        <div
          v-for="(file, index) in selectedFiles"
          :key="index"
          class="flex justify-between items-center p-2 border rounded"
        >
          <span>{{ file.name }}</span>
          <button
            @click="removeFile(index)"
            class="text-red-600 hover:text-red-800"
          >
            Remove
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  upload: [files: File[]]
}>()

const isDragOver = ref(false)
const selectedFiles = ref<File[]>([])

const handleDrop = (e: DragEvent) => {
  isDragOver.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  addFiles(files)
}

const handleFileSelect = (e: Event) => {
  const target = e.target as HTMLInputElement
  const files = Array.from(target.files || [])
  addFiles(files)
}

const addFiles = (files: File[]) => {
  const validFiles = files.filter(file => {
    const validTypes = ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    const maxSize = 10 * 1024 * 1024 // 10MB
    return validTypes.includes(file.type) && file.size <= maxSize
  })
  
  selectedFiles.value = [...selectedFiles.value, ...validFiles]
  emit('upload', validFiles)
}

const removeFile = (index: number) => {
  selectedFiles.value.splice(index, 1)
}
</script>

<style scoped>
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  padding: 32px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.upload-area:hover,
.upload-area.drag-over {
  border-color: #3b82f6;
  background-color: #eff6ff;
}
</style>