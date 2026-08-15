// 🔍 [语法] React Hooks
import { useEffect, useState } from 'react'
// 🔍 [语法] react-router-dom
import { useNavigate, useSearchParams } from 'react-router-dom'
// 🔍 [语法] 全局 store
import useStore from '../store/useStore'
// 🔍 [语法] toast
import toast from 'react-hot-toast'
import SearchSortBar, { sortResources } from './SearchSortBar'

// 🔍 [语法] 共享产品类型元数据（名称/图标/配色集中维护，前后端统一）
import { TYPE_META, resolveType, useTypeMap } from '../utils/typeMeta'
import { formatDateTime } from '../utils/dateTime'
import { productMatchesTask, productTaskLabel } from '../utils/productTrace'

// 🔍 [语法] default export
// 🔍 [作用] 产品库 + 多维筛选 + 发布/删除
export default function ProductLibrary() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const taskId = Number(searchParams.get('taskId')) || null
  const typeMap = useTypeMap()
  // 🔍 [语法] 解构
  const { products, fetchProducts, updateProduct, deleteProduct } = useStore()

  // 🔍 [语法] 2 个状态
  // 🔍 [作用] 筛选器 + 删除二次确认
  const [filter, setFilter] = useState('all')
  const [deletingId, setDeletingId] = useState(null)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState('updated')

  // 🔍 [语法] useEffect 空依赖
  useEffect(() => { fetchProducts(taskId ? { task_id: taskId } : {}) }, [taskId])

  // 🔍 [语法] 多维筛选
  // 🔍 [作用] 按状态或类型过滤
  const filtered = filter === 'all'
    ? products
    : filter === 'published'
      ? products.filter((p) => p.status === 'published')
      : filter === 'draft'
        ? products.filter((p) => p.status === 'draft')
        : products.filter((p) => p.product_type === filter)
  const visibleProducts = sortResources(filtered.filter((item) => {
    const matchesTitle = item.title.toLowerCase().includes(query.trim().toLowerCase())
    const matchesTask = productMatchesTask(item, taskId)
    return matchesTitle && matchesTask
  }), sort, (item) => (item.content || '').length)

  // 🔍 [语法] reduce 累加
  // 🔍 [作用] 总价值
  const totalValue = products.reduce((sum, p) => sum + Number(p.price_suggestion || 0), 0)
  // 🔍 [语法] filter 计数
  const publishedCount = products.filter((p) => p.status === 'published').length

  // 🔍 [语法] async 发布（草稿 → 已发布）
  const handlePublish = async (id) => {
    try {
      await updateProduct(id, { status: 'published' })
      toast.success('已标记为已发布！')
      fetchProducts()
    } catch (e) {
      toast.error(e.message)
    }
  }

  // 🔍 [语法] async 双击确认删除
  const handleDelete = async (id) => {
    if (deletingId !== id) {
      setDeletingId(id)
      return
    }
    try {
      await deleteProduct(id)
      toast.success('已删除')
      setDeletingId(null)
    } catch (e) {
      toast.error(e.message)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* ========== 头部统计 ========== */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">💎 产品库</h1>
        <p className="text-gray-500 mt-1">
          {/* 🔍 [语法] 模板字符串 + 三个值 */}
          共 {products.length} 个产品 · 已发布 {publishedCount} 个 · 总价值 ¥{totalValue.toLocaleString()}
        </p>
      </div>
      <SearchSortBar query={query} onQuery={setQuery} sort={sort} onSort={setSort} noun="产品" />
      {taskId && <div className="mb-4 flex items-center justify-between border-l-4 border-emerald-500 bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><span>正在显示任务 #{taskId} 生成的 {visibleProducts.length} 个产品</span><button className="font-medium hover:underline" onClick={() => setSearchParams({})}>查看全部产品</button></div>}

      {/* ========== 筛选器 ========== */}
      <div className="flex flex-wrap gap-2 mb-6">
        {/* 全部按钮 */}
        <button onClick={() => setFilter('all')} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'all' ? 'bg-primary-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'}`}>
          全部
        </button>
        {/* 草稿按钮 */}
        <button onClick={() => setFilter('draft')} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'draft' ? 'bg-gray-700 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'}`}>
          📝 草稿
        </button>
        {/* 已发布按钮 */}
        <button onClick={() => setFilter('published')} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === 'published' ? 'bg-emerald-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'}`}>
          ✅ 已发布
        </button>
        {/* 分隔线 */}
        <div className="w-px bg-gray-200 mx-1" />
        {/* 🔍 [语法] 当前全部产品类型 */}
        {/* 🔍 [作用] 需求：全部产品形态在产品库展示，供用户筛选 */}
        {Object.entries(TYPE_META).map(([type, info]) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`px-3 py-2 rounded-xl text-sm transition-all ${
              filter === type ? 'bg-amber-100 text-amber-700 font-medium' : 'bg-white text-gray-500 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            {info.icon} {info.name}
          </button>
        ))}
      </div>

      {/* ========== 产品列表 ========== */}
      {visibleProducts.length === 0 ? (
        // 🔍 [语法] 空状态
        <div className="text-center py-20">
          <div className="text-6xl mb-4">💎</div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">还没有产品</h2>
          <p className="text-gray-400 mb-6">记完笔记后，AI会自动生成知识付费产品</p>
          <button onClick={() => navigate('/subjects')} className="bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors">
            去记笔记 →
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {visibleProducts.map((product) => {
            const info = resolveType(product.product_type, typeMap)
            return (
              // 🔍 [语法] 卡片 + border-l-4
              <div
                key={product.id}
                className={`bg-white rounded-xl p-5 border border-gray-100 border-l-4 hover:shadow-md transition-all group cursor-pointer ${taskId ? 'ring-2 ring-emerald-300' : ''} ${info.border || 'border-l-gray-300'}`}
                onClick={() => navigate(`/products/${product.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-xl">{info.icon || '📦'}</span>
                      <h3 className="font-semibold text-gray-800 truncate">{product.title}</h3>
                      {/* 状态标签 */}
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${product.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                        {product.status === 'published' ? '已发布' : '草稿'}
                      </span>
                    </div>
                    {/* 🔍 [语法] 正则去除 Markdown 标记 */}
                    {/* 🔍 [作用] 摘要 */}
                    <p className="text-xs text-gray-400 line-clamp-1 mb-2">
                      {product.content?.replace(/[#*`>]/g, '').substring(0, 100)}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span>{info.name || product.product_type}</span>
                      {product.price_suggestion > 0 && <span className="text-amber-500 font-medium">💰 ¥{product.price_suggestion}</span>}
                      {product.estimated_value && <span className="text-gray-500">📈 {product.estimated_value}</span>}
                      <span>生成时间：{formatDateTime(product.created_at)}</span>
                      {/* 🔍 [作用] 所有产品都展示任务关联状态；历史产品没有可追溯任务时明确说明。 */}
                      <span className={product.generation_meta?.task_id ? 'font-medium text-emerald-600' : 'text-gray-400'}>
                        {productTaskLabel(product)}
                      </span>
                    </div>
                    {/* 🔍 [作用] 展示本产品的生成策略映射（Skill/算法/质量技术），存在矛盾时给出警示。 */}
                    {product.generation_meta && <StrategyMap product={product} />}
                  </div>
                  {/* 操作按钮 */}
                  {/* 🔍 [语法] stopPropagation */}
                  {/* 🔍 [作用] 防止跳转到详情 */}
                  <div className="flex items-center gap-1.5 ml-3 shrink-0" onClick={(e) => e.stopPropagation()}>
                    {/* 发布按钮（草稿状态才显示） */}
                    {product.status === 'draft' && (
                      <button onClick={() => handlePublish(product.id)} className="text-xs bg-emerald-50 text-emerald-600 px-2.5 py-1.5 rounded-lg hover:bg-emerald-100 transition-colors" title="标记为已发布（未对接真实平台，仅改变状态）">
                        ✅ 标记为已发布
                      </button>
                    )}
                    {/* 双击确认删除 */}
                    <button onClick={() => handleDelete(product.id)} className={`text-xs px-2.5 py-1.5 rounded-lg transition-colors ${deletingId === product.id ? 'bg-red-50 text-red-600 font-medium' : 'text-gray-400 hover:bg-gray-100'}`}>
                      {deletingId === product.id ? '确认？' : '🗑️'}
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// 🔍 [语法] 子组件
// 🔍 [作用] 展示当前产品采用的生成策略映射（Skills / 算法 / 质量技术）+ 矛盾警告。
//          数据来源 product.generation_meta（后端在生成时写入）。
function StrategyMap({ product }) {
  const meta = product.generation_meta || {}
  const skillNames = meta.skill_names || []
  const algorithms = meta.algorithms || []
  const techniques = meta.techniques || []
  const warnings = meta.strategy_warnings || []
  const memorybear = meta.memorybear || {}
  const layerCount = Object.values(memorybear.layers || {}).reduce((sum, n) => sum + (n || 0), 0)
  const hasContent = skillNames.length || algorithms.length || techniques.length
  if (!hasContent) return null
  // 策略矛盾检测：memorybear + rag_grounding 同时启用时，权重已统一为 MB 优先；技术层面视为并存。
  // 真正的矛盾指“同一轴内出现冲突”：比如 quality_scoring + hallucination_check 同存（不冲突）vs
  // 单次直出（未实装）+ iterative_refinement 同时选（冲突，已记录为 warning）。
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
      <span className="text-gray-400 mr-1">生成策略：</span>
      {skillNames.map((name) => (
        <span key={`s-${name}`} className="bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded">Skill: {name}</span>
      ))}
      {algorithms.map((name) => (
        <span key={`a-${name}`} className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">算法: {name}</span>
      ))}
      {techniques.map((name) => (
        <span key={`t-${name}`} className={`px-1.5 py-0.5 rounded ${name === 'memorybear' ? 'bg-amber-50 text-amber-800' : name === 'rag_grounding' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>质量: {name}</span>
      ))}
      {memorybear.layers && layerCount > 0 && (
        <span className="bg-amber-50 text-amber-800 px-1.5 py-0.5 rounded" title="参与这次决策的记忆条目数">🧠 {layerCount} 条记忆</span>
      )}
      {warnings.length > 0 && (
        <span className="bg-red-50 text-red-700 px-1.5 py-0.5 rounded" title={warnings.join('\n')}>⚠️ 策略警告 {warnings.length}</span>
      )}
    </div>
  )
}
