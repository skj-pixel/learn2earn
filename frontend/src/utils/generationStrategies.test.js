import test from 'node:test'
import assert from 'node:assert/strict'

import { implementedStrategies, productPreference, selectedConflicts, strategySummary } from './generationStrategies.js'

test('implementedStrategies removes unavailable algorithms and techniques', () => {
  const strategies = {
    algorithms: [{ id: 'ready', implemented: true }, { id: 'planned', implemented: false }],
    techniques: [{ id: 'quality', implemented: true }, { id: 'future', implemented: false }],
  }

  assert.deepEqual(implementedStrategies(strategies), {
    algorithms: [{ id: 'ready', implemented: true }],
    techniques: [{ id: 'quality', implemented: true }],
  })
})

test('productPreference returns the saved product-level defaults', () => {
  const strategies = {
    user_overrides: {
      ppt: {
        algorithms: ['hierarchical_planning'],
        techniques: ['quality_scoring'],
        skill_keywords: ['dashi-ppt'],
      },
    },
  }

  assert.deepEqual(productPreference(strategies, 'ppt'), {
    algorithms: ['hierarchical_planning'],
    techniques: ['quality_scoring'],
    skill_keywords: ['dashi-ppt'],
  })
  assert.deepEqual(productPreference(strategies, 'article'), {
    algorithms: [], techniques: [], skill_keywords: [],
  })
})

test('strategySummary hides component details in overview cards', () => {
  assert.equal(strategySummary({ algorithms: ['a'], techniques: [], skill_keywords: ['ppt-skill'] }), '已自定义生成策略')
  assert.equal(strategySummary({ algorithms: [], techniques: [], skill_keywords: [] }), '使用默认生成策略')
})

test('selectedConflicts reports declared pair conflicts only', () => {
  const rows = selectedConflicts(
    { algorithms: ['a', 'b'], techniques: [], skill_ids: [] },
    { generation: [{ left: 'algorithm:a', right: 'algorithm:b', left_name: 'A', right_name: 'B', status: 'conflict', reason: 'cannot combine' }] },
  )
  assert.equal(rows.length, 1)
  assert.equal(rows[0].reason, 'cannot combine')
  assert.equal(rows[0].left_name, 'A')
})

test('selectedConflicts detects algorithm-skill and quality conflicts in two groups', () => {
  const rows = selectedConflicts(
    { algorithms: ['a'], skill_ids: [7], techniques: ['q1', 'q2'] },
    {
      generation: [{ left: 'algorithm:a', right: 'skill:7', status: 'conflict', reason: 'generation conflict' }],
      quality: [{ left: 'q1', right: 'q2', status: 'conflict', reason: 'quality conflict' }],
    },
  )
  assert.deepEqual(rows.map((row) => row.group), ['generation', 'quality'])
})

test('selectedConflicts checks per-product overrides and deduplicates repeated pairs', () => {
  const rows = selectedConflicts(
    {
      algorithms: ['safe'], skill_ids: [], techniques: [],
      product_strategies: {
        ppt: { algorithms: ['a'], skill_ids: [7], techniques: [] },
        article: { algorithms: ['a'], skill_ids: [7], techniques: [] },
      },
    },
    { generation: [{ left: 'algorithm:a', right: 'skill:7', status: 'conflict', reason: 'conflict' }] },
  )
  assert.equal(rows.length, 1)
})
