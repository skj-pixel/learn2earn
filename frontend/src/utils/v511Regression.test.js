import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

test('product viewer renders TeX and each Mermaid fence in place', () => {
  const viewer = read('../components/ProductViewer.jsx')
  const markdown = read('../components/MathMarkdown.jsx')
  assert.match(viewer, /<MathMarkdown>/)
  assert.match(markdown, /remarkMath/)
  assert.match(markdown, /rehypeKatex/)
  assert.match(markdown, /language === 'mermaid'/)
  assert.match(markdown, /<MermaidBlock code=/)
})

test('BlockNote renders Mermaid beside its source block without a whole-document preview', () => {
  const editor = read('../components/RichTextEditor.jsx')
  const note = read('../components/NoteEditor.jsx')
  assert.match(editor, /InlineMermaidPreviews/)
  assert.doesNotMatch(note, /Mermaid 图表预览|editorPreview/)
})

test('generation UI sends a common prompt and per-product prompts', () => {
  const generator = read('../components/ProductGenerator.jsx')
  assert.match(generator, /common_prompt:/)
  assert.match(generator, /product_prompts:/)
  assert.match(generator, /公共提示词/)
  assert.match(generator, /该产品提示词/)
})

test('dashboard uses exact API stats rather than partial store lengths', () => {
  const dashboard = read('../components/Dashboard.jsx')
  assert.match(dashboard, /stats\?\.products \?\? 0/)
  assert.match(dashboard, /stats\?\.notes \?\? 0/)
  assert.doesNotMatch(dashboard, /stats\?\.products \|\| products\.length/)
  assert.doesNotMatch(dashboard, /stats\?\.notes \|\| notes\.length/)
})
