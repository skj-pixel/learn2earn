import fs from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import assert from 'node:assert/strict'

const source = fs.readFileSync(path.resolve('src/components/NoteEditor.jsx'), 'utf8')

test('note editor exposes a restrained five-layer knowledge enhancement status', () => {
  assert.match(source, /知识增强状态/)
  assert.match(source, /感知记忆/)
  assert.match(source, /Memory Bear 已启用/)
  assert.match(source, /RAG 按需检索/)
})

test('routing advice is not presented as actual Memory Bear and RAG usage', () => {
  assert.doesNotMatch(source, /MB 权重/)
  assert.match(source, /路由建议/)
})
