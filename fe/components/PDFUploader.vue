<template>
  <div class="w-full max-w-3xl border border-border bg-card shadow-xl rounded-lg">
    <div class="p-8 md:p-12 space-y-8">
      <!-- Header -->
      <div class="space-y-3 text-center">
        <h1 class="text-4xl md:text-5xl font-bold text-primary tracking-tight leading-tight">
          Document Upload
        </h1>
        <p class="text-muted-foreground text-base md:text-lg leading-relaxed max-w-2xl mx-auto">
          Upload your PDF document securely. Drag and drop or click to browse your files.
        </p>
      </div>

      <!-- Upload Area -->
      <div class="space-y-6">
        <div
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
          :class="cn(
            'border-2 border-dashed rounded-lg transition-all duration-300 ease-in-out',
            isDragging
              ? 'border-primary bg-primary/5 scale-[1.02] shadow-lg'
              : 'border-border hover:border-primary/50 hover:bg-muted/30',
            error && 'border-destructive bg-destructive/5'
          )"
        >
          <!-- REDUCED PADDING HERE: from p-10 md:p-16 to p-6 md:p-8 -->
          <div class="p-6 md:p-8 space-y-6">
            <!-- REDUCED GAP HERE: from gap-6 to gap-4 -->
            <div class="flex flex-col items-center gap-4 text-center">
              <div class="relative">
                <div class="absolute inset-0 bg-primary/10 rounded-full blur-2xl" />
                <!-- REDUCED PADDING HERE: from p-6 to p-4 -->
                <div class="relative bg-primary/10 p-4 rounded-full">
                  <!-- REDUCED ICON SIZE: from 64 to 48 -->
                  <Icons name="FileText" :size="48" class="text-primary" />
                </div>
              </div>

              <!-- REDUCED SPACING HERE: from space-y-3 to space-y-2 -->
              <div class="space-y-2">
                <!-- REDUCED TEXT SIZE: from text-xl to text-lg -->
                <p class="text-lg font-semibold text-foreground">Drop your PDF file here</p>
                <p class="text-sm text-muted-foreground">or click the button below to browse</p>
              </div>

              <button
                @click="() => fileInputRef?.click()"
                class="bg-primary hover:bg-primary/90 text-primary-foreground font-semibold px-8 py-6 text-base shadow-md hover:shadow-lg transition-all duration-200 rounded-lg"
              >
                <Icons name="Upload" :size="20" class="mr-2 inline" />
                Select PDF File
              </button>

              <input
                ref="fileInputRef"
                type="file"
                accept=".pdf,application/pdf"
                @change="handleFileInput"
                class="hidden"
              />

              <p class="text-xs text-muted-foreground pt-2">Maximum file size: 10MB • PDF format only</p>
            </div>
          </div>
        </div>

        <!-- Rest of your template stays the same -->
        <!-- Error Message -->
        <div
          v-if="error"
          class="flex items-center gap-3 p-4 border border-destructive bg-destructive/10 rounded-lg animate-fade-in"
        >
          <Icons name="AlertCircle" :size="20" class="text-destructive flex-shrink-0" />
          <p class="text-destructive font-medium text-sm">{{ error }}</p>
        </div>

        <!-- File Preview -->
        <div
          v-if="file"
          class="border border-border rounded-lg bg-card p-6 space-y-5 shadow-sm animate-fade-in"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="flex items-start gap-4 flex-1 min-w-0">
              <div class="bg-primary/10 p-3 rounded-lg flex-shrink-0">
                <Icons name="FileText" :size="28" class="text-primary" />
              </div>
              <div class="flex-1 min-w-0 pt-1">
                <p class="font-semibold text-base text-foreground truncate leading-tight">{{ file.name }}</p>
                <p class="text-sm text-muted-foreground mt-1">{{ formatFileSize(file.size) }}</p>
              </div>
            </div>
            <button
              v-if="!isUploading && !uploadComplete"
              @click="removeFile"
              class="flex-shrink-0 p-2 hover:bg-destructive/10 hover:text-destructive transition-colors rounded"
            >
              <Icons name="X" :size="20" />
            </button>
            <div v-if="uploadComplete" class="bg-green-100 p-2 rounded-full">
              <Icons name="CheckCircle2" :size="24" class="text-green-600 flex-shrink-0" />
            </div>
          </div>

          <!-- Progress Bar -->
          <div v-if="isUploading || uploadComplete" class="space-y-3">
            <div class="flex justify-between items-center text-sm font-medium">
              <span class="text-foreground">{{ uploadComplete ? 'Upload Complete' : 'Uploading...' }}</span>
              <span class="text-primary font-semibold tabular-nums">{{ uploadProgress }}%</span>
            </div>
            <div class="h-2.5 bg-secondary rounded-full overflow-hidden">
              <div
                class="h-full bg-primary transition-all duration-500 ease-out rounded-full"
                :style="{ width: `${uploadProgress}%` }"
              />
            </div>
          </div>

          <!-- Upload Button -->
          <button
            v-if="!isUploading && !uploadComplete"
            @click="simulateUpload"
            class="w-full bg-accent hover:bg-accent/90 text-accent-foreground font-semibold text-base py-6 shadow-md hover:shadow-lg transition-all duration-200 rounded-lg"
          >
            <Icons name="Upload" :size="20" class="mr-2 inline" />
            Upload Document
          </button>

          <!-- Success Message -->
          <div
            v-if="uploadComplete"
            class="flex items-center justify-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg"
          >
            <Icons name="CheckCircle2" :size="20" class="text-green-600" />
            <p class="text-green-700 font-semibold text-sm">Document uploaded successfully</p>
          </div>
        </div>
      </div>

      <!-- Info Section -->
      <div class="border-t border-border pt-6">
        <div class="bg-muted/50 rounded-lg p-6">
          <h3 class="font-semibold text-foreground text-sm mb-3 uppercase tracking-wide">Upload Requirements</h3>
          <ul class="space-y-2.5 text-sm text-muted-foreground">
            <li class="flex items-center gap-3">
              <div class="w-1.5 h-1.5 bg-primary rounded-full flex-shrink-0" />
              <span>Accepted format: PDF documents only</span>
            </li>
            <li class="flex items-center gap-3">
              <div class="w-1.5 h-1.5 bg-primary rounded-full flex-shrink-0" />
              <span>Maximum file size: 10 MB</span>
            </li>
            <li class="flex items-center gap-3">
              <div class="w-1.5 h-1.5 bg-primary rounded-full flex-shrink-0" />
              <span>Supports drag and drop or file selection</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<!-- Script section stays the same -->
