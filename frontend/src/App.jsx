// 🔍 [语法] react-router-dom 路由组件
// 🔍 [作用] Routes + Route 用于声明路由
import { Routes, Route } from 'react-router-dom'

// 🔍 [语法] React Hooks
// 🔍 [作用] useEffect 副作用；useState 状态
import { useEffect, useState } from 'react'

// 🔍 [语法] Zustand store
// 🔍 [作用] 全局状态管理
import useStore from './store/useStore'

// 🔍 [语法] 路由组件导入
// 🔍 [作用] 各页面组件
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import SubjectManager from './components/SubjectManager'
import NoteEditor from './components/NoteEditor'
import NotesList from './components/NotesList'
import ProductGenerator from './components/ProductGenerator'
import ProductLibrary from './components/ProductLibrary'
import ProductViewer from './components/ProductViewer'
import Settings from './components/Settings'
import StrategyPreferences from './components/StrategyPreferences'
import AuthGate from './components/AuthGate'
import GenerationTasks from './components/GenerationTasks'
import SkillsManager from './components/SkillsManager'

// 🔍 [语法] default export
// 🔍 [作用] 主应用组件（仅 AuthGate 包裹）
export default function App() {
  return (
    // 🔍 [语法] AuthGate 包裹
    // 🔍 [作用] 鉴权门禁（未登录显示登录页）
    <AuthGate>
      {/* 登录后渲染 */}
      <AuthenticatedApp />
    </AuthGate>
  )
}

// 🔍 [语法] 内部组件
// 🔍 [作用] 登录后展示主界面
function AuthenticatedApp() {
  // 🔍 [语法] 解构 store
  // 🔍 [作用] 从 Zustand store 取 action
  // 🔍 [作用] 2026-08 fix/26：fetchTasks 在首次加载时一并预热，「生成任务」页打开就看到所有任务
  const { fetchSubjects, fetchStats, fetchTasks } = useStore()

  // 🔍 [语法] useState 布尔
  // 🔍 [作用] 数据加载状态
  const [ready, setReady] = useState(false)

  // 🔍 [语法] useEffect + 空依赖
  // 🔍 [作用] 仅首次挂载执行
  useEffect(() => {
    // 🔍 [语法] Promise.all
    // 🔍 [作用] 并行加载数据
    Promise.all([fetchSubjects(), fetchStats(), fetchTasks().catch(() => [])])
      // 🔍 [语法] .finally
      // 🔍 [作用] 无论成功失败都设置 ready=true
      .finally(() => setReady(true))
  }, [])  // 空依赖：仅挂载一次

  // 🔍 [语法] 早返回
  // 🔍 [作用] 数据未就绪显示加载占位
  if (!ready) {
    return (
      // 🔍 [语法] 全屏居中
      // 🔍 [作用] 加载占位 UI
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          {/* 浮动动画的钱币 emoji */}
          <div className="text-5xl mb-4 animate-float">💰</div>
          {/* shimmer 闪烁效果文本 */}
          <div className="text-xl font-semibold text-gray-700 shimmer inline-block px-4 py-2 rounded-lg">
            Learn2Earn 加载中...
          </div>
        </div>
      </div>
    )
  }

  // 🔍 [语法] 数据就绪渲染主界面
  // 🔍 [作用] Layout 包裹路由
  return (
    <Layout>
      {/* Routes：路由容器 */}
      <Routes>
        {/* 首页：Dashboard */}
        <Route path="/" element={<Dashboard />} />
        {/* 科目管理 */}
        <Route path="/subjects" element={<SubjectManager />} />
        {/* 某科目下的笔记列表 */}
        <Route path="/subjects/:subjectId/notes" element={<NotesList />} />
        {/* 新建笔记 */}
        <Route path="/subjects/:subjectId/notes/new" element={<NoteEditor />} />
        {/* 编辑笔记 */}
        <Route path="/subjects/:subjectId/notes/:noteId" element={<NoteEditor />} />
        {/* AI 产品生成器 */}
        <Route path="/notes/:noteId/generate" element={<ProductGenerator />} />
        {/* 产品库 */}
        <Route path="/products" element={<ProductLibrary />} />
        {/* 产品详情 */}
        <Route path="/products/:productId" element={<ProductViewer />} />
        {/* 系统设置 */}
        <Route path="/settings" element={<Settings />} />
        <Route path="/strategy-preferences" element={<StrategyPreferences />} />
        <Route path="/tasks" element={<GenerationTasks />} />
        <Route path="/skills" element={<SkillsManager />} />
      </Routes>
    </Layout>
  )
}
