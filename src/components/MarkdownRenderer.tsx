import { FC, memo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '@/lib/utils'

interface MarkdownRendererProps {
  content: string
  className?: string
}

// Marked renderer'ı özelleştir
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  highlight: function(code, lang) {
    if (lang && SyntaxHighlighter.supportedLanguages.includes(lang)) {
      return `<pre class="language-${lang}"><code>${code}</code></pre>`;
    }
    return `<pre><code>${code}</code></pre>`;
  }
})

// Code bloklarını render etmek için özel hook
const useCodeHighlighting = () => {
  const renderer = new marked.Renderer()
  
  renderer.code = (code, language, isEscaped) => {
    if (language && SyntaxHighlighter.supportedLanguages.includes(language)) {
      return `<pre class="syntax-highlight" data-language="${language}"><code>${code}</code></pre>`
    }
    return `<pre><code>${code}</code></pre>`
  }
  
  return renderer
}

const MarkdownRenderer: FC<MarkdownRendererProps> = ({ content, className }) => {
  const renderer = useCodeHighlighting()
  
  // İçeriği markdown ve HTML olarak dönüştür
  const htmlContent = DOMPurify.sanitize(marked(content, { renderer }))
  
  // Code bloklarını bul ve Syntax Highlighter ile değiştir
  const processedContent = (node: HTMLElement): React.ReactNode => {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.textContent
    }
    
    if (node.nodeName === 'PRE' && node.classList.contains('syntax-highlight')) {
      const code = node.querySelector('code')?.textContent || ''
      const language = node.getAttribute('data-language') || ''
      
      return (
        <SyntaxHighlighter 
          language={language} 
          style={vscDarkPlus}
          customStyle={{ margin: '1em 0' }}
        >
          {code}
        </SyntaxHighlighter>
      )
    }
    
    return <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
  }
  
  return (
    <div className={cn("markdown-content", className)}>
      <div dangerouslySetInnerHTML={{ __html: htmlContent }} />
    </div>
  )
}

export default memo(MarkdownRenderer)