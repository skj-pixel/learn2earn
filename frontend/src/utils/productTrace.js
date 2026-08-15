// 🔍 [作用] 生成任务页跳转到产品库时使用稳定的 taskId 查询参数。
export function taskProductsUrl(taskId) {
  // 🔍 [陷阱] encodeURIComponent 防止未来任务标识改为字符串后破坏 URL。
  return `/products?taskId=${encodeURIComponent(taskId)}`
}

// 🔍 [作用] 判断产品是否属于指定生成任务；没有筛选条件时保留全部产品。
export function productMatchesTask(product, taskId) {
  // 🔍 [语法] Number 统一 URL 字符串与后端数字 ID 的比较类型。
  return !taskId || Number(product?.generation_meta?.task_id) === Number(taskId)
}

// 🔍 [作用] 每个产品都返回明确任务标签，历史数据不再出现字段空缺。
export function productTaskLabel(product) {
  // 🔍 [语法] 可选链兼容没有 generation_meta 的历史产品。
  const taskId = product?.generation_meta?.task_id
  // 🔍 [返回] 有关联时给出编号，否则明确标记为历史产品。
  return taskId ? `任务 #${taskId}` : '任务：历史产品（未关联）'
}
