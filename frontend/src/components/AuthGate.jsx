// 🔍 [语法] React Hooks
// 🔍 [作用] useEffect 副作用；useState 状态
import { useEffect, useState } from 'react'

// 🔍 [语法] react-hot-toast
// 🔍 [作用] 全局消息提示
import toast from 'react-hot-toast'

// 🔍 [语法] API 客户端
// 🔍 [作用] auth.me 检查登录状态；getAccessToken 取 Token
import { api, getAccessToken } from '../utils/api'

// 🔍 [语法] default export
// 🔍 [作用] 鉴权门禁组件（包裹整个应用）
export default function AuthGate({ children }) {
  // 🔍 [语法] 三个状态
  // 🔍 [作用] 检查中、当前用户、模式（login/signup）
  const [checking, setChecking] = useState(true)
  const [user, setUser] = useState(null)
  const [mode, setMode] = useState('login')
  // 🔍 [语法] 受控表单
  // 🔍 [作用] 表单输入
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // 🔍 [语法] 提交中标志
  // 🔍 [作用] 防止重复提交
  const [busy, setBusy] = useState(false)

  // 🔍 [语法] useEffect + 空依赖
  // 🔍 [作用] 仅挂载时检查登录
  useEffect(() => {
    // 🔍 [语法] 早返回
    // 🔍 [作用] 无 Token 直接跳到登录
    if (!getAccessToken()) {
      setChecking(false)
      return
    }
    // 🔍 [语法] .then/.catch/.finally
    // 🔍 [作用] 异步验证 Token
    api.auth.me()
      .then((res) => setUser(res.user))
      // 🔍 [语法] .catch
      // 🔍 [作用] Token 无效则清空
      .catch(() => api.auth.logout())
      .finally(() => setChecking(false))
  }, [])

  // 🔍 [语法] async 函数
  // 🔍 [作用] 表单提交（登录或注册）
  const submit = async (event) => {
    // 🔍 [语法] preventDefault
    // 🔍 [作用] 阻止表单默认提交（避免页面刷新）
    event.preventDefault()
    setBusy(true)
    try {
      // 🔍 [语法] if 分支
      // 🔍 [作用] 根据模式选登录或注册
      if (mode === 'login') {
        const res = await api.auth.login(email, password)
        setUser(res.user)
        toast.success('登录成功')
      } else {
        const res = await api.auth.signup(email, password)
        // 🔍 [语法] 条件 setUser
        // 🔍 [作用] Supabase 邮箱验证流程可能无 token
        if (res.access_token) {
          setUser(res.user)
          toast.success('注册成功')
        } else {
          toast.success('注册成功，请按邮件提示完成确认后登录')
          setMode('login')
        }
      }
    } catch (error) {
      // 🔍 [语法] toast.error
      // 🔍 [作用] 错误反馈
      toast.error(error.message)
    } finally {
      setBusy(false)
    }
  }

  // 🔍 [语法] 三态渲染
  // 🔍 [作用] checking → form；user → children
  if (checking) {
    return <div className="min-h-screen grid place-items-center bg-gray-50 text-gray-500">正在确认登录状态...</div>
  }

  if (user) {
    // 🔍 [语法] 已登录则渲染子组件
    return children
  }

  return (
    // 🔍 [语法] 双栏布局
    // 🔍 [作用] 左侧品牌 + 右侧表单
    <div className="min-h-screen bg-gray-50 flex">
      {/* ========== 左侧品牌区（lg 以上才显示） ========== */}
      <section className="hidden lg:flex flex-1 bg-slate-950 text-white p-12 flex-col justify-between">
        <div>
          <div className="text-sm text-emerald-300 font-medium mb-8">Learn2Earn</div>
          <h1 className="text-4xl font-bold leading-tight max-w-xl">把学习笔记沉淀成可售卖的知识产品库</h1>
          <p className="mt-5 text-slate-300 max-w-lg leading-7">
            登录后，你的科目、笔记、AI 生成产品会按账号隔离保存到秒悟云数据库。
          </p>
        </div>
        <div className="grid grid-cols-3 gap-3 text-sm text-slate-300">
          <div className="border border-white/10 p-4 rounded-lg">云端笔记</div>
          <div className="border border-white/10 p-4 rounded-lg">AI 产品生成</div>
          <div className="border border-white/10 p-4 rounded-lg">收益看板</div>
        </div>
      </section>

      {/* ========== 右侧表单 ========== */}
      <main className="w-full lg:w-[460px] bg-white flex items-center justify-center p-8">
        {/* 🔍 [语法] form onSubmit */}
        {/* 🔍 [作用] 表单提交 */}
        <form onSubmit={submit} className="w-full max-w-sm">
          <div className="mb-8">
            <p className="text-sm text-gray-500 mb-2">{mode === 'login' ? '欢迎回来' : '创建账号'}</p>
            <h2 className="text-2xl font-bold text-gray-900">{mode === 'login' ? '登录 Learn2Earn' : '注册 Learn2Earn'}</h2>
          </div>

          {/* 🔍 [语法] label + input */}
          {/* 🔍 [作用] 邮箱字段 */}
          <label className="block text-sm font-medium text-gray-700 mb-2">邮箱</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full h-11 border border-gray-300 rounded-lg px-3 mb-4 focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="you@example.com"
            required
          />

          {/* 🔍 [语法] minLength={6} */}
          {/* 🔍 [作用] HTML5 校验最少 6 位 */}
          <label className="block text-sm font-medium text-gray-700 mb-2">密码</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full h-11 border border-gray-300 rounded-lg px-3 mb-6 focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="至少 6 位"
            minLength={6}
            required
          />

          <button
            type="submit"
            disabled={busy}
            className="w-full h-11 bg-primary-600 text-white rounded-lg font-medium hover:bg-primary-700 disabled:opacity-60 transition-colors"
          >
            {busy ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>

          {/* 🔍 [语法] 切换模式 */}
          {/* 🔍 [作用] 登录/注册切换 */}
          <button
            type="button"
            onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
            className="w-full mt-4 text-sm text-primary-600 hover:underline"
          >
            {mode === 'login' ? '没有账号？注册一个' : '已有账号？去登录'}
          </button>
        </form>
      </main>
    </div>
  )
}
