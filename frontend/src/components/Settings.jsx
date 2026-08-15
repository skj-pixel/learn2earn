// 🔍 [语法] React Hooks
import { useState, useEffect } from 'react'
// 🔍 [语法] react-router-dom
import { useNavigate } from 'react-router-dom'
// 🔍 [语法] toast
import toast from 'react-hot-toast'
import { api } from '../utils/api'

// 🔍 [语法] 模块级常量
// 🔍 [作用] 6 家提供商预设（选择即自动填充）
const PROVIDER_INFO = {
  openrouter:  { name: 'OpenRouter', desc: '聚合200+模型', icon: '🌐', defaultModel: 'openai/gpt-4o', baseUrl: 'https://openrouter.ai/api/v1', getKeyUrl: 'https://openrouter.ai/keys',
    models: ['openai/gpt-4o', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.0-flash', 'deepseek/deepseek-r1'] },
  modelscope:  { name: 'ModelScope魔搭', desc: '阿里达摩院·通义千问', icon: '☁️', defaultModel: 'qwen-plus', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', getKeyUrl: 'https://bailian.console.aliyun.com/',
    models: ['qwen-plus', 'qwen-max', 'qwen-turbo', 'deepseek-v3'] },
  siliconflow: { name: '硅基流动', desc: 'DeepSeek/Qwen/GLM，注册送额度', icon: '⚡', defaultModel: 'deepseek-ai/DeepSeek-V3', baseUrl: 'https://api.siliconflow.cn/v1', getKeyUrl: 'https://cloud.siliconflow.cn/account/ak',
    models: ['deepseek-ai/DeepSeek-V3', 'deepseek-ai/DeepSeek-R1', 'Qwen/Qwen2.5-72B-Instruct', 'Pro/zai-org/GLM-4'] },
  minimax:     { name: 'MiniMax', desc: '国产大模型·abab6.5s', icon: '🧠', defaultModel: 'abab6.5s-chat', baseUrl: 'https://api.minimax.chat/v1', getKeyUrl: 'https://platform.minimaxi.com/user-center/basic-information/interface-key',
    models: ['abab6.5s-chat', 'abab5.5-chat'] },
  teamorouter: { name: 'TeamoRouter', desc: '多模型聚合路由', icon: '🔀', defaultModel: 'gpt-4o', baseUrl: 'https://api.teamorouter.com/v1', getKeyUrl: 'https://teamorouter.com/dashboard',
    models: ['gpt-4o', 'claude-3.5-sonnet', 'gemini-2.0-flash'] },
  custom:      { name: '自定义API', desc: 'OpenAI兼容格式·Ollama等', icon: '🔧', defaultModel: 'gpt-4o', baseUrl: 'https://api.openai.com/v1', getKeyUrl: '',
    models: ['gpt-4o', 'gpt-4-turbo', 'claude-3-opus'] },
}

const MAX_CONFIGS = 10  // 最大配置数

// 🔍 [语法] default export
// 🔍 [作用] LLM 配置管理页（CRUD + 测试连接）
export default function Settings() {
  const navigate = useNavigate()

  // 🔍 [语法] 6 个状态
  // 🔍 [作用] 配置数据 + 编辑模式 + 测试状态
  const [configs, setConfigs] = useState([])
  const [activeConfig, setActiveConfig] = useState('')
  const [loading, setLoading] = useState(true)

  // 编辑表单
  const [showEdit, setShowEdit] = useState(false)
  const [editingName, setEditingName] = useState(null)
  const [form, setForm] = useState({ name: '', provider: 'siliconflow', api_key: '', base_url: '', model: '', max_tokens: 4096, temperature: 0.7, is_enabled: false })

  // 测试连接
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState(null)

  // 保存
  const [saving, setSaving] = useState(false)

  // 🔍 [语法] 本地演示模式：从环境变量导入 Key
  const [localMode, setLocalMode] = useState(false)
  const [envVars, setEnvVars] = useState([])
  const [envImportEnabled, setEnvImportEnabled] = useState(false)

  // 🔍 [语法] useEffect 空依赖
  useEffect(() => { loadData() }, [])

  // 🔍 [语法] async 加载
  // 🔍 [作用] fetch /api/config/llms
  const loadData = async () => {
    setLoading(true)
    try {
      const data = await api.config.llms()
      setConfigs(data.configs || [])
      setActiveConfig(data.active_config || '')
      // 🔍 [语法] 独立 try，失败不影响主列表
      // 🔍 [作用] 拉取本地演示模式的"从环境变量导入"可用变量名
      try {
        const meta = await api.config.envImportMeta()
        setLocalMode(!!meta.local_mode)
        setEnvVars(meta.env_vars || [])
      } catch (e) { /* 非本地模式忽略 */ }
    } catch (e) { toast.error('加载配置失败') }
    finally { setLoading(false) }
  }

  // 🔍 [语法] 打开新建窗口
  // 🔍 [作用] 用硅基流动默认值
  const openNew = () => {
    const info = PROVIDER_INFO.siliconflow
    setForm({ name: '', provider: 'siliconflow', api_key: '', api_key_env: '', base_url: info.baseUrl, model: info.defaultModel, max_tokens: 4096, temperature: 0.7, is_enabled: false })
    setEnvImportEnabled(false)
    setEditingName(null)
    setShowEdit(true)
    setTestResult(null)
  }

  // 🔍 [语法] 打开编辑窗口
  const openEdit = (cfg) => {
    setForm({
      name: cfg.name,
      provider: cfg.provider || 'custom',
      api_key: '',  // 🔍 [语法] 清空 Key
      api_key_env: cfg.api_key_env || '',
      base_url: cfg.base_url || '',
      model: cfg.model || '',
      max_tokens: cfg.max_tokens || 4096,
      temperature: cfg.temperature ?? 0.7,
      is_enabled: cfg.is_enabled || false,
    })
    setEditingName(cfg.name)
    setEnvImportEnabled(!!cfg.api_key_env)
    setShowEdit(true)
    setTestResult(null)
  }

  // 🔍 [语法] 切换提供商
  // 🔍 [作用] 自动填充 base_url 和 model
  const handleProviderChange = (prov) => {
    const info = PROVIDER_INFO[prov]
    setForm({ ...form, provider: prov, base_url: info.baseUrl, model: info.defaultModel })
  }

  // 🔍 [语法] async 保存配置
  const handleSave = async () => {
    if (!form.name.trim()) return toast.error('请输入配置名称')
    setSaving(true)
    try {
      const body = {
        ...form,
        api_key: form.api_key.trim() || undefined,  // 🔍 [语法] 空字符串不更新
        api_key_env: envImportEnabled ? form.api_key_env.trim() : '',  // 🔍 [语法] 本地演示模式：从环境变量导入的变量名
        max_tokens: Number(form.max_tokens),
        temperature: Number(form.temperature),
      }
      if (editingName) await api.config.updateLlm(editingName, body)
      else await api.config.createLlm(body)
      toast.success(editingName ? '配置已更新' : '配置已创建')
      setShowEdit(false)
      await loadData()
    } catch (e) { toast.error('保存失败: ' + e.message) }
    finally { setSaving(false) }
  }

  // 🔍 [语法] 切换激活
  const handleActivate = async (name) => {
    try {
      await api.config.activateLlm(name)
      toast.success(`已切换到配置 '${name}'`)
      setActiveConfig(name)
    } catch (e) { toast.error('切换失败: ' + e.message) }
  }

  // 🔍 [语法] confirm 确认
  // 🔍 [作用] 防止误删
  const handleDelete = async (name) => {
    if (!confirm(`确定删除配置 '${name}'？`)) return
    try {
      await api.config.deleteLlm(name)
      toast.success('已删除')
      await loadData()
    } catch (e) { toast.error('删除失败') }
  }

  // 🔍 [语法] async 测试连接
  // 🔍 [作用] POST /api/config/llms/test
  const handleTest = async () => {
    // 🔍 [语法] 明文 Key 或 环境变量导入 任一即可
    if (!form.api_key.trim() && !(envImportEnabled && form.api_key_env.trim())) return toast.error('请填写 API Key 或从环境变量导入')
    setTesting(true); setTestResult(null)
    try {
      const result = await api.config.testLlm({
        provider: form.provider,
        api_key: form.api_key.trim(),
        api_key_env: envImportEnabled ? form.api_key_env.trim() : '',
        base_url: form.base_url,
        model: form.model,
      })
      setTestResult(result)
      toast[result.success ? 'success' : 'error'](result.success ? '连接成功！' : '连接失败: ' + (result.error || ''))
    } catch (e) { setTestResult({ success: false, error: e.message }) }
    finally { setTesting(false) }
  }

  if (loading) return <div className="p-6 text-center text-gray-400 pt-20">加载中...</div>

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* ========== 头部 ========== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-gray-600 text-sm mb-1 block">← 返回</button>
          <h1 className="text-2xl font-bold text-gray-800">⚙️ LLM API 配置</h1>
          <p className="text-gray-500 text-sm mt-1">管理最多 {MAX_CONFIGS} 个 API 配置，可在不同模型间快速切换</p>
        </div>
        {/* 🔍 [语法] 条件显示 */}
        {/* 🔍 [作用] 未达上限才能新增 */}
        {configs.length < MAX_CONFIGS && (
          <button onClick={openNew} className="bg-primary-600 text-white px-5 py-2.5 rounded-xl font-medium hover:bg-primary-700 transition-colors shadow-lg shadow-primary-200 flex items-center gap-2 text-sm">
            <span>+</span> 新增配置 ({configs.length}/{MAX_CONFIGS})
          </button>
        )}
      </div>

      {/* ========== 配置列表 ========== */}
      {configs.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-200">
          <div className="text-5xl mb-4">🔧</div>
          <p className="text-gray-500 mb-4">还没有配置任何 API</p>
          <button onClick={openNew} className="bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors">创建第一个配置 →</button>
        </div>
      ) : (
        <div className="space-y-3 mb-8">
          {configs.map((cfg) => {
            const isActive = cfg.is_active
            const info = PROVIDER_INFO[cfg.provider] || PROVIDER_INFO.custom
            return (
              // 🔍 [语法] 激活配置用 emerald 左边框
              <div key={cfg.name} className={`bg-white rounded-xl p-5 border-l-4 transition-all ${isActive ? 'border-l-emerald-500 shadow-sm bg-emerald-50/30' : 'border-l-gray-200'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-lg">{info.icon}</span>
                      <span className="font-semibold text-gray-800">{cfg.name}</span>
                      {isActive && <span className="text-[10px] bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">当前激活</span>}
                      {cfg.is_enabled && <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">已启用</span>}
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-400 flex-wrap">
                      <span>{info.name}</span>
                      <span className="font-mono">{cfg.model}</span>
                      <span className="font-mono text-[10px]">{cfg.base_url}</span>
                      {cfg.has_key && <span className="text-green-500">✅ 已填 Key{cfg.key_source === 'env' ? '（来源：环境变量）' : ''}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5 ml-3 shrink-0">
                    {!isActive && <button onClick={() => handleActivate(cfg.name)} className="text-xs bg-emerald-50 text-emerald-600 px-2.5 py-1.5 rounded-lg hover:bg-emerald-100 transition-colors">激活</button>}
                    {isActive && <span className="text-xs text-emerald-500 font-medium">使用中</span>}
                    <button onClick={() => openEdit(cfg)} className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1.5 rounded-lg hover:bg-gray-200 transition-colors">编辑</button>
                    {!isActive && <button onClick={() => handleDelete(cfg.name)} className="text-xs bg-gray-100 text-gray-400 px-2 py-1.5 rounded-lg hover:bg-red-50 hover:text-red-500 transition-colors">🗑</button>}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ========== 编辑 / 新建面板 ========== */}
      {showEdit && (
        <div className="bg-white rounded-2xl border border-gray-100 p-6 mb-8 animate-slide-up">
          <h2 className="font-semibold text-gray-800 mb-4">{editingName ? `✏️ 编辑「${editingName}」` : '🆕 新建配置'}</h2>

          {/* 配置名称 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1.5">配置名称 *</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              disabled={!!editingName}  // 🔍 [语法] !! 转 bool
              placeholder="如：default / deepseek / openai-gpt4"
              className={`w-full px-4 py-2.5 border border-gray-200 rounded-xl outline-none transition-all font-mono text-sm ${editingName ? 'bg-gray-50 text-gray-400' : 'focus:ring-2 focus:ring-primary-200 focus:border-primary-400'}`}
            />
          </div>

          {/* 提供商选择 */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1.5">提供商（选择后自动填充地址和默认模型）</label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(PROVIDER_INFO).map(([key, val]) => (
                <button
                  key={key}
                  onClick={() => handleProviderChange(key)}
                  className={`p-3 rounded-xl text-left border-2 transition-all ${form.provider === key ? 'border-primary-500 bg-primary-50 ring-1 ring-primary-300' : 'border-gray-100 hover:border-gray-200'}`}
                >
                  <span className="text-xl">{val.icon}</span>
                  <span className="block text-xs font-medium text-gray-700 mt-0.5">{val.name}</span>
                  <span className="text-[10px] text-gray-400 leading-tight">{val.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 选中提供商后的快捷信息 */}
          {(() => {
            const info = PROVIDER_INFO[form.provider]
            return info ? (
              <div className="bg-blue-50 rounded-xl p-3 mb-4 text-xs">
                <span className="text-blue-700 font-medium">{info.name} — {info.desc}</span>
                {info.getKeyUrl && (
                  <span className="block mt-0.5">🔑 获取API Key：<a href={info.getKeyUrl} target="_blank" rel="noreferrer" className="text-blue-600 underline">{info.getKeyUrl}</a></span>
                )}
              </div>
            ) : null
          })()}

          {/* API Key */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1.5">API Key *</label>
            <input
              type="password"
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              disabled={envImportEnabled}
              placeholder={editingName ? '留空不修改' : (envImportEnabled ? '已选择从环境变量导入' : '粘贴你的 API Key')}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl outline-none font-mono text-sm focus:ring-2 focus:ring-primary-200 focus:border-primary-400 transition-all disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          {/* 本地演示模式：从环境变量导入 Key（仅本地演示模式显示） */}
          {localMode && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200">
              <label className="flex items-center gap-2 cursor-pointer mb-2">
                <input
                  type="checkbox"
                  checked={envImportEnabled}
                  onChange={(e) => {
                    setEnvImportEnabled(e.target.checked)
                    setForm({ ...form, api_key_env: e.target.checked ? (form.api_key_env || envVars[0] || '') : '' })
                  }}
                  className="accent-emerald-600"
                />
                <span className="text-sm font-medium text-emerald-800">🌿 从环境变量导入 Key（本地演示模式）</span>
              </label>
              {envImportEnabled && (
                <div className="space-y-2">
                  <select
                    value={envVars.includes(form.api_key_env) ? form.api_key_env : '__custom__'}
                    onChange={(e) => setForm({ ...form, api_key_env: e.target.value === '__custom__' ? '' : e.target.value })}
                    className="w-full px-3 py-2 border border-emerald-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-emerald-200 font-mono"
                  >
                    {envVars.map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                    <option value="__custom__">手动输入其他变量名…</option>
                  </select>
                  {!envVars.includes(form.api_key_env) && (
                    <input
                      type="text"
                      value={form.api_key_env}
                      onChange={(e) => setForm({ ...form, api_key_env: e.target.value })}
                      placeholder="输入完整环境变量名"
                      className="w-full px-3 py-2 border border-emerald-300 rounded-lg text-sm bg-white outline-none focus:ring-2 focus:ring-emerald-200 font-mono"
                    />
                  )}
                  {envVars.length === 0 && (
                    <p className="text-[11px] text-amber-700">⚠️ 未检测到匹配 KEY/TOKEN/API/SECRET/PASSWORD 的环境变量；你可以手动输入完整变量名。</p>
                  )}
                  {envVars.length > 0 && !envVars.includes(form.api_key_env) && (
                    <p className="text-[11px] text-amber-700">⚠️ 自定义名称「{form.api_key_env}」不在已识别列表中；运行时会从 OS 环境读取，确保拼写正确。</p>
                  )}
                </div>
              )}
              <p className="text-[11px] text-emerald-600 mt-2">选择已有变量或手动输入变量名，系统运行时从该环境变量读取（避免密钥落库）。</p>
            </div>
          )}

          {/* Base URL */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1.5">Base URL（已自动填充）</label>
            <input
              type="text"
              value={form.base_url}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl outline-none font-mono text-xs focus:ring-2 focus:ring-primary-200 focus:border-primary-400 transition-all bg-gray-50"
            />
          </div>

          {/* Model */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-600 mb-1.5">Model *（用户自行填写）</label>
            <input
              type="text"
              value={form.model}
              onChange={(e) => setForm({ ...form, model: e.target.value })}
              placeholder="输入模型名称"
              className="w-full px-4 py-2.5 border border-gray-200 rounded-xl outline-none font-mono text-sm focus:ring-2 focus:ring-primary-200 focus:border-primary-400 transition-all"
            />
            {/* 常用模型快捷填入 */}
            {(() => {
              const info = PROVIDER_INFO[form.provider]
              if (info?.models?.length) return (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {info.models.map((m) => (
                    <button
                      key={m}
                      onClick={() => setForm({ ...form, model: m })}
                      className={`text-[11px] px-2 py-1 rounded-lg border transition-colors ${form.model === m ? 'bg-primary-50 border-primary-300 text-primary-700' : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'}`}
                    >{m}</button>
                  ))}
                </div>
              )
              return null
            })()}
          </div>

          {/* 参数滑块 */}
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Max Tokens ({form.max_tokens})</label>
              <input
                type="range"
                min={512} max={16384} step={512}
                value={form.max_tokens}
                onChange={(e) => setForm({ ...form, max_tokens: Number(e.target.value) })}
                className="w-full accent-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-1.5">Temperature ({form.temperature})</label>
              <input
                type="range" min={0} max={2} step={0.1}
                value={form.temperature}
                onChange={(e) => setForm({ ...form, temperature: Number(e.target.value) })}
                className="w-full accent-primary-500"
              />
            </div>
          </div>

          {/* 启用开关 */}
          <label className="flex items-center gap-3 mb-4 cursor-pointer" onClick={() => setForm({ ...form, is_enabled: !form.is_enabled })}>
            <div className={`w-12 h-7 rounded-full transition-colors ${form.is_enabled ? 'bg-primary-600' : 'bg-gray-300'}`}>
              <div className={`w-6 h-6 rounded-full bg-white shadow transition-transform ${form.is_enabled ? 'translate-x-[22px]' : 'translate-x-0.5'}`} />
            </div>
            <span className="text-sm text-gray-700">{form.is_enabled ? '🟢 已启用' : '⚫ 未启用'}</span>
          </label>

          {/* 操作按钮 */}
          <div className="flex gap-3">
            <button onClick={handleSave} disabled={saving} className="flex-1 bg-primary-600 text-white py-3 rounded-xl font-medium hover:bg-primary-700 disabled:opacity-50 transition-colors">{saving ? '⏳ 保存中...' : '💾 保存'}</button>
            <button onClick={handleTest} disabled={testing} className="px-8 py-3 rounded-xl font-medium border-2 border-amber-300 text-amber-700 hover:bg-amber-50 disabled:opacity-40 transition-all">{testing ? '⏳ 测试中...' : '🔍 测试连接'}</button>
            <button onClick={() => setShowEdit(false)} className="px-6 py-3 rounded-xl text-gray-500 hover:bg-gray-100 transition-colors">取消</button>
          </div>

          {/* 测试结果 */}
          {testResult && (
            <div className={`mt-4 rounded-xl p-4 ${testResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
              <span className={`font-semibold ${testResult.success ? 'text-green-700' : 'text-red-700'}`}>{testResult.success ? '✅ 成功' : '❌ 失败'}</span>
              {testResult.success && <p className="text-sm text-green-600 mt-1">⏱ {testResult.elapsed_ms}ms | 💬 {testResult.response?.slice(0, 100)}</p>}
              {!testResult.success && <p className="text-sm text-red-600 mt-1">{testResult.error}</p>}
            </div>
          )}
        </div>
      )}

      {/* 使用提示 */}
      <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5">
        <span className="font-semibold text-amber-800 block mb-2">💡 使用提示</span>
        <ul className="text-sm text-amber-700 space-y-1">
          <li>• 支持最多 <strong>{MAX_CONFIGS} 个</strong>配置，点击列表中的「激活」按钮切换当前使用的 API</li>
          <li>• 可以同时配置不同模型用于不同场景（如 DeepSeek 日常生成 + GPT 精修）</li>
          <li>• 未启用 LLM 时可免费使用内置模板引擎生成产品</li>
        </ul>
      </div>
    </div>
  )
}
