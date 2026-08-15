// 🔍 [语法] @blocknote React 集成
// 🔍 [作用] BlockNote 块级富文本编辑器（开源、类思源风格、开箱支持截图粘贴 + slash 菜单）
import { useCreateBlockNote } from '@blocknote/react'

// 🔍 [语法] @blocknote mantine 视图
// 🔍 [作用] BlockNote 的 UI 视图（toolbar + slash menu + drag handle）
import { BlockNoteView } from '@blocknote/mantine'

// 🔍 [语法] 全局样式导入（必须）
// 🔍 [作用] BlockNote 字体 + Mantine 主题样式
import '@blocknote/core/fonts/inter.css'
import '@blocknote/mantine/style.css'

// 🔍 [语法] React Hooks
// 🔍 [作用] useEffect 监听文档变化；useRef 保存 editor 实例供父组件保存时直接读取
import { useEffect, useRef } from 'react'
import { repairFencedCodeBlocks } from '../utils/editorContent'

/**
 * 🔍 [作用] 把 BlockNote blocks 转成纯文本（用于 raw_content 字段，供 AI 生成器使用）
 * 🔍 [说明] BlockNote 的 block 结构是嵌套的，这里扁平抽取所有 inline content 的 text 字段
 */
function blocksToPlainText(blocks) {
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
    // 🔍 [递归] 处理嵌套块（list item、table cell 等）
    if (Array.isArray(block.children) && block.children.length > 0) {
      parts.push(blocksToPlainText(block.children))
    }
  }
  return parts.filter(Boolean).join('\n\n')
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(reader.error || new Error('图片读取失败'))
    reader.readAsDataURL(file)
  })
}

function resolveInputFormat(value, requestedFormat) {
  if (requestedFormat === 'html' || requestedFormat === 'markdown') return requestedFormat
  return /<\/?[a-z][\s\S]*>/i.test((value || '').trim()) ? 'html' : 'markdown'
}

/**
 * 🔍 [组件] BlockNote 富文本编辑器（替代旧 TipTap StarterKit 实现）
 * 🔍 [特性]
 *   - 块级编辑、slash 菜单（输入 / 唤起）、拖拽手柄
 *   - 开箱支持截图粘贴（剪贴板图片自动作为 image block 插入）
 *   - 支持 markdown 粘贴、表格、代码块、checklist
 *   - 通过 editorRef 把 BlockNote editor 实例暴露给父组件，保存时直接读取最新文档，避免 React state 异步导致的"无法保存"问题
 */
export default function RichTextEditor({ value, onChange, editorRef, valueFormat = 'auto', outputFormat = 'html' }) {
  // 🔍 [语法] useRef 容器
  // 🔍 [作用] 让父组件能拿到 editor 实例（保存按钮直接 await editor.blocksToFullHTML(editor.document)）
  const localRef = useRef(null)
  const editor = useCreateBlockNote({
    // 🔍 [空初始内容]
    // [说明] 新建笔记场景；如果有 HTML 内容，组件挂载后通过 tryParseHTMLToBlocks 替换
    initialContent: [{ type: 'paragraph', content: [] }],
    uploadFile: fileToDataUrl,
  })

  // 🔍 [副作用] 把 editor 实例写到 ref（同时兼容传进来的 editorRef）
  useEffect(() => {
    localRef.current = editor
    if (editorRef) editorRef.current = editor
  }, [editor, editorRef])

  // 🔍 [副作用] 监听 BlockNote 文档变更（任意 transaction 后触发）
  // 🔍 [陷阱] 必须返回 cleanup，否则 React strict mode 双调用会重复注册
  useEffect(() => {
    const handler = async () => {
      const content = outputFormat === 'markdown'
        ? editor.blocksToMarkdownLossy(editor.document)
        : await editor.blocksToFullHTML(editor.document)
      const plain = blocksToPlainText(editor.document)
      if (typeof onChange === 'function') onChange(content, plain)
    }
    const unsubscribe = editor.onChange(handler)
    return () => {
      if (typeof unsubscribe === 'function') unsubscribe()
    }
  }, [editor, onChange, outputFormat])

  // 🔍 [副作用] 把外部 HTML 灌入编辑器（仅在 value 首次变化时执行一次，避免覆盖用户输入）
  const loadedRef = useRef(false)
  useEffect(() => {
    if (loadedRef.current) return
    if (!value) {
      loadedRef.current = true
      return
    }
    loadedRef.current = true
    ;(async () => {
      try {
        const format = resolveInputFormat(value, valueFormat)
        const parsedBlocks = format === 'markdown'
          ? editor.tryParseMarkdownToBlocks(value)
          : await editor.tryParseHTMLToBlocks(value)
        const blocks = repairFencedCodeBlocks(parsedBlocks)
        editor.replaceBlocks(editor.document, blocks)
      } catch (e) {
        console.warn('[RichTextEditor] HTML 反向解析失败:', e)
      }
    })()
  }, [value, editor, valueFormat])

  return (
    <div className="editor-shell">
      {/* 🔍 [语法] BlockNote 视图
          [作用] 完整 UI：toolbar / slash menu / drag handle / block menu
          [自动行为] 截图粘贴 (Ctrl+V 剪贴板图片) → 自动创建 image block；上传走 base64 内嵌 */}
      <BlockNoteView editor={editor} theme="light" />
    </div>
  )
}
