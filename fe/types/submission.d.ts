export interface UploadedFile {
  name: string
  size: number
  type: string
  url: string
  uploadedAt: Date
  file: File
}

export interface Submission {
  id: string
  title: string
  courseId: string
  courseName: string
  description: string
  dueDate: string
  priority: 'low' | 'medium' | 'high' | 'critical'
  status: 'draft' | 'submitted' | 'graded' | 'overdue'
  attachments?: {
    id: string
    name: string
    url: string
    size: number
  }[]
  grade?: number
  feedback?: string
  createdAt: string
  updatedAt: string
}

export interface SubmissionFormData {
  title: string
  courseId: string
  description: string
  dueDate: string
  priority: string
  attachments: File[]
}