// 🔍 [语法] 使用 Node 内置测试器，不增加第三方测试依赖。
import test from 'node:test'
// 🔍 [语法] 严格断言用于验证页面追溯契约。
import assert from 'node:assert/strict'
// 🔍 [作用] 导入任务跳转、筛选和标签三个纯函数。
import { productMatchesTask, productTaskLabel, taskProductsUrl } from './productTrace.js'

// 🔍 [作用] 验证任务页始终跳到带 taskId 的产品库，而非单一产品编辑页。
test('taskProductsUrl targets the filtered product library', () => {
  // 🔍 [断言] 路由与查询参数必须保持稳定。
  assert.equal(taskProductsUrl(42), '/products?taskId=42')
})

// 🔍 [作用] 验证同一任务的多个产品都会保留，其他任务产品会被排除。
test('productMatchesTask filters every product by generation task', () => {
  // 🔍 [准备] 两个产品模拟同任务多产品结果。
  const first = { generation_meta: { task_id: 42 } }
  const second = { generation_meta: { task_id: 42 } }
  // 🔍 [断言] 数字或 URL 字符串形式的任务号均可匹配。
  assert.equal(productMatchesTask(first, '42'), true)
  assert.equal(productMatchesTask(second, 42), true)
  // 🔍 [断言] 其他任务不会混入筛选结果。
  assert.equal(productMatchesTask({ generation_meta: { task_id: 7 } }, 42), false)
})

// 🔍 [作用] 验证新旧产品都展示明确的任务关联信息。
test('productTaskLabel describes linked and legacy products', () => {
  // 🔍 [断言] 新产品显示具体任务编号。
  assert.equal(productTaskLabel({ generation_meta: { task_id: 42 } }), '任务 #42')
  // 🔍 [断言] 历史产品明确显示未关联状态。
  assert.equal(productTaskLabel({}), '任务：历史产品（未关联）')
})
