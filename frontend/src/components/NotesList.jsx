// 🔍 [语法] React Hooks
import { useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
// 🔍 [语法] react-router-dom
import { useParams, useNavigate } from 'react-router-dom'
// 🔍 [语法] 全局 store
import useStore from '../store/useStore'
// 🔍 [语法] toast
import toast from 'react-hot-toast'
// 🔍 [语法] API 客户端
import { api } from '../utils/api'
import SearchSortBar, { sortResources } from './SearchSortBar'

// 🔍 [语法] 模块级常量
// 🔍 [作用] 4 阶段标签
const STAGE_LABELS = {
  stage1: { label: '筑基期', color: 'bg-blue-100 text-blue-700' },
  stage2: { label: '专精期', color: 'bg-indigo-100 text-indigo-700' },
  stage3: { label: '融合期', color: 'bg-purple-100 text-purple-700' },
  stage4: { label: '创业期', color: 'bg-emerald-100 text-emerald-700' },
}

// 🔍 [语法] default export
// 🔍 [作用] 笔记列表 + 批量生成
export default function NotesList() {
  // 🔍 [语法] useParams 解构
  // 🔍 [作用] 取 URL 参数
  const { subjectId } = useParams()
  const navigate = useNavigate()
  // 🔍 [作用] 2026-08 fix/26：enqueueTask 让批量后台任务写入全局 store，「生成任务」页能立即看到
  const { subjects, fetchSubjects, enqueueTask, deleteNote } = useStore()
  // 🔍 [语法] find
  // 🔍 [作用] 找当前科目
  const subject = subjects.find((s) => s.id === Number(subjectId))

  // 🔍 [语法] 批量模式状态
  // 🔍 [作用] Set 去重
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [batchMode, setBatchMode] = useState(false)
  const [batchGenerating, setBatchGenerating] = useState(false)
  const [batchProgress, setBatchProgress] = useState('')
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('updated')
  const [subjectNotes, setSubjectNotes] = useState([])
  const [notesLoading, setNotesLoading] = useState(true)
  const visibleNotes = sortResources(subjectNotes.filter((item) => item.title.toLowerCase().includes(query.trim().toLowerCase())), sort, (item) => item.content_length ?? (item.raw_content || item.content || '').length)

  // 🔍 [语法] useEffect 依赖 subjectId
  // 🔍 [作用] URL 变化时重新加载
  useEffect(() => {
    let cancelled = false
    setSubjectNotes([])
    setSelectedIds(new Set())
    setBatchMode(false)
    setBatchProgress('')
    setBatchGenerating(false)
    fetchSubjects()
    setNotesLoading(true)
    api.notes.list({ subject_id: subjectId, summary: true })
      .then((rows) => { if (!cancelled) setSubjectNotes(rows || []) })
      .catch((error) => {
        if (!cancelled) {
          setSubjectNotes([])
          toast.error(`加载笔记失败：${error.message}`)
        }
      })
      .finally(() => { if (!cancelled) setNotesLoading(false) })
    return () => { cancelled = true }
  }, [subjectId])

  // 🔍 [语法] 退出批量时清空选择
  useEffect(() => {
    if (!batchMode) setSelectedIds(new Set())
  }, [batchMode])

  // 🔍 [语法] 切换单条选中
  // 🔍 [作用] 阻止冒泡（不跳转笔记详情）
  const toggleSelect = (id, e) => {
    e.stopPropagation()
    // 🔍 [语法] 复制 Set
    // 🔍 [作用] 不可变更新
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // 🔍 [语法] 全选/取消全选
  const toggleSelectAll = () => {
    // 🔍 [语法] Set 对比
    // 🔍 [作用] 全部已选 → 取消；否则全选
    if (selectedIds.size === subjectNotes.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(subjectNotes.map((n) => n.id)))
    }
  }

  // 🔍 [语法] async 批量生成
  // 🔍 [作用] 为每篇笔记提交后台生成任务（不阻塞，切换页面不中断）
  const handleBatchGenerate = async () => {
    if (selectedIds.size === 0) {
      toast.error('请先选择要批量生成的笔记')
      return
    }
    setBatchGenerating(true)
    setBatchProgress(`正在提交 ${selectedIds.size} 篇笔记的后台生成任务...`)
    try {
      const typesResp = await api.ai.productTypes()
      const allTypes = Object.keys(typesResp || {})
      let count = 0
      for (const id of Array.from(selectedIds)) {
        setBatchProgress(`已提交笔记 ${id} 的后台任务...`)
        // 🔍 [语法] 后台任务：提交即返回，生成在后端线程池执行
        // 🔍 [作用] 用户可立即切换到其他页面，进度在「生成任务」页查看
        await enqueueTask({ note_id: Number(id), product_types: allTypes })
        count += 1
      }
      toast.success(`已提交 ${count} 个后台生成任务，可切换页面查看进度`)
      setBatchProgress(`✅ 已提交 ${count} 个后台任务，前往「生成任务」查看进度`)
      setBatchMode(false)
      navigate('/tasks')
    } catch (e) {
      toast.error('批量提交失败: ' + e.message)
      setBatchProgress('❌ ' + e.message)
      setBatchGenerating(false)
    }
  }

  const handleDelete = async (note) => {
    if (!confirm(`删除笔记“${note.title}”？关联产品不会自动删除。`)) return
    try {
      await deleteNote(note.id)
      setSubjectNotes((rows) => rows.filter((row) => row.id !== note.id))
      await fetchSubjects()
      toast.success('笔记已删除')
    } catch (error) {
      toast.error(`删除笔记失败：${error.message}`)
    }
  }

  // 🔍 [语法] 早返回（科目未加载）
  if (!subject || notesLoading) {
    return <div className="p-6 text-center text-gray-400 pt-20">加载中...</div>
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* ========== 头部 ========== */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/subjects')} className="text-gray-400 hover:text-gray-600">
            ← 返回
          </button>
          <span className="text-3xl">{subject.icon}</span>
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{subject.name}</h1>
            <p className="text-sm text-gray-500">{subjectNotes.length}篇笔记</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {/* 批量模式切换 */}
          {subjectNotes.length > 0 && (
            <button
              onClick={() => setBatchMode(!batchMode)}
              className={`px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                batchMode
                  ? 'bg-amber-100 text-amber-700 border border-amber-300'
                  : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'
              }`}
            >
              {batchMode ? '✕ 退出批量' : '☐ 批量生成'}
            </button>
          )}
          {/* 新建笔记 */}
          <button
            onClick={() => navigate(`/subjects/${subjectId}/notes/new`)}
            className="bg-primary-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-primary-700 transition-colors shadow-lg shadow-primary-200 flex items-center gap-2"
          >
            <span>+</span> 新建笔记
          </button>
        </div>
      </div>
      <SearchSortBar query={query} onQuery={setQuery} sort={sort} onSort={setSort} noun="笔记" />

      {/* ========== 批量操作栏 ========== */}
      {batchMode && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-4 flex items-center justify-between animate-slide-up">
          <div className="flex items-center gap-3">
            <button onClick={toggleSelectAll} className="text-sm text-amber-700 hover:text-amber-900 underline">
              {selectedIds.size === subjectNotes.length ? '取消全选' : '全选'}
            </button>
            <span className="text-sm text-amber-600">已选 {selectedIds.size} / {subjectNotes.length} 篇</span>
            {batchProgress && <span className="text-xs text-gray-500">{batchProgress}</span>}
          </div>
          <button
            onClick={handleBatchGenerate}
            disabled={batchGenerating || selectedIds.size === 0}
            className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-5 py-2.5 rounded-xl font-medium hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 transition-all shadow-lg shadow-amber-200 flex items-center gap-2 text-sm"
          >
            {batchGenerating ? (
              <>
                <span className="animate-spin">⏳</span> 批量生成中...
              </>
            ) : (
              <>🚀 批量生成 ({selectedIds.size}篇)</>
            )}
          </button>
        </div>
      )}

      {/* ========== 笔记列表 ========== */}
      {subjectNotes.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📝</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">开始你的第一篇笔记</h2>
          <p className="text-gray-400 mb-6">记下学习内容，AI将自动帮你生成知识付费产品</p>
          <button
            onClick={() => navigate(`/subjects/${subjectId}/notes/new`)}
            className="bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors"
          >
            记第一篇笔记 ✍️
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {visibleNotes.map((note) => {
            const isSelected = selectedIds.has(note.id)
            return (
              // 🔍 [语法] 点击切换选中/跳转
              <div
                key={note.id}
                onClick={() => {
                  if (batchMode) {
                    toggleSelect(note.id, { stopPropagation: () => {} })
                  } else {
                    navigate(`/subjects/${subjectId}/notes/${note.id}`)
                  }
                }}
                className={`bg-white rounded-xl p-5 border transition-all group cursor-pointer ${
                  batchMode && isSelected
                    ? 'border-amber-400 bg-amber-50 shadow-md ring-1 ring-amber-300'
                    : 'border-gray-100 hover:border-primary-200 hover:shadow-md'
                }`}
              >
                <div className="flex items-start gap-3">
                  {/* 复选框（批量模式） */}
                  {batchMode && (
                    <div onClick={(e) => toggleSelect(note.id, e)} className="shrink-0 mt-0.5">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                        isSelected ? 'bg-amber-500 border-amber-500 text-white' : 'border-gray-300 hover:border-amber-400'
                      }`}>
                        {isSelected && <span className="text-xs">✓</span>}
                      </div>
                    </div>
                  )}

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold text-gray-800 truncate">{note.title}</h3>
                      <span className={`text-[10px] px-1.5 py-0.3 rounded-full shrink-0 ${STAGE_LABELS[note.learning_stage]?.color || 'bg-gray-100 text-gray-500'}`}>
                        {STAGE_LABELS[note.learning_stage]?.label || note.learning_stage}
                      </span>
                    </div>
                    {/* 🔍 [语法] substring(0, 120) */}
                    {/* 🔍 [作用] 摘要 120 字 */}
                    <p className="text-sm text-gray-500 line-clamp-2 mb-2">{(note.raw_content || note.content || '').substring(0, 120)}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-400">
                      <span>⏱ {note.estimated_minutes}分钟</span>
                      <span>💎 {note.product_count || 0}个产品</span>
                      {note.tags?.length > 0 && (
                        <div className="flex gap-1">
                          {note.tags.slice(0, 3).map((tag, i) => (
                            <span key={i} className="bg-gray-100 px-1.5 py-0.5 rounded text-[10px]">{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* 单笔记快捷生成 */}
                  {!batchMode && (
                    <div className="flex items-center gap-1.5 ml-3 shrink-0" onClick={(e) => e.stopPropagation()}>
                      {note.product_count > 0 ? (
                        <span className="text-xs text-amber-500 font-medium">已产出</span>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/notes/${note.id}/generate`)
                          }}
                          className="text-xs bg-amber-50 text-amber-600 px-2.5 py-1 rounded-lg hover:bg-amber-100 transition-colors shrink-0"
                        >
                          ✨ 生成产品
                        </button>
                      )}
                      <button title="删除笔记" className="icon-command text-red-500" onClick={() => handleDelete(note)}><Trash2 size={16} /></button>
                      <span className="text-gray-300 group-hover:text-primary-500 transition-colors">→</span>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 批量生成说明 */}
      {batchMode && (
        <div className="mt-6 bg-blue-50 border border-blue-200 rounded-2xl p-5 animate-fade-in">
          <h3 className="font-semibold text-blue-800 mb-2">📦 批量生成说明</h3>
          <ul className="text-sm text-blue-700 space-y-1">
            <li>• 采用<strong>分块生成算法</strong>，每个产品拆分为多个逻辑块独立生成</li>
            <li>• 每篇笔记产出存入<strong>独立文件夹</strong>（output/note_X_标题/）</li>
            <li>• 多篇笔记<strong>串行处理</strong>，避免打爆 LLM 服务</li>
            <li>• ⚠️ 需要先配置 LLM API（前往左侧「LLM 设置」）</li>
          </ul>
        </div>
      )}
    </div>
  )
}
