<template>
  <div class="submission-page">
    <div class="container mx-auto p-6 space-y-8">
      <!-- File Upload Section -->
      <div class="upload-section">
        <h1 class="text-2xl font-bold mb-6">Submit Your Files</h1>
        
        <FileUpload @upload="handleFileUpload" />
        
        <!-- Uploaded Files List -->
        <UploadedFilesList 
          :files="uploadedFiles"
          @download="downloadFile"
          @preview="openPreview"
          @remove="removeFile"
        />
        
        <!-- Submit Button -->
        <SubmitButton 
          :file-count="uploadedFiles.length"
          :is-submitting="isSubmitting"
          @submit="submitFiles"
        />
      </div>
      
      <!-- PDF Preview Modal -->
      <PDFPreviewModal 
        v-if="previewFile"
        :file="previewFile"
        @close="previewFile = null"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { UploadedFile } from '~/types/submission'

// State
const uploadedFiles = ref<UploadedFile[]>([])
const previewFile = ref<UploadedFile | null>(null)
const isSubmitting = ref(false)

// Handlers
const handleFileUpload = (files: File[]) => {
  files.forEach(file => {
    const uploadedFile: UploadedFile = {
      name: file.name,
      size: file.size,
      type: file.type,
      url: URL.createObjectURL(file),
      uploadedAt: new Date(),
      file: file
    }
    uploadedFiles.value.push(uploadedFile)
  })
}

const removeFile = (index: number) => {
  const file = uploadedFiles.value[index]
  URL.revokeObjectURL(file.url)
  uploadedFiles.value.splice(index, 1)
}

const downloadFile = (file: UploadedFile) => {
  const link = document.createElement('a')
  link.href = file.url
  link.download = file.name
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const openPreview = (file: UploadedFile) => {
  if (file.type === 'application/pdf') {
    previewFile.value = file
  }
}

const submitFiles = async () => {
  if (uploadedFiles.value.length === 0) return
  
  try {
    isSubmitting.value = true
    
    console.log('Submitting files:', uploadedFiles.value.map(f => f.name))
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    
    // Clear uploaded files after successful submission
    uploadedFiles.value.forEach(file => URL.revokeObjectURL(file.url))
    uploadedFiles.value = []
    
    alert('Files submitted successfully!')
    
  } catch (error) {
    console.error('Failed to submit files:', error)
    alert('Failed to submit files. Please try again.')
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.submission-page {
  min-height: 100vh;
  background: #f8fafc;
}

.container {
  max-width: 800px;
}

.upload-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}
</style>