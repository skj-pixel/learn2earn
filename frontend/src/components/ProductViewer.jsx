// 🔍 [语法] React Hooks
import { useEffect, useRef, useState } from 'react'
// 🔍 [语法] react-router-dom
import { useParams, useNavigate } from 'react-router-dom'
// 🔍 [语法] react-markdown
// 🔍 [作用] 渲染 Markdown 内容
// 🔍 [语法] marked + DOMPurify
// 🔍 [作用] 导出 PDF：Markdown→HTML（消毒后）→打印窗口另存为 PDF
// 🔍 [语法] 全局 store
import useStore from '../store/useStore'
// 🔍 [语法] toast
import toast from 'react-hot-toast'
// 🔍 [语法] API
import { api, getAccessToken } from '../utils/api'
import { resolveProductImageMarkers, restoreProductImageMarkers } from '../utils/productImageMarkers'
// 🔍 [语法] 富文本编辑器（与笔记编辑共用同一个 BlockNote 编辑器）
// 🔍 [作用] 产品编辑也走 BlockNote 框架，UI 与笔记保持一致
import RichTextEditor from './RichTextEditor'
import MathMarkdown from './MathMarkdown'
import { renderMarkdownForPrint } from '../utils/mathRendering'

// 🔍 [语法] 共享产品类型元数据（名称/图标/配色集中维护，前后端统一）
import { resolveType, useTypeMap } from '../utils/typeMeta'

