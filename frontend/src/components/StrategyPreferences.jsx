// 🔍 [语法] React Hooks
import { useEffect, useMemo, useState } from 'react'
// 🔍 [语法] toast
import toast from 'react-hot-toast'
import { api } from '../utils/api'
import { TYPE_META } from '../utils/typeMeta'
import { implementedStrategies, strategySummary } from '../utils/generationStrategies'

// 🔍 [语法] default export
// 🔍 [作用] 用户自定义每种产品类型的生成策略（algorithms / techniques / skill_keywords）
export default function StrategyPreferences() {
  const [items, setItems] = useState([])
  const [strategies, setStrategies] = useState({ algorithms: [], techniques: [], defaults: {} })
  const [loading, setLoading] = useState(true)
  const [savingType, setSavingType] = useState(null)
  // 🔍 [语法] 受控状态：当前正在编辑的产品类型（默认第一个未自定义的，便于用户从空白卡入手）
  const [activeType, setActiveType] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const prefs = await api.strategyPreferences.list()
      setItems(prefs.product_types || [])
      setLoading(false)
      api.tasks.strategies()
        .then(setStrategies)
        .catch((error) => toast.error('生成策略元数据加载失败: ' + error.message))
    } catch (e) {
      toast.error('加载失败: ' + e.message)
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // 🔍 [语法] 默认选中首个产品类型作为「新增策略偏好」的入口
  useEffect(() => {
    if (items.length && !activeType) setActiveType(items[0].id)
  }, [items, activeType])

  const availableStrategies = implementedStrategies(strategies)
  const algoList = availableStrategies.algorithms || []
  const techList = availableStrategies.techniques || []

  const updateItem = (productType, field, value) => {
    setItems((prev) => prev.map((item) => (
      item.id === productType ? { ...item, override: { ...(item.override || {}), [field]: value } } : item
    )))
  }

  const save = async (productType) => {
    const item = items.find((x) => x.id === productType)
    if (!item) return
    setSavingType(productType)
    try {
      await api.strategyPreferences.update(productType, item.override || {})
      toast.success(`${item.name} 策略已保存`)
    } catch (e) {
      toast.error('保存失败: ' + e.message)
    } finally {
      setSavingType(null)
    }
  }

  const reset = async (productType) => {
    setSavingType(productType)
    try {
      const result = await api.strategyPreferences.reset(productType)
      setItems((prev) => prev.map((item) => (
        item.id === productType ? { ...item, override: result.override } : item
      )))
      toast.success('已恢复默认策略')
    } catch (e) {
      toast.error('重置失败: ' + e.message)
    } finally {
      setSavingType(null)
    }
  }

  const isOverridden = (item) => {
    const o = item.override || {}
    return (o.algorithms && o.algorithms.length > 0) || (o.techniques && o.techniques.length > 0) || (o.skill_keywords && o.skill_keywords.length > 0)
  }

  const overrideCount = useMemo(() => items.filter(isOverridden).length, [items])

  if (loading) {
    return <div className="p-6 text-center text-gray-400 pt-20">加载策略偏好…</div>
  }

  const activeItem = items.find((x) => x.id === activeType)

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">🎛️ 产品策略偏好</h1>
          <p className="text-gray-500 mt-1 text-sm">
            按产品类型自定义生成算法与质量技术组合；留空表示沿用默认偏好。已有 <b>{overrideCount}</b> / {items.length} 项覆盖。
          </p>
        </div>
      </div>

      {/* 🔍 [语法] 产品类型快速切换 tab：作为"新增策略偏好"的左侧目录 */}
      <div className="flex flex-wrap gap-1.5 mb-4 bg-white border border-gray-200 rounded-2xl p-2">
        {items.map((item) => {
          const meta = TYPE_META[item.id] || {}
          const overridden = isOverridden(item)
          const isActive = activeType === item.id
          return (
            <button
              key={item.id}
              onClick={() => setActiveType(item.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${isActive ? 'bg-emerald-600 text-white shadow' : overridden ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100' : 'bg-gray-50 text-gray-600 hover:bg-gray-100'}`}
            >
              <span>{meta.icon || '📦'}</span>
              <span>{item.name}</span>
              {overridden && !isActive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
            </button>
          )
        })}
      </div>

      {/* 🔍 [语法] 单卡片视图：聚焦当前激活产品类型（"新增/编辑" 入口主视图） */}
      {activeItem && (
        <StrategyCard
          item={activeItem}
          strategies={strategies}
          algoList={algoList}
          techList={techList}
          onUpdate={updateItem}
          onSave={save}
          onReset={reset}
          saving={savingType === activeItem.id}
          isOverridden={isOverridden(activeItem)}
        />
      )}

      {/* 🔍 [语法] 其他产品类型摘要列表（只读 + 快速跳转） */}
      <div className="mt-8">
        <h2 className="text-sm font-semibold text-gray-500 mb-2">📋 全部产品类型策略概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {items.map((item) => {
            const meta = TYPE_META[item.id] || {}
            const overridden = isOverridden(item)
            const override = item.override || {}
            return (
              <div
                key={item.id}
                onClick={() => setActiveType(item.id)}
                className={`cursor-pointer bg-white border ${overridden ? 'border-emerald-300' : 'border-gray-200'} rounded-xl p-3 hover:shadow-md transition-all`}
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span>{meta.icon || '📦'}</span>
                  <span className="text-sm font-medium text-gray-800 truncate">{item.name}</span>
                  {overridden && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">已自定义</span>}
                </div>
                <p className={`text-xs ${overridden ? 'text-emerald-700' : 'text-gray-400'}`}>
                  {strategySummary(override)}
                </p>
              </div>
            )
          })}
        </div>
      </div>

      <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800">
        💡 偏好仅对「用户未手动勾选」的策略生效；任务提交时如果显式传了 algorithms / techniques，则完全以显式值为准。详细说明见 docs/生成算法与质量把控详解.md。
      </div>
    </div>
  )
}

// 🔍 [语法] 子组件：单产品类型策略编辑卡
function StrategyCard({ item, strategies, algoList, techList, onUpdate, onSave, onReset, saving, isOverridden }) {
  const meta = TYPE_META[item.id] || {}
  const override = item.override || { algorithms: [], techniques: [], skill_keywords: [] }
  const defaults = strategies.defaults?.[item.id] || {}

  return (
    <div id={`strategy-card-${item.id}`} className={`bg-white border ${isOverridden ? 'border-emerald-300 ring-1 ring-emerald-100' : 'border-gray-200'} rounded-2xl p-5 transition-shadow`}>
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{meta.icon || '📦'}</span>
            <h2 className="font-semibold text-gray-800">{item.name || item.id}</h2>
            <span className="text-xs text-gray-400 font-mono">{item.id}</span>
            {isOverridden && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">已自定义</span>}
          </div>
          <p className="text-xs text-gray-400">
            默认算法：{(defaults.algorithms || []).join('、') || '(无)'}<br />
            默认质量技术：{(defaults.techniques || []).join('、') || '(无)'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isOverridden && <button onClick={() => onReset(item.id)} disabled={saving} className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border border-gray-200 rounded-lg">重置</button>}
          <button onClick={() => onSave(item.id)} disabled={saving} className="text-xs bg-emerald-600 text-white px-3 py-1.5 rounded-lg hover:bg-emerald-700 disabled:opacity-50">
            {saving ? '保存中…' : '保存'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-3">
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-2">生成算法</div>
          <div className="flex flex-wrap gap-1.5">
            {algoList.map((algo) => {
              const on = (override.algorithms || []).includes(algo.id)
              return (
                <button
                  key={algo.id}
                  onClick={() => onUpdate(item.id, 'algorithms', on ? (override.algorithms || []).filter((x) => x !== algo.id) : [...(override.algorithms || []), algo.id])}
                  className={`px-2 py-1 rounded text-xs border transition-colors ${on ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'}`}
                  title={algo.description}
                >
                  {algo.name}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-500 mb-2">质量技术</div>
          <div className="flex flex-wrap gap-1.5">
            {techList.map((tech) => {
              const on = (override.techniques || []).includes(tech.id)
              return (
                <button
                  key={tech.id}
                  onClick={() => onUpdate(item.id, 'techniques', on ? (override.techniques || []).filter((x) => x !== tech.id) : [...(override.techniques || []), tech.id])}
                  className={`px-2 py-1 rounded text-xs border transition-colors ${on ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200 hover:border-emerald-300'}`}
                  title={tech.description}
                >
                  {tech.name}
                </button>
              )
            })}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-500 mb-2">推荐 Skill</div>
          <SkillPicker
            value={override.skill_keywords || []}
            onChange={(next) => onUpdate(item.id, 'skill_keywords', next)}
          />
        </div>
      </div>
    </div>
  )
}

// 🔍 [语法] 子组件
// 🔍 [作用] 用关键词过滤已安装 Skill，点击结果后保存 Skill 名称。
function SkillPicker({ value, onChange }) {
  const [expanded, setExpanded] = useState(false)
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState([])
  const [loadingSkills, setLoadingSkills] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const pageSize = 20

  const loadSkills = async (offset = 0, append = false) => {
    setLoadingSkills(true)
    try {
      const rows = await api.skills.list({ q: query.trim(), limit: pageSize, offset })
      setMatches((previous) => append ? [...previous, ...rows] : rows)
      setHasMore(rows.length === pageSize)
    } catch (error) {
      toast.error('Skill 加载失败: ' + error.message)
    } finally {
      setLoadingSkills(false)
    }
  }

  useEffect(() => {
    if (!expanded) return undefined
    const timer = setTimeout(() => loadSkills(0, false), 250)
    return () => clearTimeout(timer)
  }, [query, expanded])

  const addSkill = (name) => {
    if (!value.includes(name)) onChange([...value, name])
    setQuery('')
  }

  return (
    <div className="border border-gray-200 rounded-lg p-2 bg-gray-50">
      <div className="flex flex-wrap gap-1 mb-2">
        {value.map((kw) => (
          <span key={kw} className="inline-flex items-center gap-1 bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-xs">
            {kw}
            <button type="button" onClick={() => onChange(value.filter((x) => x !== kw))} className="text-indigo-500 hover:text-indigo-700">×</button>
          </span>
        ))}
        {value.length === 0 && <span className="text-xs text-gray-400">(空)</span>}
      </div>
      <button type="button" onClick={() => setExpanded((current) => !current)} className="w-full text-left text-xs text-emerald-700 hover:text-emerald-800">
        {expanded ? '收起 Skill 选择器' : '选择或搜索 Skill'}
      </button>
      {expanded && <><input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="输入关键词搜索已安装 Skill"
        className="w-full text-xs px-2 py-1 border border-gray-200 rounded outline-none focus:ring-1 focus:ring-emerald-300"
      />
      <div className="mt-2 border border-gray-200 rounded bg-white divide-y divide-gray-100 max-h-48 overflow-auto">
          {matches.length > 0 ? matches.map((skill) => (
            <button
              key={skill.id}
              type="button"
              onClick={() => addSkill(skill.name)}
              className="w-full text-left px-2 py-1.5 hover:bg-emerald-50"
            >
              <span className="flex items-center gap-1 text-xs font-medium text-gray-700">{skill.name}<ProductNumberTags ids={skill.product_type_ids} /></span>
              <span className="block text-[10px] text-gray-400 truncate">{skill.description || skill.category}</span>
            </button>
          )) : <p className="px-2 py-2 text-xs text-gray-400">{loadingSkills ? '加载 Skill 中...' : '没有匹配的已安装 Skill'}</p>}
          {hasMore && <button type="button" disabled={loadingSkills} onClick={() => loadSkills(matches.length, true)} className="w-full px-2 py-2 text-xs text-emerald-700 hover:bg-emerald-50 disabled:opacity-50">{loadingSkills ? '加载中...' : '加载更多'}</button>}
        </div>
      </>}
    </div>
  )
}

function ProductNumberTags({ ids = [] }) {
  return <>{ids.map((id) => <span key={id} title={`适合知识产品 ${id}`} className="text-[10px] min-w-5 h-5 px-1 inline-flex items-center justify-center bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">{id}</span>)}</>
}
