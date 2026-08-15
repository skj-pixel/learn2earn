import { useEffect, useId, useState } from 'react'
import DOMPurify from 'dompurify'

let mermaidPromise

function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', theme: 'default' })
      return mermaid
    })
  }
  return mermaidPromise
}

export default function MermaidBlock({ code }) {
  const id = useId().replace(/:/g, '')
  const [svg, setSvg] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    loadMermaid()
      .then((mermaid) => mermaid.render(`mermaid-${id}`, code || ''))
      .then(({ svg: rendered }) => {
        if (!active) return
        setSvg(DOMPurify.sanitize(rendered, { USE_PROFILES: { svg: true } }))
        setError('')
      })
      .catch((reason) => {
        if (!active) return
        setSvg('')
        setError(reason?.message || 'Mermaid 语法错误')
      })
    return () => { active = false }
  }, [code, id])

  if (error) return <div className="mermaid-inline-error" role="alert">{error}</div>
  return <div className="mermaid-inline-diagram" dangerouslySetInnerHTML={{ __html: svg }} />
}
