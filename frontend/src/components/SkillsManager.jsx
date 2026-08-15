import { useEffect, useRef, useState } from 'react'
import { Files, PackagePlus, Search, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '../utils/api'

export default function SkillsManager() {
  const [skills, setSkills] = useState([])
  const [query, setQuery] = useState('')
  const [uploading, setUploading] = useState(false)
  const [batchSummary, setBatchSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [hasMore, setHasMore] = useState(false)
  const batchInput = useRef(null)
  const requestId = useRef(0)
  const pageSize = 30
  const load = async (value = '', offset = 0, append = false) => {
    const currentRequest = ++requestId.current
    setLoading(true)
    try {
      const rows = await api.skills.list({ ...(value ? { q: value } : {}), limit: pageSize, offset })
      if (currentRequest !== requestId.current) return
      setSkills((previous) => append ? [...previous, ...rows] : rows)
      setHasMore(rows.length === pageSize)
    } catch (error) {
      if (currentRequest === requestId.current) toast.error(error.message)
    } finally {
      if (currentRequest === requestId.current) setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => load(query.trim()), query ? 200 : 0)
    return () => clearTimeout(timer)
  }, [query])

  const batchUpload = async (files) => {
    if (!files?.length) return
    setUploading(true)
    try {
      const result = await api.skills.batchUpload(files)
      const installed = result.installed || 0
      const duplicates = result.duplicates || []
      const duplicateArchives = (result.per_archive || []).filter((row) => row.duplicates?.length > 0).length
      setBatchSummary({ ...result, installed, duplicates, duplicateArchives })
      if (result.success) {
        toast.success(`处理 ${result.received} 个压缩包：安装 ${installed} 个 Skill，跳过 ${duplicates.length} 个重复 Skill`)
      } else {
        toast.error(result.failures?.[0]?.error || '部分 Skill 压缩包安装失败，请查看明细')
      }
      await load(query)
    } catch (error) {
      toast.error(error.message)
    } finally {
      setUploading(false)
      if (batchInput.current) batchInput.current.value = ''
    }
  }

  const toggle = async (skill) => { await api.skills.update(skill.id, { enabled: !skill.enabled }); await load(query) }
  const remove = async (skill) => {
    if (!confirm(`删除 Skill“${skill.name}”？`)) return
    await api.skills.delete(skill.id)
    await load(query)
  }

  return <div className="p-6 max-w-5xl mx-auto">
    <div className="flex items-center justify-between gap-4 mb-6 flex-wrap">
      <div className="flex-1 min-w-[240px]"><h1 className="text-2xl font-bold text-gray-800">Skills 仓库</h1><p className="text-sm text-gray-500 mt-1">批量安装支持单个汇总 ZIP，或同时选择多个 Skill ZIP。系统只读取 SKILL.md，不执行包内脚本。</p></div>
      <button className="primary-command" disabled={uploading} onClick={() => batchInput.current?.click()} title="选择一个汇总 ZIP，或同时选择多个 Skill ZIP"><Files size={17} />{uploading ? '安装中...' : '批量安装'}</button>
      <input ref={batchInput} hidden type="file" accept=".zip" multiple onChange={(event) => batchUpload(event.target.files)} />
    </div>

    {batchSummary && <div className="mb-4 bg-white border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between gap-4 mb-2"><div className="text-sm font-medium text-gray-700">本次处理 {batchSummary.received} 个压缩包，安装 {batchSummary.installed} 个 Skill；跳过 {batchSummary.duplicates.length} 个重复 Skill（来自 {batchSummary.duplicateArchives} 个压缩包）</div><button onClick={() => setBatchSummary(null)} className="text-xs text-gray-400 hover:text-gray-600">关闭</button></div>
      {batchSummary.per_archive?.length > 0 && <ul className="text-xs space-y-1 max-h-40 overflow-auto">{batchSummary.per_archive.map((row) => <li key={row.archive} className={row.error ? 'text-red-600' : 'text-emerald-700'}><span className="font-mono">{row.archive}</span><span> - {row.error || `安装 ${row.installed} 个 Skill${row.duplicates?.length ? `，跳过 ${row.duplicates.length} 个重复 Skill：${row.duplicates.join('、')}` : ''}`}</span></li>)}</ul>}
      {batchSummary.invalid_filenames?.length > 0 && <p className="text-xs text-amber-600 mt-2">已忽略非 ZIP 文件：{batchSummary.invalid_filenames.join('、')}</p>}
    </div>}

    <div className="relative mb-4"><Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="按名称、摘要或功能搜索 Skill" className="w-full pl-9 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm outline-none focus:ring-2 focus:ring-primary-200" /></div>
    {skills.length === 0 ? <div className="empty-band"><PackagePlus size={32} /><span>{loading ? '加载 Skill 中…' : query ? '没有匹配的 Skill' : '尚未安装 Skill'}</span></div> : <div className="bg-white border border-gray-200 divide-y divide-gray-100">{skills.map((skill) => <div className="p-4 flex items-center gap-4" key={skill.id}>
      <button title={skill.enabled ? '点击停用' : '点击启用'} onClick={() => toggle(skill)} className={`w-10 h-6 rounded-full p-1 transition-colors ${skill.enabled ? 'bg-emerald-600' : 'bg-gray-300'}`}><span className={`block w-4 h-4 rounded-full bg-white transition-transform ${skill.enabled ? 'translate-x-4' : ''}`} /></button>
      <div className="flex-1 min-w-0"><div className="flex items-center gap-2"><strong className="text-sm text-gray-800 truncate block">{skill.name}</strong>{(skill.product_type_ids || []).map((id) => <span key={id} title={`适合知识产品 ${id}`} className="text-[10px] min-w-5 h-5 px-1 inline-flex items-center justify-center bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">{id}</span>)}</div><p className="text-xs text-gray-500 truncate mt-1">{skill.description || '自定义生成工作规范'} · {skill.instruction_chars.toLocaleString()} 字符</p></div>
      <button title="删除" className="icon-command text-red-500" onClick={() => remove(skill)}><Trash2 size={17} /></button>
    </div>)}</div>}
    {skills.length > 0 && <div className="mt-3 flex items-center justify-between"><p className="text-xs text-gray-400">已加载 {skills.length} 个 Skill{query ? '（已按搜索词过滤）' : ''}</p>{hasMore && <button type="button" disabled={loading} onClick={() => load(query.trim(), skills.length, true)} className="text-xs text-emerald-700 px-3 py-1.5 border border-emerald-200 hover:bg-emerald-50 disabled:opacity-50">{loading ? '加载中…' : '加载更多'}</button>}</div>}
  </div>
}
