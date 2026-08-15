// 🔍 [语法] Zustand 导入
// 🔍 [作用] 状态管理库 create 函数
import { create } from 'zustand'

// 🔍 [语法] API 客户端
// 🔍 [作用] 后端 API 封装
import { api } from '../utils/api'

// 🔍 [语法] Zustand create
// 🔍 [作用] 创建 store（全局 state + actions）
// 🔍 [示例] const subjects = useStore(s => s.subjects)
const useStore = create((set, get) => ({
  // ==================== 全局状态 ====================
  // 🔍 [语法] 空数组默认值
  // 🔍 [作用] 业务数据
  subjects: [],
  notes: [],
  products: [],
  // 🔍 [语法] 后台任务列表（2026-08 fix/26：跨页面统一可见，避免 navigate 后空闪）
  // 🔍 [作用] 由 enqueueTask 维护；GenerationTasks 页面读它，提交任务时立即可见
  tasks: [],
  // 🔍 [语法] null 默认
  // 🔍 [作用] 统计信息
  stats: null,
  // 🔍 [语法] 布尔默认值
  // 🔍 [作用] 全局 loading 标志
  loading: false,
  // 🔍 [语法] null
  // 🔍 [作用] 最近错误信息
  error: null,

  // ==================== 当前选中 ====================
  // 🔍 [语法] 三个 null
  // 🔍 [作用] 跨页面传递的"当前对象"
  currentSubject: null,
  currentNote: null,
  currentProduct: null,

  // ==================== 科目相关 Actions ====================
  // 🔍 [语法] set 简写
  // 🔍 [作用] 设置当前选中科目
  setCurrentSubject: (subject) => set({ currentSubject: subject }),

  // 🔍 [语法] async 拉取
  // 🔍 [作用] 覆盖式更新 subjects
  fetchSubjects: async () => {
    try {
      const subjects = await api.subjects.list()
      // 🔍 [语法] set partial
      // 🔍 [作用] 只更新 subjects 字段
      set({ subjects })
      return subjects
    } catch (e) {
      // 🔍 [语法] 错误捕获
      // 🔍 [作用] 不阻塞 UI
      set({ error: e.message })
      return []
    }
  },

  // 🔍 [语法] insert 头部
  // 🔍 [作用] 创建后插入到列表头部
  createSubject: async (data) => {
    const subject = await api.subjects.create(data)
    // 🔍 [语法] set with function
    // 🔍 [作用] 基于旧状态插入
    set((s) => ({ subjects: [subject, ...s.subjects] }))
    return subject
  },

  // 🔍 [语法] 按 id 替换
  // 🔍 [作用] map 替换指定项
  updateSubject: async (id, data) => {
    const subject = await api.subjects.update(id, data)
    set((s) => ({
      subjects: s.subjects.map((sub) => (sub.id === id ? { ...sub, ...subject } : sub)),
    }))
    return subject
  },

  // 🔍 [语法] 过滤删除
  // 🔍 [作用] 同时清空 currentSubject（如果指向被删项）
  deleteSubject: async (id) => {
    await api.subjects.delete(id)
    set((s) => ({
      subjects: s.subjects.filter((sub) => sub.id !== id),
      // 🔍 [语法] 可选链 + 逻辑等
      // 🔍 [作用] 检查是否需要清空 currentSubject
      currentSubject: s.currentSubject?.id === id ? null : s.currentSubject,
    }))
  },

  // ==================== 笔记相关 Actions ====================
  setCurrentNote: (note) => set({ currentNote: note }),

  // 🔍 [语法] 支持 params 过滤
  fetchNotes: async (params = {}) => {
    try {
      const notes = await api.notes.list({ summary: true, ...params })
      set({ notes })
      return notes
    } catch (e) {
      set({ error: e.message, notes: [] })
      return []
    }
  },

  createNote: async (data) => {
    const note = await api.notes.create(data)
    set((s) => ({ notes: [note, ...s.notes] }))
    return note
  },

  // 🔍 [语法] 同时更新 currentNote
  // 🔍 [作用] 编辑笔记后立即反映
  updateNote: async (id, data) => {
    const note = await api.notes.update(id, data)
    set((s) => ({
      notes: s.notes.map((n) => (n.id === id ? { ...n, ...note } : n)),
      currentNote: s.currentNote?.id === id ? { ...s.currentNote, ...note } : s.currentNote,
    }))
    return note
  },

  deleteNote: async (id) => {
    await api.notes.delete(id)
    set((s) => ({
      notes: s.notes.filter((n) => n.id !== id),
      currentNote: s.currentNote?.id === id ? null : s.currentNote,
    }))
  },

  // ==================== 产品相关 Actions ====================
  setCurrentProduct: (product) => set({ currentProduct: product }),

  fetchProducts: async (params = {}) => {
    try {
      const products = await api.products.list(params)
      set({ products })
      return products
    } catch (e) {
      set({ error: e.message, products: [] })
      return []
    }
  },

  createProduct: async (data) => {
    const product = await api.products.create(data)
    set((s) => ({ products: [product, ...s.products] }))
    return product
  },

  updateProduct: async (id, data) => {
    const product = await api.products.update(id, data)
    set((s) => ({
      products: s.products.map((p) => (p.id === id ? { ...p, ...product } : p)),
    }))
    return product
  },

  deleteProduct: async (id) => {
    await api.products.delete(id)
    set((s) => ({
      products: s.products.filter((p) => p.id !== id),
      currentProduct: s.currentProduct?.id === id ? null : s.currentProduct,
    }))
  },

  // 🔍 [语法] 业务封装
  // 🔍 [作用] 一键发布（status: draft → published）
  publishProduct: async (id) => {
    // 🔍 [语法] 调用 update 传 status
    // 🔍 [作用] 复用 update action
    const product = await api.products.update(id, { status: 'published' })
    set((s) => ({
      products: s.products.map((p) => (p.id === id ? { ...p, ...product } : p)),
    }))
    return product
  },

  // ==================== AI 生成 ====================
  // 🔍 [语法] loading 状态管理
  // 🔍 [作用] 生成时显示 loading 动画
  generateProducts: async (noteId, productTypes) => {
    set({ loading: true })
    try {
      const result = await api.ai.generate(noteId, productTypes)
      // 🔍 [语法] get() 取当前 state
      // 🔍 [作用] 生成后刷新产品列表
      await get().fetchProducts()
      return result
    } catch (e) {
      set({ error: e.message })
      // 🔍 [语法] rethrow
      // 🔍 [作用] UI 可 catch 后提示
      throw e
    } finally {
      // 🔍 [语法] finally 清理
      // 🔍 [作用] 无论成功失败都关闭 loading
      set({ loading: false })
    }
  },

  // ==================== 后台生成任务（2026-08 fix/26） ====================
  deletedTaskIds: [],
  // 🔍 [作用] 拉取当前用户的所有后台任务；与本地 store.tasks 合并去重（按 id）
  fetchTasks: async () => {
    try {
      const list = await api.tasks.list()
      // 🔍 [作用] 排序：按 created_at 倒序；与后端默认一致
      const deletedIds = new Set(get().deletedTaskIds || [])
      const sorted = [...(list || [])].filter((task) => !deletedIds.has(task.id)).sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
      set((s) => {
        // 🔍 [作用] 保留内存中尚未被后端 list 返回的新建任务（乐观更新防丢）
        const knownIds = new Set(sorted.map((t) => t.id))
        const pending = (s.tasks || []).filter((t) => !deletedIds.has(t.id) && !knownIds.has(t.id))
        return { tasks: [...sorted, ...pending] }
      })
      return sorted
    } catch (e) {
      set({ error: e.message })
      return []
    }
  },
  // 🔍 [作用] 提交后台任务：写 store + 调后端；UI 立即看到，无需等后端写盘
  enqueueTask: async (data) => {
    const task = await api.tasks.create(data)
    set((s) => ({
      deletedTaskIds: (s.deletedTaskIds || []).filter((id) => id !== task.id),
      tasks: [task, ...(s.tasks || []).filter((t) => t.id !== task.id)],
    }))
    return task
  },
  retryTask: async (id) => {
    const task = await api.tasks.retry(id)
    set((s) => ({ tasks: [task, ...(s.tasks || []).filter((item) => item.id !== task.id)] }))
    return task
  },
  // 🔍 [作用] 单条刷新任务状态（用于任务页轮询）
  refreshTask: async (id) => {
    try {
      const fresh = await api.tasks.get(id)
      if ((get().deletedTaskIds || []).includes(id)) return null
      set((s) => ({ tasks: (s.tasks || []).map((t) => (t.id === id ? fresh : t)) }))
      return fresh
    } catch (e) {
      return null
    }
  },
  deleteTask: async (id) => {
    await api.tasks.delete(id)
    set((s) => ({
      deletedTaskIds: [...new Set([...(s.deletedTaskIds || []), id])],
      tasks: (s.tasks || []).filter((task) => task.id !== id),
    }))
  },

  generateAllProducts: async (noteId) => {
    set({ loading: true })
    try {
      const result = await api.ai.generateAll(noteId)
      await get().fetchProducts()
      return result
    } catch (e) {
      set({ error: e.message })
      throw e
    } finally {
      set({ loading: false })
    }
  },

  // ==================== 统计 ====================
  fetchStats: async () => {
    try {
      const stats = await api.stats()
      set({ stats })
      return stats
    } catch (e) {
      set({ error: e.message })
      return null
    }
  },
}))

// 🔍 [语法] default export
// 🔍 [作用] 默认导出
export default useStore
