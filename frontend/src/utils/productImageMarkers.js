export function resolveProductImageMarkers(content, assets, token = '') {
  if (!content || !assets?.length) return content
  return content.replace(/\[插图\s*(\d+)[^\]]*\]/g, (marker, number) => {
    const asset = assets[Number(number) - 1]
    if (!asset) return marker
    const url = `${asset.url}${token ? `?access_token=${encodeURIComponent(token)}` : ''}`
    return `![${asset.filename || `插图 ${number}`}](${url})`
  })
}

export function restoreProductImageMarkers(content, assets) {
  if (!content || !assets?.length) return content
  let restored = content
  assets.forEach((asset, index) => {
    const escaped = asset.url.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    restored = restored.replace(
      new RegExp(`!\\[[^\\]]*\\]\\(${escaped}(?:\\?access_token=[^)]*)?\\)`, 'g'),
      `[插图 ${index + 1}: ${asset.filename}]`,
    )
  })
  return restored
}
