import { useEffect, useRef } from 'react'
import { createRoot } from 'react-dom/client'
import MermaidBlock from './MermaidBlock'

const blockCode = (block) => typeof block?.content === 'string'
  ? block.content
  : (block?.content || []).map((part) => part?.text || '').join('')

export default function InlineMermaidPreviews({ editor, containerRef }) {
  const rootsRef = useRef(new Map())

  useEffect(() => {
    const roots = rootsRef.current
    const sync = () => {
      const container = containerRef.current
      if (!container) return
      const active = new Set()
      for (const block of editor.document) {
        if (block.type !== 'codeBlock' || block.props?.language?.toLowerCase() !== 'mermaid') continue
        const source = container.querySelector(`[data-id="${CSS.escape(block.id)}"]`)
        if (!source) continue
        active.add(block.id)
        let entry = roots.get(block.id)
        if (!entry) {
          const mount = document.createElement('div')
          mount.className = 'mermaid-inline-host'
          mount.contentEditable = 'false'
          source.appendChild(mount)
          entry = { mount, root: createRoot(mount) }
          roots.set(block.id, entry)
        }
        entry.root.render(<MermaidBlock code={blockCode(block)} />)
      }
      for (const [id, entry] of roots) {
        if (active.has(id) && entry.mount.isConnected) continue
        entry.root.unmount(); entry.mount.remove(); roots.delete(id)
      }
    }
    sync()
    const unsubscribe = editor.onChange(sync)
    const observer = new MutationObserver(sync)
    if (containerRef.current) observer.observe(containerRef.current, { childList: true, subtree: true })
    return () => {
      observer.disconnect()
      if (typeof unsubscribe === 'function') unsubscribe()
      for (const entry of roots.values()) entry.root.unmount()
      roots.clear()
    }
  }, [containerRef, editor])
  return null
}
