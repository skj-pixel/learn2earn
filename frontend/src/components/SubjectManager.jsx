// 🔍 [语法] React Hooks
// 🔍 [作用] useState/useEffect
import { useState, useEffect } from 'react'

// 🔍 [语法] react-router-dom
// 🔍 [作用] 编程式导航
import { useNavigate } from 'react-router-dom'

// 🔍 [语法] Zustand store
// 🔍 [作用] 科目数据 + CRUD actions
import useStore from '../store/useStore'

// 🔍 [语法] react-hot-toast
// 🔍 [作用] 消息提示
import toast from 'react-hot-toast'
import SearchSortBar, { sortResources } from './SearchSortBar'
import { formatDateTime } from '../utils/dateTime'
import { withUniqueSubjectDisplayNames } from '../utils/subjectDisplayNames'

// 🔍 [语法] 模块级常量
// 🔍 [作用] 15 个 emoji 图标 + 8 个主题色
const ICONS = ['📚', '💻', '🔬', '🧮', '🎨', '🎵', '🌍', '📈', '⚙️', '🧠', '🤖', '⚡', '🔧', '📱', '🎮']
const COLORS = ['#6366f1', '#ec4899', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ef4444', '#06b6d4']

// 🔍 [语法] default export
// 🔍 [作用] 科目管理页（CRUD + 图标选择器 + 颜色选择器）
export default function SubjectManager() {
  const navigate = useNavigate()
  // 🔍 [语法] 解构
  // 🔍 [作用] 取科目数据 + 4 个 CRUD action
  // 🔍 [作用] 2026-08 fix/27：notes 用于前端按 store 实时重算 note_count，不依赖后端字段
  const { subjects, fetchSubjects, createSubject, updateSubject, deleteSubject } = useStore()

  // 🔍 [语法] 5 个状态
  // 🔍 [作用] 表单显隐 + 编辑 ID + 表单数据 + 删除二次确认
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [form, setForm] = useState({ name: '', icon: '📚', description: '', color: '#6366f1' })
  const [deletingId, setDeletingId] = useState(null)  // null 或 id
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('updated')

  // 🔍 [语法] useEffect + 空依赖
  // 🔍 [作用] 仅挂载时拉取
  useEffect(() => {
    // 🔍 [作用] 2026-08 fix/27：同时拉取 notes，前端按 store 实时重算 note_count，避免后端懒加载 / 缓存导致显示 0
    fetchSubjects()
  }, [])

  // Existing duplicate rows are preserved. Stable display suffixes distinguish them
  // without mutating user data; new duplicates are suffixed by the API on creation.
  const enrichedSubjects = withUniqueSubjectDisplayNames(subjects || []).map((subject) => ({
    ...subject,
    note_count: Number(subject.note_count || 0),
  }))
  const visibleSubjects = sortResources(enrichedSubjects.filter((item) => item.displayName.toLowerCase().includes(query.trim().toLowerCase())), sort, (item) => item.note_count || 0)

  // 🔍 [语法] async 函数
  // 🔍 [作用] 提交表单（新建 / 更新）
  const handleSubmit = async (e) => {
    // 🔍 [语法] preventDefault
    // 🔍 [作用] 阻止表单默认提交
    e.preventDefault()
    // 🔍 [语法] 校验
    // 🔍 [作用] 名称必填
    if (!form.name.trim()) return toast.error('请输入科目名称')

    try {
      // 🔍 [语法] if 分支
      // 🔍 [作用] editingId 决定新建还是更新
      if (editingId) {
        await updateSubject(editingId, form)
        toast.success('科目已更新')
        setEditingId(null)
      } else {
        await createSubject(form)
        toast.success('科目创建成功！开始学习吧 🚀')
      }
      // 🔍 [语法] 重置表单
      setShowForm(false)
      setForm({ name: '', icon: '📚', description: '', color: '#6366f1' })
    } catch (e) {
      toast.error(e.message)
    }
  }

  // 🔍 [语法] 函数
  // 🔍 [作用] 进入编辑模式
  const startEdit = (subject) => {
    setEditingId(subject.id)
    // 🔍 [语法] 复制对象
    // 🔍 [作用] 避免引用共享
    setForm({
      name: subject.name,
      icon: subject.icon,
      description: subject.description || '',
      color: subject.color,
    })
    setShowForm(true)
  }

  // 🔍 [语法] 双击确认模式
  // 🔍 [作用] 第一次点击标记，第二次点击确认
  const handleDelete = async (id) => {
    if (deletingId !== id) {
      // 🔍 [语法] 设置标记
      // 🔍 [作用] 下次点击才真正删
      setDeletingId(id)
      return
    }
    try {
      await deleteSubject(id)
      toast.success('科目已删除')
      setDeletingId(null)
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    // 🔍 [语法] max-w-4xl mx-auto
    // 🔍 [作用] 居中容器
    <div className="p-6 max-w-4xl mx-auto">
      {/* ========== 顶部 ========== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">📚 科目管理</h1>
          <p className="text-gray-500 mt-1">添加你要学习的科目，不限领域</p>
        </div>
        {/* 🔍 [语法] 切换表单 */}
        <button
          onClick={() => { setShowForm(!showForm); setEditingId(null); setForm({ name: '', icon: '📚', description: '', color: '#6366f1' }) }}
          className="bg-primary-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-primary-700 transition-colors shadow-lg shadow-primary-200 flex items-center gap-2"
        >
          <span>{showForm ? '✕' : '+'}</span> {showForm ? '取消' : '新建科目'}
        </button>
      </div>
      <SearchSortBar query={query} onQuery={setQuery} sort={sort} onSort={setSort} noun="科目" />

      {/* ========== 表单（新建/编辑） ========== */}
      {showForm && (
        // 🔍 [语法] animate-slide-up
        // 🔍 [作用] 入场动画
        <form onSubmit={handleSubmit} className="bg-white rounded-2xl p-6 mb-6 border border-gray-100 shadow-sm animate-slide-up">
          <h3 className="font-semibold text-gray-800 mb-4">{editingId ? '✏️ 编辑科目' : '🆕 新建科目'}</h3>

          <div className="space-y-4">
            {/* 科目名称 */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">科目名称 *</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="例如：Python编程、嵌入式开发、英语学习..."
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-200 focus:border-primary-400 outline-none transition-all"
                autoFocus  // 🔍 [语法] 自动聚焦
              />
            </div>

            {/* 图标选择器 */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">图标</label>
              <div className="flex flex-wrap gap-2">
                {ICONS.map((icon) => (
                  <button
                    key={icon}
                    type="button"  // 🔍 [语法] 不触发表单提交
                    onClick={() => setForm({ ...form, icon })}
                    className={`text-2xl p-2 rounded-lg transition-all ${form.icon === icon ? 'bg-primary-100 ring-2 ring-primary-400 scale-110' : 'hover:bg-gray-100'}`}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>

            {/* 颜色选择器 */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">主题色</label>
              <div className="flex gap-2">
                {COLORS.map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => setForm({ ...form, color })}
                    className={`w-8 h-8 rounded-full transition-all ${form.color === color ? 'ring-2 ring-offset-2 ring-gray-400 scale-110' : ''}`}
                    style={{ backgroundColor: color }}  // 🔍 [语法] 内联样式
                  />
                ))}
              </div>
            </div>

            {/* 描述 */}
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">描述（选填）</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="简单描述这个科目，比如学习目标、计划时长..."
                rows={2}
                className="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-200 focus:border-primary-400 outline-none transition-all resize-none"
              />
            </div>

            <button type="submit" className="w-full bg-primary-600 text-white py-2.5 rounded-xl font-medium hover:bg-primary-700 transition-colors">
              {editingId ? '💾 保存修改' : '✨ 创建科目，开始变现之旅'}
            </button>
          </div>
        </form>
      )}

      {/* ========== 科目列表 ========== */}
      {subjects.length === 0 && !showForm ? (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">📭</div>
          <p className="text-gray-400">还没有科目，点击上方按钮创建吧</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {visibleSubjects.map((subject) => (
            // 🔍 [语法] 左边框用主题色
            <div
              key={subject.id}
              className="bg-white rounded-2xl p-5 border border-gray-100 hover:shadow-md transition-all group"
              style={{ borderLeftColor: subject.color, borderLeftWidth: '4px' }}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <span className="text-3xl">{subject.icon}</span>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-800 truncate">{subject.displayName}</h3>
                    <p className="text-xs text-gray-400 mt-0.5">{subject.note_count || 0}篇笔记</p>
                    <p className="text-xs text-gray-400 mt-1">创建时间：{formatDateTime(subject.created_at)}</p>
                  </div>
                </div>
              </div>

              {subject.description && <p className="text-sm text-gray-500 mt-2 line-clamp-2">{subject.description}</p>}

              {/* 操作按钮 */}
              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-50">
                <button onClick={() => navigate(`/subjects/${subject.id}/notes`)} className="flex-1 text-center py-2 rounded-lg bg-primary-50 text-primary-700 text-sm font-medium hover:bg-primary-100 transition-colors">
                  📝 查看笔记
                </button>
                <button onClick={() => startEdit(subject)} className="px-3 py-2 rounded-lg text-gray-500 hover:bg-gray-100 text-sm transition-colors">
                  ✏️
                </button>
                {/* 🔍 [语法] 双击确认 */}
                <button
                  onClick={() => handleDelete(subject.id)}
                  className={`px-3 py-2 rounded-lg transition-colors text-sm ${deletingId === subject.id ? 'bg-red-50 text-red-600 font-medium' : 'text-gray-500 hover:bg-gray-100'}`}
                >
                  {deletingId === subject.id ? '确认？' : '🗑️'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
