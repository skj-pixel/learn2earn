import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import MermaidBlock from './MermaidBlock'

const components = {
  code({ className, children, ...props }) {
    const language = /language-([^\s]+)/.exec(className || '')?.[1]?.toLowerCase()
    if (language === 'mermaid') return <MermaidBlock code={String(children).replace(/\n$/, '')} />
    return <code className={className} {...props}>{children}</code>
  },
}

export default function MathMarkdown({ children }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[[rehypeKatex, { strict: false, throwOnError: false }]]} components={components}>{children || ''}</ReactMarkdown>
}
