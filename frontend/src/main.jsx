// 🔍 [语法] React 核心导入
// 🔍 [作用] React 18 主库
import React from 'react'

// 🔍 [语法] ReactDOM 客户端入口
// 🔍 [作用] React 18 客户端渲染 API（替代旧的 ReactDOM.render）
import ReactDOM from 'react-dom/client'

// 🔍 [语法] BrowserRouter from react-router-dom
// 🔍 [作用] 浏览器端路由（HTML5 history API）
import { BrowserRouter } from 'react-router-dom'

// 🔍 [语法] Toaster from react-hot-toast
// 🔍 [作用] 全局消息提示组件
import { Toaster } from 'react-hot-toast'

// 🔍 [语法] 导入主组件
// 🔍 [作用] 根应用组件（含路由配置）
import App from './App'

// 🔍 [语法] 导入全局样式
// 🔍 [作用] Tailwind + 全局样式入口
import './index.css'

// 🔍 [语法] ReactDOM.createRoot
// 🔍 [作用] React 18 新 API：创建根节点
// 🔍 [示例] 等价于旧版 ReactDOM.render(<App/>, document.getElementById('root'))
ReactDOM.createRoot(document.getElementById('root')).render(
  // 🔍 [语法] React.StrictMode
  // 🔍 [作用] 开发模式额外检查（不安全的生命周期等）
  // 🔍 [陷阱] 仅开发模式生效，生产会被移除
  <React.StrictMode>
    {/* BrowserRouter：启用前端路由 */}
    <BrowserRouter>
      {/* App 组件：定义所有页面路由规则 */}
      <App />
      {/* Toaster：全局消息提示容器，固定在顶部居中 */}
      <Toaster
        position="top-center"
        toastOptions={{
          duration: 3000,
          style: {
            borderRadius: '10px',
            background: '#1f2937',
            color: '#fff',
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>,
)
