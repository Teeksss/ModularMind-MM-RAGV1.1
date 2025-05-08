import { ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Tailwind sınıflarını birleştirme
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Metni belirli uzunlukta kırpma
export function truncateText(text: string, maxLength: number = 100): string {
  if (text && text.length > maxLength) {
    return text.substring(0, maxLength) + '...'
  }
  return text
}

// Dosya boyutunu formatla
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Tarihi formatla
export function formatDate(date: string | Date): string {
  if (!date) return ''
  
  const d = new Date(date)
  if (isNaN(d.getTime())) return ''
  
  return d.toLocaleDateString('tr-TR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

// Renk oluşturma
export function stringToColor(str: string): string {
  if (!str) return '#6b7280' // Varsayılan gri
  
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash)
  }
  
  let color = '#'
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xFF
    color += ('00' + value.toString(16)).substr(-2)
  }
  
  return color
}

// Metin benzerliği skoru
export function similarityScoreToPercent(score: number): number {
  return Math.round(score * 100)
}

// Debounce fonksiyonu
export function debounce<T extends (...args: any[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  
  return function(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }
    
    if (timeout !== null) {
      clearTimeout(timeout)
    }
    
    timeout = setTimeout(later, wait)
  }
}

// API Hata Mesajını Temizle
export function cleanApiErrorMessage(error: any): string {
  if (!error) return 'Bilinmeyen hata'
  
  if (typeof error === 'string') {
    // API ön eki ile gelen hata mesajlarını temizle
    return error.replace(/^(ERROR:|Error:)\s*/i, '')
  }
  
  if (error instanceof Error) {
    return error.message.replace(/^(ERROR:|Error:)\s*/i, '')
  }
  
  return 'Bilinmeyen hata'
}

// Meta veri anahtarlarını daha okunabilir biçime dönüştür
export function formatMetadataKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
}

// Relative zamanlama
export function getRelativeTime(date: string | Date): string {
  const now = new Date()
  const targetDate = new Date(date)
  
  if (isNaN(targetDate.getTime())) {
    return ''
  }
  
  const diffInSeconds = Math.floor((now.getTime() - targetDate.getTime()) / 1000)
  
  if (diffInSeconds < 60) {
    return 'Az önce'
  }
  
  const diffInMinutes = Math.floor(diffInSeconds / 60)
  if (diffInMinutes < 60) {
    return `${diffInMinutes} dakika önce`
  }
  
  const diffInHours = Math.floor(diffInMinutes / 60)
  if (diffInHours < 24) {
    return `${diffInHours} saat önce`
  }
  
  const diffInDays = Math.floor(diffInHours / 24)
  if (diffInDays < 30) {
    return `${diffInDays} gün önce`
  }
  
  const diffInMonths = Math.floor(diffInDays / 30)
  if (diffInMonths < 12) {
    return `${diffInMonths} ay önce`
  }
  
  const diffInYears = Math.floor(diffInMonths / 12)
  return `${diffInYears} yıl önce`
}