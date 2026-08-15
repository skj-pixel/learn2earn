// 🔍 [作用] 统一把后端 ISO 时间格式化为本地日期时间，空值显示明确占位。
export function formatDateTime(value) {
  // 🔍 [作用] 历史数据可能没有时间戳，避免显示 Invalid Date。
  if (!value) return '时间未知'
  // 🔍 [作用] 后端 SQLite 存储无时区本地时间；JS new Date 会把无时区字符串视为本地时间，
  //          所以这里 toLocaleString 不会重复加 8 小时，与北京时钟一致。
  const date = new Date(value)
  // 🔍 [作用] 非法时间字符串安全降级，不让整个 React 组件报错。
  if (Number.isNaN(date.getTime())) return '时间未知'
  // 🔍 [作用] 固定为易扫描的年月日和 24 小时时间。
  return date.toLocaleString('zh-CN', { hour12: false })
}
