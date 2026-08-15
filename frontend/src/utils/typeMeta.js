// 🔍 [语法] 共享产品类型元数据
// 🔍 [作用] 14 种产品类型的名称/图标/配色集中维护，前后端统一；
//          名称与图标优先取后端 /api/ai/product-types，本地 TYPE_META 作为完整兜底。
import { useEffect, useState } from 'react'
import { api } from './api'

// 🔍 [语法] 全量 14 类静态映射（2026-08 移除 8 种历史类型，仅旧数据可读）
// 🔍 [作用] 后端未返回时也能正确显示；badge=徽标配色，border=左侧色条
export const TYPE_META = {
  article:             { name: '技术文章',      icon: '📝', badge: 'text-blue-700 bg-blue-50',    border: 'border-l-blue-500' },
  ppt:         { name: 'PPT大纲',       icon: '📊', badge: 'text-indigo-700 bg-indigo-50', border: 'border-l-indigo-500' },
  sop:                 { name: 'SOP文档',        icon: '📋', badge: 'text-purple-700 bg-purple-50',  border: 'border-l-purple-500' },
  prompt_template:     { name: '提示词模板',    icon: '💡', badge: 'text-violet-700 bg-violet-50',  border: 'border-l-violet-500' },
  course_outline:      { name: '课程大纲',      icon: '🎓', badge: 'text-pink-700 bg-pink-50',     border: 'border-l-pink-500' },
  interview_qa:        { name: '面试题库',      icon: '❓', badge: 'text-rose-700 bg-rose-50',      border: 'border-l-rose-500' },
  workflow:            { name: '工作流程图',    icon: '🔄', badge: 'text-cyan-700 bg-cyan-50',      border: 'border-l-cyan-500' },
  quiz:                { name: '自测题',        icon: '✍️', badge: 'text-orange-700 bg-orange-50',  border: 'border-l-orange-500' },
  mindmap:             { name: '思维导图',      icon: '🧠', badge: 'text-lime-700 bg-lime-50',      border: 'border-l-lime-500' },
  checklist:           { name: '行动清单',      icon: '✅', badge: 'text-green-700 bg-green-50',    border: 'border-l-green-500' },
  flashcard:           { name: '记忆卡片',      icon: '🃏', badge: 'text-yellow-700 bg-yellow-50',  border: 'border-l-yellow-500' },
  script:              { name: '视频脚本',      icon: '🎬', badge: 'text-red-700 bg-red-50',        border: 'border-l-red-500' },
  product_intro:       { name: '产品文案',      icon: '📢', badge: 'text-amber-700 bg-amber-50',    border: 'border-l-amber-500' },
  llm_skill:           { name: 'LLM Skill',     icon: '🧩', badge: 'text-indigo-700 bg-indigo-50',  border: 'border-l-indigo-500' },
}

// 🔍 [语法] 合并后端类型定义与本地兜底
// 🔍 [作用] 后端新增类型无需改前端即可正确显示；返回 {name,icon,badge,border}
export function resolveType(type, typeMap = {}) {
  const api = typeMap[type] || {}
  const meta = TYPE_META[type] || {}
  return {
    name: api.name || meta.name || type,
    icon: api.icon || meta.icon || '📦',
    badge: meta.badge || 'text-gray-700 bg-gray-50',
    border: meta.border || 'border-l-gray-300',
  }
}

// 🔍 [语法] 钩子：从后端拉取产品类型映射
// 🔍 [作用] 组件内 const typeMap = useTypeMap()，传给 resolveType 即可
export function useTypeMap() {
  const [typeMap, setTypeMap] = useState({})
  useEffect(() => {
    api.ai.productTypes()
      .then((r) => setTypeMap(r || {}))
      .catch(() => {})
  }, [])
  return typeMap
}
