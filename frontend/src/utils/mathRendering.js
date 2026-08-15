import { marked } from 'marked'
import DOMPurify from 'dompurify'
import renderMathInElement from 'katex/contrib/auto-render'

export function renderMarkdownForPrint(markdown, documentRef = document) {
  const container = documentRef.createElement('div')
  container.innerHTML = DOMPurify.sanitize(marked.parse(markdown || ''))
  renderMathInElement(container, {
    delimiters: [
      { left: '$$', right: '$$', display: true },
      { left: '\\[', right: '\\]', display: true },
      { left: '\\(', right: '\\)', display: false },
      { left: '$', right: '$', display: false },
    ],
    ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code'],
    strict: false,
    throwOnError: false,
  })
  return container.innerHTML
}
