// 🔍 [语法] React Hooks
// 🔍 [作用] useEffect 副作用；useState 状态
import { useEffect, useState } from 'react'

// 🔍 [语法] react-router-dom
// 🔍 [作用] 编程式导航
import { useNavigate } from 'react-router-dom'

// 🔍 [语法] 全局 store
// 🔍 [作用] 全局数据 + action
import useStore from '../store/useStore'

// 🔍 [语法] 模块级常量
// 🔍 [作用] 4 个学习阶段标签配置
const STAGE_LABELS = {
  stage1: { label: '筑基期', color: 'bg-blue-100 text-blue-700', desc: '基础入门，能做小Demo' },
  stage2: { label: '专精期', color: 'bg-indigo-100 text-indigo-700', desc: '深度学习，稳定接单' },
  stage3: { label: '融合期', color: 'bg-purple-100 text-purple-700', desc: '全栈融合，产品化' },
  stage4: { label: '创业期', color: 'bg-emerald-100 text-emerald-700', desc: '品牌矩阵，商业化' },
}

// 🔍 [语法] default export
// 🔍 [作用] Dashboard 主页
export default function Dashboard() {
  const navigate = useNavigate()
  // 🔍 [语法] 解构
  const { subjects, notes, products, stats, fetchNotes, fetchProducts, fetchStats } = useStore()
  // 🔍 [语法] 本地状态
  // 🔍 [作用] 最近 6 条笔记 / 6 个产品
  const [recentNotes, setRecentNotes] = useState([])
  const [recentProducts, setRecentProducts] = useState([])

  // 🔍 [语法] useEffect
  // 🔍 [作用] 加载数据
  useEffect(() => {
    fetchStats()
    // 🔍 [语法] .then 链
    // 🔍 [作用] 取前 6 条
    fetchNotes().then((n) => setRecentNotes(n?.slice(0, 6) || []))
    fetchProducts().then((p) => setRecentProducts(p?.slice(0, 6) || []))
  }, [])

  // 🔍 [语法] 解构 stats
  // 🔍 [作用] 显示数据
  const totalValue = stats?.estimated_total_value || 0
  const productCount = stats?.products ?? 0
  const noteCount = stats?.notes ?? 0

  return (
    // 🔍 [语法] max-w-6xl mx-auto
    // 🔍 [作用] 居中容器
    <div className="p-6 max-w-6xl mx-auto">
      {/* ========== 顶部标题 ========== */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-800">📊 工作台</h1>
        <p className="text-gray-500 mt-1">把学习过程变成赚钱过程，每一步都算数</p>
      </div>

      {/* ========== 4 张统计卡片 ========== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* 🔍 [语法] StatCard 子组件 */}
        {/* 🔍 [作用] 4 个数据卡片 */}
        <StatCard icon="📝" label="学习笔记" value={noteCount} color="from-indigo-500 to-purple-500" onClick={() => navigate('/subjects')} />
        <StatCard icon="💎" label="知识产品" value={productCount} color="from-amber-500 to-orange-500" onClick={() => navigate('/products')} />
        <StatCard icon="💰" label="潜在收入" value={`¥${totalValue.toLocaleString()}`} color="from-emerald-500 to-teal-500" highlight />
      </div>

      {/* ========== 快速操作（空状态引导） ========== */}
      {subjects.length === 0 ? (
        // 🔍 [语法] 空状态卡片
        // 🔍 [作用] 无科目时引导创建
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
          <div className="text-6xl mb-4">🚀</div>
          <h2 className="text-xl font-semibold text-gray-700 mb-2">开始你的变现之旅</h2>
          <p className="text-gray-500 mb-6 max-w-md mx-auto">先创建一个科目，然后边学习边记笔记，AI会自动帮你生成知识付费产品</p>
          <button
            onClick={() => navigate('/subjects')}
            className="bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors shadow-lg shadow-primary-200"
          >
            创建第一个科目 →
          </button>
        </div>
      ) : (
        <>
          {/* ========== 科目概览 ========== */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-800">📚 学习科目</h2>
              <button onClick={() => navigate('/subjects')} className="text-sm text-primary-600 hover:text-primary-700">管理科目 →</button>
            </div>
            {/* 🔍 [语法] 网格布局 */}
            {/* 🔍 [作用] 3 列卡片网格 */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* 🔍 [语法] slice 前 6 个 */}
              {subjects.slice(0, 6).map((subject) => (
                <div
                  key={subject.id}
                  onClick={() => navigate(`/subjects/${subject.id}/notes`)}
                  className="bg-white rounded-xl p-5 border border-gray-100 hover:border-primary-200 hover:shadow-md cursor-pointer transition-all group"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-3xl">{subject.icon}</span>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-gray-800 truncate">{subject.name}</h3>
                      <p className="text-xs text-gray-400">{subject.note_count || 0}篇笔记</p>
                    </div>
                  </div>
                  {subject.description && <p className="text-sm text-gray-500 line-clamp-2">{subject.description}</p>}
                  <div className="mt-3 flex items-center justify-end text-xs">
                    <span className="text-primary-600 opacity-0 group-hover:opacity-100 transition-opacity">开始学习 →</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ========== 两栏布局：最近笔记 + 最近产品 ========== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 左侧：最近笔记 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">📝 最近笔记</h2>
              </div>
              <div className="space-y-3">
                {recentNotes.length === 0 ? (
                  <div className="text-center py-8 bg-white rounded-xl border border-dashed border-gray-200">
                    <p className="text-gray-400">还没有笔记，开始学习吧</p>
                  </div>
                ) : (
                  recentNotes.map((note) => (
                    <div
                      key={note.id}
                      onClick={() => navigate(`/subjects/${note.subject_id}/notes/${note.id}`)}
                      className="bg-white rounded-xl p-4 border border-gray-100 hover:border-primary-200 cursor-pointer transition-all hover:shadow-sm"
                    >
                      <h3 className="font-medium text-gray-800 mb-1 truncate">{note.title}</h3>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span>{note.subject_name}</span>
                        <span>⏱ {note.estimated_minutes}分钟</span>
                        <span className={`px-1.5 py-0.3 rounded-full text-[10px] ${STAGE_LABELS[note.learning_stage]?.color || 'bg-gray-100 text-gray-500'}`}>
                          {STAGE_LABELS[note.learning_stage]?.label || note.learning_stage}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* 右侧：最近产品 */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-gray-800">💎 最新产品</h2>
              </div>
              <div className="space-y-3">
                {recentProducts.length === 0 ? (
                  <div className="text-center py-8 bg-white rounded-xl border border-dashed border-gray-200">
                    <p className="text-gray-400">记完笔记后，AI会自动生成产品</p>
                  </div>
                ) : (
                  recentProducts.map((product) => (
                    <div
                      key={product.id}
                      onClick={() => navigate(`/products/${product.id}`)}
                      className="bg-white rounded-xl p-4 border border-gray-100 hover:border-amber-200 cursor-pointer transition-all hover:shadow-sm"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <h3 className="font-medium text-gray-800 truncate flex-1 mr-2">{product.title}</h3>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${product.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                          {product.status === 'published' ? '已发布' : '草稿'}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span>{product.product_type}</span>
                        {product.price_suggestion > 0 && <span className="text-amber-600 font-medium">¥{product.price_suggestion}</span>}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// 🔍 [语法] 子组件
// 🔍 [作用] 统计卡片
function StatCard({ icon, label, value, color, highlight, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-white rounded-xl p-5 border border-gray-100 hover:shadow-md transition-all ${onClick ? 'cursor-pointer' : ''} ${highlight ? 'ring-2 ring-amber-200' : ''}`}
    >
      <div className="flex items-center gap-3 mb-2">
        <span className="text-2xl">{icon}</span>
        <span className="text-sm text-gray-500">{label}</span>
      </div>
      {/* 🔍 [语法] bg-clip-text + text-transparent */}
      {/* 🔍 [作用] 渐变文字 */}
      <p className={`text-2xl font-bold bg-gradient-to-r ${color} bg-clip-text text-transparent`}>
        {value}
      </p>
    </div>
  )
}
