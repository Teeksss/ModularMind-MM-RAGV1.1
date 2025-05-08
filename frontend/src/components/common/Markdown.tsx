import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus, vs } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '@/hooks/useTheme';

interface MarkdownProps {
  children: string;
  className?: string;
}

const Markdown: React.FC<MarkdownProps> = ({ children, className }) => {
  const { theme } = useTheme();
  const isDarkMode = theme === 'dark';
  
  return (
    <ReactMarkdown
      className={`prose dark:prose-invert max-w-none ${className || ''}`}
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex, rehypeRaw, rehypeSanitize]}
      components={{
        code({ node, inline, className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          
          if (!inline && language) {
            return (
              <SyntaxHighlighter
                style={isDarkMode ? vscDarkPlus : vs}
                language={language}
                PreTag="div"
                className="rounded-md"
                showLineNumbers={true}
                {...props}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            );
          }
          
          return inline ? (
            <code className={`${className || ''} text-sm px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded`} {...props}>
              {children}
            </code>
          ) : (
            <SyntaxHighlighter
              style={isDarkMode ? vscDarkPlus : vs}
              language="text"
              PreTag="div"
              className="rounded-md"
              {...props}
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          );
        },
        table({ node, ...props }) {
          return (
            <div className="overflow-x-auto">
              <table className="border-collapse border border-gray-300 dark:border-gray-700" {...props} />
            </div>
          );
        },
        thead({ node, ...props }) {
          return <thead className="bg-gray-100 dark:bg-gray-800" {...props} />;
        },
        th({ node, ...props }) {
          return <th className="border border-gray-300 dark:border-gray-700 px-4 py-2 text-left" {...props} />;
        },
        td({ node, ...props }) {
          return <td className="border border-gray-300 dark:border-gray-700 px-4 py-2" {...props} />;
        },
        a({ node, children, href, ...props }) {
          const isExternal = href?.startsWith('http');
          return (
            <a 
              href={href} 
              target={isExternal ? "_blank" : undefined}
              rel={isExternal ? "noopener noreferrer" : undefined}
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
              {...props}
            >
              {children}
              {isExternal && (
                <span className="inline-block ml-0.5 text-xs">↗</span>
              )}
            </a>
          );
        },
        img({ node, ...props }) {
          return (
            <img 
              className="max-w-full rounded-md" 
              alt={props.alt || ""}
              {...props} 
            />
          );
        },
        blockquote({ node, ...props }) {
          return (
            <blockquote 
              className="pl-4 border-l-4 border-gray-300 dark:border-gray-600 italic text-gray-700 dark:text-gray-300"
              {...props} 
            />
          );
        }
      }}
    >
      {children}
    </ReactMarkdown>
  );
};

export default Markdown;