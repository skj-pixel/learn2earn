import test from 'node:test'
import assert from 'node:assert/strict'

import { withUniqueSubjectDisplayNames } from './subjectDisplayNames.js'

test('duplicate display names never collide with real suffixed subject names', () => {
  const result = withUniqueSubjectDisplayNames([
    { id: 3, name: '名称' },
    { id: 1, name: '名称' },
    { id: 2, name: '名称-1' },
  ])

  assert.deepEqual(result.map((subject) => subject.displayName), ['名称-2', '名称', '名称-1'])
  assert.equal(new Set(result.map((subject) => subject.displayName)).size, 3)
})
