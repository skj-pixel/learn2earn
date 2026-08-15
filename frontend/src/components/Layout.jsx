// 🔍 [语法] react-router-dom
// 🔍 [作用] NavLink 带 active 样式；useLocation 取当前路径
import { NavLink, useLocation } from 'react-router-dom'

// 🔍 [语法] 全局 store
// 🔍 [作用] 取 stats 显示在侧边栏底部
import useStore from '../store/useStore'

// 🔍 [语法] API 客户端
// 🔍 [作用] 登出功能
import { api } from '../utils/api'

// 🔍 [语法] 模块级数组
// 🔍 [作用] 4 个导航项配置
const navItems = [
  { to: '/',          icon: '📊', label: '工作台' },
  { to: '/subjects',  icon: '📚', label: '科目管理' },
  { to: '/products',  icon: '💎', label: '产品库' },
  { to: '/tasks',     icon: '⏳', label: '生成任务' },
  { to: '/skills',    icon: '🧩', label: 'Skills 仓库' },
  { to: '/strategy-preferences', icon: '🎛️', label: '策略偏好' },
  { to: '/settings',  icon: '⚙️', label: 'LLM 设置' },
]

// 🔍 [语法] default export 函数组件
// 🔍 [作用] 布局组件（侧边栏 + 主内容区）
export default function Layout({ children }) {
  // 🔍 [语法] 解构 store
  // 🔍 [作用] 获取统计信息
  const { stats } = useStore()

  // 🔍 [语法] 箭头函数
  // 🔍 [作用] 登出：清 Token + 刷新页面
  const handleLogout = () => {
    api.auth.logout()
    window.location.reload()
  }

  return (
    // 🔍 [语法] flex h-screen
    // 🔍 [作用] 全屏 flex 布局
    <div className="app-shell flex h-screen bg-gray-50 overflow-hidden">
      {/* ========== 侧边栏 ========== */}
      <aside className="app-sidebar w-56 bg-white border-r border-gray-200 flex flex-col shrink-0">
        {/* Logo */}
        <div className="app-logo p-5 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <span className="text-2xl">💰</span>
            <div>
              <h1 className="text-base font-bold text-gray-800 leading-tight">Learn2Earn</h1>
              <p className="text-[11px] text-gray-400 leading-tight">学习即赚钱</p>
            </div>
          </div>
        </div>

        {/* 导航 */}
        <nav className="app-nav flex-1 p-3 space-y-1">
          {/* 🔍 [语法] map 渲染 */}
          {/* 🔍 [作用] 动态生成导航项 */}
          {navItems.map((item) => (
            // 🔍 [语法] NavLink
            // 🔍 [作用] 自动应用 active 样式
            <NavLink
              key={item.to}
              to={item.to}
              // 🔍 [语法] end prop
              // 🔍 [作用] 仅精确匹配 / 时 active
              end={item.to === '/'}
              // 🔍 [语法] 函数式 className
              // 🔍 [作用] 根据 isActive 动态样式
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-primary-50 text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* ========== 底部统计卡片 ========== */}
        {/* 🔍 [语法] 条件渲染 */}
        {/* 🔍 [作用] 仅 stats 存在时显示 */}
        {stats && (
          <div className="app-sidebar-stats p-4 border-t border-gray-100">
            {/* 渐变背景卡片 */}
            <div className="bg-gradient-to-br from-primary-50 to-indigo-50 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-2">潜在收益</p>
              {/* 🔍 [语法] toLocaleString */}
              {/* 🔍 [作用] 千分位格式化 */}
              <p className="text-lg font-bold text-primary-700">
                ¥{stats.estimated_total_value?.toLocaleString() || 0}
              </p>
              <div className="flex justify-between mt-2 text-xs text-gray-500">
                <span>📝 {stats.notes || 0}篇笔记</span>
                <span>💎 {stats.products || 0}个产品</span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="mt-3 w-full text-xs text-gray-500 hover:text-gray-800 border border-gray-200 rounded-lg py-2 transition-colors"
            >
              退出登录
            </button>
          </div>
        )}
      </aside>

      {/* ========== 主内容区 ========== */}
      {/* 🔍 [语法] flex-1 + overflow-auto */}
      {/* 🔍 [作用] 占满剩余空间 + 可滚动 */}
      <main className="app-main flex-1 overflow-auto min-w-0">
        <div className="h-full">{children}</div>
      </main>
    </div>
  )
}
