// 🔍 [语法] React Hooks
// 🔍 [作用] useEffect 副作用；useRef 保存 editor 实例；useState 本地状态
import { useEffect, useRef, useState } from 'react'

// 🔍 [语法] React Router 6 hooks
// 🔍 [作用] navigate 跳转；useParams 取路由参数
import { useNavigate, useParams } from 'react-router-dom'

// 🔍 [语法] lucide-react 图标
// 🔍 [作用] 返回箭头 / 保存 / 文件上传 / 机器人助手
import { ArrowLeft, Bot, FileUp, Save } from 'lucide-react'

// 🔍 [语法] react-hot-toast
// 🔍 [作用] 全局消息提示
import toast from 'react-hot-toast'

// 🔍 [语法] mammoth 浏览器端 Word 解析库
// 🔍 [作用] 把 .docx 转成 HTML（不依赖后端；前端纯 JS 实现）
import mammoth from 'mammoth/mammoth.browser'

// 🔍 [语法] 项目内模块
// 🔍 [作用] Zustand store + API 封装
import useStore from '../store/useStore'
import { api } from '../utils/api'

// 🔍 [语法] BlockNote 富文本编辑器（替代旧 TipTap 实现）
// 🔍 [特性] 开箱支持截图粘贴 + slash 菜单 + 块级拖拽
import RichTextEditor from './RichTextEditor'

// 🔍 [语法] BlockNote 库
// 🔍 [作用] 用 tryParseHTMLToBlocks 把 mammoth 输出的 HTML 灌入编辑器
import '@blocknote/core/fonts/inter.css'
import '@blocknote/mantine/style.css'

// 🔍 [语法] 学习阶段常量
// 🔍 [作用] 4 阶段单选选项（与后端 learning_stage 字段对齐）
const STAGES = [
  { value: 'stage1', label: '筑基期', desc: '建立基础概念与最小实践能力' },
  { value: 'stage2', label: '专精期', desc: '围绕一个方向深入训练并形成稳定技能' },
  { value: 'stage3', label: '融合期', desc: '把多项技能组合成完整产品或解决方案' },
  { value: 'stage4', label: '创业期', desc: '形成品牌、产品矩阵与可持续商业闭环' },
]

