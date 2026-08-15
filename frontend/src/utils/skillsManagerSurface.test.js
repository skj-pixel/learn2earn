import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const source = readFileSync(new URL('../components/SkillsManager.jsx', import.meta.url), 'utf8')

test('Skills repository exposes only the batch installation surface', () => {
  assert.match(source, /批量安装/)
  assert.doesNotMatch(source, /导入知识付费包/)
  assert.doesNotMatch(source, /上传 Skill 包/)
  assert.doesNotMatch(source, /importBundled/)
  assert.doesNotMatch(source, /api\.skills\.upload\(/)
})

test('Skill cards display compact product number labels', () => {
  assert.match(source, /skill\.product_type_ids/)
  assert.match(source, /适合知识产品 \$\{id\}/)
})

test('Skill repository pages results and rejects stale search responses', () => {
  assert.match(source, /const requestId = useRef\(0\)/)
  assert.match(source, /currentRequest !== requestId\.current/)
  assert.match(source, /limit: pageSize, offset/)
  assert.match(source, /加载更多/)
  assert.doesNotMatch(source, /useEffect\(\(\) => \{ load\(\) \}, \[\]\)/)
})
