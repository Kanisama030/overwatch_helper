import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';

interface MarkdownContentProps {
  content: string;
  className?: string;
  textClassName?: string;
  listItemClassName?: string;
  imageClassName?: string;
}

function getFallbackFromSrc(src: string | undefined): string | null {
  if (!src) return null;
  const marker = '#fallback=';
  const idx = src.indexOf(marker);
  if (idx < 0) return null;
  try {
    return decodeURIComponent(src.slice(idx + marker.length));
  } catch {
    return null;
  }
}

export function MarkdownContent({
  content,
  className = '',
  textClassName = 'text-sm leading-relaxed text-white mb-2 last:mb-0',
  listItemClassName = 'text-sm leading-relaxed text-gray-200',
  imageClassName = 'inline-block align-text-bottom w-4 h-4 md:w-[18px] md:h-[18px] mx-1 my-0 rounded-sm border border-white/10 object-contain',
}: MarkdownContentProps) {
  return (
    <div className={`prose prose-invert max-w-none ${className}`}>
      <ReactMarkdown
        rehypePlugins={[rehypeSanitize]}
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className={textClassName}>{children}</p>,
          strong: ({ children }) => <strong className="font-extrabold text-white">{children}</strong>,
          ul: ({ children }) => <ul className="list-disc pl-5 space-y-1 mb-2 last:mb-0">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1 mb-2 last:mb-0">{children}</ol>,
          li: ({ children }) => (
            <li className={`${listItemClassName} [&:has(>ul)]:list-none [&:has(>ol)]:list-none`}>{children}</li>
          ),
          img: ({ src, alt }) => (
            <img
              src={src}
              alt={alt ?? ''}
              className={imageClassName}
              loading="lazy"
              onError={e => {
                const target = e.currentTarget;
                const fallback = getFallbackFromSrc(target.src);
                if (fallback && target.dataset.fallbackApplied !== '1') {
                  target.dataset.fallbackApplied = '1';
                  target.src = fallback;
                  return;
                }
                target.style.display = 'none';
              }}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
