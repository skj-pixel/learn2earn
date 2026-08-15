import test from 'node:test'
import assert from 'node:assert/strict'

import { repairFencedCodeBlocks } from './editorContent.js'

const paragraph = (text) => ({ type: 'paragraph', content: [{ type: 'text', text, styles: {} }] })

test('repairs historical Python fence paragraphs into a code block', () => {
  const result = repairFencedCodeBlocks([
    paragraph('```python\nfrom gm.api import *'),
    paragraph('def init(context):\n    context.period = 20'),
    paragraph('```'),
  ])

  assert.equal(result.length, 1)
  assert.equal(result[0].type, 'codeBlock')
  assert.equal(result[0].props.language, 'python')
  assert.match(result[0].content, /def init\(context\)/)
})

test('preserves Mermaid fences as Mermaid code blocks', () => {
  const result = repairFencedCodeBlocks([
    paragraph('```mermaid'),
    paragraph('graph TD\nA-->B'),
    paragraph('```'),
  ])

  assert.equal(result[0].type, 'codeBlock')
  assert.equal(result[0].props.language, 'mermaid')
  assert.match(result[0].content, /A-->B/)
})

test('repairs a complete fenced block stored in one historical paragraph', () => {
  const result = repairFencedCodeBlocks([
    paragraph('```python\nprint(1)\n```'),
  ])

  assert.equal(result.length, 1)
  assert.equal(result[0].type, 'codeBlock')
  assert.equal(result[0].props.language, 'python')
  assert.equal(result[0].content, 'print(1)')
})
