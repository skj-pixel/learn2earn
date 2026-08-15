import { useEffect, useState } from 'react'
import { ArrowDownUp, CheckCircle2, Clock3, Loader2, RefreshCw, RotateCcw, Search, Trash2, XCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import useStore from '../store/useStore'
import { formatDateTime } from '../utils/dateTime'
import { taskProductsUrl } from '../utils/productTrace'

const statusMeta = {
  queued: [Clock3, '排队中', 'text-amber-600 bg-amber-50'],
  running: [Loader2, '生成中', 'text-blue-600 bg-blue-50'],
  completed: [CheckCircle2, '已完成', 'text-emerald-600 bg-emerald-50'],
  failed: [XCircle, '失败', 'text-red-600 bg-red-50'],
}

export default function GenerationTasks() {
  const { tasks: storeTasks, fetchTasks, refreshTask, deleteTask, retryTask } = useStore()
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('created_at')
  const [order, setOrder] = useState('desc')
  const navigate = useNavigate()
  const load = () => fetchTasks().finally(() => setLoading(false))

  useEffect(() => {
    load()
    const timer = setInterval(() => {
      const running = (useStore.getState().tasks || []).filter((task) => ['queued', 'running'].includes(task.status))
      if (running.length === 0) load()
      else Promise.all(running.map((task) => refreshTask(task.id))).then(() => setLoading(false))
    }, 2500)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const removeTask = async (task) => {
    if (!confirm(`删除任务 #${task.id}？已生成的产品不会被删除。`)) return
    try {
      await deleteTask(task.id)
      toast.success('任务已删除')
    } catch (error) {
      toast.error(`删除失败：${error.message}`)
    }
  }

  const rerunTask = async (task) => {
    try {
      const next = await retryTask(task.id)
      toast.success(`已创建重新生成任务 #${next.id}`)
    } catch (error) {
      toast.error(`重新生成失败：${error.message}`)
    }
  }

  const sorted = [...(storeTasks || [])]
  if (sort === 'name') sorted.sort((a, b) => (a.product_types || []).join('、').localeCompare((b.product_types || []).join('、')))
  else sorted.sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
  if (order === 'asc') sorted.reverse()
  const needle = query.trim().toLowerCase()
  const tasks = needle ? sorted.filter((task) => [
    ...(task.product_types || []), task.status, task.subject_name, task.note_title,
  ].some((value) => String(value || '').toLowerCase().includes(needle))) : sorted

  return <div className="p-6 max-w-5xl mx-auto">
    <div className="flex items-center justify-between mb-6">
      <div><h1 className="text-2xl font-bold text-gray-800">生成任务</h1><p className="text-sm text-gray-500 mt-1">任务会在后台继续执行。</p></div>
      <button title="刷新" className="icon-command" onClick={load}><RefreshCw size={18} /></button>
    </div>
    <div className="flex flex-wrap items-center gap-3 mb-4">
      <div className="relative flex-1 min-w-[200px]"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="按科目、笔记、产品类型或状态搜索" className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-primary-200" /></div>
      <select value={sort} onChange={(event) => setSort(event.target.value)} className="border border-gray-200 rounded-xl text-sm px-3 py-2"><option value="created_at">按时间</option><option value="name">按产品类型</option></select>
      <button onClick={() => setOrder(order === 'desc' ? 'asc' : 'desc')} className="flex items-center gap-1.5 border border-gray-200 rounded-xl text-sm px-3 py-2 text-gray-600" title="切换升序或降序"><ArrowDownUp size={15} />{order === 'desc' ? '降序' : '升序'}</button>
    </div>
    {loading && tasks.length === 0 ? <p className="text-gray-400">正在读取任务...</p> : tasks.length === 0 ? <div className="empty-band">{query ? '没有匹配的任务' : '还没有生成任务'}</div> : <div className="bg-white border border-gray-200 divide-y divide-gray-100">
      {tasks.map((task) => {
        const [Icon, label, tone] = statusMeta[task.status] || statusMeta.queued
        const productCount = task.result?.products?.length || 0
        return <div key={task.id} className="p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2"><span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium ${tone}`}><Icon size={14} className={task.status === 'running' ? 'animate-spin' : ''} />{label}</span><strong className="text-sm text-gray-800">任务 #{task.id}</strong></div>
              <p className="mt-2 text-sm text-gray-600">{task.current_step}</p>
              <p className="mt-1 text-xs text-gray-500">科目：{task.subject_name || '未知科目'}{task.note_title ? ` · 笔记：${task.note_title}` : ''}</p>
              <p className="mt-1 text-xs text-gray-400">产品类型：{(task.product_types || []).join('、')}</p>
              {task.started_at && <p className="mt-1 text-xs text-gray-400">开始：{formatDateTime(task.started_at)}</p>}
              {task.completed_at && <p className="mt-1 text-xs text-gray-400">完成：{formatDateTime(task.completed_at)}</p>}
              {task.error && <p className="mt-2 text-xs text-red-600">{task.error}</p>}
            </div>
            <div className="flex items-center gap-2">
              {task.status === 'completed' && <button className="secondary-command" onClick={() => navigate(taskProductsUrl(task.id))}>查看对应产品{productCount ? `（${productCount}）` : ''}</button>}
              {['completed', 'failed'].includes(task.status) && <button title="使用相同配置重新生成" className="icon-command" onClick={() => rerunTask(task)}><RotateCcw size={17} /></button>}
              {['completed', 'failed'].includes(task.status) && <button title="删除任务" className="icon-command text-red-500" onClick={() => removeTask(task)}><Trash2 size={17} /></button>}
            </div>
          </div>
          <div className="mt-4 h-2 bg-gray-100 rounded overflow-hidden"><div className="h-full bg-emerald-600 transition-all" style={{ width: `${task.progress}%` }} /></div>
        </div>
      })}
    </div>}
    {tasks.length > 0 && <p className="text-xs text-gray-400 mt-3">共 {tasks.length} 个任务</p>}
  </div>
}