<script setup lang="ts">
import { ref } from 'vue'
import { cn } from '@/utils/cn'

// State
const file = ref<File | null>(null)
const isDragging = ref(false)
const uploadProgress = ref(0)
const isUploading = ref(false)
const uploadComplete = ref(false)
const error = ref<string | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

// Methods
const validateFile = (file: File): boolean => {
  if (file.type !== 'application/pdf') {
    error.value = 'Only PDF files are allowed'
    return false
  }
  if (file.size > 10 * 1024 * 1024) {
    error.value = 'File size must be less than 10MB'
    return false
  }
  error.value = null
  return true
}

const handleFile = (selectedFile: File) => {
  if (validateFile(selectedFile)) {
    file.value = selectedFile
    uploadComplete.value = false
    uploadProgress.value = 0
  }
}

const handleDragOver = () => {
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = (e: DragEvent) => {
  isDragging.value = false
  const droppedFile = e.dataTransfer?.files[0]
  if (droppedFile) {
    handleFile(droppedFile)
  }
}

const handleFileInput = (e: Event) => {
  const target = e.target as HTMLInputElement
  const selectedFile = target.files?.[0]
  if (selectedFile) {
    handleFile(selectedFile)
  }
}

const simulateUpload = () => {
  isUploading.value = true
  uploadProgress.value = 0

  const interval = setInterval(() => {
    uploadProgress.value += 10
    if (uploadProgress.value >= 100) {
      clearInterval(interval)
      isUploading.value = false
      uploadComplete.value = true
      uploadProgress.value = 100
    }
  }, 200)
}

const removeFile = () => {
  file.value = null
  uploadProgress.value = 0
  uploadComplete.value = false
  error.value = null
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}
</script>