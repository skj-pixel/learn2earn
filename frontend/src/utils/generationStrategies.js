export function implementedStrategies(strategies = {}) {
  return {
    ...strategies,
    algorithms: (strategies.algorithms || []).filter((item) => item.implemented !== false),
    techniques: (strategies.techniques || []).filter((item) => item.implemented !== false),
  }
}

export function productPreference(strategies = {}, productType) {
  const preference = strategies.user_overrides?.[productType] || {}
  return {
    algorithms: preference.algorithms || [],
    techniques: preference.techniques || [],
    skill_keywords: preference.skill_keywords || [],
  }
}

export function strategySummary(override = {}) {
  const customized = ['algorithms', 'techniques', 'skill_keywords']
    .some((field) => (override[field] || []).length > 0)
  return customized ? '已自定义生成策略' : '使用默认生成策略'
}

export function selectedConflicts(selected = {}, compatibility = {}) {
  const selections = [selected, ...Object.values(selected.product_strategies || {})]
  const conflicts = []
  const seen = new Set()
  for (const selection of selections) {
    const groups = [
      ['generation', new Set([
        ...(selection.algorithms || []).map((value) => `algorithm:${value}`),
        ...(selection.skill_ids || []).map((value) => `skill:${value}`),
      ])],
      ['quality', new Set(selection.techniques || [])],
    ]
    for (const [group, values] of groups) {
      for (const row of compatibility[group] || []) {
        const key = `${group}:${row.left}:${row.right}`
        if (!seen.has(key) && row.status === 'conflict' && values.has(String(row.left)) && values.has(String(row.right))) {
          conflicts.push({ group, ...row })
          seen.add(key)
        }
      }
    }
  }
  return conflicts
}
