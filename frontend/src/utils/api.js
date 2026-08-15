// 🔍 [语法] 常量定义
// 🔍 [作用] API base URL 和 Token localStorage key
const BASE_URL = '/api'
const TOKEN_KEY = 'learn2earn_access_token'

// 🔍 [语法] export function + 同步
// 🔍 [作用] 从 localStorage 取 Token
export function getAccessToken() {
  // 🔍 [语法] 或运算
  // 🔍 [作用] 空字符串兜底
  return localStorage.getItem(TOKEN_KEY) || ''
}

// 🔍 [语法] export function + 同步
// 🔍 [作用] 写入/删除 Token
export function setAccessToken(token) {
  // 🔍 [语法] 条件分支
  // 🔍 [作用] 空字符串删除，否则保存
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

// 🔍 [语法] async function + 私有
// 🔍 [作用] 通用 fetch 封装（自动注入 Token）
async function request(url, options = {}) {
  // 🔍 [语法] 取 Token
  // 🔍 [作用] 用于 Authorization header
  const token = getAccessToken()

  // 🔍 [语法] fetch + await
  // 🔍 [作用] 发起 HTTP 请求
  const res = await fetch(`${BASE_URL}${url}`, {
    // 🔍 [语法] headers spread
    // 🔍 [作用] 默认 headers + 自定义 + 条件 Authorization
    headers: {
      'Content-Type': 'application/json',
      // 🔍 [语法] 条件 spread
      // 🔍 [作用] 有 token 才加 Authorization 头
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    // 🔍 [语法] options spread
    // 🔍 [作用] 允许 method/body 等覆盖
    ...options,
  })

  // 🔍 [语法] 错误处理
  // 🔍 [作用] 非 2xx 抛错
  if (!res.ok) {
    // 🔍 [语法] try/catch + .catch
    // 🔍 [作用] 尝试解析 JSON 错误，失败回退文本
    const err = await res.json().catch(() => ({ detail: '请求失败' }))
    // 🔍 [语法] throw Error
    // 🔍 [作用] 抛出供 UI catch 的错误
    throw new Error(err.detail || '请求失败')
  }

  // 🔍 [语法] JSON 解析
  // 🔍 [作用] 正常响应
  return res.json()
}

async function requestForm(url, formData) {
  const token = getAccessToken()
  const res = await fetch(`${BASE_URL}${url}`, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: formData })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: '上传失败' }))
    throw new Error(err.detail || '上传失败')
  }
  return res.json()
}

