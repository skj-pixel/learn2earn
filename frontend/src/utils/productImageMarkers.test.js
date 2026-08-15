import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { resolveProductImageMarkers, restoreProductImageMarkers } from './productImageMarkers.js'

const assets = [{ url: '/api/assets/7', filename: '封面.png' }]

describe('product image anchors', () => {
  it('renders verbose legacy anchors as authenticated Markdown images', () => {
    const source = '[插图 1：书籍封面图，base64 编码——位置 block-1]'
    assert.equal(resolveProductImageMarkers(source, assets, 'a b'), '![封面.png](/api/assets/7?access_token=a%20b)')
  })

  it('restores rendered images to stable anchors before saving', () => {
    const rendered = resolveProductImageMarkers('[插图 1: 封面.png]', assets, 'secret')
    assert.equal(restoreProductImageMarkers(rendered, assets), '[插图 1: 封面.png]')
  })
})
