function blockText(block) {
  if (typeof block?.content === 'string') return block.content
  if (!Array.isArray(block?.content)) return ''
  return block.content.map((item) => item?.text || '').join('')
}

function paragraphBlock(text) {
  return { type: 'paragraph', content: [{ type: 'text', text, styles: {} }] }
}

export function repairFencedCodeBlocks(blocks) {
  if (!Array.isArray(blocks)) return blocks
  const repaired = []

  for (let index = 0; index < blocks.length; index += 1) {
    const block = blocks[index]
    const text = blockText(block)
    const opening = block?.type === 'paragraph' && text.match(/^\s*```([\w+-]*)\s*(?:\n([\s\S]*))?$/)
    if (!opening) {
      repaired.push({
        ...block,
        ...(Array.isArray(block?.children) && block.children.length
          ? { children: repairFencedCodeBlocks(block.children) }
          : {}),
      })
      continue
    }

    const language = opening[1] || 'text'
    const openingBody = opening[2] || ''
    const inlineClosingAt = openingBody.indexOf('```')
    if (inlineClosingAt >= 0) {
      repaired.push({
        type: 'codeBlock',
        props: { language },
        content: openingBody.slice(0, inlineClosingAt).replace(/^\n+|\n+$/g, ''),
      })
      const trailing = openingBody.slice(inlineClosingAt + 3).trim()
      if (trailing) repaired.push(paragraphBlock(trailing))
      continue
    }

    const codeLines = openingBody ? [openingBody] : []
    let closingFound = false
    let trailing = ''

    while (index + 1 < blocks.length) {
      index += 1
      const nextText = blockText(blocks[index])
      const closingAt = nextText.indexOf('```')
      if (closingAt >= 0) {
        codeLines.push(nextText.slice(0, closingAt))
        trailing = nextText.slice(closingAt + 3).trim()
        closingFound = true
        break
      }
      codeLines.push(nextText)
    }

    if (!closingFound) {
      repaired.push(block)
      for (const line of codeLines.slice(opening[2] ? 1 : 0)) repaired.push(paragraphBlock(line))
      continue
    }

    repaired.push({
      type: 'codeBlock',
      props: { language },
      content: codeLines.join('\n').replace(/^\n+|\n+$/g, ''),
    })
    if (trailing) repaired.push(paragraphBlock(trailing))
  }

  return repaired
}