// 🔍 [语法] 默认导出函数组件
// 🔍 [作用] 笔记编辑页面：新建 / 编辑笔记，含标题 / 元数据 / 富文本正文 / 右侧助手面板
export default function NoteEditor() {
  // 🔍 [语法] useParams 取 URL 参数
  // 🔍 [作用] subjectId 外键；noteId 可选（新建时为 undefined）
  const { subjectId, noteId } = useParams()
  // 🔍 [语法] 编程式导航
  // 🔍 [作用] 保存后跳转 / 返回列表
  const navigate = useNavigate()

  // 🔍 [语法] ref 保存文件选择 input
  // 🔍 [作用] 触发隐藏的 .docx 文件选择
  const wordInput = useRef(null)

  // 🔍 [语法] ref 保存 BlockNote editor 实例
  // 🔍 [作用] 保存时直接 await editor.blocksToFullHTML(editor.document) 拿最新内容，绕过 React onChange 异步竞态（这是旧版"无法保存"根因）
  const editorRef = useRef(null)

  // 🔍 [语法] Zustand 取科目列表 + 笔记 action
  // 🔍 [作用] 注入科目面包屑 + 保存/更新/列表刷新
  const { subjects, createNote, updateNote, fetchNotes, fetchSubjects } = useStore()
  const subject = subjects.find((item) => item.id === Number(subjectId))

  // 🔍 [语法] 根据是否有 noteId 判断新建 / 编辑
  const isNew = !noteId

  // 🔍 [语法] 本地 state
  // 🔍 [作用] 表单字段 + 操作状态
  const [title, setTitle] = useState('')
  const [tags, setTags] = useState('')
  const [stage, setStage] = useState('stage1')
  const [minutes, setMinutes] = useState(30)
  const [saving, setSaving] = useState(false)
  const [importing, setImporting] = useState(false)
  const [pendingWordImages, setPendingWordImages] = useState([])
  // 🔍 [语法] 加载状态（异步导入 Word 时显示 loading 占位）
  const [editorLoading, setEditorLoading] = useState(false)
  // 🔍 [语法] MemoryBear 预览状态
  // 🔍 [作用] 编辑既有笔记时，拉取五层记忆上下文 + 场景路由权重
  const [mbPreview, setMbPreview] = useState(null)
  const [mbLoading, setMbLoading] = useState(false)

  // 🔍 [语法] 派生：正文字符数（从 editor ref 直接读，避免 React state 滞后）

  // 🔍 [副作用] 加载已有笔记（编辑模式）
  useEffect(() => {
    if (!noteId) return
    api.notes.get(noteId).then((note) => {
      setTitle(note.title || '')
      setTags((note.tags || []).join(', '))
      setStage(note.learning_stage || 'stage1')
      setMinutes(note.estimated_minutes || 30)
      // 🔍 [语法] 把 HTML 灌入 BlockNote 编辑器
      // [机制] RichTextEditor 内部 useEffect 检测到 value 非空，会调 tryParseHTMLToBlocks + replaceBlocks
      setEditorLoading(true)
      setHtmlSeed(note.content || '')
      setTimeout(() => setEditorLoading(false), 200)
    }).catch((error) => toast.error(error.message))
  }, [noteId])

  // 🔍 [副作用] MemoryBear 预览：编辑既有笔记时拉取五层记忆上下文
  useEffect(() => {
    if (!noteId) { setMbPreview(null); return }
    let cancelled = false
    setMbLoading(true)
    api.memorybear.preview(noteId).then((data) => {
      if (!cancelled) setMbPreview(data)
    }).catch(() => {
      if (!cancelled) setMbPreview(null)
    }).finally(() => { if (!cancelled) setMbLoading(false) })
    return () => { cancelled = true }
  }, [noteId])

  // 🔍 [语法] 单次种子值
  // 🔍 [作用] 编辑模式下把已有 HTML 作为初始 value 传给 RichTextEditor
  const [htmlSeed, setHtmlSeed] = useState('')

  /**
   * 🔍 [语法] async 保存函数（核心修复点）
   * 🔍 [修复] 不再依赖 onChange 同步的 plainText state，而是从 BlockNote editor 实例直接拿最新文档
   * 🔍 [原因] 旧实现里 RichTextEditor 的 onUpdate 只在文档变更时触发；如果用户编辑后没触发（罕见的 React 边界场景），
   *            或者 onChange 还没写回父组件 state 时用户就点保存，会出现"明明有内容但 plainText 为空"的假失败。
   */
  const save = async () => {
    if (!title.trim()) return toast.error('请填写标题')
    // 🔍 [修复] 直接从 editor ref 拿 HTML + plainText，绕过 React state 竞态
    const ed = editorRef.current
    if (!ed) return toast.error('编辑器尚未就绪，请稍候')
    const liveHtml = await ed.blocksToFullHTML(ed.document)
    const livePlain = blocksToPlainTextOfDocument(ed.document)
    if (!livePlain.trim()) return toast.error('请填写正文')
    setSaving(true)
    try {
      // 🔍 [语法] 清洗 HTML：去掉 BlockNote 自带的 bn- 类名 + 内嵌 base64 图片外的额外属性
      // [说明] BlockNote 输出的 HTML 已经相对干净；不再走 DOMPurify（避免误删合法的 data 属性）
      const payload = {
        title: title.trim(),
        content: liveHtml,
        raw_content: livePlain,
        subject_id: Number(subjectId),
        tags: tags.split(',').map((v) => v.trim()).filter(Boolean),
        learning_stage: stage,
        estimated_minutes: Number(minutes),
      }
      const note = isNew ? await createNote(payload) : await updateNote(Number(noteId), payload)
      if (pendingWordImages.length) {
        await Promise.all(pendingWordImages.map((item) => api.notes.uploadImage(note.id, item.file)))
        setPendingWordImages([])
      }
      toast.success('笔记已保存')
      await fetchNotes({ subject_id: subjectId })
      await fetchSubjects()
      if (isNew) navigate(`/subjects/${subjectId}/notes/${note.id}`, { replace: true })
      return note
    } catch (error) {
      toast.error(`保存失败：${error.message}`)
    } finally {
      setSaving(false)
    }
  }

  /**
   * 🔍 [语法] async 导入 Word
   * 🔍 [改动] 完全前端化：mammoth 在浏览器把 .docx 转成 HTML，再用 tryParseHTMLToBlocks 灌入 BlockNote
   * 🔍 [好处] 不再依赖后端 /api/notes/import-docx 端点；离线也能用；图片以 base64 内嵌（演示场景够用）
   */
  const importWord = async (file) => {
    if (!file) return
    setImporting(true)
    try {
      // 🔍 [语法] mammoth.convertToHtml 返回 { value: html, messages }
      // [陷阱] mammoth.browser.js 入口是 mammoth/mammoth.browser（已在 import 行固定）
      const arrayBuffer = await file.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      const html = result.value || ''
      setPendingWordImages(extractEmbeddedImages(html))
      // 🔍 [灌入 BlockNote 编辑器]
      const ed = editorRef.current
      if (!ed) throw new Error('编辑器尚未就绪，请稍候')
      const blocks = await ed.tryParseHTMLToBlocks(html)
      ed.replaceBlocks(ed.document, blocks)
      toast.success(`Word 导入完成：识别 ${result.messages?.length || 0} 条提示`)
    } catch (error) {
      toast.error(`Word 导入失败：${error.message}`)
    } finally {
      setImporting(false)
      if (wordInput.current) wordInput.current.value = ''
    }
  }

  // 🔍 [回调] BlockNote 文档变化时同步 plainText 到顶部"正文字符"统计（保存时仍以 editorRef 为准）
  const handleEditorChange = (nextHtml, nextPlain) => {
  }

  return (
    <div className="note-workspace">
      <header className="note-topbar">
        <button className="icon-command" title="返回笔记列表" onClick={() => navigate(`/subjects/${subjectId}/notes`)}><ArrowLeft size={19} /></button>
        <div className="note-breadcrumb"><span>{subject?.icon || '📚'}</span><strong>{subject?.name || '学习笔记'}</strong><span>/</span><span>{isNew ? '新建笔记' : '编辑'}</span></div>
        <div className="note-actions">
          <button className="secondary-command" onClick={() => wordInput.current?.click()} disabled={importing}><FileUp size={17} />{importing ? '正在解析…' : '导入 Word'}</button>
          <input ref={wordInput} hidden type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={(event) => importWord(event.target.files?.[0])} />
          <button className="primary-command" onClick={save} disabled={saving}><Save size={17} />{saving ? '保存中…' : '保存'}</button>
        </div>
      </header>

      <main className="note-document-wrap">
        <article className="note-document">
          <input className="note-title-input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="无标题笔记" />
          <div className="note-meta-grid">
            <label><span>学习阶段</span><select value={stage} onChange={(e) => setStage(e.target.value)}>{STAGES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select><small>{STAGES.find((item) => item.value === stage)?.desc}</small></label>
            <label><span>预计学习</span><div className="minute-input"><input type="number" min="1" value={minutes} onChange={(e) => setMinutes(e.target.value)} /><em>分钟</em></div></label>
            <label><span>标签</span><input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="用逗号分隔" /></label>
          </div>
          {editorLoading ? (
            <div className="editor-loading-placeholder">编辑器加载中…</div>
          ) : (
            <RichTextEditor value={htmlSeed} onChange={handleEditorChange} editorRef={editorRef} />
          )}
        </article>
        <aside className="note-context-panel">
          <div className="context-heading"><Bot size={18} /><strong>笔记助手</strong></div>
          <p>Word 中的段落、标题、表格和插图会按原顺序导入。支持截图粘贴 (Ctrl+V) 自动插入图片。</p>
          <div className="context-stat"><span>学习阶段</span><strong>{STAGES.find((item) => item.value === stage)?.label}</strong></div>
          <button className="generate-link" disabled={isNew} onClick={() => navigate(`/notes/${noteId}/generate`)}>进入产品生成中心</button>
          <div className="mb-panel">
            <div className="context-heading"><Bot size={18} /><strong>知识增强状态</strong></div>
            {isNew ? (
              <p className="mb-hint">保存后显示 Memory Bear 五层记忆状态和 RAG 路由建议。</p>
            ) : mbLoading ? (
              <p className="mb-hint">正在加载记忆上下文…</p>
            ) : mbPreview ? (
              <>
                <div className="mb-capabilities">
                  <span><i className="mb-status-dot" />Memory Bear 已启用</span>
                  <span>RAG 按需检索</span>
                </div>
                <div className="mb-scene">
                  <span>路由建议</span>
                  <strong>Memory Bear {Math.round((mbPreview.meta?.scene_router?.memorybear_weight ?? 0) * 100)}%</strong>
                  <span>· RAG {Math.round((mbPreview.meta?.scene_router?.rag_weight ?? 0) * 100)}%</span>
                </div>
                {mbPreview.meta?.scene_router?.reason && <p className="mb-hint">{mbPreview.meta.scene_router.reason}</p>}
                <div className="mb-layers">
                  {['perception', 'working', 'episodic', 'explicit', 'implicit'].map((k) => {
                    const n = mbPreview.meta?.layers?.[k] ?? 0
                    return (
                      <span key={k} className="mb-chip">{layerLabel(k)} ×{n}</span>
                    )
                  })}
                </div>
              </>
            ) : (
              <p className="mb-hint">暂无可提取的记忆上下文。</p>
            )}
          </div>
        </aside>
      </main>
    </div>
  )
}

function extractEmbeddedImages(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html')
  return Array.from(doc.querySelectorAll('img[src^="data:image/"]')).map((img, index) => {
    const [header, encoded] = img.src.split(',', 2)
    const mediaType = header.match(/^data:([^;]+)/)?.[1] || 'image/png'
    const bytes = Uint8Array.from(atob(encoded || ''), (char) => char.charCodeAt(0))
    const extension = mediaType.split('/')[1]?.replace('jpeg', 'jpg') || 'png'
    return { file: new File([bytes], `word-image-${index + 1}.${extension}`, { type: mediaType }) }
  })
}

/**
 * 🔍 [说明] 记忆层中文标签
 * 🔍 [作用] 把英文 layer key 映射成界面可读中文
 */
function layerLabel(key) {
  const map = {
    working: '工作记忆',
    episodic: '情景记忆',
    explicit: '显性记忆',
    implicit: '隐性记忆',
    perception: '感知记忆',
  }
  return map[key] || key
}

/**
 * 🔍 [说明] BlockNote document → 纯文本
 * 🔍 [本地副本] 与 RichTextEditor.jsx 中的 blocksToPlainText 保持一致；此处用于 save() 直接读 editor.document
 */
function blocksToPlainTextOfDocument(blocks) {
  if (!Array.isArray(blocks)) return ''
  const parts = []
  for (const block of blocks) {
    if (Array.isArray(block.content)) {
      parts.push(block.content.map((inline) => inline.text || '').join(''))
    } else if (typeof block.content === 'string') {
      parts.push(block.content)
    } else if (block.type === 'image' && block.props?.url) {
      parts.push(`[图片: ${block.props.url}]`)
    }
    if (Array.isArray(block.children) && block.children.length > 0) {
      parts.push(blocksToPlainTextOfDocument(block.children))
    }
  }
  return parts.filter(Boolean).join('\n\n')
}
