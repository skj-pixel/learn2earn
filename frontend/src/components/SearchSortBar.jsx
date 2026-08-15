import { ArrowDownAZ, Search } from 'lucide-react'

export function sortResources(rows, sort, getSize) {
  return [...rows].sort((a, b) => {
    if (sort === 'name') return (a.name || a.title || '').localeCompare(b.name || b.title || '', 'zh-CN')
    if (sort === 'size') return getSize(b) - getSize(a)
    return new Date(b.updated_at || b.created_at || 0) - new Date(a.updated_at || a.created_at || 0)
  })
}

export default function SearchSortBar({ query, onQuery, sort, onSort, noun }) {
  return <div className="resource-controls">
    <label className="resource-search"><Search size={16} /><input value={query} onChange={(e) => onQuery(e.target.value)} placeholder={`按名称搜索${noun}`} /></label>
    <label className="resource-sort"><ArrowDownAZ size={16} /><span>排序</span><select value={sort} onChange={(e) => onSort(e.target.value)}><option value="updated">最后修改时间</option><option value="name">名称</option><option value="size">大小</option></select></label>
  </div>
}
