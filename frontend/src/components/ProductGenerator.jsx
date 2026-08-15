// 🔍 [语法] React Hooks
import { useEffect, useState } from 'react'
// 🔍 [语法] react-router-dom
import { useParams, useNavigate } from 'react-router-dom'
// 🔍 [语法] react-markdown
// 🔍 [作用] 渲染 Markdown（规划展示用）
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
// 🔍 [语法] 全局 store
import useStore from '../store/useStore'
// 🔍 [语法] API
import { api } from '../utils/api'
// 🔍 [语法] toast
import toast from 'react-hot-toast'

import { resolveType, useTypeMap, TYPE_META } from '../utils/typeMeta'
import { implementedStrategies, productPreference, selectedConflicts } from '../utils/generationStrategies'

// 🔍 [语法] 常量
// 🔍 [作用] 当前全部 14 种产品形态 key 列表（需求：全部展示供选择生成）
const ALL_PRODUCT_TYPES = Object.keys(TYPE_META)

// 🔍 [语法] default export
// 🔍 [作用] 产品生成中心（3 模式）
export default function ProductGenerator() {
  const { noteId } = useParams()
  const navigate = useNavigate()
  // 🔍 [语法] 解构
  const { fetchProducts, loading, enqueueTask } = useStore()

  // 🔍 [语法] 8 个状态
  // 🔍 [作用] 数据 + 模式切换 + 进度
  const [suggestions, setSuggestions] = useState([])
  const [noteProducts, setNoteProducts] = useState([])
  const [loadingSuggestions, setLoadingSuggestions] = useState(true)
  const [generating, setGenerating] = useState(false)
  // 🔍 [语法] 规划相关
  const [plan, setPlan] = useState(null)
  const [planning, setPlanning] = useState(false)
  const [selectedForGen, setSelectedForGen] = useState(new Set())
  const [showPlanRaw, setShowPlanRaw] = useState(false)
  const [agentReport, setAgentReport] = useState(null)
  const [skills, setSkills] = useState([])
  const [strategies, setStrategies] = useState({ algorithms: [], techniques: [], defaults: {} })
  const typeMap = useTypeMap()
  const [selectedSkills, setSelectedSkills] = useState(new Set())
  const [skillQuery, setSkillQuery] = useState('')
  const [selectedAlgorithms, setSelectedAlgorithms] = useState(new Set(['hierarchical_planning', 'iterative_refinement']))
  const [selectedTechniques, setSelectedTechniques] = useState(new Set(['source_grounding', 'quality_scoring', 'hallucination_check', 'memorybear']))
  // 🔍 [语法] Set 状态
  // 🔍 [作用] 当前 14 种形态中用户勾选的类型（需求：全部展示供选择生成）
  const [selectedAllTypes, setSelectedAllTypes] = useState(new Set())
  // 🔍 [作用] 2026-08 feat/29：每产品类型独立 strategy 覆盖；空对象表示沿用顶部默认
  // 结构：{ [product_type]: { skill_ids: number[], algorithms: string[], techniques: string[] } }
  const [perProductStrategies, setPerProductStrategies] = useState({})
  // 🔍 [作用] 当前正在编辑 per-product strategy 的产品类型（弹窗）
  const [editingProductType, setEditingProductType] = useState(null)
  const [commonPrompt, setCommonPrompt] = useState('')
  const [productPrompts, setProductPrompts] = useState({})

  // 🔍 [语法] 依赖 [noteId]
  // 🔍 [作用] URL 变化时重新加载
  useEffect(() => { loadData() }, [noteId])

  // 🔍 [语法] async 加载数据
  const loadData = async () => {
    setLoadingSuggestions(true)
    try {
      // 🔍 [语法] Promise.all 并行
      const [sugResult, productResult, skillResult, strategyResult] = await Promise.allSettled([
        api.ai.suggest(Number(noteId)),
        fetchProducts({ note_id: noteId }),
        api.skills.list(), api.tasks.strategies(),
      ])
      if (sugResult.status === 'fulfilled') setSuggestions(sugResult.value.suggestions || [])
      if (productResult.status === 'fulfilled') setNoteProducts(productResult.value || [])
      if (skillResult.status === 'fulfilled') setSkills((skillResult.value || []).filter((item) => item.enabled))
      if (strategyResult.status === 'fulfilled') setStrategies(implementedStrategies(strategyResult.value))
      const failures = [sugResult, productResult, skillResult, strategyResult].filter((item) => item.status === 'rejected')
      if (failures.length) toast.error(`部分数据暂时繁忙，已保留现有内容（${failures.length} 项稍后重试）`)
    } catch (e) {
      toast.error('加载失败: ' + e.message)
    } finally {
      setLoadingSuggestions(false)
    }
  }

  // 🔍 [语法] 异步生成规划
  // 🔍 [作用] 调用 /api/ai/plan
  const handlePlan = async () => {
    setPlanning(true)
    setPlan(null)
    try {
      const result = await api.ai.plan(Number(noteId), false)
      setPlan(result)
      setAgentReport({ mode: 'plan', products: [], plan: result, generated: 0 })
      // 🔍 [语法] 默认全选
      const types = result.plan_json?.product_items?.map((p) => p.type) || []
      setSelectedForGen(new Set(types))
      toast.success(`架构规划完成！推荐 ${result.product_count} 个产品`)
    } catch (e) {
      toast.error('规划失败: ' + e.message)
    } finally {
      setPlanning(false)
    }
  }

  // 🔍 [语法] 自动规划+生成
  const handleAutoPlanAndGenerate = async () => {
    setPlanning(true)
    setPlan(null)
    try {
      const result = await api.ai.plan(Number(noteId), false)
      setPlan(result)
      const types = result.plan_json?.product_items?.map((item) => item.type) || []
      const task = await submitTask(types)
      toast.success(`规划完成，后台任务 #${task.id} 已开始`)
      navigate('/tasks')
    } catch (e) {
      toast.error('规划失败: ' + e.message)
    } finally {
      setPlanning(false)
    }
  }

  // 🔍 [语法] 极速生成
  const handleFastGenerate = async () => {
    setPlanning(true)
    setPlan(null)
    try {
      const task = await submitTask(suggestions.map((item) => item.type))
      toast.success(`快速后台任务 #${task.id} 已开始`)
      navigate('/tasks')
    } catch (e) {
      toast.error('极速生成失败: ' + e.message)
    } finally {
      setPlanning(false)
    }
  }

  // 🔍 [语法] 切换规划中某产品选中
  const toggleProductInPlan = (ptype) => {
    setSelectedForGen((prev) => {
      const next = new Set(prev)
      if (next.has(ptype)) next.delete(ptype)
      else next.add(ptype)
      return next
    })
  }

  // 🔍 [语法] 全选/取消全选
  const toggleAllInPlan = () => {
    const allTypes = plan?.plan_json?.product_items?.map((p) => p.type) || []
    if (selectedForGen.size === allTypes.length) {
      setSelectedForGen(new Set())
    } else {
      setSelectedForGen(new Set(allTypes))
    }
  }

  // 🔍 [语法] 确认规划 + 生成
  const handleConfirmAndGenerate = async () => {
    if (selectedForGen.size === 0) {
      toast.error('请至少选择一个产品')
      return
    }
    try {
      const task = await submitTask(Array.from(selectedForGen))
      toast.success(`已提交后台任务 #${task.id}，切换页面不会中断`)
      navigate('/tasks')
    } catch (e) {
      toast.error('生成失败: ' + e.message)
    } finally {}
  }

  // 🔍 [语法] 单个产品快捷生成
  const handleGenerateSpecific = async (types) => {
    try {
      const task = await submitTask(types)
      toast.success(`后台任务 #${task.id} 已开始`)
      navigate('/tasks')
    } catch (e) {
      toast.error('生成失败: ' + e.message)
    } finally {}
  }

  // 🔍 [作用] 2026-08 feat/29：按 product_types 收集每个产品的 strategy
  // - task 级（顶部"生成策略"卡片）作为兜底默认
  // - perProductStrategies 中的字段覆盖默认；缺省字段自动回退到 task 级
  // 返回值：{ task 级字段, product_strategies: { ptype: { skill_ids, algorithms, techniques } } }
  const buildPayload = (types) => {
    const taskSkillIds = Array.from(selectedSkills)
    const taskAlgorithms = Array.from(selectedAlgorithms)
    const taskTechniques = Array.from(selectedTechniques)
    const product_strategies = {}
    for (const t of types) {
      const override = perProductStrategies[t]
      if (!override) continue
      // 🔍 [作用] 字段为 undefined / null / 空数组 → 回退到 task 级（不写入 product_strategies，由后端 fallback）
      const skill_ids = override.skill_ids && override.skill_ids.length ? override.skill_ids : taskSkillIds
      const algorithms = override.algorithms && override.algorithms.length ? override.algorithms : taskAlgorithms
      const techniques = override.techniques && override.techniques.length ? override.techniques : taskTechniques
      product_strategies[t] = { skill_ids, algorithms, techniques }
    }
    return {
      note_id: Number(noteId),
      product_types: types,
      skill_ids: taskSkillIds,
      algorithms: taskAlgorithms,
      techniques: taskTechniques,
      product_strategies,
      common_prompt: commonPrompt.trim(),
      product_prompts: Object.fromEntries(types
        .map((type) => [type, (productPrompts[type] || '').trim()])
        .filter(([, value]) => value)),
    }
  }

  // 🔍 [作用] 2026-08 feat/29：计算"产品当前生效的 strategy"，供 UI 展示
  // 优先用 perProductStrategies[t] 的字段；缺省回退到 task 级
  const getEffectiveStrategy = (productType) => {
    const override = perProductStrategies[productType] || {}
    return {
      skill_ids: override.skill_ids && override.skill_ids.length ? override.skill_ids : Array.from(selectedSkills),
      algorithms: override.algorithms && override.algorithms.length ? override.algorithms : Array.from(selectedAlgorithms),
      techniques: override.techniques && override.techniques.length ? override.techniques : Array.from(selectedTechniques),
      has_override: !!(override && (override.skill_ids?.length || override.algorithms?.length || override.techniques?.length)),
    }
  }

  const submitTask = (types) => {
    const payload = buildPayload(types)
    const conflicts = selectedConflicts(payload, strategies.compatibility)
    if (conflicts.length > 0) {
      const detail = conflicts.map((row) => `${row.left_name || row.left} + ${row.right_name || row.right}：${row.reason}`).join('\n')
      toast.error(`所选策略存在冲突，请重新选择：\n${detail}`)
      return Promise.reject(new Error(detail))
    }
    return enqueueTask(payload)
  }

  const toggleSet = (setter, value) => setter((previous) => { const next = new Set(previous); next.has(value) ? next.delete(value) : next.add(value); return next })

  // 🔍 [语法] 早返回
  if (loadingSuggestions) {
    return <div className="p-6 text-center text-gray-400 pt-20">加载中...</div>
  }

  // 🔍 [语法] 解构 + 计算
  const planItems = plan?.plan_json?.product_items || []
  const isAllSelected = planItems.length > 0 && selectedForGen.size === planItems.length
  // 🔍 [作用] 根据后端登记的真实实现状态即时检查当前组合；警告不阻断自由组合。
  const combinationRunnable = selectedAlgorithms.size > 0

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* ========== 头部 ========== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600">← 返回</button>
            <h1 className="text-2xl font-bold text-gray-800">💎 产品生成中心</h1>
          </div>
          <p className="text-gray-500 text-sm ml-7">从笔记生成知识付费产品</p>
        </div>
      </div>

      {/* ========== 规划卡片 ========== */}
      <div className="bg-white border border-gray-200 p-5 mb-6">
        <div className="flex items-start justify-between gap-4 mb-4"><div><h2 className="font-semibold text-gray-800">生成策略</h2><p className="text-xs text-gray-500 mt-1">可多选 Skills、算法和质量技术。未选择时使用产品类型默认策略。</p></div><span className="text-xs text-emerald-700 bg-emerald-50 px-2 py-1 rounded">后台执行</span></div>
        <label className="block mb-4">
          <span className="block text-xs font-medium text-gray-700 mb-1">公共提示词</span>
          <textarea value={commonPrompt} onChange={(event) => setCommonPrompt(event.target.value)} rows={3} maxLength={4000} placeholder="适用于本次生成的所有知识付费产品" className="w-full resize-y border border-gray-200 px-3 py-2 text-sm outline-none focus:border-primary-400 focus:ring-2 focus:ring-primary-100" />
        </label>
        <div className="mb-4 border border-blue-100 bg-blue-50 px-3 py-2 text-xs leading-5 text-blue-800">图片说明：上传的 Word 若包含图片，生成产品会尽量保留原图；底层大模型只处理文字，不会生成新图片，因此仅提供纯文字材料时，输出也会是纯文字。</div>
        <OptionGroup title="Skills" items={skills.filter((item) => {
          const q = skillQuery.trim().toLowerCase()
          if (!q) return true
          return (item.name || '').toLowerCase().includes(q) || (item.description || '').toLowerCase().includes(q) || (item.category || '').toLowerCase().includes(q)
        }).map((item) => ({ id: item.id, name: item.name, desc: item.description, productTypeIds: item.product_type_ids || [] }))} selected={selectedSkills} onToggle={(id) => toggleSet(setSelectedSkills, id)} empty={skillQuery ? '没有匹配的 Skill' : '尚未安装 Skill，可前往 Skills 仓库上传'} >
          <input value={skillQuery} onChange={(e) => setSkillQuery(e.target.value)} placeholder="按功能搜索 Skill（如 PPT、公众号、做课、电商…）" className="w-full mb-3 px-3 py-2 border border-gray-200 rounded-lg text-xs outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-400" />
        </OptionGroup>
        <OptionGroup title="算法" items={strategies.algorithms} selected={selectedAlgorithms} onToggle={(id) => toggleSet(setSelectedAlgorithms, id)} />
        <OptionGroup title="质量技术" items={strategies.techniques} selected={selectedTechniques} onToggle={(id) => toggleSet(setSelectedTechniques, id)} />
        <div className={`border px-3 py-2 text-xs ${combinationRunnable ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-700'}`}>
          <div className="font-semibold">组合检查：{combinationRunnable ? '可以运行' : '至少选择一种生成算法'}</div>
          <p className="mt-1">Skills、算法和质量技术按“知识增强 → 生成 → 质量检查”顺序组合；MemoryBear 可独立使用。</p>
        </div>
      </div>
      <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold text-gray-800 text-lg">📐 生成产品</h2>
            <p className="text-sm text-gray-400">⚡极速模式：1次调用完成 | 🚀自动：规划+生成 | 📐手动：审核后生成</p>
          </div>
          {/* ========== 3 个生成模式按钮 ========== */}
          <div className="flex items-center gap-2">
            {/* ⚡ 极速生成 */}
            <button onClick={handleFastGenerate} disabled={planning}
              className="bg-gradient-to-r from-amber-400 to-orange-500 text-white px-5 py-2.5 rounded-xl font-medium hover:from-amber-500 hover:to-orange-600 disabled:opacity-50 transition-all shadow-lg shadow-amber-200 flex items-center gap-1.5 text-sm">
              {planning ? <><span className="animate-spin">⏳</span> 生成中...</> : <>⚡ 极速生成</>}
            </button>
            {/* 🚀 自动规划+生成 */}
            <button onClick={handleAutoPlanAndGenerate} disabled={planning}
              className="bg-gradient-to-r from-emerald-500 to-teal-500 text-white px-5 py-2.5 rounded-xl font-medium hover:from-emerald-600 hover:to-teal-600 disabled:opacity-50 transition-all shadow-lg shadow-emerald-200 flex items-center gap-1.5 text-sm">
              {planning ? <><span className="animate-spin">⏳</span> 自动中...</> : <>🚀 自动</>}
            </button>
            {/* 📐 手动规划 */}
            <button onClick={handlePlan} disabled={planning}
              className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-5 py-2.5 rounded-xl font-medium hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 transition-all shadow-lg shadow-indigo-200 flex items-center gap-1.5 text-sm">
              {planning ? <><span className="animate-spin">⏳</span> 规划中...</> : plan ? '🔄 重新规划' : '📐 生成架构规划'}
            </button>
          </div>
        </div>

        {/* 规划内容 */}
        {plan && (
          <div className="animate-slide-up">
            {/* 4 个概览卡片 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
              <PlanStatCard label="推荐产品" value={`${plan.product_count} 个`} icon="📦" />
              <PlanStatCard label="预估收入" value={`¥${(plan.total_revenue || 0).toLocaleString()}`} icon="💰" />
              <PlanStatCard label="难度" value={plan.plan_json?.overview?.difficulty || '-'} icon="👥" />
              <PlanStatCard label="已选" value={`${selectedForGen.size}/${planItems.length}`} icon="✅" />
            </div>

            {/* 独特价值主张 */}
            <div className="bg-indigo-50 rounded-xl p-4 mb-5">
              <p className="text-sm font-medium text-indigo-700 mb-1">🎯 独特价值主张</p>
              <p className="text-sm text-indigo-600">{plan.plan_json?.overview?.unique_value}</p>
            </div>

            {/* 产品蓝图列表 */}
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-700">📦 推荐产品蓝图</h3>
              <button onClick={toggleAllInPlan} className="text-xs text-indigo-600 hover:underline">
                {isAllSelected ? '取消全选' : '全选'}
              </button>
            </div>

            <div className="space-y-2 mb-5">
              {planItems.map((item, idx) => {
                const info = resolveType(item.type, typeMap)
                const isSelected = selectedForGen.has(item.type)
                return (
                  // 🔍 [语法] 点击切换选中
                  <div
                    key={item.type}
                    onClick={() => toggleProductInPlan(item.type)}
                    className={`flex items-start gap-3 p-4 rounded-xl border-l-4 cursor-pointer transition-all ${
                      isSelected ? 'bg-indigo-50 border-l-indigo-500 shadow-sm' : 'bg-gray-50 border-l-gray-200 opacity-60 hover:opacity-80'
                    }`}
                  >
                    <div className="shrink-0 mt-0.5">
                      <div className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                        isSelected ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-gray-300'
                      }`}>
                        {isSelected && <span className="text-xs">✓</span>}
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-lg">{info.icon || item.icon}</span>
                        <span className="font-medium text-sm text-gray-800">P{idx+1}. {item.suggested_title}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${info.color?.split(' ')?.[1] || 'bg-gray-100'}`}>
                          {info.name || item.type}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-1">{item.angle}</p>
                      {item.outline?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {item.outline.map((o, i) => (
                            <span key={i} className="text-[10px] bg-white px-2 py-0.5 rounded-full border border-gray-200 text-gray-500">
                              {o.length > 30 ? o.slice(0, 30) + '...' : o}
                            </span>
                          ))}
                        </div>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-gray-400">
                        <span>💰 ¥{item.estimated_price}</span>
                        {(item.platforms || []).slice(0, 2).map((p, i) => (
                          <span key={i} className="bg-gray-100 px-1.5 py-0.5 rounded">{p}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 操作栏 */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-100">
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <button onClick={() => setShowPlanRaw(!showPlanRaw)} className="text-xs text-gray-400 hover:text-gray-600 underline">
                  {showPlanRaw ? '收起完整规划' : '查看完整规划文档'}
                </button>
                {plan.timeline?.estimated_minutes > 0 && (
                  <span>⏱ 预估 {plan.timeline.estimated_minutes} 分钟</span>
                )}
              </div>
              <button
                onClick={handleConfirmAndGenerate}
                disabled={generating || selectedForGen.size === 0}
                className="bg-gradient-to-r from-amber-500 to-orange-500 text-white px-6 py-2.5 rounded-xl font-medium hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 transition-all shadow-lg shadow-amber-200 flex items-center gap-2 text-sm"
              >
                {generating ? <><span className="animate-spin">⏳</span> 生成中...</> : <>🚀 确认并生成 ({selectedForGen.size}个) </>}
              </button>
            </div>

            {/* 完整规划 Markdown */}
            {showPlanRaw && plan.plan_markdown && (
              <div className="mt-5 bg-white border border-gray-200 rounded-xl p-6 max-h-96 overflow-auto">
                <div className="markdown-body text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{plan.plan_markdown}</ReactMarkdown>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 无规划引导 */}
        {!plan && !planning && (
          <div className="text-center py-6 bg-gray-50 rounded-xl border border-dashed border-gray-200">
            <div className="text-4xl mb-2">📐</div>
            <p className="text-sm text-gray-500 mb-1">点击上方按钮开始</p>
            <p className="text-xs text-gray-400">🚀 自动模式 = 规划+确认+生成一步到位（推荐）<br/>📐 手动模式 = 先生成规划，你审核后再确认生成</p>
          </div>
        )}
      </div>

      {/* ========== 下方的推荐+已生成 ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 左侧：快捷生成 */}
        <div>
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <h3 className="font-semibold text-gray-800 mb-1">⚡ 快捷生成（跳过规划）</h3>
            <p className="text-xs text-gray-400 mb-4">适合已经清楚要生成什么的情况</p>

            <div className="space-y-2 mb-4">
              {suggestions.map((s) => {
                const alreadyGenerated = noteProducts.some((p) => p.product_type === s.type)
                return (
                  <div key={s.type} className={`flex items-center justify-between p-3 rounded-xl transition-all ${alreadyGenerated ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-100'}`}>
                    <div className="flex items-center gap-2.5">
                      <span className="text-lg">{s.icon}</span>
                      <div>
                        <span className="text-sm font-medium text-gray-700">{s.name}</span>
                        <p className="text-[11px] text-gray-400">{s.reason}</p>
                      </div>
                    </div>
                    {alreadyGenerated ? (
                      <span className="text-xs text-green-600">✅ 已生成</span>
                    ) : (
                      <button onClick={() => handleGenerateSpecific([s.type])} disabled={generating} className="text-xs bg-primary-50 text-primary-600 px-3 py-1.5 rounded-lg hover:bg-primary-100 disabled:opacity-50">
                        生成
                      </button>
                    )}
                  </div>
                )
              })}
            </div>

            {suggestions.length > 0 && (
              <button
                onClick={async () => {
                  setGenerating(true)
                  try {
                    const task = await submitTask(suggestions.map((item) => item.type))
                    toast.success(`后台任务 #${task.id} 已开始`)
                    navigate('/tasks')
                  } catch (e) {
                    toast.error('生成失败: ' + e.message)
                  } finally { setGenerating(false) }
                }}
                disabled={generating || loading}
                className="w-full bg-gradient-to-r from-amber-500 to-orange-500 text-white py-3 rounded-xl font-medium hover:from-amber-600 hover:to-orange-600 disabled:opacity-50 transition-all shadow-lg shadow-amber-200 flex items-center justify-center gap-2"
              >
                {generating ? <><span className="animate-spin">⏳</span> 正在生成...</> : <>🚀 一键生成全部</>}
              </button>
            )}

            {/* ========== 当前全部产品形态（多选生成） ========== */}
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-gray-700">🗂️ 全部 {ALL_PRODUCT_TYPES.length} 种产品形态（可多选）</h4>
                <button
                  onClick={() => setSelectedAllTypes((prev) => (prev.size === ALL_PRODUCT_TYPES.length ? new Set() : new Set(ALL_PRODUCT_TYPES)))}
                  className="text-xs text-primary-600 hover:underline"
                >
                  {selectedAllTypes.size === ALL_PRODUCT_TYPES.length ? '清空' : '全选'}
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5 mb-3">
                {ALL_PRODUCT_TYPES.map((t) => {
                  const info = resolveType(t, typeMap)
                  const on = selectedAllTypes.has(t)
                  const alreadyGenerated = noteProducts.some((p) => p.product_type === t)
                  return (
                    <button
                      key={t}
                      onClick={() => toggleSet(setSelectedAllTypes, t)}
                      title={alreadyGenerated ? '该笔记已生成过此类型（可再次生成）' : '点击勾选'}
                      className={`px-2 py-1 rounded-lg text-xs border transition-colors ${
                        on ? 'bg-primary-600 text-white border-primary-600' : 'bg-white text-gray-600 border-gray-200 hover:border-primary-300'
                      }`}
                    >
                      {info.icon} {info.name}{alreadyGenerated ? ' ✅' : ''}
                    </button>
                  )
                })}
              </div>
              <button
                onClick={() => handleGenerateSpecific(Array.from(selectedAllTypes))}
                disabled={generating || selectedAllTypes.size === 0}
                className="w-full bg-primary-600 text-white py-2 rounded-xl text-sm font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors"
              >
                🎯 生成所选形态（{selectedAllTypes.size}）
              </button>

              {/* ========== 2026-08 feat/29：按产品独立配置生成策略 ========== */}
              {selectedAllTypes.size > 0 && (
                <div className="mt-4 p-3 rounded-xl bg-indigo-50/40 border border-indigo-100">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-semibold text-indigo-700">🎯 已选产品的生效策略（按产品可独立配）</h4>
                    <span className="text-[10px] text-indigo-500">{Object.values(perProductStrategies).filter(Boolean).length} / {selectedAllTypes.size} 已自定义</span>
                  </div>
                  <div className="space-y-1.5 max-h-48 overflow-auto pr-1">
                    {Array.from(selectedAllTypes).map((t) => {
                      const info = resolveType(t, typeMap)
                      const eff = getEffectiveStrategy(t)
                      const algoNames = (eff.algorithms || []).map((id) => strategies.algorithms?.find((a) => a.id === id)?.name || id)
                      const techNames = (eff.techniques || []).map((id) => strategies.techniques?.find((a) => a.id === id)?.name || id)
                      const skillNames = (eff.skill_ids || []).map((id) => skills.find((s) => s.id === id)?.name || `#${id}`)
                      return (
                        <div key={t} className="bg-white border border-indigo-100 rounded-lg p-2">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-1.5 text-xs">
                              <span>{info.icon || '📦'}</span>
                              <span className="font-medium text-gray-800">{info.name || t}</span>
                              {eff.has_override ? <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full">已自定义</span> : <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded-full">沿用默认</span>}
                            </div>
                            <button
                              onClick={() => setEditingProductType(t)}
                              className="text-[10px] text-indigo-600 hover:underline"
                            >
                              {eff.has_override ? '✏️ 编辑' : '🎚️ 配置'}
                            </button>
                          </div>
                          <label className="block mt-2">
                            <span className="block text-[11px] font-medium text-gray-600 mb-1">该产品提示词</span>
                            <textarea value={productPrompts[t] || ''} onChange={(event) => setProductPrompts((previous) => ({ ...previous, [t]: event.target.value }))} rows={2} maxLength={4000} placeholder={`仅用于${info.name || t}`} className="w-full resize-y border border-gray-200 px-2 py-1.5 text-xs outline-none focus:border-indigo-400" />
                          </label>
                          <div className="flex flex-wrap gap-1 text-[10px] text-gray-500">
                            {algoNames.length > 0 && <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">算法: {algoNames.join('、')}</span>}
                            {techNames.length > 0 && <span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded">质量: {techNames.join('、')}</span>}
                            {skillNames.length > 0 && <span className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded">Skill: {skillNames.join('、')}</span>}
                            {algoNames.length === 0 && techNames.length === 0 && skillNames.length === 0 && <span className="text-gray-300">空（将使用 task 级默认）</span>}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 右侧：已生成产品 */}
        <div>
          <div className="bg-white rounded-2xl border border-gray-100 p-5">
            <h3 className="font-semibold text-gray-800 mb-1">📦 已生成产品 <span className="text-sm text-gray-400">({noteProducts.length})</span></h3>
            <p className="text-xs text-gray-400 mb-4">点击查看内容或导出</p>

            {noteProducts.length === 0 ? (
              <div className="text-center py-12">
                <div className="text-6xl mb-3">💎</div>
                <p className="text-gray-400 text-sm">还没有生成产品</p>
                <p className="text-gray-400 text-xs mt-1">先规划、再生成效果更好</p>
              </div>
            ) : (
              <div className="space-y-2">
                {noteProducts.map((product) => {
                  const info = resolveType(product.product_type, typeMap)
                  return (
                    <div key={product.id} onClick={() => navigate(`/products/${product.id}`)}
                      className="flex items-center justify-between p-3 rounded-xl bg-gray-50 hover:bg-amber-50 cursor-pointer transition-all group border border-gray-100 hover:border-amber-200">
                      <div className="flex items-center gap-2.5 min-w-0 flex-1">
                        <span className="text-lg shrink-0">{info.icon || '📦'}</span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-700 truncate">{product.title}</p>
                          <div className="flex items-center gap-2 text-[11px] text-gray-400">
                            <span className={(info.badge?.split(' ')?.[1] || '') + ' px-1.5 py-0.3 rounded-full text-[10px]'}>
                              {info.name || product.product_type}
                            </span>
                            {product.price_suggestion > 0 && <span className="text-amber-500">¥{product.price_suggestion}</span>}
                          </div>
                        </div>
                      </div>
                      <span className="text-gray-300 group-hover:text-primary-500 shrink-0">→</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
      {agentReport && <AgentRunReport report={agentReport} />}
      {/* 🔍 [作用] 2026-08 feat/29：单产品 strategy 编辑弹窗 */}
      {editingProductType && (
        <PerProductStrategyModal
          productType={editingProductType}
          typeMap={typeMap}
          perProductStrategies={perProductStrategies}
          taskDefault={{
            skill_ids: Array.from(selectedSkills),
            algorithms: Array.from(selectedAlgorithms),
            techniques: Array.from(selectedTechniques),
          }}
          productDefault={productPreference(strategies, editingProductType)}
          skills={skills}
          strategies={strategies}
          onSave={(ptype, value) => setPerProductStrategies((prev) => {
            const next = { ...prev }
            // 🔍 [作用] 全字段为空视为"无独立覆盖"，从 map 中删除
            const isEmpty = !value.skill_ids?.length && !value.algorithms?.length && !value.techniques?.length
            if (isEmpty) delete next[ptype]
            else next[ptype] = value
            return next
          })}
          onClose={() => setEditingProductType(null)}
        />
      )}
    </div>
  )
}

function AgentRunReport({ report }) {
  const products = report.products || []
  const traces = products.flatMap((p) => (p.workflow_trace || []).map((step) => ({ ...step, productType: p.type || p.product_type })))
  const bestScore = products.reduce((max, p) => Math.max(max, Number(p.quality_report?.overall_score || p.quality_report?.score || 0)), 0)
  return (
    <div className="mt-6 bg-white rounded-2xl border border-indigo-100 p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <h3 className="font-semibold text-gray-800 text-lg">🤖 Agent 执行链与质量报告</h3>
          <p className="text-xs text-gray-400 mt-1">展示任务理解、知识增强、计划生成、LLM 生成、质量检查和结果交付全过程</p>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-indigo-600">{products.length || report.generated || 0}</div>
          <div className="text-xs text-gray-400">本次交付产品</div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
        <div className="rounded-xl bg-indigo-50 p-4">
          <div className="text-xs text-indigo-500 mb-1">运行模式</div>
          <div className="font-semibold text-indigo-800">{report.mode}</div>
        </div>
        <div className="rounded-xl bg-emerald-50 p-4">
          <div className="text-xs text-emerald-500 mb-1">LLM 调用</div>
          <div className="font-semibold text-emerald-800">{products.some((p) => p.used_llm) ? '真实模型优先' : '等待生成结果'}</div>
        </div>
        <div className="rounded-xl bg-amber-50 p-4">
          <div className="text-xs text-amber-500 mb-1">最高质量分</div>
          <div className="font-semibold text-amber-800">{bestScore || '待评分'}</div>
        </div>
      </div>
      {traces.length > 0 ? (
        <div className="space-y-2">
          {traces.slice(0, 12).map((step, idx) => (
            <div key={`${step.productType}-${idx}`} className="flex items-start gap-3 rounded-xl bg-gray-50 p-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs text-white">{idx + 1}</span>
              <div className="min-w-0">
                <div className="text-sm font-medium text-gray-800">{step.stage || step.node || 'agent_step'} <span className="text-xs text-gray-400">{step.productType}</span></div>
                <div className="text-xs text-gray-500 mt-0.5">{step.message || step.summary || (step.ok === false ? '需要人工复核' : '已完成')}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="rounded-xl bg-gray-50 p-4 text-sm text-gray-500">当前仅完成规划，还没有生成阶段 trace。点击“确认并生成”后可看到完整执行链。</div>
      )}
    </div>
  )
}

// 🔍 [语法] 子组件
// 🔍 [作用] 规划统计卡片
function PlanStatCard({ label, value, icon }) {
  return (
    <div className="bg-indigo-50 rounded-xl p-3">
      <div className="text-lg mb-0.5">{icon}</div>
      <div className="text-lg font-bold text-indigo-700">{value}</div>
      <div className="text-[11px] text-indigo-400">{label}</div>
    </div>
  )
}

function OptionGroup({ title, items = [], selected, onToggle, empty, children }) {
  return <div className="mb-4 last:mb-0"><div className="text-xs font-semibold text-gray-500 mb-2">{title}</div>{children}{items.length === 0 ? <p className="text-xs text-gray-400">{empty || '暂无可选项'}</p> : <div className="flex flex-wrap gap-2">{items.map((item) => <label key={item.id} className={`cursor-pointer border px-3 py-1.5 rounded text-xs transition-colors ${selected.has(item.id) ? 'border-emerald-600 bg-emerald-50 text-emerald-800' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`} title={item.desc || item.name}><input className="sr-only" type="checkbox" checked={selected.has(item.id)} onChange={() => onToggle(item.id)} /><span className="inline-flex items-center gap-1">{item.name}<ProductNumberTags ids={item.productTypeIds} /></span></label>)}</div>}</div>
}

function ProductNumberTags({ ids = [] }) {
  return <>{ids.map((id) => <span key={id} title={`适合知识产品 ${id}`} className="text-[10px] min-w-5 h-5 px-1 inline-flex items-center justify-center bg-emerald-50 text-emerald-700 border border-emerald-200 rounded">{id}</span>)}</>
}


// 🔍 [语法] 子组件（feat/29）：单产品类型 strategy 编辑弹窗
// 🔍 [作用] 让用户为单个 product_type 独立设置 skill_ids / algorithms / techniques；
// 字段为空数组或 null = 沿用 task 级默认；不点保存即丢弃。
function PerProductStrategyModal({ productType, typeMap, perProductStrategies, taskDefault, productDefault, skills, strategies, onSave, onClose }) {
  const meta = resolveType(productType, typeMap) || { name: productType, icon: '📦' }
  const initial = perProductStrategies[productType] || { skill_ids: [], algorithms: [], techniques: [] }
  const [skillIds, setSkillIds] = useState(new Set(initial.skill_ids || []))
  const [algorithms, setAlgorithms] = useState(new Set(initial.algorithms || []))
  const [techniques, setTechniques] = useState(new Set(initial.techniques || []))
  const [skillQuery, setSkillQuery] = useState('')
  const normalizedSkillQuery = skillQuery.trim().toLowerCase()
  const visibleSkills = normalizedSkillQuery
    ? skills.filter((skill) => [skill.name, skill.description, skill.category].some((value) => (value || '').toLowerCase().includes(normalizedSkillQuery)))
    : skills

  const toggle = (setter, value) => setter((prev) => {
    const next = new Set(prev)
    if (next.has(value)) next.delete(value)
    else next.add(value)
    return next
  })

  const save = () => {
    onSave(productType, {
      skill_ids: Array.from(skillIds),
      algorithms: Array.from(algorithms),
      techniques: Array.from(techniques),
    })
  }
  const clearAll = () => {
    setSkillIds(new Set())
    setAlgorithms(new Set())
    setTechniques(new Set())
  }
  const useTaskDefault = () => {
    setSkillIds(new Set(taskDefault.skill_ids || []))
    setAlgorithms(new Set(taskDefault.algorithms || []))
    setTechniques(new Set(taskDefault.techniques || []))
  }
  const useProductDefault = () => {
    const keywords = new Set(productDefault.skill_keywords || [])
    const availableAlgorithms = new Set((strategies.algorithms || []).map((item) => item.id))
    const availableTechniques = new Set((strategies.techniques || []).map((item) => item.id))
    setSkillIds(new Set(skills.filter((skill) => keywords.has(skill.name)).map((skill) => skill.id)))
    setAlgorithms(new Set((productDefault.algorithms || []).filter((id) => availableAlgorithms.has(id))))
    setTechniques(new Set((productDefault.techniques || []).filter((id) => availableTechniques.has(id))))
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl max-w-2xl w-full max-h-[85vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="p-5 border-b border-gray-100 flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <span>{meta.icon}</span>
              <span>{meta.name || productType} · 独立生成策略</span>
            </h3>
            <p className="text-xs text-gray-500 mt-1">未勾选任何项 = 完全沿用顶部"task 级默认"策略。</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">×</button>
        </div>
        <div className="p-5 space-y-4">
          <div className="flex items-center gap-2">
            <button onClick={useTaskDefault} className="text-xs text-indigo-600 hover:underline">📋 复制 task 级默认</button>
            <button onClick={useProductDefault} className="text-xs text-emerald-600 hover:underline">复制产品级默认</button>
            <button onClick={clearAll} className="text-xs text-gray-500 hover:underline">🧹 清空（全部沿用默认）</button>
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">生成算法</div>
            <div className="flex flex-wrap gap-2">
              {(strategies.algorithms || []).map((a) => (
                <label key={a.id} className={`cursor-pointer border px-3 py-1.5 rounded text-xs transition-colors ${algorithms.has(a.id) ? 'border-blue-600 bg-blue-50 text-blue-800' : 'border-gray-200 text-gray-600 hover:border-blue-300'}`} title={a.description}>
                  <input className="sr-only" type="checkbox" checked={algorithms.has(a.id)} onChange={() => toggle(setAlgorithms, a.id)} />
                  {a.name}
                </label>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">质量技术</div>
            <div className="flex flex-wrap gap-2">
              {(strategies.techniques || []).map((t) => (
                <label key={t.id} className={`cursor-pointer border px-3 py-1.5 rounded text-xs transition-colors ${techniques.has(t.id) ? 'border-emerald-600 bg-emerald-50 text-emerald-800' : 'border-gray-200 text-gray-600 hover:border-emerald-300'}`} title={t.description}>
                  <input className="sr-only" type="checkbox" checked={techniques.has(t.id)} onChange={() => toggle(setTechniques, t.id)} />
                  {t.name}
                </label>
              ))}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-2">技能（Skills）</div>
            <input value={skillQuery} onChange={(event) => setSkillQuery(event.target.value)} placeholder="按 Skill 名称或摘要搜索" className="w-full mb-3 px-3 py-2 border border-gray-200 rounded-lg text-xs outline-none focus:ring-2 focus:ring-primary-200 focus:border-primary-400" />
            {skills.length === 0 ? <p className="text-xs text-gray-400">尚未安装 Skill</p> : (
              <div className="flex flex-wrap gap-2 max-h-40 overflow-auto">
                {visibleSkills.map((s) => (
                  <label key={s.id} className={`cursor-pointer border px-3 py-1.5 rounded text-xs transition-colors ${skillIds.has(s.id) ? 'border-indigo-600 bg-indigo-50 text-indigo-800' : 'border-gray-200 text-gray-600 hover:border-indigo-300'}`} title={s.description || s.name}>
                    <input className="sr-only" type="checkbox" checked={skillIds.has(s.id)} onChange={() => toggle(setSkillIds, s.id)} />
                    <span className="inline-flex items-center gap-1">{s.name}<ProductNumberTags ids={s.product_type_ids} /></span>
                  </label>
                ))}
                {visibleSkills.length === 0 && <p className="text-xs text-gray-400">没有匹配的 Skill</p>}
              </div>
            )}
          </div>
        </div>
        <div className="p-4 border-t border-gray-100 flex items-center justify-between">
          <button
            onClick={() => { onSave(productType, { skill_ids: [], algorithms: [], techniques: [] }); onClose() }}
            className="text-xs text-red-600 hover:underline"
          >
            清除该产品独立配置
          </button>
          <div className="flex items-center gap-2">
            <button onClick={onClose} className="px-3 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-100">取消</button>
            <button onClick={() => { save(); onClose() }} className="px-4 py-1.5 rounded-lg text-sm bg-indigo-600 text-white hover:bg-indigo-700">保存</button>
          </div>
        </div>
      </div>
    </div>
  )
}