// 🔍 [语法] default export
// 🔍 [作用] 产品详情查看 + 编辑 + 导出 + 重新生成
export default function ProductViewer() {
  const { productId } = useParams()
  const navigate = useNavigate()
  const typeMap = useTypeMap()
  // 🔍 [作用] 2026-08 fix/26：重新生成走 store.enqueueTask，让"生成任务"页立即可见
  const { products, fetchProducts, updateProduct, enqueueTask, fetchTasks } = useStore()

  // 🔍 [语法] 状态
  // 🔍 [作用] 产品数据 + 编辑模式 + 编辑内容 + loading
  const [product, setProduct] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [editPlain, setEditPlain] = useState('')
  const [loading, setLoading] = useState(true)
  const [sourceAssets, setSourceAssets] = useState([])
  const editorRef = useRef(null)

  // 🔍 [语法] useEffect 依赖
  // 🔍 [作用] 监听 productId 和 products 变化
  useEffect(() => {
    findProduct()
  }, [productId, products])

  // 🔍 [语法] async 查找产品
  // 🔍 [作用] 先从 store 找，找不到再请求 API
  const findProduct = async () => {
    let p = products.find((p) => p.id === Number(productId))
    if (!p) {
      const allProducts = await fetchProducts()
      p = allProducts?.find((p) => p.id === Number(productId))
    }
    setProduct(p || null)
    if (p) {
      setEditContent(p.content)
      api.products.sourceAssets(p.id).then(setSourceAssets).catch(() => setSourceAssets([]))
    }
    setLoading(false)
  }

  // 🔍 [语法] 导出 PDF（打印方式）
  // 🔍 [作用] Markdown→HTML（消毒后）→打印窗口另存为 PDF
  const handleExportPdf = () => {
    if (!product || !product.content) {
      toast.error('暂无内容可导出')
      return
    }
    const bodyHtml = renderMarkdownForPrint(product.content)
    const title = (product.title || 'product').replace(/</g, '&lt;')
    const win = window.open('', '_blank')
    if (!win) {
      toast.error('浏览器拦截了弹窗，请允许弹窗后重试')
      return
    }
    win.document.write(`<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>${title}</title>
<style>
  body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; margin: 40px; color: #1f2937; line-height: 1.7; }
  h1 { font-size: 22px; border-bottom: 2px solid #f59e0b; padding-bottom: 8px; }
  h2 { font-size: 18px; margin-top: 24px; } h3 { font-size: 15px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; page-break-inside: auto; }
  tr { page-break-inside: avoid; }
  th, td { border: 1px solid #9ca3af; padding: 6px 10px; font-size: 12px; text-align: left; }
  th { background: #f3f4f6; }
  pre { background: #f6f8fa; border: 1px solid #e5e7eb; border-radius: 6px; padding: 10px; font-size: 12px; white-space: pre-wrap; }
  code { font-family: Consolas, monospace; font-size: 12px; }
  blockquote { border-left: 3px solid #d1d5db; margin: 8px 0; padding: 4px 12px; color: #6b7280; }
  .meta { color: #6b7280; font-size: 12px; margin-bottom: 16px; }
</style></head><body>
<h1>${title}</h1>
<div class="meta">Learn2Earn 知识付费产品 · 导出时间 ${new Date().toLocaleString('zh-CN')}</div>
${bodyHtml}
<script>window.onload = function () { setTimeout(function () { window.print() }, 300) }<\/script>
</body></html>`)
    win.document.close()
    toast.success('已打开打印窗口，选择"另存为 PDF"即可')
  }

  // 🔍 [语法] 重新生成
  // 🔍 [作用] 用 LLM 覆盖内容
  const handleRegenerate = async () => {
    // 🔍 [作用] 2026-08 fix/26：note_id 是后端任务创建必填字段，独立产品（note_id=null）要走"产品生成中心"重新选择笔记生成
    if (!product.note_id) {
      toast.error('该产品未关联笔记，请前往「产品生成中心」选择笔记重新生成')
      return
    }
    try {
      const task = await enqueueTask({ note_id: product.note_id, product_id: product.id, product_types: [product.product_type] })
      // 🔍 [作用] 主动预热 tasks 列表，避免 navigate 后首次渲染为空
      fetchTasks().catch(() => {})
      toast.success(`已提交后台任务 #${task.id}，可继续处理其他内容`)
      navigate('/tasks')
    } catch (e) {
      toast.error('重新生成失败: ' + e.message)
    }
  }

  // 🔍 [语法] 发布
  const handlePublish = async () => {
    try {
      await updateProduct(Number(productId), { status: 'published' })
      toast.success('产品已发布！🎉')
      setProduct({ ...product, status: 'published' })
    } catch (e) {
      toast.error(e.message)
    }
  }

  // 🔍 [语法] 保存编辑（BlockNote 编辑器 → HTML → 后端）
  // 🔍 [作用] 与笔记编辑器共用同一套编辑体验：截图粘贴、块级菜单、Markdown 工具栏等
  const handleSaveEdit = async () => {
    // 🔍 [语法] 优先从 editor 实例实时拿最新内容（避免 onChange 异步未触发）
    let latestMarkdown = editContent
    if (editorRef.current?.document) {
      try {
        latestMarkdown = await editorRef.current.blocksToMarkdownLossy(editorRef.current.document)
      } catch (e) {
        // 忽略，回退到 state
      }
    }
    try {
      latestMarkdown = restoreProductImageMarkers(latestMarkdown, sourceAssets)
      const updated = await updateProduct(Number(productId), { content: latestMarkdown })
      setProduct({ ...product, ...updated })
      setEditing(false)
      toast.success('内容已更新')
    } catch (e) {
      toast.error(e.message)
    }
  }

  // 🔍 [语法] 复制到剪贴板
  const handleCopy = () => {
    navigator.clipboard.writeText(product.content)
    toast.success('已复制全部内容')
  }

  if (loading) {
    return <div className="p-6 text-center text-gray-400 pt-20">加载中...</div>
  }

  if (!product) {
    return (
      <div className="p-6 text-center pt-20">
        <div className="text-6xl mb-4">🔍</div>
        <p className="text-gray-500 mb-4">产品不存在</p>
        <button onClick={() => navigate('/products')} className="text-primary-600">返回产品库</button>
      </div>
    )
  }

  const info = resolveType(product.product_type, typeMap)
  const displayContent = resolveProductImageMarkers(product.content || '', sourceAssets, getAccessToken())

  return (
    <div className="h-full flex">
      {/* ========== 内容查看器 ========== */}
      <div className="flex-1 flex flex-col min-w-0 h-full">
        {/* ========== 顶部工具栏 ========== */}
        <div className="p-4 border-b border-gray-100 bg-white shrink-0">
          {/* 第 1 行：标题 + 操作 */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600 text-sm">← 返回</button>
              <span className="text-xl">{info.icon || '📦'}</span>
              <div>
                <h1 className="text-lg font-bold text-gray-800">{product.title}</h1>
                <p className="text-xs text-gray-400">{info.name || product.product_type}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={handleRegenerate}
                className="bg-amber-500 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-colors">
                🔄 后台重新生成
              </button>
              {product.status === 'draft' && (
                <button onClick={handlePublish} className="bg-emerald-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-emerald-700 transition-colors">
                  ✅ 标记为已发布
                </button>
              )}
              <span className={`text-xs px-2 py-1 rounded-full ${product.status === 'published' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>
                {product.status === 'published' ? '已发布' : '草稿'}
              </span>
            </div>
          </div>
          {/* 第 2 行：复制 + 导出 + 编辑 */}
          <div className="flex items-center gap-2">
            <button onClick={handleCopy} className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-200 transition-colors">📋 复制内容</button>
            <button onClick={handleExportPdf} className="text-xs bg-gray-100 text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-200 transition-colors">🖨️ 导出 PDF</button>
            {!editing && (
              <button onClick={() => setEditing(true)} className="text-xs bg-primary-50 text-primary-600 px-3 py-1.5 rounded-lg hover:bg-primary-100 transition-colors">✏️ 编辑</button>
            )}
            <div className="flex-1" />
            {product.price_suggestion > 0 && (
              <span className="text-sm font-semibold text-amber-600 bg-amber-50 px-3 py-1 rounded-lg">💰 建议售价 ¥{product.price_suggestion}</span>
            )}
          </div>
          {/* 推荐平台标签 */}
          {product.platform_suggestion?.length > 0 && (
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              <span className="text-[10px] text-gray-400">推荐平台：</span>
              {product.platform_suggestion.map((p, i) => (
                <span key={i} className="text-[10px] bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">{p}</span>
              ))}
            </div>
          )}
        </div>

        {/* ========== 内容区 ========== */}
        <div className="flex-1 overflow-auto p-6 md:p-10">
          {editing ? (
            <div className="h-full flex flex-col max-w-4xl mx-auto">
              <div className="note-document flex-1 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-3">
                  <strong className="text-sm text-gray-700">编辑产品内容</strong>
                  <span className="text-xs text-gray-400">{editPlain.length} 字</span>
                </div>
                <div className="flex-1 min-h-0 overflow-auto">
                  <RichTextEditor
                    value={resolveProductImageMarkers(editContent, sourceAssets, getAccessToken())}
                    valueFormat="markdown"
                    outputFormat="markdown"
                    onChange={(markdown, plain) => {
                      setEditContent(markdown)
                      setEditPlain(plain || '')
                    }}
                    editorRef={editorRef}
                  />
                </div>
              </div>
              <div className="flex gap-2 mt-3 justify-end">
                <button onClick={() => { setEditing(false); setEditContent(product.content) }} className="px-4 py-2 rounded-lg text-sm text-gray-600 hover:bg-gray-100">
                  取消
                </button>
                <button onClick={handleSaveEdit} className="px-4 py-2 rounded-lg text-sm bg-primary-600 text-white hover:bg-primary-700">
                  保存
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-gray-100 p-6 md:p-10 shadow-sm">
              <div className="markdown-body max-w-3xl">
                <MathMarkdown>{displayContent || '*暂无内容*'}</MathMarkdown>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