async function downloadFile(url) {
  const token = getAccessToken()
  const res = await fetch(`${BASE_URL}${url}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || '下载失败')
  return { blob: await res.blob(), disposition: res.headers.get('content-disposition') || '' }
}

export { request as apiRequest }

// 🔍 [语法] export const api = { ... }
// 🔍 [作用] 模块导出 API 客户端（6 大模块）
export const api = {
  // 🔍 [语法] 嵌套对象
  // 🔍 [作用] 认证 API
  auth: {
    // 🔍 [语法] 箭头函数 + async
    // 🔍 [作用] 登录（保存 Token）
    login: async (email, password) => {
      const result = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
      setAccessToken(result.access_token)
      return result
    },
    // 🔍 [语法] 注册（条件保存 Token）
    signup: async (email, password) => {
      const result = await request('/auth/signup', { method: 'POST', body: JSON.stringify({ email, password }) })
      if (result.access_token) setAccessToken(result.access_token)
      return result
    },
    // 🔍 [语法] GET 包装
    // 🔍 [作用] 获取当前用户
    me: () => request('/auth/me'),
    // 🔍 [语法] 同步
    // 🔍 [作用] 登出（清 Token）
    logout: () => setAccessToken(''),
    // 🔍 [语法] 忘记密码
    forgotPassword: (email) => request('/auth/forgot-password', { method: 'POST', body: JSON.stringify({ email }) }),
  },

  // 🔍 [语法] 科目 CRUD
  // 🔍 [作用] 复用同一 request 函数
  subjects: {
    list: () => request('/subjects'),
    create: (data) => request('/subjects', { method: 'POST', body: JSON.stringify(data) }),
    get: (id) => request(`/subjects/${id}`),
    update: (id, data) => request(`/subjects/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id) => request(`/subjects/${id}`, { method: 'DELETE' }),
  },

  // 🔍 [语法] 笔记 CRUD（带查询参数）
  notes: {
    // 🔍 [语法] URLSearchParams
    // 🔍 [作用] 构造 query string
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString()
      return request(`/notes${qs ? '?' + qs : ''}`)
    },
    create: (data) => request('/notes', { method: 'POST', body: JSON.stringify(data) }),
    get: (id) => request(`/notes/${id}`),
    update: (id, data) => request(`/notes/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id) => request(`/notes/${id}`, { method: 'DELETE' }),
    uploadImage: (id, file) => { const form = new FormData(); form.append('file', file); return requestForm(`/notes/${id}/images`, form) },
  },

  // 🔍 [语法] 产品 CRUD
  products: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString()
      return request(`/products${qs ? '?' + qs : ''}`)
    },
    create: (data) => request('/products', { method: 'POST', body: JSON.stringify(data) }),
    get: (id) => request(`/products/${id}`),
    update: (id, data) => request(`/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id) => request(`/products/${id}`, { method: 'DELETE' }),
    exportDocx: (id) => downloadFile(`/products/${id}/export.docx`),
    sourceAssets: (id) => request(`/products/${id}/source-assets`),
  },

  // 🔍 [语法] AI 端点（11+ 个）
  // 🔍 [作用] AI 生成相关
  ai: {
    productTypes: () => request('/ai/product-types'),
    // 🔍 [语法] content + subject_name 参数
    // 🔍 [作用] 分析笔记内容
    analyze: (content, subjectName = '') =>
      request('/ai/analyze', { method: 'POST', body: JSON.stringify({ content, subject_name: subjectName }) }),
    // 🔍 [语法] 4 个布尔参数（默认值）
    // 🔍 [作用] 生成指定产品类型
    generate: (noteId, productTypes, save = true, regenerate = false) =>
      request('/ai/generate', { method: 'POST', body: JSON.stringify({ note_id: noteId, product_types: productTypes, save_to_db: save, regenerate }) }),
    // 🔍 [语法] 一键生成
    generateAll: (noteId, save = true, regenerate = false) =>
      request('/ai/generate-all', { method: 'POST', body: JSON.stringify({ note_id: noteId, save_to_db: save, regenerate }) }),
    // 🔍 [语法] 产品规划
    plan: (noteId, autoConfirm = false) =>
      request('/ai/plan', { method: 'POST', body: JSON.stringify({ note_id: noteId, auto_confirm: autoConfirm }) }),
    // 🔍 [语法] 从规划生成
    generateFromPlan: (noteId, productTypes, save = true) =>
      request('/ai/generate-from-plan', { method: 'POST', body: JSON.stringify({ note_id: noteId, product_types: productTypes, save_to_db: save }) }),
    // 🔍 [语法] 极速生成
    fastGenerate: (noteId, save = true) =>
      request('/ai/fast-generate', { method: 'POST', body: JSON.stringify({ note_id: noteId, save_to_db: save }) }),
    // 🔍 [语法] 重新生成（覆盖）
    regenerate: (productId) =>
      request('/ai/regenerate', { method: 'POST', body: JSON.stringify({ product_id: productId }) }),
    suggest: (noteId) => request(`/ai/suggest/${noteId}`),
  },

  // 🔍 [语法] 全局统计
  // 🔍 [作用] Dashboard 用
  stats: () => request('/stats'),

  config: {
    llms: () => request('/config/llms'),
    createLlm: (data) => request('/config/llms', { method: 'POST', body: JSON.stringify(data) }),
    updateLlm: (name, data) => request(`/config/llms/${name}`, { method: 'PUT', body: JSON.stringify(data) }),
    activateLlm: (name) => request('/config/llms/active', { method: 'PUT', body: JSON.stringify({ name }) }),
    deleteLlm: (name) => request(`/config/llms/${name}`, { method: 'DELETE' }),
    testLlm: (data) => request('/config/llms/test', { method: 'POST', body: JSON.stringify(data) }),
    envImportMeta: () => request('/config/llms/env-import-meta'),
  },
  skills: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString()
      return request(`/skills${qs ? '?' + qs : ''}`)
    },
    upload: (file, category = '知识产品') => { const form = new FormData(); form.append('file', file); form.append('category', category); return requestForm('/skills/upload', form) },
    // 🔍 [作用] 2026-08 feat/28：批量上传多个 zip 压缩包；后端逐个解压，失败项返回 failures
    batchUpload: (files, category = '知识产品') => { const form = new FormData(); Array.from(files || []).forEach((f) => form.append('files', f)); form.append('category', category); return requestForm('/skills/batch-upload', form) },
    importBundled: () => request('/skills/import-bundled', { method: 'POST' }),
    update: (id, data) => request(`/skills/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
    delete: (id) => request(`/skills/${id}`, { method: 'DELETE' }),
  },
  tasks: {
    list: (params = {}) => {
      const qs = new URLSearchParams(params).toString()
      return request(`/tasks${qs ? '?' + qs : ''}`)
    },
    get: (id) => request(`/tasks/${id}`),
    strategies: () => request('/tasks/strategies'),
    // 🔍 [作用] 2026-08 feat/29：data.product_strategies 可选，dict[product_type] = {skill_ids, algorithms, techniques}
    create: (data) => request('/tasks', { method: 'POST', body: JSON.stringify(data) }),
    retry: (id) => request(`/tasks/${id}/retry`, { method: 'POST' }),
    delete: (id) => request(`/tasks/${id}`, { method: 'DELETE' }),
  },
  // 🔍 [语法] MemoryBear 长程记忆 API
  // 🔍 [作用] 五层记忆预览 / 全局统计 / 场景路由权重
  memorybear: {
    // 🔍 [语法] query 参数 note_id
    // 🔍 [作用] 预览当前笔记的 MemoryBear 上下文
    preview: (noteId) => request(`/memorybear/preview?note_id=${noteId}`),
    // 🔍 [语法] 无参数
    // 🔍 [作用] 全局记忆统计（各层条目数 + 重要性分布 + 冲突点）
    stats: () => request('/memorybear/stats'),
    // 🔍 [语法] query 参数 note_id
    // 🔍 [作用] 查询 MemoryBear vs RAG 权重建议
    sceneRouter: (noteId) => request(`/memorybear/scene-router?note_id=${noteId}`),
  },
  // 🔍 [语法] 用户策略偏好 API
  // 🔍 [作用] 按产品类型自定义 algorithms / techniques / skill_keywords 覆盖
  strategyPreferences: {
    list: () => request('/strategy-preferences'),
    get: (productType) => request(`/strategy-preferences/${productType}`),
    update: (productType, data) => request(`/strategy-preferences/${productType}`, { method: 'PUT', body: JSON.stringify(data) }),
    reset: (productType) => request(`/strategy-preferences/${productType}`, { method: 'DELETE' }),
  },
}
