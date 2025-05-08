import React, { useState, useRef, useEffect } from 'react'
import { FiSearch, FiX, FiLoader } from 'react-icons/fi'
import { cn } from '@/lib/utils'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  initialValue?: string
  isLoading?: boolean
  className?: string
  autoFocus?: boolean
}

const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  placeholder = 'Ara...',
  initialValue = '',
  isLoading = false,
  className,
  autoFocus = false
}) => {
  const [query, setQuery] = useState(initialValue)
  const inputRef = useRef<HTMLInputElement>(null)
  
  // Otomatik odaklanma
  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus()
    }
  }, [autoFocus])
  
  // Form gönderimi
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (query.trim() && !isLoading) {
      onSearch(query.trim())
    }
  }
  
  // Metin alanını temizle
  const handleClear = () => {
    setQuery('')
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }
  
  return (
    <form 
      onSubmit={handleSubmit}
      className={cn(
        "flex items-center w-full relative",
        className
      )}
    >
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        <FiSearch className="text-gray-400" size={16} />
      </div>
      
      <input
        ref={inputRef}
        type="text"
        className="block w-full pl-10 pr-10 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        disabled={isLoading}
      />
      
      {isLoading ? (
        <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
          <FiLoader className="text-primary-500 animate-spin" size={16} />
        </div>
      ) : query ? (
        <button
          type="button"
          onClick={handleClear}
          className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
        >
          <FiX size={16} />
        </button>
      ) : null}
    </form>
  )
}

export default SearchBar